from math import ceil


def calcular_k(registros, max_unidades, max_pedidos):
    """Calcula la cantidad inicial de clusters según capacidad y demanda."""
    for nombre, valor in (
        ("max_unidades", max_unidades),
        ("max_pedidos", max_pedidos),
    ):
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise TypeError(f"{nombre} debe ser un entero.")
        if valor <= 0:
            raise ValueError(f"{nombre} debe ser mayor a cero.")

    if not registros:
        return 0

    total_unidades = sum(r.cantidad for r in registros)
    total_pedidos = len({r.id_pedido for r in registros})
    total_registros = len(registros)
    ubicaciones = {tuple(r.producto.ubicacion) for r in registros}

    k_unidades = ceil(total_unidades / max_unidades)
    k_pedidos = ceil(total_pedidos / max_pedidos)

    # K es una estimación inicial, no la cantidad definitiva de waves.
    return min(
        max(k_unidades, k_pedidos),
        total_registros,
        len(ubicaciones),
    )
