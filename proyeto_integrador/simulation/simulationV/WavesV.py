"""Armado de waves (PROVISORIO).

La generación de waves es responsabilidad de otro módulo del proyecto. Esto solo
se usa como respaldo cuando a Simulacion no se le pasan waves armadas.

Una wave es un grupo de pedidos que se prepara en un solo recorrido, y cada
wave la ejecuta UN solo picker. Por eso la cantidad de waves es también el
máximo de pickers que pueden trabajar a la vez.

Este módulo no depende de nada del proyecto, así que lo usan tanto la
simulación (para repartir el trabajo) como el generador (para validar que no
haya más pickers que waves).
"""


def _clave_pedido(pedido):
    return (-pedido.prioridad, pedido.id)


def peso_pedido(pedido):
    """Peso total (kg) de un pedido: suma de cantidad x peso de cada ítem con producto."""
    peso = 0.0
    for item in pedido.items:
        if item.producto is not None:
            peso += item.cantidad * item.producto.peso_kg
    return peso


def armar_waves(pedidos, max_pedidos, max_productos, max_peso=0):
    """Agrupa los pedidos en waves.

    max_pedidos:   máximo de pedidos por wave (0 = sin límite).
    max_productos: máximo de ítems (líneas de pedido) por wave (0 = sin límite).
    max_peso:      máximo de kg por wave (0 = sin límite). Se usa la capacidad del
                   picker más chico, así cualquier picker puede cargar cualquier wave.

    Los pedidos se recorren de mayor a menor prioridad y cada uno va a la
    primera wave donde entra; si no entra en ninguna, se abre una wave nueva.

    Devuelve (waves, excluidos):
        waves:     lista de listas de pedidos.
        excluidos: pedidos que no entran ni en una wave vacía (tienen más
                   ítems o más peso que el máximo por wave).
    """
    waves = []
    items_por_wave = []
    peso_por_wave = []
    excluidos = []

    for pedido in sorted(pedidos, key=_clave_pedido):
        cantidad_items = len(pedido.items)
        peso = peso_pedido(pedido) if max_peso > 0 else 0.0

        if max_productos > 0 and cantidad_items > max_productos:
            excluidos.append(pedido)
            continue
        if max_peso > 0 and peso > max_peso:
            excluidos.append(pedido)
            continue

        destino = None
        for i, wave in enumerate(waves):
            if max_pedidos > 0 and len(wave) >= max_pedidos:
                continue
            if max_productos > 0 and items_por_wave[i] + cantidad_items > max_productos:
                continue
            if max_peso > 0 and peso_por_wave[i] + peso > max_peso:
                continue
            destino = i
            break

        if destino is None:
            waves.append([pedido])
            items_por_wave.append(cantidad_items)
            peso_por_wave.append(peso)
        else:
            waves[destino].append(pedido)
            items_por_wave[destino] += cantidad_items
            peso_por_wave[destino] += peso

    return waves, excluidos