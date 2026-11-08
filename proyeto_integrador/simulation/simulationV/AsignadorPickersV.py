from .PlanificadorViajesV import (
    ALGORITMOS_CAMINO,
    ESTRATEGIAS,
    PlanificadorViajesV,
)

EPSILON = 1e-9


def _id(picker):
    return str(picker.id).upper()


def _capacidad(picker):
    if hasattr(picker, "capacidad"):
        return float(picker.capacidad)
    if hasattr(picker, "capacidad_carga_kg"):
        return float(picker.capacidad_carga_kg)
    return float(picker.entidad.capacidad_carga_kg)


def _lineas_wave(wave, productos):
    """Lee una wave, resuelve sus productos y consolida repetidos."""
    if isinstance(wave, dict):
        items = wave.get("products", wave.get("productos"))
        wave_id = wave.get("id")
    else:
        items = getattr(wave, "products", getattr(wave, "productos", None))
        wave_id = getattr(wave, "id", None)
    if items is None:
        raise TypeError("La wave debe exponer products o productos.")
    lineas = {}
    for item in items:
        if isinstance(item, dict):
            producto = item.get("product", item.get("producto"))
            producto_id = item.get("producto_id")
            cantidad = item.get("quantity", item.get("cantidad"))
        else:
            producto = getattr(item, "product", getattr(item, "producto", None))
            producto_id = getattr(item, "producto_id", None)
            cantidad = getattr(item, "quantity", getattr(item, "cantidad", None))
        if producto is None and producto_id is not None:
            producto = productos.get(str(producto_id).upper())
        if producto is None:
            raise ValueError(
                f"La wave referencia un producto inexistente: {producto_id}."
            )
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
            raise ValueError("Cada línea de wave requiere una cantidad positiva.")
        if producto.id not in lineas:
            lineas[producto.id] = [producto, 0]
        lineas[producto.id][1] += cantidad
    return wave_id, lineas


class Asignador:
    """Asigna como máximo un viaje por picker libre en cada ronda.

    Usa backtracking cuando (pickers + 1) ** unidades no supera el umbral
    configurado y una asignación voraz determinista en rondas más grandes.
    """

    def __init__(
        self, nav, zonas, waves, productos, racks,
        algoritmo_camino="a_estrella", estrategia="cercania",
        max_combinaciones_exactas=5000,
    ):
        self.nav = nav
        self.planificador = PlanificadorViajesV(
            nav,
            productos,
            racks,
            algoritmo_camino=algoritmo_camino,
            estrategia=estrategia,
        )
        self.evaluador_viaje = self.planificador.evaluar_viaje
        self.max_combinaciones_exactas = max_combinaciones_exactas
        self.zonas = {}
        for zona in zonas.values():
            capacidad = float(zona.peso_max_kg)
            self.zonas[zona.id] = {
                "restante": capacidad,
                "restante_inicial": capacidad,
                "celdas": set(nav.despacho_por_zona.get(zona.id, ())),
            }

        self.waves = []
        self.productos = {}
        self.accesos = {}
        self.wave_de_trabajo = {}
        self.peso_de_trabajo = {}
        self.zona_de_trabajo = {}
        self.imposibles = []
        self._estado_busqueda_ronda = None

        ids_waves = set()
        for indice, wave in enumerate(waves, 1):
            wave_id, lineas = _lineas_wave(wave, productos)
            id_wave = str(wave_id if wave_id is not None else indice)
            if id_wave in ids_waves:
                raise ValueError(f"La wave {id_wave} está repetida.")
            ids_waves.add(id_wave)
            registro = {
                "id": id_wave,
                "orden": list(lineas),
                "solicitados": {producto_id: cantidad for producto_id, (_, cantidad) in lineas.items()},
                "pendiente": {producto_id: cantidad for producto_id, (_, cantidad) in lineas.items()},
                "trabajos": set(),
                "numero": 0,
                "estado": "CREADA",
                "completada": False,
                "incompleta": False,
            }
            for producto_id, (producto, _) in lineas.items():
                self.productos[producto_id] = producto
                if producto.acceso is None:
                    accesos = nav.accesos(producto.ubicacion[0], producto.ubicacion[1])
                    producto.acceso = min(accesos) if accesos else None
                self.accesos[producto_id] = producto.acceso
            self.waves.append(registro)

    def _opciones_de_viaje(self, picker, productos, peso, wave):
        opciones = []
        clave = (picker.id, frozenset(productos))
        planes = self._cache_planes.get(clave)
        if planes is None:
            planes = {}
            for zona_id in sorted(self.zonas):
                zona = self.zonas[zona_id]
                plan = self.evaluador_viaje(
                    picker,
                    set(productos),
                    wave["orden"],
                    zona_id,
                    zona["celdas"],
                    self.accesos,
                )
                if plan is not None:
                    planes[zona_id] = plan
            self._cache_planes[clave] = planes

        for zona_id in sorted(self.zonas):
            zona = self.zonas[zona_id]
            if zona["restante"] + EPSILON < peso:
                continue
            plan = planes.get(zona_id)
            if plan is not None:
                distancia = plan["total_distance"]
                opciones.append((distancia, zona_id))
        return opciones, {zona_id: planes[zona_id] for _, zona_id in opciones}

    def _elegir_zonas(self, activos, opciones, cargas):
        if len(activos) > 8:
            return self._elegir_zonas_voraz(activos, opciones, cargas)

        mejor = None
        estado = {
            "activos": activos,
            "opciones": opciones,
            "cargas": cargas,
            "usados": {zona_id: 0.0 for zona_id in self.zonas},
            "elegidos": {},
            "mejor": mejor,
        }
        self._estado_busqueda_zonas = estado
        try:
            self._buscar_zonas(0)
        finally:
            self._estado_busqueda_zonas = None
        return estado["mejor"]

    def _buscar_zonas(self, pos):
        estado = self._estado_busqueda_zonas
        activos = estado["activos"]
        elegidos = estado["elegidos"]
        if pos == len(activos):
            distancias = [elegidos[i][0] for i in activos]
            clave = (
                max(distancias, default=0),
                sum(distancias),
                tuple((self._ids[i], elegidos[i][1]) for i in activos),
            )
            mejor = estado["mejor"]
            if mejor is None or clave < mejor[0]:
                estado["mejor"] = (clave, dict(elegidos))
            return

        indice = activos[pos]
        for distancia, zona_id in estado["opciones"][indice]:
            if (
                estado["usados"][zona_id] + estado["cargas"][indice]
                > self.zonas[zona_id]["restante"] + EPSILON
            ):
                continue
            distancia_maxima_actual = max(
                (elegidos[j][0] for j in activos[:pos]), default=0
            )
            mejor = estado["mejor"]
            if (
                mejor is not None
                and max(distancia_maxima_actual, distancia) > mejor[0][0]
            ):
                continue
            estado["usados"][zona_id] += estado["cargas"][indice]
            elegidos[indice] = (distancia, zona_id)
            self._buscar_zonas(pos + 1)
            estado["usados"][zona_id] -= estado["cargas"][indice]
            del elegidos[indice]

    def _elegir_zonas_voraz(self, activos, opciones, cargas):
        orden = sorted((-cargas[i], self._ids[i], i) for i in activos)
        usados = {zona_id: 0.0 for zona_id in self.zonas}
        elegidos = {}
        for _, _, indice in orden:
            factibles = sorted(opciones[indice], key=lambda opcion: (opcion[0], opcion[1]))
            for distancia, zona_id in factibles:
                if (
                    usados[zona_id] + cargas[indice]
                    <= self.zonas[zona_id]["restante"] + EPSILON
                ):
                    usados[zona_id] += cargas[indice]
                    elegidos[indice] = (distancia, zona_id)
                    break
            else:
                return None

        distancias = [elegidos[i][0] for i in activos]
        clave = (
            max(distancias, default=0),
            sum(distancias),
            tuple((self._ids[i], elegidos[i][1]) for i in activos),
        )
        return clave, elegidos

    def _resolver_ronda(self, wave, pickers):
        self._cache_planes = {}
        self._pickers = list(pickers)
        self._ids = [_id(p) for p in pickers]
        unidades = []
        for producto_id in wave["orden"]:
            unidades.extend([producto_id] * wave["pendiente"].get(producto_id, 0))

        # La búsqueda exacta crece exponencialmente con la cantidad de unidades.
        # Para rondas grandes usamos una asignación voraz determinista: la consigna
        # pide una estrategia justificada, pero no una solución global óptima.
        combinaciones = 1
        for _ in unidades:
            combinaciones *= len(pickers) + 1
            if combinaciones > self.max_combinaciones_exactas:
                break
        if combinaciones > self.max_combinaciones_exactas:
            return self._resolver_ronda_voraz(wave, pickers, unidades)

        self._estado_busqueda_ronda = {
            "wave": wave,
            "pickers": pickers,
            "unidades": unidades,
            "asignados": [[] for _ in pickers],
            "cargas": [0.0 for _ in pickers],
            "bits": [],
            "mejor": None,
        }
        try:
            self._buscar_asignaciones(0)
        finally:
            estado = self._estado_busqueda_ronda
            self._estado_busqueda_ronda = None
        mejor = estado["mejor"]
        if mejor is None:
            return []

        return self._crear_trabajos(wave, pickers, mejor)

    def _buscar_asignaciones(self, indice_unidad, primer_picker=0):
        estado = self._estado_busqueda_ronda
        pickers = estado["pickers"]
        unidades = estado["unidades"]
        asignados = estado["asignados"]
        cargas = estado["cargas"]
        bits = estado["bits"]
        mejor = estado["mejor"]

        if mejor is not None and tuple(bits) < mejor[0][:len(bits)]:
            return
        if indice_unidad == len(unidades):
            activos = [i for i, productos in enumerate(asignados) if productos]
            evaluaciones = {
                i: self._opciones_de_viaje(
                    pickers[i], asignados[i], cargas[i], estado["wave"]
                )
                for i in activos
            }
            opciones = {i: evaluaciones[i][0] for i in activos}
            if any(not opciones[i] for i in activos):
                return
            zonas = self._elegir_zonas(activos, opciones, cargas)
            if zonas is None:
                return
            vector = tuple(bits)
            if (
                mejor is None
                or vector > mejor[0]
                or (vector == mejor[0] and zonas[0] < mejor[1])
            ):
                planes = {i: evaluaciones[i][1] for i in activos}
                estado["mejor"] = (
                    vector,
                    zonas[0],
                    [list(productos) for productos in asignados],
                    list(cargas),
                    zonas[1],
                    planes,
                )
            return

        producto_id = unidades[indice_unidad]
        peso = self.productos[producto_id].peso_kg
        mismo_producto_despues = (
            indice_unidad + 1 < len(unidades)
            and unidades[indice_unidad + 1] == producto_id
        )
        if self.accesos.get(producto_id) is not None:
            for i in range(primer_picker, len(pickers)):
                if cargas[i] + peso > _capacidad(pickers[i]) + EPSILON:
                    continue
                cargas[i] += peso
                asignados[i].append(producto_id)
                bits.append(1)
                self._buscar_asignaciones(
                    indice_unidad + 1, i if mismo_producto_despues else 0
                )
                bits.pop()
                asignados[i].pop()
                cargas[i] -= peso

        codigo_omitir = len(pickers)
        if codigo_omitir >= primer_picker:
            bits.append(0)
            self._buscar_asignaciones(
                indice_unidad + 1,
                codigo_omitir if mismo_producto_despues else 0,
            )
            bits.pop()

    def _crear_trabajos(self, wave, pickers, mejor):
        _, _, productos_por_picker, pesos, zonas, planes = mejor
        trabajos = []
        for i, productos in enumerate(productos_por_picker):
            if not productos:
                continue
            cantidades = {}
            for producto_id in productos:
                cantidades[producto_id] = cantidades.get(producto_id, 0) + 1
                wave["pendiente"][producto_id] -= 1
                if wave["pendiente"][producto_id] == 0:
                    del wave["pendiente"][producto_id]

            zona_id = zonas[i][1]
            self.zonas[zona_id]["restante"] -= pesos[i]
            wave["numero"] += 1
            trabajo = {
                "id": f"{wave['id']}:T{wave['numero']}",
                "wave_id": wave["id"],
                "picker": self._ids[i],
                "zona": zona_id,
                "peso": pesos[i],
                "distancia_estimada": planes[i][zona_id]["total_distance"],
                "orden_productos": list(planes[i][zona_id]["orden_productos"]),
                "productos": [
                    {"producto_id": pid, "cantidad": cantidad, "acceso": self.accesos[pid]}
                    for pid, cantidad in cantidades.items()
                ],
            }
            wave["trabajos"].add(trabajo["id"])
            wave["estado"] = "EN_PROCESO"
            self.wave_de_trabajo[trabajo["id"]] = wave
            self.peso_de_trabajo[trabajo["id"]] = pesos[i]
            self.zona_de_trabajo[trabajo["id"]] = zona_id
            trabajos.append(trabajo)
        return trabajos

    def _resolver_ronda_voraz(self, wave, pickers, unidades):
        """Asigna en orden de wave, minimizando distancia entre opciones factibles.

        El desempate por zonas e identificador hace determinista el resultado.
        """
        asignados = [[] for _ in pickers]
        cargas = [0.0 for _ in pickers]
        bits = []
        productos_sin_lugar = set()

        for producto_id in unidades:
            if producto_id in productos_sin_lugar:
                bits.append(0)
                continue
            peso = self.productos[producto_id].peso_kg
            mejor_paso = None

            for i, picker in enumerate(pickers):
                if cargas[i] + peso > _capacidad(picker) + EPSILON:
                    continue

                asignados[i].append(producto_id)
                cargas[i] += peso
                activos = [j for j, productos in enumerate(asignados) if productos]
                evaluaciones = {
                    j: self._opciones_de_viaje(
                        pickers[j], asignados[j], cargas[j], wave,
                    )
                    for j in activos
                }
                opciones = {j: evaluaciones[j][0] for j in activos}
                zonas = None
                if all(opciones[j] for j in activos):
                    zonas = self._elegir_zonas(activos, opciones, cargas)

                if zonas is not None:
                    clave = (
                        zonas[0],
                        tuple((self._ids[j], zonas[1][j][1]) for j in activos),
                        self._ids[i],
                    )
                    if mejor_paso is None or clave < mejor_paso[0]:
                        mejor_paso = (
                            clave,
                            i,
                        )

                cargas[i] -= peso
                asignados[i].pop()

            if mejor_paso is None:
                productos_sin_lugar.add(producto_id)
                bits.append(0)
                continue

            bits.append(1)
            _, i = mejor_paso
            asignados[i].append(producto_id)
            cargas[i] += peso

        activos = [i for i, productos in enumerate(asignados) if productos]
        evaluaciones = {
            i: self._opciones_de_viaje(
                pickers[i], asignados[i], cargas[i], wave
            )
            for i in activos
        }
        opciones = {i: evaluaciones[i][0] for i in activos}
        zonas = self._elegir_zonas(activos, opciones, cargas) if activos else None
        if zonas is None:
            return []
        planes = {i: evaluaciones[i][1] for i in activos}
        mejor = (
            tuple(bits),
            zonas[0],
            [list(productos) for productos in asignados],
            list(cargas),
            zonas[1],
            planes,
        )
        return self._crear_trabajos(wave, pickers, mejor)

    def asignar(self, libres):
        """Asigna dinámicamente un viaje a cada picker libre, como máximo."""
        candidatos = sorted(list(libres), key=_id)
        trabajos = []
        for wave in self.waves:
            if not candidatos:
                break
            if not wave["pendiente"]:
                continue
            asignados = self._resolver_ronda(wave, candidatos)
            trabajos.extend(asignados)
            ocupados = {trabajo["picker"] for trabajo in asignados}
            candidatos = [p for p in candidatos if _id(p) not in ocupados]
        if not trabajos and self.hay_pendiente() and not self.hay_trabajos_en_curso():
            self.descartar_imposibles(candidatos)
        return trabajos

    def trabajo_entregado(self, trabajo_id):
        wave = self.wave_de_trabajo.pop(trabajo_id)
        wave["trabajos"].discard(trabajo_id)
        peso = self.peso_de_trabajo.pop(trabajo_id, 0.0)
        # La capacidad de despacho vuelve a estar disponible al entregar el viaje.
        # Aquí se busca la zona del trabajo desde el registro guardado al asignarlo.
        zona_id = self.zona_de_trabajo.pop(trabajo_id, None)
        if zona_id is not None:
            self.zonas[zona_id]["restante"] += peso
        if not wave["pendiente"] and not wave["trabajos"]:
            wave["completada"] = True
            wave["estado"] = "COMPLETADA"
        return wave["completada"]

    def restaurar_estado(self, estados_waves, trabajos_activos):
        """Restaura pendientes y reservas desde una partida guardada."""
        por_id = {wave["id"]: wave for wave in self.waves}
        for zona in self.zonas.values():
            zona["restante"] = zona["restante_inicial"]
        for wave in self.waves:
            wave["trabajos"].clear()
            wave["estado"] = "CREADA"
            wave["completada"] = False
        self.wave_de_trabajo.clear()
        self.peso_de_trabajo.clear()
        self.zona_de_trabajo.clear()

        for estado in estados_waves:
            wave = por_id.get(estado["id"])
            if wave is None:
                continue
            wave["pendiente"] = {
                pid: cantidad for pid, cantidad in estado.get("pendiente", {}).items()
                if cantidad > 0
            }
            wave["completada"] = estado.get("completada", False)
            wave["incompleta"] = estado.get("incompleta", False)
            wave["estado"] = estado.get("estado", "CREADA")
            wave["numero"] = estado.get("numero", 0)

        for trabajo in trabajos_activos:
            wave = por_id[trabajo["wave_id"]]
            wave["trabajos"].add(trabajo["id"])
            wave["estado"] = "EN_PROCESO"
            self.wave_de_trabajo[trabajo["id"]] = wave
            self.peso_de_trabajo[trabajo["id"]] = trabajo["peso"]
            self.zona_de_trabajo[trabajo["id"]] = trabajo["zona"]
            self.zonas[trabajo["zona"]]["restante"] -= trabajo["peso"]

    def hay_pendiente(self):
        return any(wave["pendiente"] for wave in self.waves)

    def hay_trabajos_en_curso(self):
        return any(wave["trabajos"] for wave in self.waves)

    def descartar_imposibles(self, libres):
        for wave in self.waves:
            for producto_id, cantidad in wave["pendiente"].items():
                self.imposibles.append({
                    "wave_id": wave["id"],
                    "producto_id": producto_id,
                    "cantidad": cantidad,
                    "motivo": "ningún picker libre puede completar un viaje factible",
                })
            if wave["pendiente"]:
                wave["incompleta"] = True
                wave["estado"] = "INCOMPLETA"
                wave["pendiente"] = {}

