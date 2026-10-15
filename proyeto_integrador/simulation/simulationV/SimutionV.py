from .NavegationV import Navegacion
from .CargadorV import cargar_warehouse

LIMITE_BLOQUEO = 20

def _clave_tarea(tarea):
    return (-tarea["prioridad"], tarea["producto_id"])


def _clave_pedido(pedido):
    return (-pedido.prioridad, pedido.id)


def _id_picker(picker):
    return picker.id


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

    def __init__(self, datos, wave=None):
        self.datos = datos
        self.wave = wave
        self.nav = Navegacion(cargar_warehouse(datos))
        self.reiniciar()


    def reiniciar(self):
        self.tick = 0
        self.terminada = False
        self.log = []
        self.fallidas = set()

        # NUEVO: control de bloqueo global.
        self.hubo_avance = False
        self.ticks_sin_avance = 0

        # Warehouse nuevo: stocks, racks y pedidos vuelven al estado del escenario.
        self.warehouse = cargar_warehouse(self.datos)
        self.productos = self.warehouse.productos

        self.pickers = []
        for entidad in self.warehouse.pickers.values():
            self.pickers.append(EstadoPicker(entidad))

        self.tareas = {}
        self.pedidos_wave = []
        self._cargar_wave()
        self._asignar_productos()

        self._registrar("Simulación inicializada.")


    def _cargar_wave(self):

        if self.wave is None:
            pedidos = self._armar_wave_demo()
        else:
            pedidos = self._pedidos_de_wave()

        self.pedidos_wave = pedidos

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

                if producto_id not in self.tareas:
                    self.tareas[producto_id] = {
                        "id": producto_id,
                        "producto_id": producto_id,
                        "cantidad": 0,
                        "prioridad": pedido.prioridad,
                        "lineas": [],
                    }

                tarea = self.tareas[producto_id]
                tarea["cantidad"] += item.cantidad
                tarea["prioridad"] = max(tarea["prioridad"], pedido.prioridad)

                tarea["lineas"].append({
                    "pedido_id": pedido.id,
                    "indice_item": indice,
                    "cantidad": item.cantidad,
                    "item": item,
                })

            pedido.estado = "EN_PREPARACION"

        # Detecta demandas que superan el stock disponible.
        for producto_id, tarea in list(self.tareas.items()):
            producto = self.productos[producto_id]

            if tarea["cantidad"] > producto.stock:
                self._registrar(
                    f"Stock insuficiente para {producto_id}: "
                    f"se solicitan {tarea['cantidad']} unidades y "
                    f"hay {producto.stock}."
                )

                # No asignamos una tarea que no pueda completarse.
                for linea in tarea["lineas"]:
                    self.fallidas.add((linea["pedido_id"], linea["indice_item"]))

                del self.tareas[producto_id]

    def _pedidos_de_wave(self):
        """Busca en el Warehouse de la simulación los pedidos de la ola recibida."""

        if isinstance(self.wave, dict):
            origen = self.wave.get("orders", [])
        elif hasattr(self.wave, "orders"):
            origen = self.wave.orders
        else:
            raise TypeError(
                "wave debe ser None, un dict con 'orders' o un objeto con .orders."
            )

        pedidos = []
        for pedido in origen:
            id_pedido = pedido["id"] if isinstance(pedido, dict) else pedido.id
            propio = self.warehouse.pedidos.get(id_pedido)
            if propio is None:
                raise ValueError(f"La ola referencia un pedido inexistente: {id_pedido}.")
            pedidos.append(propio)
        return pedidos

    def _armar_wave_demo(self):
        """Construye una ola respetando los límites de configuración."""

        configuracion = self.datos["configuracion"]
        max_pedidos = configuracion["wave_max_pedidos"]
        max_productos = configuracion["wave_max_productos"]

        pendientes = []
        for pedido in self.warehouse.pedidos.values():
            if pedido.estado == "PENDIENTE":
                pendientes.append(pedido)

        pendientes.sort(key=_clave_pedido)

        seleccionados = []
        cantidad_items = 0

        for pedido in pendientes:
            nuevos_items = len(pedido.items)

            if max_pedidos > 0 and len(seleccionados) >= max_pedidos:
                break

            if max_productos > 0 and cantidad_items + nuevos_items > max_productos:
                continue

            seleccionados.append(pedido)
            cantidad_items += nuevos_items

        return seleccionados


    def _asignar_productos(self):
        """Asigna cada tarea a un preparador con capacidad suficiente."""

        cargas = {}
        for picker in self.pickers:
            cargas[picker.id] = 0.0

        tareas = sorted(self.tareas.values(), key=_clave_tarea)

        for tarea in tareas:
            producto = self.productos[tarea["producto_id"]]
            peso_total = producto.peso_kg * tarea["cantidad"]

            # Entre los que tienen capacidad, el menos cargado (desempata por id).
            elegido = None
            for picker in self.pickers:
                if cargas[picker.id] + peso_total > picker.capacidad:
                    continue
                if (
                    elegido is None
                    or (cargas[picker.id], picker.id)
                    < (cargas[elegido.id], elegido.id)
                ):
                    elegido = picker

            if elegido is None:
                self._registrar(
                    f"No se pudo asignar {producto.id}: capacidad insuficiente."
                )

                for linea in tarea["lineas"]:
                    self.fallidas.add((linea["pedido_id"], linea["indice_item"]))

                continue

            elegido.pendientes.append(tarea)
            cargas[elegido.id] += peso_total

        self._actualizar_pedidos()


    def paso(self):
        """Avanza la simulación un tick."""

        if self.terminada:
            return self.estado()

        self.tick += 1
        self.hubo_avance = False  # NUEVO

        # El orden de movimiento es determinista.
        for picker in sorted(self.pickers, key=_id_picker):
            if picker.estado in ("terminado", "bloqueado"):
                continue

            self._avanzar(picker)

        self._actualizar_pedidos()
        self._detectar_bloqueo()  # NUEVO

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
            if otro is not picker and otro.estado != "terminado":  # CAMBIO
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
        """Recoge las líneas de la tarea con Picker.pick (descuenta el stock)."""

        tarea = picker.objetivo

        if tarea is None:
            return

        producto = self.productos[tarea["producto_id"]]
        cantidad = tarea["cantidad"]

        if producto.stock < cantidad:
            self._registrar(
                f"{picker.id}: stock insuficiente para "
                f"{producto.id} al intentar recoger."
            )

            for linea in tarea["lineas"]:
                self.fallidas.add((linea["pedido_id"], linea["indice_item"]))

            picker.pendientes.remove(tarea)
            picker.objetivo = None
            picker.destinos = set()
            picker.estado = "disponible"
            self.hubo_avance = True  # NUEVO
            return

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
        self.hubo_avance = True  # NUEVO

        self._registrar(
            f"{picker.id}: recogió {cantidad} unidades de {producto.id}."
        )

        self._actualizar_pedidos()


    def _planificar_regreso(self, picker):
        """Planifica el regreso a despacho al terminar sus tareas."""

        if picker.pos in self.nav.despacho:
            picker.estado = "terminado"
            self.hubo_avance = True  # NUEVO
            self._registrar(f"{picker.id}: llegó a despacho.")
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
            picker.estado = "terminado"
            self.hubo_avance = True  # NUEVO


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
        self.hubo_avance = True  # NUEVO

        self._registrar(f"{picker.id}: {anterior} -> {siguiente}.")

        if picker.estado == "regresando" and picker.pos in self.nav.despacho:
            picker.ruta = []
            picker.estado = "terminado"
            self._registrar(f"{picker.id}: llegó a despacho.")

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
        """Actualiza el estado de los pedidos de la ola."""

        for pedido in self.pedidos_wave:
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
                }
                for p in self.pickers
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
        Parte de un reinicio y reproduce los pick: el stock sale de ahí."""

        ids = estado.get("pedidos_wave_ids")
        if ids is not None:
            pedidos = []
            for id_pedido in ids:
                pedidos.append({"id": id_pedido})
            self.wave = {"orders": pedidos}

        self.reiniciar()

        self.tick = estado["tick"]
        self.terminada = estado["terminada"]
        self.log = list(estado.get("log", []))

        self.fallidas = {tuple(fallida) for fallida in estado.get("fallidas", [])}

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

            picker.pendientes = []
            for producto_id in guardado["pendientes"]:
                if producto_id in self.tareas:
                    picker.pendientes.append(self.tareas[producto_id])

            picker.objetivo = self.tareas.get(guardado["objetivo"])
