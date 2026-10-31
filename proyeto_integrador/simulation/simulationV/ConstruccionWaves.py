from dataclasses import replace

from domain.Wave import Wave


def dividir_registros(registros, max_unidades):
    """
    Divide solo solicitudes individuales cuya cantidad excede max_unidades.
    No fragmenta registros para completar el espacio sobrante de una wave.
    """
    resultado = []

    for registro in registros:
        restante = registro.cantidad

        while restante > max_unidades:
            resultado.append(replace(registro, cantidad=max_unidades))
            restante -= max_unidades

        if restante:
            resultado.append(replace(registro, cantidad=restante))

    return resultado


def construir_waves(clusters, max_pedidos, max_unidades):
    for nombre, valor in (
        ("max_pedidos", max_pedidos),
        ("max_unidades", max_unidades),
    ):
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise TypeError(f"{nombre} debe ser un entero.")
        if valor <= 0:
            raise ValueError(f"{nombre} debe ser mayor a cero.")

    waves = []
    numero_wave = 1

    for cluster in clusters:
        pendientes = sorted(
            cluster,
            key=lambda r: (-r.prioridad, r.id_pedido, r.producto.id),
        )
        pendientes = dividir_registros(pendientes, max_unidades)

        while pendientes:
            wave = Wave(
                id=f"WAVE_{numero_wave}",
                max_orders_capacity=max_pedidos,
                max_products_capacity=max_unidades,
            )
            numero_wave += 1

            pedidos_incluidos = set()
            unidades_incluidas = 0
            siguientes = []

            for registro in pendientes:
                nuevo_pedido = registro.id_pedido not in pedidos_incluidos

                if nuevo_pedido and len(pedidos_incluidos) >= max_pedidos:
                    siguientes.append(registro)
                    continue

                if unidades_incluidas + registro.cantidad > max_unidades:
                    siguientes.append(registro)
                    continue

                wave.add_product(
                    order=registro.pedido,
                    product=registro.producto,
                    quantity=registro.cantidad,
                )
                pedidos_incluidos.add(registro.id_pedido)
                unidades_incluidas += registro.cantidad

            if not wave.products:
                raise RuntimeError(
                    "No se pudo incorporar ningún registro a una wave; "
                    "revisar las capacidades y las cantidades."
                )

            waves.append(wave)
            pendientes = siguientes

    return waves
