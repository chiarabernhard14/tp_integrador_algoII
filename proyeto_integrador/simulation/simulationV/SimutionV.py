from .NavegationV import Navegacion
from .CargadorV import cargar_warehouse
from .WavesV import armar_waves, peso_pedido

LIMITE_BLOQUEO = 20

#Mandar a generación de waves
def _clave_tarea(tarea):
    return (-tarea["prioridad"], tarea["producto_id"])


def _id_picker(picker):
    return picker.id

#Mandar a generación de waves
def _clave_cola(wave):
    return (-len(wave["tareas"]), -wave["peso"], wave["id"])


class EstadoPicker:
    
    def __init__(self, picker):
        self.entidad = picker
        self.id = picker.id
        self.capacidad = picker.capacidad_carga_kg

        self.anterior = None
        self.pendientes = []
        self.recogidos = []
        self.objetivo = None
        self.destinos = set()
        self.estado = "disponible"
        self.trail = [picker.posicion]

        # Wave que está ejecutando (un picker ejecuta una wave a la vez).
        self.wave = None
        self.waves_hechas = []

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
    """Regla de trabajo: cada wave la ejecuta un único picker.

    - Las waves llegan ARMADAS (las genera otro módulo del proyecto) como una
      lista de dicts {"id", "orders"} u objetos con .id y .orders (clase Wave).
      Esta clase no arma waves: las recibe, las reparte y las simula.
    - Las waves esperan en una cola ordenada de la más larga a la más corta;
      cada picker toma la primera que puede cargar (por peso), la prepara y
      vuelve al despacho.
    - Si quedan waves que puede cargar, toma la siguiente; si no, termina.
    - Por eso no puede haber más pickers que waves, y ninguna wave puede
      pesar más que lo que carga el picker más grande.
    - El stock se reserva (se descuenta) cuando la wave entra a la simulación.
    """

    def __init__(self, datos, waves=None):
        self.datos = datos
        self.waves_entrada = waves
        self.nav = Navegacion(cargar_warehouse(datos))
        self.reiniciar()


    def reiniciar(self):
        self.tick = 0
        self.terminada = False
        self.log = []
        self.fallidas = set()

        # Control de bloqueo global.
        self.hubo_avance = False
        self.ticks_sin_avance = 0
        self.ticks_espera = 0

        # Warehouse nuevo: stocks, racks y pedidos vuelven al estado del escenario.
        self.warehouse = cargar_warehouse(self.datos)
        self.productos = self.warehouse.productos

        self.pickers = []
        for entidad in self.warehouse.pickers.values():
            self.pickers.append(EstadoPicker(entidad))

        self.waves = []
        self.cola_waves = []
        self.pedidos_wave = []
        self._armar_waves()
        self._validar_pickers()
        self.cola_waves.sort(key=_clave_cola)
        self._repartir_waves_iniciales()

        self._registrar("Simulación inicializada.")

#todavía estoy solucionando la implementacion de los distintods recorridos 
    # ---------- armado de waves ----------

    def _armar_waves(self):
        """Crea las waves recibidas. Si no se recibió ninguna, usa un armado
        PROVISORIO hasta integrar el generador de waves del proyecto."""

        if self.waves_entrada is None:
            grupos = self._grupos_provisorios()
            for numero, pedidos in enumerate(grupos, start=1):
                self._crear_wave(f"W{numero}", pedidos)
            return

        if not isinstance(self.waves_entrada, list):
            raise TypeError("waves debe ser una lista de waves.")

        vistos = set()
        for wave in self.waves_entrada:
            id_wave, pedidos = self._leer_wave(wave)

            for pedido in pedidos:
                if pedido.id in vistos:
                    raise ValueError(f"El pedido {pedido.id} está en más de una wave.")
                vistos.add(pedido.id)

            self._crear_wave(id_wave, pedidos)

    def _leer_wave(self, wave):
        """Devuelve (id, pedidos propios) de una wave recibida: un dict con 'id'
        y 'orders', o un objeto con .id y .orders (como la clase Wave)."""

        if isinstance(wave, dict):
            id_wave = wave.get("id")
            origen = wave.get("orders")
        elif hasattr(wave, "id") and hasattr(wave, "orders"):
            id_wave = wave.id
            origen = wave.orders
        else:
            raise TypeError(
                "Cada wave debe ser un dict con 'id' y 'orders' o un objeto con .id y .orders."
            )

        if id_wave is None or origen is None:
            raise ValueError("Una wave recibida no tiene 'id' u 'orders'.")

        pedidos = []
        for pedido in origen:
            id_pedido = pedido["id"] if isinstance(pedido, dict) else pedido.id
            propio = self.warehouse.pedidos.get(id_pedido)
            if propio is None:
                raise ValueError(
                    f"La wave {id_wave} referencia un pedido inexistente: {id_pedido}."
                )
            pedidos.append(propio)

        return str(id_wave), pedidos

    def _grupos_provisorios(self):
        """PROVISORIO: agrupa los pedidos pendientes con WavesV.armar_waves.
        Se reemplaza por el generador de waves del proyecto."""

        configuracion = self.datos.get("configuracion", {})
        max_pedidos = configuracion.get("wave_max_pedidos", 0)
        max_productos = configuracion.get("wave_max_productos", 0)

        capacidad_maxima = 0.0
        for picker in self.pickers:
            capacidad_maxima = max(capacidad_maxima, picker.capacidad)

        pendientes = []
        for pedido in self.warehouse.pedidos.values():
            if pedido.estado == "PENDIENTE":
                pendientes.append(pedido)

        grupos, excluidos = armar_waves(
            pendientes, max_pedidos, max_productos, capacidad_maxima)

        for pedido in excluidos:
            self._registrar(
                f"Pedido {pedido.id}: no entra ni en una wave vacía (supera el "
                f"máximo de productos o el peso que carga el picker más grande) "
                f"y no se incluye en ninguna."
            )

        return grupos

    def _crear_wave(self, id_wave, pedidos):
        """Arma las tareas (una por producto) de una wave y la deja en la cola."""

        peso = 0.0
        for pedido in pedidos:
            peso += peso_pedido(pedido)

        tareas = {}

        for pedido in pedidos:
            for indice, item in enumerate(pedido.items):
                producto_id = item.producto_id

                if item.producto is None:
                    self._registrar(
                        f"Pedido {pedido.id}: producto "
                        f"{producto_id} inexistente."
                    )
                    self.fallidas.add((pedido.id, indice))
                    continue

                if producto_id not in tareas:
                    tareas[producto_id] = {
                        "id": f"{id_wave}:{producto_id}",
                        "producto_id": producto_id,
                        "cantidad": 0,
                        "prioridad": pedido.prioridad,
                        "lineas": [],
                    }

                tarea = tareas[producto_id]
                tarea["cantidad"] += item.cantidad
                tarea["prioridad"] = max(tarea["prioridad"], pedido.prioridad)

                tarea["lineas"].append({
                    "pedido_id": pedido.id,
                    "indice_item": indice,
                    "cantidad": item.cantidad,
                    "item": item,
                })

            self.pedidos_wave.append(pedido)

        # Detecta demandas que superan el stock disponible y reserva el resto:
        # el stock se descuenta ahora, al armarse la wave (no cuando el picker recoge).
        for producto_id, tarea in list(tareas.items()):
            producto = self.productos[producto_id]

            if tarea["cantidad"] > producto.stock:
                self._registrar(
                    f"Stock insuficiente para {producto_id} en {id_wave}: "
                    f"se solicitan {tarea['cantidad']} unidades y "
                    f"hay {producto.stock}."
                )

                # No asignamos una tarea que no pueda completarse.
                for linea in tarea["lineas"]:
                    self.fallidas.add((linea["pedido_id"], linea["indice_item"]))

                del tareas[producto_id]
            else:
                producto.take_product(tarea["cantidad"])

        wave = {
            "id": id_wave,
            "pedidos": list(pedidos),
            "tareas": tareas,
            "peso": peso,
            "picker": None,
            "estado": "CREADA",
        }
        self.waves.append(wave)
        self.cola_waves.append(wave)

    def _validar_pickers(self):
        """Cada wave la ejecuta un solo picker: no puede haber más pickers que
        waves, y cada wave tiene que entrar en al menos un picker (por peso)."""

        cantidad_waves = len(self.waves)
        cantidad_pickers = len(self.pickers)

        if cantidad_waves == 0:
            raise ValueError("No hay waves para ejecutar.")

        if cantidad_pickers > cantidad_waves:
            raise ValueError(
                f"Hay {cantidad_pickers} pickers pero solo {cantidad_waves} "
                f"wave(s). Cada wave la ejecuta un solo picker, así que el máximo "
                f"es {cantidad_waves}."
            )

        capacidad_maxima = 0.0
        for picker in self.pickers:
            capacidad_maxima = max(capacidad_maxima, picker.capacidad)

        for wave in self.waves:
            if wave["peso"] > capacidad_maxima:
                raise ValueError(
                    f"La wave {wave['id']} pesa {wave['peso']:g} kg y ningún "
                    f"picker carga tanto (máximo {capacidad_maxima:g} kg)."
                )

    # ---------- reparto de waves a pickers ----------

    def _repartir_waves_iniciales(self):
        for picker in sorted(self.pickers, key=_id_picker):
            wave = self._buscar_wave(picker)
            if wave is not None:
                self._tomar_wave(picker, wave)

    def _buscar_wave(self, picker):
        """Primera wave de la cola que el picker puede cargar (por peso)."""

        for wave in self.cola_waves:
            if wave["peso"] <= picker.capacidad:
                return wave
        return None

    def _tomar_wave(self, picker, wave):
        """El picker toma una wave de la cola y carga sus tareas."""

        for i, candidata in enumerate(self.cola_waves):
            if candidata is wave:
                del self.cola_waves[i]
                break

        wave["picker"] = picker.id
        wave["estado"] = "EN_PROCESO"

        picker.wave = wave
        picker.objetivo = None
        picker.destinos = set()
        picker.estado = "disponible"

        # La wave ya se comprobó contra la capacidad del picker en _buscar_wave.
        picker.pendientes = sorted(wave["tareas"].values(), key=_clave_tarea)

        for pedido in wave["pedidos"]:
            pedido.estado = "EN_PREPARACION"

        self.hubo_avance = True
        self._registrar(
            f"{picker.id}: toma la wave {wave['id']} "
            f"({len(wave['pedidos'])} pedidos, {len(picker.pendientes)} productos)."
        )
        self._actualizar_pedidos()

    def _llegar_a_despacho(self, picker):
        """El picker llegó a despacho con su wave lista: toma otra o termina."""

        self.hubo_avance = True

        if picker.wave is not None:
            picker.wave["estado"] = "COMPLETADA"
            picker.waves_hechas.append(picker.wave["id"])
            self._registrar(f"{picker.id}: completó la wave {picker.wave['id']}.")
            picker.wave = None

        siguiente = self._buscar_wave(picker)

        if siguiente is not None:
            self._tomar_wave(picker, siguiente)
        else:
            picker.estado = "terminado"
            self._registrar(f"{picker.id}: llegó a despacho.")


    def paso(self):
        """Avanza la simulación un tick."""

        if self.terminada:
            return self.estado()

        self.tick += 1
        self.hubo_avance = False

        # El orden de movimiento es determinista.
        for picker in sorted(self.pickers, key=_id_picker):
            if picker.estado in ("terminado", "bloqueado"):
                continue

            self._avanzar(picker)

        # Congestión: cuántos pickers pasaron este tick esperando a otro.
        for picker in self.pickers:
            if picker.estado == "esperando":
                self.ticks_espera += 1

        self._actualizar_pedidos()
        self._detectar_bloqueo()

        if all(p.estado in ("terminado", "bloqueado") for p in self.pickers):
            self.terminada = True
            self._registrar("Simulación finalizada.")

        return self.estado()

    def _detectar_bloqueo(self):
        """Si pasan LIMITE_BLOQUEO ticks sin avance, los pickers que siguen
        en juego pasan a 'bloqueado' para que la simulación pueda terminar."""

        if self.hubo_avance:
            self.ticks_sin_avance = 0
            return

        self.ticks_sin_avance += 1

        if self.ticks_sin_avance < LIMITE_BLOQUEO:
            return

        for picker in self.pickers:
            if picker.estado != "terminado":
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


    def _ocupadas(self, picker):
        """Celdas ocupadas por los demás pickers que siguen en juego.
        Un picker terminado (ya entregó en despacho) no bloquea celdas."""

        ocupadas = set()
        for otro in self.pickers:
            if otro is not picker and otro.estado != "terminado":
                ocupadas.add(otro.pos)
        return ocupadas

    def _avanzar(self, picker):
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
        """Elige la tarea pendiente cuyo acceso tenga una ruta más corta."""

        ocupadas = self._ocupadas(picker)

        mejor_tarea = None
        mejor_ruta = None
        mejor_acceso = None

        for tarea in sorted(picker.pendientes, key=_clave_tarea):
            producto = self.productos[tarea["producto_id"]]
            x = producto.ubicacion[0]
            y = producto.ubicacion[1]

            accesos = self.nav.accesos(x, y)

            if not accesos:
                continue

            ruta = self.nav.camino(picker.pos, accesos, ocupadas=ocupadas)

            if ruta is None:
                continue

            if (
                mejor_ruta is None
                or len(ruta) < len(mejor_ruta)
                or (
                    len(ruta) == len(mejor_ruta)
                    and tarea["producto_id"] < mejor_tarea["producto_id"]
                )
            ):
                mejor_tarea = tarea
                mejor_ruta = ruta
                mejor_acceso = ruta[-1] if ruta else picker.pos

        if mejor_tarea is None:
            picker.estado = "esperando"
            self._registrar(f"{picker.id}: no hay ruta disponible por ahora.")
            return

        picker.objetivo = mejor_tarea
        picker.destinos = {mejor_acceso}
        picker.ruta = list(mejor_ruta)
        picker.estado = "yendo_a_producto"

        self._registrar(f"{picker.id}: se dirige a {mejor_tarea['producto_id']}.")

    def _recoger(self, picker):
        """Recoge las líneas de la tarea con Picker.pick (las marca como recogidas;
        el stock ya se reservó cuando se armó la wave)."""

        tarea = picker.objetivo

        if tarea is None:
            return

        producto = self.productos[tarea["producto_id"]]
        cantidad = tarea["cantidad"]

        for linea in tarea["lineas"]:
            picker.entidad.pick(linea["item"])

            picker.recogidos.append({
                "producto_id": producto.id,
                "pedido_id": linea["pedido_id"],
                "cantidad": linea["cantidad"],
            })

        picker.pendientes.remove(tarea)
        picker.objetivo = None
        picker.destinos = set()
        picker.estado = "disponible"
        self.hubo_avance = True

        self._registrar(
            f"{picker.id}: recogió {cantidad} unidades de {producto.id}."
        )

        self._actualizar_pedidos()


    def _planificar_regreso(self, picker):
        """Planifica el regreso a despacho al terminar sus tareas."""

        if picker.pos in self.nav.despacho:
            self._llegar_a_despacho(picker)
            return

        ruta = self.nav.camino(
            picker.pos,
            self.nav.despacho,
            ocupadas=self._ocupadas(picker),
        )

        if ruta is None:
            picker.estado = "esperando"
            return

        picker.ruta = list(ruta)
        picker.destinos = set(self.nav.despacho)
        picker.estado = "regresando"

        if not picker.ruta and picker.pos in self.nav.despacho:
            self._llegar_a_despacho(picker)


    def _mover(self, picker):
        """Mueve al preparador una celda, sin ocupar celdas ajenas."""

        if not picker.ruta:
            return

        siguiente = picker.ruta[0]

        if siguiente in self._ocupadas(picker):
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
            picker.estado = "esperando"
            self._replanificar(picker)
            return

        anterior = picker.pos
        picker.anterior = anterior
        picker.pos = siguiente
        picker.trail.append(siguiente)
        picker.ruta.pop(0)
        self.hubo_avance = True

        self._registrar(f"{picker.id}: {anterior} -> {siguiente}.")

        if picker.estado == "regresando" and picker.pos in self.nav.despacho:
            picker.ruta = []
            self._llegar_a_despacho(picker)

    def _replanificar(self, picker):
        """Intenta encontrar una ruta alternativa."""

        if picker.objetivo is not None:
            producto = self.productos[picker.objetivo["producto_id"]]
            destinos = self.nav.accesos(producto.ubicacion[0], producto.ubicacion[1])
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


    def _actualizar_pedidos(self):
        """Actualiza el estado de los pedidos: los de una wave que todavía
        espera en la cola siguen PENDIENTES."""

        for wave in self.waves:
            en_cola = wave["picker"] is None

            for pedido in wave["pedidos"]:
                if en_cola:
                    pedido.estado = "PENDIENTE"
                    continue

                todos_recogidos = True
                algun_fallido = False

                for indice, item in enumerate(pedido.items):
                    if not item.picked:
                        todos_recogidos = False
                    if (pedido.id, indice) in self.fallidas:
                        algun_fallido = True

                if todos_recogidos and not algun_fallido:
                    pedido.estado = "PREPARADO"
                else:
                    pedido.estado = "EN_PREPARACION"

    def _registrar(self, mensaje):
        self.log.append(f"[Tick {self.tick}] {mensaje}")

        if len(self.log) > 200:
            self.log.pop(0)


    def estado(self):
        """Devuelve una instantánea del estado para la interfaz gráfica."""

        return {
            "tick": self.tick,
            "terminada": self.terminada,
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
                    "wave_id": p.wave["id"] if p.wave else None,
                    "waves_hechas": list(p.waves_hechas),
                }
                for p in self.pickers
            ],
            "waves": [
                {
                    "id": w["id"],
                    "estado": w["estado"],
                    "picker": w["picker"],
                    "pedidos": [pedido.id for pedido in w["pedidos"]],
                }
                for w in self.waves
            ],
            "productos": {
                producto_id: producto.stock
                for producto_id, producto in self.productos.items()
            },
            "pedidos": [
                {
                    "id": pedido.id,
                    "estado": pedido.estado,
                    "items_picked": [item.picked for item in pedido.items],
                }
                for pedido in self.pedidos_wave
            ],
            "log": list(self.log),
            "fallidas": [list(fallida) for fallida in self.fallidas],
            "pedidos_wave_ids": [pedido.id for pedido in self.pedidos_wave],
        }

    def restaurar(self, estado):
        """Restaura el progreso de una instantánea guardada.
        Parte de un reinicio con las mismas waves que se guardaron (el stock
        reservado sale de ahí) y reproduce los pick solo para marcar los ítems
        como recogidos."""

        # Las waves se reconstruyen con lo guardado: no dependen del generador.
        self.waves_entrada = []
        for guardada in estado["waves"]:
            pedidos = []
            for id_pedido in guardada["pedidos"]:
                pedidos.append({"id": id_pedido})
            self.waves_entrada.append({"id": guardada["id"], "orders": pedidos})

        self.reiniciar()

        # Deshace el reparto inicial: la partida dice qué wave tiene cada picker.
        self.cola_waves = sorted(self.waves, key=_clave_cola)
        waves_por_id = {}
        for wave in self.waves:
            wave["picker"] = None
            wave["estado"] = "CREADA"
            waves_por_id[wave["id"]] = wave

        for picker in self.pickers:
            picker.wave = None
            picker.pendientes = []
            picker.objetivo = None
            picker.waves_hechas = []

        self.tick = estado["tick"]
        self.terminada = estado["terminada"]
        self.log = list(estado.get("log", []))

        self.fallidas = {tuple(fallida) for fallida in estado.get("fallidas", [])}

        for guardada in estado["waves"]:
            wave = waves_por_id.get(guardada["id"])

            if wave is None:
                continue

            wave["picker"] = guardada["picker"]
            wave["estado"] = guardada["estado"]

            if guardada["picker"] is not None:
                self.cola_waves.remove(wave)

        pedidos_por_id = {}
        for pedido in self.pedidos_wave:
            pedidos_por_id[pedido.id] = pedido

        for guardado in estado["pedidos"]:
            pedido = pedidos_por_id.get(guardado["id"])

            if pedido is None:
                continue

            for indice, picked in enumerate(guardado.get("items_picked", [])):
                if indice < len(pedido.items):
                    if picked and not pedido.items[indice].picked:
                        pedido.items[indice].pick_item()

            pedido.estado = guardado["estado"]

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
            picker.destinos = {tuple(d) for d in guardado.get("destinos", [])}
            picker.waves_hechas = list(guardado.get("waves_hechas", []))

            picker.wave = waves_por_id.get(guardado["wave_id"])

            picker.pendientes = []
            picker.objetivo = None

            if picker.wave is not None:
                for producto_id in guardado["pendientes"]:
                    if producto_id in picker.wave["tareas"]:
                        picker.pendientes.append(picker.wave["tareas"][producto_id])

                picker.objetivo = picker.wave["tareas"].get(guardado["objetivo"])
