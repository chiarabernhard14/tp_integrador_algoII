from .RecorridosV import PathFinderV, RouteFinderV


EPSILON = 1e-9
ALGORITMOS_DISTANCIA = {
    "a_estrella": PathFinderV.a_estrella,
    "dijkstra": PathFinderV.dijkstra,
}


def _id(picker):
    return str(picker.id).upper()


def _pos(picker):
    return tuple(picker.pos if hasattr(picker, "pos") else picker.posicion)


def _capacidad(picker):
    if hasattr(picker, "capacidad"):
        return float(picker.capacidad)
    if hasattr(picker, "capacidad_carga_kg"):
        return float(picker.capacidad_carga_kg)
    return float(picker.entidad.capacidad_carga_kg)


def _lineas_wave(wave):
    """Consolida productos repetidos y conserva el orden de la wave."""
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
            cantidad = item.get("quantity", item.get("cantidad"))
        else:
            producto = getattr(item, "product", getattr(item, "producto", None))
            cantidad = getattr(item, "quantity", getattr(item, "cantidad", None))
        if producto is None or not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
            raise ValueError("Cada línea de wave requiere un producto y una cantidad positiva.")
        if producto.id not in lineas:
            lineas[producto.id] = [producto, 0]
        lineas[producto.id][1] += cantidad
    return wave_id, lineas


class Asignador:
    """Asigna como máximo un viaje por picker libre en cada ronda.

    Backtracking explora las asignaciones de las unidades pendientes. Se prioriza
    el orden de la wave y, entre las asignaciones equivalentes, se minimiza el
    mayor recorrido estimado; luego, la distancia total. Las restricciones de
    peso, acceso, regreso y capacidad de las zonas se comprueban antes de elegir.
    """

    def __init__(
        self, nav, zonas, waves, estrategia="cercania",
        algoritmo_asignacion="a_estrella",
    ):
        self.nav = nav
        self.estrategia = estrategia
        self.configurar_algoritmo(algoritmo_asignacion)
        self.zonas = {}
        for zona in zonas.values():
            celdas = set()
            for x, y in zona.cells():
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    celda = (x + dx, y + dy)
                    if celda in nav.grafo:
                        celdas.add(celda)
            capacidad = float(zona.peso_max_kg)
            self.zonas[zona.id] = {
                "restante": capacidad,
                "restante_inicial": capacidad,
                "celdas": celdas,
            }

        self.waves = []
        self.productos = {}
        self.accesos = {}
        self.wave_de_trabajo = {}
        self.peso_de_trabajo = {}
        self.zona_de_trabajo = {}
        self.imposibles = []
        self._cache_recorrido = {}

        for indice, wave in enumerate(waves, 1):
            wave_id, lineas = _lineas_wave(wave)
            registro = {
                "id": str(wave_id if wave_id is not None else indice),
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
                acceso = producto.acceso
                if acceso is None:
                    accesos = nav.accesos(producto.ubicacion[0], producto.ubicacion[1])
                    acceso = min(accesos) if accesos else None
                self.accesos[producto_id] = tuple(acceso) if acceso is not None else None
            self.waves.append(registro)

    def configurar_algoritmo(self, algoritmo):
        if algoritmo not in ALGORITMOS_DISTANCIA:
            raise ValueError(
                f"Algoritmo de asignación desconocido: {algoritmo}. "
                f"Opciones: {', '.join(ALGORITMOS_DISTANCIA)}."
            )
        self.algoritmo_asignacion = algoritmo
        self._buscador = ALGORITMOS_DISTANCIA[algoritmo]

    def _buscar_con_cache(self, grafo, origen, destino):
        origen, destino = tuple(origen), tuple(destino)
        key = (origen, destino)
        if key not in self._cache_recorrido:
            if origen not in grafo or destino not in grafo:
                self._cache_recorrido[key] = (float("inf"), [], 0)
            else:
                self._cache_recorrido[key] = self._buscador(grafo, origen, destino)
        return self._cache_recorrido[key]

    def _recorrido_hasta_zona(self, picker, producto_ids, orden, zona_id):
        paradas = []
        for producto_id in orden:
            acceso = self.accesos.get(producto_id)
            if producto_id in producto_ids and acceso is not None and acceso not in paradas:
                paradas.append(acceso)

        zona = self.zonas[zona_id]
        inicio = _pos(picker)
        if self.estrategia == "cercania":
            distancias = []
            for celda in zona["celdas"]:
                try:
                    recorrido = RouteFinderV.cercania(
                        self.nav.grafo,
                        inicio,
                        paradas,
                        buscador=self._buscar_con_cache,
                        destino_final=celda,
                    )
                except ValueError:
                    continue
                distancias.append(recorrido["total_distance"])
            return min(distancias) if distancias else None

        actual = inicio
        distancia_total = 0.0
        for parada in paradas:
            distancia, _, _ = self._buscar_con_cache(
                self.nav.grafo, actual, parada
            )
            if distancia == float("inf"):
                return None
            distancia_total += distancia
            actual = parada

        vueltas = [
            self._buscar_con_cache(self.nav.grafo, actual, celda)[0]
            for celda in zona["celdas"]
        ]
        vueltas = [distancia for distancia in vueltas if distancia != float("inf")]
        return distancia_total + min(vueltas) if vueltas else None

    def _opciones_de_viaje(self, picker, productos, peso, wave):
        opciones = []
        for zona_id in sorted(self.zonas):
            zona = self.zonas[zona_id]
            if zona["restante"] + EPSILON < peso:
                continue
            distancia = self._recorrido_hasta_zona(
                picker, set(productos), wave["orden"], zona_id
            )
            if distancia is not None:
                opciones.append((distancia, zona_id))
        return opciones

    def _elegir_zonas(self, activos, opciones, cargas):
        mejor = None
        usados = {zona_id: 0.0 for zona_id in self.zonas}
        elegidos = {}

        def buscar(pos):
            nonlocal mejor
            if pos == len(activos):
                ds = [elegidos[i][0] for i in activos]
                clave = (max(ds, default=0), sum(ds), tuple((self._ids[i], elegidos[i][1]) for i in activos))
                if mejor is None or clave < mejor[0]:
                    mejor = (clave, dict(elegidos))
                return

            i = activos[pos]
            for distancia, zona_id in opciones[i]:
                if usados[zona_id] + cargas[i] > self.zonas[zona_id]["restante"] + EPSILON:
                    continue
                if mejor is not None and max(max((elegidos[j][0] for j in activos[:pos]), default=0), distancia) > mejor[0][0]:
                    continue
                usados[zona_id] += cargas[i]
                elegidos[i] = (distancia, zona_id)
                buscar(pos + 1)
                usados[zona_id] -= cargas[i]
                del elegidos[i]

        buscar(0)
        return mejor

    def _resolver_ronda(self, wave, pickers):
        self._pickers = list(pickers)
        self._ids = [_id(p) for p in pickers]
        unidades = []
        for producto_id in wave["orden"]:
            unidades.extend([producto_id] * wave["pendiente"].get(producto_id, 0))

        asignados = [[] for _ in pickers]
        cargas = [0.0 for _ in pickers]
        bits = []
        mejor = None

        def buscar(k, primer_picker=0):
            nonlocal mejor
            if mejor is not None and tuple(bits) < mejor[0][:len(bits)]:
                return
            if k == len(unidades):
                activos = [i for i, productos in enumerate(asignados) if productos]
                opciones = {
                    i: self._opciones_de_viaje(pickers[i], asignados[i], cargas[i], wave)
                    for i in activos
                }
                if any(not opciones[i] for i in activos):
                    return
                zonas = self._elegir_zonas(activos, opciones, cargas)
                if zonas is None:
                    return
                vector = tuple(bits)
                if mejor is None or vector > mejor[0] or (vector == mejor[0] and zonas[0] < mejor[1]):
                    mejor = (vector, zonas[0], [list(x) for x in asignados], list(cargas), zonas[1])
                return

            producto_id = unidades[k]
            peso = self.productos[producto_id].peso_kg
            mismo_producto_despues = (
                k + 1 < len(unidades) and unidades[k + 1] == producto_id
            )
            if self.accesos.get(producto_id) is not None:
                for i in range(primer_picker, len(pickers)):
                    picker = pickers[i]
                    if cargas[i] + peso > _capacidad(picker) + EPSILON:
                        continue
                    cargas[i] += peso
                    asignados[i].append(producto_id)
                    bits.append(1)
                    buscar(k + 1, i if mismo_producto_despues else 0)
                    bits.pop()
                    asignados[i].pop()
                    cargas[i] -= peso

            codigo_omitir = len(pickers)
            if codigo_omitir >= primer_picker:
                bits.append(0)
                buscar(k + 1, codigo_omitir if mismo_producto_despues else 0)
                bits.pop()

        buscar(0)
        if mejor is None:
            return []

        _, _, productos_por_picker, pesos, zonas = mejor
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

