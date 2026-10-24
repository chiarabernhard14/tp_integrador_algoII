"""Asignación de las tareas de cada wave a pickers."""
from collections import defaultdict
from domain.Wave import Wave


def _asignar_pickers_a_waves(
    waves_intermedias, productos, pickers, max_pedidos, max_unidades,
    objetos_pedido_por_id, distancia, accesos, despacho, calcular_recorrido,
):
    """Distribuye los productos entre pickers y construye los objetos Wave."""
    usados_alguna_vez = set()
    usados_por_prioridad = defaultdict(set)
    resultado = []
    for indice, wave in enumerate(waves_intermedias, 1):
        pickers_ya_usados_antes = set(usados_alguna_vez)
        items_por_picker = {p["id"]: [] for p in pickers}
        carga_por_picker = {p["id"]: 0.0 for p in pickers}
        for pedido_id, pid, cantidad in wave["items"]:
            peso_unitario = productos[pid]["peso_kg"]
            restante = cantidad
            while restante > 0:
                opciones_picker = []
                for picker in pickers:
                    pkid = picker["id"]
                    capacidad_restante = picker["capacidad_carga_kg"] - carga_por_picker[pkid]
                    unidades_cabida = int((capacidad_restante + 1e-9) // peso_unitario)
                    if unidades_cabida <= 0:
                        continue
                    pos = picker["posicion_inicial"]
                    origenes = ([(pos["x"], pos["y"])] if pkid not in usados_alguna_vez
                                else despacho)
                    d = min((distancia(origen, acceso)
                             for origen in origenes for acceso in accesos[pid]),
                            default=float("inf"))
                    if d < float("inf"):
                        opciones_picker.append((pkid in usados_por_prioridad[wave["prioridad"]],
                                                d, str(pkid), picker, unidades_cabida))
                if not opciones_picker:
                    raise ValueError(
                        f"No hay picker alcanzable con capacidad disponible para el producto {pid}"
                    )
                _, _, _, picker, unidades_cabida = min(
                    opciones_picker, key=lambda x: (x[0], x[1], x[2])
                )
                pkid = picker["id"]
                q = min(restante, unidades_cabida)
                items_por_picker[pkid].append((pedido_id, pid, q))
                carga_por_picker[pkid] += peso_unitario * q
                usados_alguna_vez.add(pkid)
                usados_por_prioridad[wave["prioridad"]].add(pkid)
                restante -= q
        asignaciones = []
        for picker in pickers:
            pkid = picker["id"]
            items_picker = items_por_picker[pkid]
            if not items_picker:
                continue
            productos_picker = [pid for _, pid, _ in items_picker]
            if pkid in pickers_ya_usados_antes:
                origenes = despacho
            else:
                pos = picker["posicion_inicial"]
                origenes = [(pos["x"], pos["y"])]
            ruta, distancia_total = calcular_recorrido(productos_picker, origenes)
            asignaciones.append({
                "picker": pkid,
                "items": items_picker,
                "route": ruta,
                "distance": distancia_total,
            })
        pedidos_incluidos_ids = sorted(
            {pedido_id for asignacion in asignaciones
             for pedido_id, _producto_id, _cantidad in asignacion["items"]},
            key=str,
        )
        pedidos_incluidos = [objetos_pedido_por_id[str(oid).upper()] for oid in pedidos_incluidos_ids]
        resultado.append(Wave(
            id=f"W{indice}",
            orders=pedidos_incluidos,
            max_orders_capacity=(0 if max_pedidos == float("inf") else max_pedidos),
            max_products_capacity=(0 if max_unidades == float("inf") else max_unidades),
            prioridad=wave["prioridad"],
            orden_ejecucion=indice,
            picker_assignments=asignaciones,
            total_distance=sum(a["distance"] for a in asignaciones),
        ))
    return resultado
