"""Construcción de waves a partir de tareas pendientes."""


def _construir_waves_intermedias(
    tareas, productos, pickers, max_pedidos, max_unidades, accesos,
    despacho, posiciones_iniciales, distancia, distancia_productos,
    accesible_desde_un_origen, existe_secuencia_factible,
):
    """Agrupa tareas por prioridad y cercanía respetando límites y factibilidad."""
    # Las tareas pueden dividirse entre waves si lo exigen los límites.

    capacidad_maxima = max(p["capacidad_carga_kg"] for p in pickers)
    capacidad_total_pickers = sum(p["capacidad_carga_kg"] for p in pickers)
    # El escenario representa un depósito real: todo producto existente con
    # stock reservado debe tener un acceso y un recorrido válido de ida y vuelta.
    # Si no se cumple, es un error de los datos/grafo, no una cantidad pendiente
    # por falta de stock. No descartamos silenciosamente el producto.
    productos_validados = set()
    for tarea in tareas:
        pid = tarea["producto_id"]
        if pid not in productos_validados:
            if not accesos.get(pid) or not accesible_desde_un_origen(pid):
                raise ValueError(
                    f"El producto {pid} tiene stock disponible pero no existe un recorrido "
                    "válido desde una posición de inicio hasta el producto y de regreso al despacho. "
                    "Revisá la conectividad del grafo y los accesos de la ubicación."
                )
            productos_validados.add(pid)
        if productos[pid]["peso_kg"] > capacidad_maxima + 1e-9:
            raise ValueError(f"No hay asignación factible: una unidad del producto {pid} supera la capacidad de todos los pickers")
    if not tareas:
        return []

    waves_intermedias = []
    prioridades = sorted({t["prioridad"] for t in tareas}, reverse=True)
    for prioridad in prioridades:
        while any(t["restante"] > 0 and t["prioridad"] == prioridad for t in tareas):
            pendientes_prioridad = [t for t in tareas
                                    if t["restante"] > 0 and t["prioridad"] == prioridad]
            semilla = pendientes_prioridad[0]
            wave = {
                "prioridad": prioridad,
                "items": [],
                "ids_pedidos": set(),
                "unidades": 0,
                "peso": 0.0,
                "ultimo_producto": None,
            }

            def puede_agregar(tarea):
                pid = tarea["producto_id"]
                nuevo_pedido = tarea["pedido_id"] not in wave["ids_pedidos"]
                if nuevo_pedido and len(wave["ids_pedidos"]) >= max_pedidos:
                    return False
                if wave["unidades"] >= max_unidades:
                    return False
                peso_unitario = productos[pid]["peso_kg"]
                capacidad_peso_restante = capacidad_total_pickers - wave["peso"]
                unidades_por_peso = int((capacidad_peso_restante + 1e-9) // peso_unitario)
                unidades_por_limite = max_unidades - wave["unidades"]
                return min(tarea["restante"], unidades_por_peso, unidades_por_limite) > 0

            def candidatos():
                opciones = []
                for tarea in tareas:
                    if tarea["restante"] <= 0 or tarea["prioridad"] != prioridad:
                        continue
                    if not puede_agregar(tarea):
                        continue
                    pid = tarea["producto_id"]
                    productos_actuales = [item[1] for item in wave["items"]]
                    if wave["ultimo_producto"] is None:
                        d = min((distancia(origen, acceso)
                                 for origen in despacho + posiciones_iniciales
                                 for acceso in accesos[pid]),
                                default=float("inf"))
                    else:
                        d = distancia_productos(wave["ultimo_producto"], pid)
                        # Si no hay camino desde el último producto, usamos
                        # la cercanía a cualquiera de los productos ya incluidos
                        # solo como criterio de orden; la factibilidad se decide
                        # comprobando una secuencia completa, no ese par aislado.
                        if d == float("inf"):
                            d = min((distancia_productos(actual, pid)
                                     for actual in productos_actuales),
                                    default=float("inf"))
                    if existe_secuencia_factible(productos_actuales + [pid]):
                        opciones.append((d, str(tarea["pedido_id"]), str(pid), tarea))
                return opciones

            # Incorporar semilla. La cantidad puede reducirse por los límites
            # configurables de unidades y de peso de la wave.
            while True:
                if wave["ultimo_producto"] is None:
                    tarea = semilla
                    pid = tarea["producto_id"]
                    peso_unitario = productos[pid]["peso_kg"]
                    unidades_por_peso = int((capacidad_total_pickers + 1e-9) // peso_unitario)
                    unidades_por_limite = max_unidades
                    q = min(tarea["restante"], unidades_por_peso, unidades_por_limite)
                    if q <= 0:
                        raise ValueError(
                            f"No se puede incorporar el producto {pid} a ninguna wave; "
                            "revisá los límites y las capacidades de los pickers."
                        )
                    wave["items"].append((tarea["pedido_id"], pid, q))
                    wave["ids_pedidos"].add(tarea["pedido_id"])
                    wave["unidades"] += q
                    wave["peso"] += productos[pid]["peso_kg"] * q
                    wave["ultimo_producto"] = pid
                    tarea["restante"] -= q
                    if tarea["restante"] > 0 or wave["unidades"] >= max_unidades:
                        break
                    continue

                # Vecino más cercano global: comparar todos los productos
                # admisibles de la prioridad actual, sin preferir un pedido.
                opciones = candidatos()
                if not opciones:
                    break
                _, _, _, elegida = min(opciones, key=lambda x: (x[0], x[1], x[2]))
                pid = elegida["producto_id"]
                peso_unitario = productos[pid]["peso_kg"]
                unidades_por_peso = int((capacidad_total_pickers - wave["peso"] + 1e-9) // peso_unitario)
                unidades_por_limite = max_unidades - wave["unidades"]
                q = min(elegida["restante"], unidades_por_peso, unidades_por_limite)
                if q <= 0:
                    break
                wave["items"].append((elegida["pedido_id"], pid, q))
                wave["ids_pedidos"].add(elegida["pedido_id"])
                wave["unidades"] += q
                wave["peso"] += productos[pid]["peso_kg"] * q
                wave["ultimo_producto"] = pid
                elegida["restante"] -= q
                if wave["unidades"] >= max_unidades:
                    break

            if wave["items"]:
                waves_intermedias.append(wave)
            else:
                # No se descartan cantidades pendientes silenciosamente.
                raise ValueError(
                    f"No se pudo planificar el producto {semilla['producto_id']} "
                    f"del pedido {semilla['pedido_id']}; revisá los límites y la factibilidad."
                )
    return waves_intermedias
