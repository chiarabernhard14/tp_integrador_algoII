from .NavegationV import Navegacion
from .CargadorV import cargar_warehouse
from .RecorridosV import RouteFinderV
from .AsignadorPickersV import Asignador

LIMITE_BLOQUEO = 20

# Estrategias de recorrido disponibles para ordenar las visitas de una wave.
ESTRATEGIAS = {
    "orden": RouteFinderV.orden_pedidos,
    "cercania": RouteFinderV.cercania,
}


def _id_picker(picker):
    return picker.id


def _clave_turno(picker):
    """Mueven primero los pickers con trabajo; los que deambulan, después."""
    return (picker.estado == "deambulando", picker.id)


class EstadoPicker:

    def __init__(self, picker):
        self.entidad = picker
        self.id = picker.id

        self.anterior = None
        self.pendientes = []
        self.recogidos = []
        self.objetivo = None
        self.destinos = set()
        self.estado = "disponible"
        self.trail = [picker.posicion]

        # Trabajo/viaje que está ejecutando el picker.
        self.wave = None
        self.waves_hechas = []

        # Se conserva para compatibilidad con partidas anteriores.
        self.waves_asignadas = []

        # Veces que se salteó la próxima tarea del orden planificado.
        self.saltos = 0

        # Sin trabajo: próximo punto de patrulla, y pasos dados mientras tenía
        # trabajo (para medir el recorrido sin contar la deambulación).
        self.indice_punto = 0
        self.pasos_trabajo = 0

    @property
    def pos(self):
        return self.entidad.posicion

    @pos.setter
    def pos(self, valor):
        self.entidad.posicion = valor

    @property
    def ruta(self):
        return self.entidad.current_route

    @ruta.setter
    def ruta(self, valor):
        self.entidad.current_route = valor


class Simulacion:
    """Simula la ejecución de waves por pickers.

    - Recibe waves armadas, sin picker asignado. El Asignador distribuye viajes
      entre los pickers libres y vuelve a decidir cuando alguno entrega.
    - Una wave puede generar varios viajes y ser atendida por varios pickers.
      Cada viaje termina en la zona de despacho que reservó el asignador.
    - El orden en que el picker visita los productos de su wave lo decide la
      estrategia de recorrido elegida ("orden" o "cercania", ver ESTRATEGIAS).
      Si la próxima tarea del orden está bloqueada por otro picker, salta a
      la siguiente alcanzable y suma un salto (picker.saltos). Con
      permitir_saltos=False el picker espera esa tarea: el recorrido
      ejecutado es exactamente el planificado.
    - Un picker sin más trabajo no se detiene: pasa a "deambulando" y recorre
      los puntos de patrulla (intersecciones libres), esquivando a los demás
      con las mismas reglas de movimiento; los que trabajan tienen prioridad.
      "terminada" indica que el trabajo terminó: ejecutar() se detiene ahí y
      tick_trabajo / pasos_trabajo miden solo el trabajo. Si se sigue
      llamando a paso(), los pickers siguen moviéndose.
    - Las waves llegan ya validadas (productos existentes y con stock): la
      simulación no las controla.
    - El stock se descuenta cuando el picker recoge el producto.
    """

    def __init__(
        self, datos, waves=None, estrategia="cercania", permitir_saltos=True,
        algoritmo_asignacion="a_estrella",
    ):
        if estrategia not in ESTRATEGIAS:
            raise ValueError(
                f"Estrategia desconocida: {estrategia}. "
                f"Opciones: {', '.join(ESTRATEGIAS)}."
            )

        self.datos = datos
        self.waves_entrada = waves
        self.estrategia = estrategia
        self.permitir_saltos = permitir_saltos
        self.algoritmo_asignacion = algoritmo_asignacion

        self.reiniciar()

    def reiniciar(self):
        self.tick = 0
        self.terminada = False
        self.tick_trabajo = None
        self.log = []

        self.hubo_avance = False
        self.ticks_sin_avance = 0
        self.ticks_espera = 0

        # Se construye el Warehouse una sola vez.
        self.warehouse = cargar_warehouse(self.datos)

        # Navegación utiliza ese mismo Warehouse.
        self.nav = Navegacion(self.warehouse)

        self.productos = self.warehouse.productos

        self.pickers = []
        self.pickers_por_id = {}

        for entidad in self.warehouse.pickers.values():
            picker = EstadoPicker(entidad)
            self.pickers.append(picker)
            self.pickers_por_id[picker.id] = picker

        self.waves = []
        self._cargar_waves()

        self.puntos_patrulla = self._calcular_puntos_patrulla()

        for numero, picker in enumerate(sorted(self.pickers, key=_id_picker)):
            if self.puntos_patrulla and self.pickers:
                picker.indice_punto = (
                    numero * len(self.puntos_patrulla) // len(self.pickers)
                )

            picker.estado = "deambulando"

        self._asignar_trabajos()

        self._registrar("Simulación inicializada.")

    # ---------- carga de waves recibidas ----------

    def _generar_waves_proyecto(self):
        """Llama al generador existente con pedidos y productos del Warehouse."""
        from .GeneradorWaves import generar_waves

        pedidos = list(self.warehouse.pedidos.values())
        configuracion = self.datos.get("configuracion", {})
        max_pedidos = configuracion.get("wave_max_pedidos", 3)
        max_unidades = configuracion.get("wave_max_productos", 15)

        # En la configuración del proyecto, cero significa "sin límite".
        # Las etapas K-means/construcción requieren límites positivos.
        if max_pedidos == 0:
            max_pedidos = max(1, len(pedidos))
        if max_unidades == 0:
            demanda = sum(item.cantidad for pedido in pedidos for item in pedido.items)
            max_unidades = max(1, demanda)

        return generar_waves(pedidos, max_pedidos, max_unidades)

    def _cargar_waves(self):
        """Carga waves armadas; el asignador decide los pickers en cada ronda."""

        if self.waves_entrada is None:
            self.waves_entrada = self._generar_waves_proyecto()

        if not isinstance(self.waves_entrada, list):
            raise TypeError("waves debe ser una lista de waves.")

        normalizadas = []
        ids_vistos = set()
        for indice, wave in enumerate(self.waves_entrada, 1):
            id_wave, productos = self._leer_wave(wave, indice)
            if id_wave in ids_vistos:
                raise ValueError(f"La wave {id_wave} está repetida.")
            ids_vistos.add(id_wave)
            normalizadas.append({"id": id_wave, "products": productos})

        self.asignador = Asignador(
            self.nav, self.warehouse.zonas_despacho, normalizadas,
            estrategia=self.estrategia,
            algoritmo_asignacion=self.algoritmo_asignacion,
        )
        self.waves = self.asignador.waves

    def _leer_wave(self, wave, indice):
        """Acepta la Wave de la compañera y formatos simples de la interfaz."""

        if isinstance(wave, dict):
            id_wave = wave.get("id", f"W_{indice:02d}")
            origen = wave.get("products", wave.get("productos", []))
        else:
            id_wave = getattr(wave, "id", f"W_{indice:02d}")
            origen = getattr(wave, "products", getattr(wave, "productos", []))

        if origen is None:
            raise ValueError(f"La wave {id_wave} no contiene productos.")

        productos = []

        for entrada in origen:
            if isinstance(entrada, dict):
                producto = entrada.get("product", entrada.get("producto"))
                producto_id = entrada.get("producto_id")
                cantidad = entrada.get("quantity", entrada.get("cantidad"))
            else:
                producto = getattr(entrada, "product", getattr(entrada, "producto", None))
                producto_id = getattr(entrada, "producto_id", None)
                cantidad = getattr(entrada, "quantity", getattr(entrada, "cantidad", None))

            if producto is not None:
                producto_id = producto.id
            if producto_id is None or cantidad is None:
                raise ValueError(f"La wave {id_wave} contiene una línea incompleta.")
            producto_id = str(producto_id).upper()

            if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
                raise ValueError(
                    f"La wave {id_wave} pide una cantidad inválida "
                    f"de {producto_id}: {cantidad}."
                )
            producto = self.productos.get(producto_id)
            if producto is None:
                raise ValueError(f"La wave {id_wave} referencia un producto inexistente: {producto_id}.")
            if producto.acceso is None:
                accesos = sorted(self.nav.accesos(*producto.ubicacion[:2]))
                if accesos:
                    producto.acceso = accesos[0]
            productos.append({"product": producto, "quantity": cantidad})

        return str(id_wave), productos

    def _asignar_trabajos(self):
        """Pide trabajo nuevo para cada picker libre en despacho/inicio."""
        libres = [p for p in self.pickers if p.wave is None and p.estado != "bloqueado"]
        for trabajo in self.asignador.asignar(libres):
            picker = self.pickers_por_id[trabajo["picker"]]
            tareas = {}
            for item in trabajo["productos"]:
                pid = item["producto_id"]
                tareas[pid] = {
                    "id": f"{trabajo['id']}:{pid}",
                    "producto_id": pid,
                    "cantidad": item["cantidad"],
                }
            picker.wave = {
                "id": trabajo["id"],
                "wave_id": trabajo["wave_id"],
                "zona": trabajo["zona"],
                "peso": trabajo["peso"],
                "tareas": tareas,
                "estado": "EN_PROCESO",
            }
            picker.pendientes = list(tareas.values())
            picker.objetivo = None
            picker.ruta = []
            picker.destinos = set()
            picker.estado = "disponible"
            self._ordenar_pendientes(picker)
            self._registrar(
                f"{picker.id}: recibe el viaje {trabajo['id']} de {trabajo['wave_id']} "
                f"({len(picker.pendientes)} productos)."
            )

    # ---------- ejecución de las waves asignadas ----------

    def _accesos_producto(self, producto):
        """Devuelve la única celda desde la que se puede recoger el producto."""

        if producto.acceso is None:
            return set()

        acceso = tuple(producto.acceso)

        if acceso not in self.nav.grafo:
            return set()

        return {acceso}
    
    def _nodo_acceso(self, picker, tarea):
        """Obtiene la celda de acceso real al producto."""

        producto = self.productos[tarea["producto_id"]]

        accesos = self._accesos_producto(producto)

        if not accesos:
            return None

        ruta = self.nav.camino(picker.pos, accesos)

        if ruta is None:
            return None

        return ruta[-1] if ruta else picker.pos

    def _ordenar_pendientes(self, picker):
        """Reordena los pendientes del picker según la estrategia de recorrido.
        Las tareas sin acceso quedan al final, en su orden original."""

        tareas_por_nodo = {}
        sin_acceso = []

        for tarea in picker.pendientes:
            nodo = self._nodo_acceso(picker, tarea)

            if nodo is None:
                sin_acceso.append(tarea)
            elif nodo in tareas_por_nodo:
                tareas_por_nodo[nodo].append(tarea)
            else:
                tareas_por_nodo[nodo] = [tarea]

        if not tareas_por_nodo:
            return

        estrategia = ESTRATEGIAS[self.estrategia]

        try:
            plan = estrategia(self.nav.grafo, picker.pos, list(tareas_por_nodo))
        except ValueError as error:
            self._registrar(
                f"{picker.id}: la estrategia '{self.estrategia}' falló ({error}); "
                f"se mantiene el orden de la wave."
            )
            return

        ordenadas = []
        for nodo in plan["order"]:
            ordenadas.extend(tareas_por_nodo[nodo])
        ordenadas.extend(sin_acceso)

        picker.pendientes = ordenadas

        self._registrar(
            f"{picker.id}: recorrido '{self.estrategia}' planificado, "
            f"distancia {plan['total_distance']:g}."
        )

    def _llegar_a_despacho(self, picker):
        """Entrega su viaje y vuelve a pedir trabajo al asignador."""

        self.hubo_avance = True

        if picker.wave is not None:
            trabajo_id = picker.wave["id"]
            wave_id = picker.wave["wave_id"]
            picker.wave["estado"] = "COMPLETADA"
            picker.waves_hechas.append(trabajo_id)
            self.asignador.trabajo_entregado(trabajo_id)
            self._registrar(f"{picker.id}: entregó {trabajo_id} de {wave_id}.")
            picker.wave = None

        picker.objetivo = None
        picker.destinos = set()
        picker.estado = "deambulando"
        self._asignar_trabajos()
        if picker.wave is None:
            self._registrar(
                f"{picker.id}: queda libre y recorre el warehouse."
            )

    def _celdas_despacho(self, zona_id):
        zona = self.warehouse.zonas_despacho[zona_id]
        destinos = set()
        for x, y in zona.cells():
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                celda = (x + dx, y + dy)
                if celda in self.nav.grafo:
                    destinos.add(celda)
        return destinos

    def _calcular_puntos_patrulla(self):
        """Celdas por las que pasan los pickers sin trabajo: intersecciones del
        grafo, sin las celdas de despacho ni las de acceso a productos (para no
        estorbar a quien trabaja). Orden fijo, así la simulación es repetible."""

        reservadas = set(self.nav.despacho)
        for accesos in self.nav.acceso_rack.values():
            reservadas.update(accesos)

        puntos = []
        for celda in self.nav.intersecciones:
            if celda in self.nav.grafo and celda not in reservadas:
                puntos.append(celda)

        # Sin intersecciones útiles (por ejemplo un pasillo recto): cualquier
        # celda libre.
        if len(puntos) < 2:
            puntos = [c for c in self.nav.grafo if c not in reservadas]

        return sorted(puntos)

    def _deambular(self, picker):
        """Sin trabajo, el picker sigue por los puntos de patrulla, esquivando
        a los demás con las mismas reglas de movimiento."""

        if not picker.ruta:
            self._elegir_punto_patrulla(picker)

        if picker.ruta:
            self._mover(picker)

    def _elegir_punto_patrulla(self, picker):
        """Va al próximo punto de patrulla con ruta libre. Si ninguno la tiene
        por ahora, espera en su celda y reintenta el próximo tick."""

        total = len(self.puntos_patrulla)
        ocupadas = self._ocupadas(picker)

        for desplazamiento in range(total):
            indice = (picker.indice_punto + desplazamiento) % total
            punto = self.puntos_patrulla[indice]

            if punto == picker.pos:
                continue

            ruta = self.nav.camino(picker.pos, {punto}, ocupadas=ocupadas)

            if ruta:
                picker.ruta = list(ruta)
                picker.destinos = {punto}
                picker.indice_punto = (indice + 1) % total
                return

    def paso(self):
        """Avanza la simulación un tick. Terminado el trabajo, los pickers
        siguen deambulando mientras se llame a paso()."""

        self.tick += 1
        self.hubo_avance = False

        # El orden de movimiento es determinista: primero los que trabajan.
        for picker in sorted(self.pickers, key=_clave_turno):
            if picker.estado == "bloqueado":
                continue

            self._avanzar(picker)

        # Congestión: cuántos pickers pasaron este tick esperando a otro.
        for picker in self.pickers:
            if picker.estado == "esperando":
                self.ticks_espera += 1

        if not self.terminada:
            self._detectar_bloqueo()

            if all(p.estado in ("deambulando", "bloqueado") for p in self.pickers):
                self.terminada = True
                self.tick_trabajo = self.tick
                self._registrar("Trabajo finalizado.")

        return self.estado()

    def _detectar_bloqueo(self):
        """Si pasan LIMITE_BLOQUEO ticks sin avance del trabajo, los pickers
        que siguen trabajando pasan a 'bloqueado' para que la simulación pueda
        terminar. Deambular no cuenta como avance."""

        if self.hubo_avance:
            self.ticks_sin_avance = 0
            return

        self.ticks_sin_avance += 1

        if self.ticks_sin_avance < LIMITE_BLOQUEO:
            return

        for picker in self.pickers:
            if picker.estado not in ("deambulando", "bloqueado"):
                picker.estado = "bloqueado"
                self._registrar(
                    f"{picker.id}: bloqueado, sin avance durante "
                    f"{LIMITE_BLOQUEO} ticks."
                )

    def ejecutar(self, max_ticks=10000):
        """Ejecuta hasta terminar o alcanzar el límite de ticks."""

        pasos = 0

        while not self.terminada and pasos < max_ticks:
            self.paso()
            pasos += 1

        if not self.terminada:
            self._registrar(f"Se alcanzó el límite de {max_ticks} ticks.")

        return self.estado()

    # ---------- movimiento ----------

    def _ocupadas(self, picker):
        """Celdas ocupadas por los demás pickers. Los que deambulan también
        ocupan su celda: nadie pisa a nadie."""

        ocupadas = set()
        for otro in self.pickers:
            if otro is not picker:
                ocupadas.add(otro.pos)
        return ocupadas

    def _avanzar(self, picker):
        if picker.estado == "deambulando":
            self._deambular(picker)
            return

        if picker.estado == "esperando":
            picker.estado = "disponible"

        if not picker.ruta:
            if picker.pendientes:
                self._elegir_objetivo(picker)

                # Si ya está junto al producto, puede recogerlo.
                if not picker.ruta and picker.objetivo is not None:
                    self._recoger(picker)

            else:
                self._planificar_regreso(picker)

        if picker.ruta:
            self._mover(picker)

    def _elegir_objetivo(self, picker):
        """Elige la primera tarea pendiente que tenga ruta disponible."""

        ocupadas = self._ocupadas(picker)

        elegida = None
        ruta = None
        posicion = 0

        for indice, tarea in enumerate(picker.pendientes):
            producto = self.productos[tarea["producto_id"]]

            accesos = self._accesos_producto(producto)

            ruta_tarea = None

            if accesos:
                ruta_tarea = self.nav.camino(
                    picker.pos,
                    accesos,
                    ocupadas=ocupadas
                )

            if ruta_tarea is None:
                if not self.permitir_saltos:
                    break
                continue

            elegida = tarea
            ruta = ruta_tarea
            posicion = indice
            break

        if elegida is None:
            picker.estado = "esperando"
            self._registrar(
                f"{picker.id}: no hay ruta disponible por ahora."
            )
            return

        if posicion > 0 and elegida is not picker.objetivo:
            picker.saltos += 1
            self._registrar(
                f"{picker.id}: salta a {elegida['producto_id']}, "
                f"{picker.pendientes[0]['producto_id']} está bloqueado."
            )

        picker.objetivo = elegida
        picker.destinos = {ruta[-1] if ruta else picker.pos}
        picker.ruta = list(ruta)
        picker.estado = "yendo_a_producto"

        self._registrar(
            f"{picker.id}: se dirige a {elegida['producto_id']}."
        )

    def _recoger(self, picker):
        """Recoge la tarea objetivo y descuenta el stock."""

        tarea = picker.objetivo

        if tarea is None:
            return

        producto = self.productos[tarea["producto_id"]]
        cantidad = tarea["cantidad"]

        if producto.acceso is None:
            raise ValueError(
                f"El producto {producto.id} no tiene acceso asignado."
            )

        if picker.pos != tuple(producto.acceso):
            raise ValueError(
                f"El picker {picker.id} no está en el acceso "
                f"correcto del producto {producto.id}."
            )

        producto.take_product(cantidad, picker.pos)

        picker.recogidos.append({
            "producto_id": producto.id,
            "wave_id": picker.wave["wave_id"],
            "trabajo_id": picker.wave["id"],
            "cantidad": cantidad,
        })

        picker.pendientes.remove(tarea)
        picker.objetivo = None
        picker.destinos = set()
        picker.estado = "disponible"
        self.hubo_avance = True

        self._registrar(
            f"{picker.id}: recogió {cantidad} unidades de {producto.id}."
        )

    def _planificar_regreso(self, picker):
        """Planifica el regreso a la zona reservada para este viaje."""

        destinos = self._celdas_despacho(picker.wave["zona"])

        if picker.pos in destinos:
            self._llegar_a_despacho(picker)
            return

        ruta = self.nav.camino(
            picker.pos,
            destinos,
            ocupadas=self._ocupadas(picker),
        )

        if ruta is None:
            picker.estado = "esperando"
            return

        picker.ruta = list(ruta)
        picker.destinos = destinos
        picker.estado = "regresando"

        if not picker.ruta and picker.pos in destinos:
            self._llegar_a_despacho(picker)

    def _mover(self, picker):
        """Mueve al preparador una celda, sin ocupar celdas ajenas."""

        if not picker.ruta:
            return

        siguiente = picker.ruta[0]

        if siguiente in self._ocupadas(picker):
            if picker.estado == "deambulando":
                # Cede el paso: elige otro punto de patrulla el próximo tick.
                picker.ruta = []
                return

            picker.estado = "esperando"
            self._replanificar(picker)
            return

        # Evita movimientos de más de una celda.
        distancia = (
            abs(siguiente[0] - picker.pos[0])
            + abs(siguiente[1] - picker.pos[1])
        )

        if distancia != 1:
            picker.ruta = []

            if picker.estado == "deambulando":
                return

            picker.estado = "esperando"
            self._replanificar(picker)
            return

        anterior = picker.pos
        picker.anterior = anterior
        picker.pos = siguiente
        picker.ruta.pop(0)

        # Deambular no cuenta como avance del trabajo ni como recorrido.
        if picker.estado != "deambulando":
            picker.trail.append(siguiente)
            picker.pasos_trabajo += 1
            self.hubo_avance = True
            self._registrar(f"{picker.id}: {anterior} -> {siguiente}.")

        if picker.estado == "regresando" and picker.pos in picker.destinos:
            picker.ruta = []
            self._llegar_a_despacho(picker)

    def _replanificar(self, picker):
            """Intenta encontrar una ruta alternativa."""

            if picker.objetivo is not None:
                producto = self.productos[picker.objetivo["producto_id"]]
                destinos = self._accesos_producto(producto)
            elif picker.wave is not None:
                destinos = self._celdas_despacho(picker.wave["zona"])
            else:
                destinos = self.nav.despacho

            ruta = self.nav.camino(
                picker.pos,
                destinos,
                ocupadas=self._ocupadas(picker),
            )

            if ruta is None:
                picker.ruta = []
                return

            picker.ruta = list(ruta)

    def _esquivar(self, picker, ocupadas=None):
        """Compatibilidad con la interfaz de la versión anterior."""

        self._replanificar(picker)

    # ---------- estado ----------

    def _registrar(self, mensaje):
        self.log.append(f"[Tick {self.tick}] {mensaje}")

        if len(self.log) > 200:
            self.log.pop(0)

    def estado(self):
        """Devuelve una instantánea del estado para la interfaz gráfica."""

        return {
            "tick": self.tick,
            "terminada": self.terminada,
            "tick_trabajo": self.tick_trabajo,
            "estrategia": self.estrategia,
            "permitir_saltos": self.permitir_saltos,
            "algoritmo_asignacion": self.algoritmo_asignacion,
            "saltos": sum(p.saltos for p in self.pickers),
            "pickers": [
                {
                    "id": p.id,
                    "posicion": p.pos,
                    "anterior": p.anterior,
                    "ruta": list(p.ruta),
                    "estado": p.estado,
                    "objetivo": (
                        p.objetivo["producto_id"]
                        if p.objetivo else None
                    ),
                    "pendientes": [t["producto_id"] for t in p.pendientes],
                    "destinos": list(p.destinos),
                    "recogidos": list(p.recogidos),
                    "trail": list(p.trail),
                    "wave_id": p.wave["wave_id"] if p.wave else None,
                    "trabajo_id": p.wave["id"] if p.wave else None,
                    "trabajo": (
                        {
                            "id": p.wave["id"],
                            "wave_id": p.wave["wave_id"],
                            "zona": p.wave["zona"],
                            "peso": p.wave["peso"],
                            "tareas": [dict(t) for t in p.wave["tareas"].values()],
                        }
                        if p.wave else None
                    ),
                    "waves_hechas": list(p.waves_hechas),
                    "saltos": p.saltos,
                    "pasos_trabajo": p.pasos_trabajo,
                    "indice_punto": p.indice_punto,
                }
                for p in self.pickers
            ],
            "waves": [
                {
                    "id": w["id"],
                    "estado": w["estado"],
                    "productos": [
                        {"producto_id": pid, "cantidad": cantidad}
                        for pid, cantidad in w["solicitados"].items()
                    ],
                    "pendiente": dict(w["pendiente"]),
                    "numero": w["numero"],
                    "completada": w["completada"],
                    "incompleta": w["incompleta"],
                }
                for w in self.waves
            ],
            "productos": {
                producto_id: producto.stock
                for producto_id, producto in self.productos.items()
            },
            "log": list(self.log),
        }

    def restaurar(self, estado):
        """Restaura el progreso de una instantánea guardada.
        Reconstruye la asignación dinámica y vuelve a descontar lo recogido."""

        # Las waves se reconstruyen con lo guardado: no dependen del generador.
        self.waves_entrada = []
        for guardada in estado["waves"]:
            self.waves_entrada.append({
                "id": guardada["id"],
                "productos": guardada["productos"],
            })

        # La estrategia guardada vale también para las waves que faltan empezar.
        self.estrategia = estado.get("estrategia", self.estrategia)
        self.permitir_saltos = estado.get("permitir_saltos", self.permitir_saltos)
        self.algoritmo_asignacion = estado.get(
            "algoritmo_asignacion", self.algoritmo_asignacion
        )
        self.asignador.configurar_algoritmo(self.algoritmo_asignacion)
        self.asignador._cache_recorrido.clear()

        self.reiniciar()

        trabajos_guardados = [
            p["trabajo"] for p in estado["pickers"] if p.get("trabajo")
        ]
        self.asignador.restaurar_estado(estado["waves"], trabajos_guardados)

        for picker in self.pickers:
            picker.wave = None
            picker.pendientes = []
            picker.objetivo = None
            picker.waves_hechas = []
            picker.waves_asignadas = []

        self.tick = estado["tick"]
        self.terminada = estado["terminada"]
        self.tick_trabajo = estado.get("tick_trabajo")
        self.log = list(estado.get("log", []))

        estados_por_id = {}
        for p in estado["pickers"]:
            estados_por_id[p["id"]] = p

        for picker in self.pickers:
            guardado = estados_por_id.get(picker.id)

            if guardado is None:
                continue

            picker.pos = tuple(guardado["posicion"])

            anterior = guardado.get("anterior")
            picker.anterior = tuple(anterior) if anterior is not None else None

            picker.ruta = [tuple(celda) for celda in guardado["ruta"]]
            picker.estado = guardado["estado"]
            picker.trail = [tuple(celda) for celda in guardado["trail"]]
            picker.recogidos = list(guardado["recogidos"])

            # El stock baja al recoger: se vuelve a descontar lo ya recogido.
            for recogido in picker.recogidos:
                producto = self.productos[recogido["producto_id"]]

                producto.take_product(
                    recogido["cantidad"],
                    producto.acceso
                )

            picker.destinos = {tuple(d) for d in guardado.get("destinos", [])}
            picker.waves_hechas = list(guardado.get("waves_hechas", []))
            picker.saltos = guardado.get("saltos", 0)
            picker.pasos_trabajo = guardado.get("pasos_trabajo", 0)
            picker.indice_punto = guardado.get("indice_punto", picker.indice_punto)

            trabajo = guardado.get("trabajo")
            if trabajo is not None:
                tareas = {
                    t["producto_id"]: dict(t)
                    for t in trabajo["tareas"]
                }
                picker.wave = {
                    "id": trabajo["id"],
                    "wave_id": trabajo["wave_id"],
                    "zona": trabajo["zona"],
                    "peso": trabajo["peso"],
                    "tareas": tareas,
                    "estado": "EN_PROCESO",
                }
            else:
                picker.wave = None
            picker.pendientes = []
            picker.objetivo = None

            if picker.wave is not None:
                for producto_id in guardado["pendientes"]:
                    if producto_id in picker.wave["tareas"]:
                        picker.pendientes.append(picker.wave["tareas"][producto_id])

                picker.objetivo = picker.wave["tareas"].get(guardado["objetivo"])
