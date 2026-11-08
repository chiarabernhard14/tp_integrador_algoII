import time
import sys
from pathlib import Path

from .NavegationV import Navegacion
from .CargadorV import cargar_warehouse
from .AsignadorPickersV import Asignador
from .EstadoPicker import EstadoPicker
from .GestorColisionesV import GestorColisionesV
from .PlanificadorViajesV import ALGORITMOS_CAMINO, ESTRATEGIAS

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ProductoInaccesible import ProductoInaccesible

LIMITE_BLOQUEO = 20
UMBRAL_ASIGNACION_MS = 2000


def _id_picker(picker):
    return picker.id


def waves_de_estado(estado):
    """Reconstruye las waves guardadas en una partida."""
    return [
        {"id": guardada["id"], "productos": guardada["productos"]}
        for guardada in estado.get("waves", [])
    ]


class Simulacion:
    """Simula la ejecución de waves por pickers.

    - Recibe waves armadas, sin picker asignado. El Asignador distribuye viajes
      entre los pickers libres y vuelve a decidir cuando alguno entrega.
    - Una wave puede generar varios viajes y ser atendida por varios pickers.
      Cada viaje termina en la zona de despacho que reservó el asignador.
    - El orden en que el picker visita los productos de su viaje lo decide la
      estrategia de recorrido elegida (ver ESTRATEGIAS).
      Si la próxima tarea del orden está bloqueada por otro picker, salta a
      la siguiente alcanzable y suma un salto (picker.saltos). Con
      permitir_saltos=False el picker espera esa tarea.
    - Un picker sin más trabajo pasa a "deambulando" y recorre los puntos de
      patrulla (intersecciones libres); los que trabajan tienen prioridad.
      "terminada" indica que el trabajo terminó: ejecutar() se detiene ahí.
    - El stock se descuenta cuando el picker recoge el producto.
    """

    def __init__(
        self, datos, waves=None, estrategia="cercania", permitir_saltos=True,
        algoritmo_camino="a_estrella",
    ):
        if estrategia not in ESTRATEGIAS:
            raise ValueError(
                f"Estrategia desconocida: {estrategia}. "
                f"Opciones: {', '.join(ESTRATEGIAS)}."
            )
        if algoritmo_camino not in ALGORITMOS_CAMINO:
            raise ValueError(
                f"Algoritmo de camino desconocido: {algoritmo_camino}. "
                f"Opciones: {', '.join(ALGORITMOS_CAMINO)}."
            )

        self.datos = datos
        self.waves_entrada = waves
        self.estrategia = estrategia
        self.permitir_saltos = permitir_saltos
        self.algoritmo_camino = algoritmo_camino

        self.reiniciar()

    def reiniciar(self):
        self.tick = 0
        self.terminada = False
        self.tick_trabajo = None
        self.log = []

        self.tiempo_asignacion_ms = 0.0
        self.llamadas_asignacion = 0
        self.max_asignacion_ms = 0.0

        self.hubo_avance = False
        self.ticks_sin_avance = 0
        self.ticks_espera = 0
        # Mientras no se dio el primer paso, los pickers deambulan libremente.
        self.en_espera = True

        self.warehouse = cargar_warehouse(self.datos)
        self.nav = Navegacion(self.warehouse, algoritmo=self.algoritmo_camino)
        self.productos = self.warehouse.productos

        # --- Productos inaccesibles: avisar y excluir de los viajes ---
        # La excepción especial ProductoInaccesible se captura en
        # validar_escenario y se guarda en datos["productos_inaccesibles"].
        self.productos_inaccesibles = set(
            self.datos.get("productos_inaccesibles", [])
        )
        if self.productos_inaccesibles:
            self._registrar(
                "ADVERTENCIA: productos inaccesibles (sin camino al despacho): "
                + ", ".join(sorted(self.productos_inaccesibles))
                + ". Se excluyen de los viajes; el escenario sigue ejecutándose."
            )
            self._excluir_productos_inaccesibles()
            # El grafo reducido ya se construyó; evitar reconstruirlo para no
            # volver a lanzar ProductoInaccesible.
            self.warehouse._grafo_reducido_listo = True

        self.pickers = []
        self.pickers_por_id = {}
        for entidad in self.warehouse.pickers.values():
            picker = EstadoPicker(entidad)
            self.pickers.append(picker)
            self.pickers_por_id[picker.id] = picker

        self.colisiones = GestorColisionesV(
            pickers=self.pickers,
            registrar=self._registrar,
            replanificar=self._replanificar,
            llegar_a_despacho=self._llegar_a_despacho,
            marcar_avance=self._marcar_avance,
        )

        self._cargar_waves()

        self.puntos_patrulla = self._calcular_puntos_patrulla()
        for numero, picker in enumerate(sorted(self.pickers, key=_id_picker)):
            if self.puntos_patrulla:
                picker.indice_punto = (
                    numero * len(self.puntos_patrulla) // len(self.pickers)
                )
            picker.estado = "deambulando"

        self._asignar_trabajos()
        self._registrar("Simulación inicializada.")

    # ---------- carga de waves ----------

    def _generar_waves_proyecto(self):
        """Llama al generador de waves con los pedidos del Warehouse."""
        from .GeneradorWaves import generar_waves

        configuracion = self.datos.get("configuracion", {})
        return generar_waves(
            list(self.warehouse.pedidos.values()),
            configuracion.get("wave_max_pedidos", 3),
            configuracion.get("wave_max_productos", 15),
        )

    def _cargar_waves(self):
        """Deja que el asignador normalice las waves y decida los pickers."""
        if self.waves_entrada is None:
            self.waves_entrada = self._generar_waves_proyecto()
        if not isinstance(self.waves_entrada, list):
            raise TypeError("waves debe ser una lista de waves.")

        self.asignador = Asignador(
            self.nav, self.warehouse.zonas_despacho, self.waves_entrada,
            self.productos, self.warehouse.racks,
            algoritmo_camino=self.algoritmo_camino, estrategia=self.estrategia,
        )
        self.planificador = self.asignador.planificador
        self.waves = self.asignador.waves

    def _excluir_productos_inaccesibles(self):
        """Quita de los pedidos los ítems de productos inaccesibles para que no
        entren en las waves ni en los viajes, y los retira del catálogo usado
        por el asignador. El escenario sigue ejecutándose."""
        if not self.productos_inaccesibles:
            return
        for orden in self.warehouse.pedidos.values():
            orden.items = [
                item for item in orden.items
                if item.producto_id not in self.productos_inaccesibles
            ]
        for pid in self.productos_inaccesibles:
            self.productos.pop(pid, None)

    def _asignar_trabajos(self):
        """Pide trabajo nuevo para cada picker libre."""
        libres = [p for p in self.pickers if p.wave is None and p.estado != "bloqueado"]
        inicio = time.perf_counter()
        try:
            trabajos = self.asignador.asignar(libres)
        finally:
            duracion_ms = (time.perf_counter() - inicio) * 1000
            self.tiempo_asignacion_ms += duracion_ms
            self.llamadas_asignacion += 1
            self.max_asignacion_ms = max(self.max_asignacion_ms, duracion_ms)
            if duracion_ms > UMBRAL_ASIGNACION_MS:
                self._registrar(
                    f"Asignación de pickers: llamada de {duracion_ms:.1f} ms."
                )

        for trabajo in trabajos:
            picker = self.pickers_por_id[trabajo["picker"]]
            tareas = {
                item["producto_id"]: {
                    "id": f"{trabajo['id']}:{item['producto_id']}",
                    "producto_id": item["producto_id"],
                    "cantidad": item["cantidad"],
                }
                for item in trabajo["productos"]
            }
            picker.asignar_viaje(
                trabajo["id"], trabajo["wave_id"],
                trabajo["zona"], trabajo["peso"], tareas,
            )
            picker.pendientes = [tareas[pid] for pid in trabajo["orden_productos"]]
            picker.objetivo = None
            picker.ruta = []
            picker.destinos = set()
            # Antes del primer paso el picker sigue deambulando aunque ya
            # tenga un viaje reservado.
            picker.estado = "deambulando" if self.en_espera else "disponible"
            self._registrar(
                f"{picker.id}: recibe el viaje {trabajo['id']} de {trabajo['wave_id']} "
                f"({len(picker.pendientes)} productos; "
                f"{self.estrategia}, {self.algoritmo_camino}, "
                f"distancia estimada {trabajo['distancia_estimada']:g})."
            )

    # ---------- despacho y patrulla ----------

    def _accesos_producto(self, producto):
        """Devuelve la única celda desde la que se puede recoger el producto."""
        if producto.acceso is None:
            return set()
        acceso = tuple(producto.acceso)
        if acceso not in self.nav.grafo:
            return set()
        return {acceso}

    def _llegar_a_despacho(self, picker):
        """Entrega su viaje y vuelve a pedir trabajo al asignador."""
        self.hubo_avance = True

        if picker.wave is not None:
            trabajo_id = picker.wave["id"]
            wave_id = picker.wave["wave_id"]
            picker.waves_hechas.append(trabajo_id)
            self.asignador.trabajo_entregado(trabajo_id)
            self._registrar(f"{picker.id}: entregó {trabajo_id} de {wave_id}.")
            picker.wave = None

        picker.objetivo = None
        picker.destinos = set()
        picker.estado = "deambulando"
        self._asignar_trabajos()
        if picker.wave is None:
            self._registrar(f"{picker.id}: queda libre y recorre el warehouse.")

    def _calcular_puntos_patrulla(self):
        """Intersecciones del grafo, sin celdas de despacho ni de acceso a
        productos. Orden fijo para que la simulación sea repetible."""
        reservadas = set(self.nav.despacho)
        for accesos in self.nav.acceso_rack.values():
            reservadas.update(accesos)

        puntos = [
            celda for celda in self.nav.intersecciones
            if celda in self.nav.grafo and celda not in reservadas
        ]
        # Sin intersecciones útiles: cualquier celda libre.
        if len(puntos) < 2:
            puntos = [c for c in self.nav.grafo if c not in reservadas]
        return sorted(puntos)

    def _deambular(self, picker):
        if not picker.ruta:
            self._elegir_punto_patrulla(picker)
        if picker.ruta:
            self.colisiones.mover(picker)

    def deambular_vista(self):
        """Avanza un paso a los pickers en espera sin consumir ticks.

        Se usa solo para la vista previa: antes de iniciar la simulación los
        pickers recorren libremente el warehouse. Cuando se da el primer paso
        real, cada picker retoma el viaje que tenía reservado.
        """
        if not self.en_espera or self.terminada:
            return
        for picker in self.colisiones.orden_movimiento():
            if picker.estado != "deambulando":
                continue
            anterior = tuple(picker.pos)
            self._deambular(picker)
            if tuple(picker.pos) != anterior:
                picker.trail.append(tuple(picker.pos))

    def _elegir_punto_patrulla(self, picker):
        """Va al próximo punto de patrulla con ruta libre; si no hay, espera."""
        total = len(self.puntos_patrulla)
        ocupadas = self.colisiones.ocupadas(picker)

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

    # ---------- avance ----------

    def paso(self):
        """Avanza un tick. Terminado el trabajo, los pickers siguen deambulando."""
        self.tick += 1
        self.hubo_avance = False

        # Limpiar reservas de celdas del tick anterior.
        self.colisiones.limpiar_reservas()

        # El primer paso deja atrás la vista previa: los pickers con viaje
        # reservado empiezan a trabajar desde donde deambulaban.
        if self.en_espera:
            self.en_espera = False
            for picker in self.pickers:
                if picker.wave is not None and picker.estado == "deambulando":
                    picker.ruta = []
                    picker.destinos = set()
                    picker.estado = "disponible"

        for picker in self.colisiones.orden_movimiento():
            if picker.estado != "bloqueado":
                self._avanzar(picker)

        # Congestión: pickers que pasaron este tick esperando a otro.
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
        """Tras LIMITE_BLOQUEO ticks sin avance, los que trabajan pasan a
        'bloqueado'. Deambular no cuenta como avance."""
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

    def _avanzar(self, picker):
        if picker.estado == "deambulando":
            self._deambular(picker)
            return

        if picker.estado == "esperando":
            picker.ticks_esperando += 1
            if picker.ticks_esperando < 3:
                # Seguir esperando para dejar que el otro picker libere el paso.
                return
            picker.estado = "disponible"
            picker.ticks_esperando = 0

        if not picker.ruta:
            if picker.pendientes:
                self._elegir_objetivo(picker)
                # Si ya está junto al producto, puede recogerlo.
                if not picker.ruta and picker.objetivo is not None:
                    self._recoger(picker)
            else:
                self._planificar_regreso(picker)

        if picker.ruta:
            self.colisiones.mover(picker)

    def _elegir_objetivo(self, picker):
        """Elige la primera tarea pendiente que tenga ruta disponible."""
        ocupadas = self.colisiones.ocupadas(picker)

        elegida = None
        ruta = None
        posicion = 0

        for indice, tarea in enumerate(picker.pendientes):
            accesos = self._accesos_producto(self.productos[tarea["producto_id"]])
            ruta_tarea = None
            if accesos:
                ruta_tarea = self.nav.camino(picker.pos, accesos, ocupadas=ocupadas)

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
            self._registrar(f"{picker.id}: no hay ruta disponible por ahora.")
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
        self._registrar(f"{picker.id}: se dirige a {elegida['producto_id']}.")

    def _recoger(self, picker):
        """Recoge la tarea objetivo y descuenta el stock."""
        tarea = picker.objetivo
        if tarea is None:
            return

        producto = self.productos[tarea["producto_id"]]
        cantidad = tarea["cantidad"]

        if producto.acceso is None:
            raise ValueError(f"El producto {producto.id} no tiene acceso asignado.")
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
        self._registrar(f"{picker.id}: recogió {cantidad} unidades de {producto.id}.")

    def _planificar_regreso(self, picker):
        """Planifica el regreso a la zona reservada para este viaje."""
        destinos = self.nav.despacho_por_zona[picker.wave["zona"]]

        if picker.pos in destinos:
            self._llegar_a_despacho(picker)
            return

        ruta = self.nav.camino(
            picker.pos, destinos, ocupadas=self.colisiones.ocupadas(picker)
        )
        if ruta is None:
            picker.estado = "esperando"
            return

        picker.ruta = list(ruta)
        picker.destinos = destinos
        picker.estado = "regresando"

    def _marcar_avance(self):
        self.hubo_avance = True

    def _replanificar(self, picker):
        """Intenta encontrar una ruta alternativa."""
        if picker.objetivo is not None:
            destinos = self._accesos_producto(self.productos[picker.objetivo["producto_id"]])
        elif picker.wave is not None:
            destinos = self.nav.despacho_por_zona[picker.wave["zona"]]
        else:
            destinos = self.nav.despacho

        ruta = self.nav.camino(
            picker.pos, destinos, ocupadas=self.colisiones.ocupadas(picker)
        )
        picker.ruta = list(ruta) if ruta is not None else []

    # ---------- estado ----------

    def _registrar(self, mensaje):
        self.log.append(f"[Tick {self.tick}] {mensaje}")
        if len(self.log) > 200:
            self.log.pop(0)

    def estado(self):
        """Devuelve una instantánea del estado para la interfaz y las partidas."""
        return {
            "tick": self.tick,
            "terminada": self.terminada,
            "tick_trabajo": self.tick_trabajo,
            "estrategia": self.estrategia,
            "permitir_saltos": self.permitir_saltos,
            "algoritmo_camino": self.algoritmo_camino,
            "saltos": sum(p.saltos for p in self.pickers),
            "tiempo_asignacion_ms": self.tiempo_asignacion_ms,
            "llamadas_asignacion": self.llamadas_asignacion,
            "max_asignacion_ms": self.max_asignacion_ms,
            "pickers": [p.a_dict() for p in self.pickers],
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
            "productos_inaccesibles": sorted(self.productos_inaccesibles),
            "log": list(self.log),
        }

    def restaurar(self, estado):
        """Restaura el progreso de una instantánea guardada: reconstruye la
        asignación dinámica y vuelve a descontar lo ya recogido."""
        # Las waves se reconstruyen con lo guardado: no dependen del generador.
        self.waves_entrada = waves_de_estado(estado)

        self.estrategia = estado.get("estrategia", self.estrategia)
        if self.estrategia not in ESTRATEGIAS:
            raise ValueError(f"Estrategia de recorrido desconocida: {self.estrategia}.")
        self.permitir_saltos = estado.get("permitir_saltos", self.permitir_saltos)
        self.algoritmo_camino = estado.get(
            "algoritmo_camino",
            estado.get("algoritmo_asignacion", self.algoritmo_camino),
        )
        if self.algoritmo_camino not in ALGORITMOS_CAMINO:
            raise ValueError(
                f"Algoritmo de camino desconocido: {self.algoritmo_camino}."
            )
        self.reiniciar()

        trabajos_guardados = [
            p["trabajo"] for p in estado["pickers"] if p.get("trabajo")
        ]
        self.asignador.restaurar_estado(estado["waves"], trabajos_guardados)

        self.tick = estado["tick"]
        self.terminada = estado["terminada"]
        self.tick_trabajo = estado.get("tick_trabajo")
        # Una partida ya iniciada no muestra la vista previa de deambulación.
        self.en_espera = self.tick == 0 and not self.terminada
        self.log = list(estado.get("log", []))
        self.tiempo_asignacion_ms = estado.get("tiempo_asignacion_ms", 0.0)
        self.llamadas_asignacion = estado.get("llamadas_asignacion", 0)
        self.max_asignacion_ms = estado.get("max_asignacion_ms", 0.0)

        guardados = {p["id"]: p for p in estado["pickers"]}
        for picker in self.pickers:
            guardado = guardados.get(picker.id)
            if guardado is None:
                continue
            picker.restaurar(guardado)
            # El stock baja al recoger: se vuelve a descontar lo ya recogido.
            for recogido in picker.recogidos:
                producto = self.productos[recogido["producto_id"]]
                producto.take_product(recogido["cantidad"], producto.acceso)

        # Las partidas guardadas en el tick 0 también muestran la vista previa:
        # los pickers pasean con su viaje reservado hasta el primer paso.
        if self.en_espera:
            for picker in self.pickers:
                if picker.wave is not None:
                    picker.estado = "deambulando"
                    picker.ruta = []
                    picker.destinos = set()