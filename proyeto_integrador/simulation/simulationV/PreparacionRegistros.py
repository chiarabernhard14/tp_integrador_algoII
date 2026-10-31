from dataclasses import dataclass


@dataclass(frozen=True)
class RegistroProductoPedido:
    """Solicitud de un producto dentro de un pedido, con cantidad disponible."""
    producto: object
    pedido: object
    id_pedido: str
    prioridad: int
    cantidad: int


def preparar_registros(pedidos):
    """
    Consolida líneas repetidas del mismo producto dentro de cada pedido y
    distribuye el stock disponible entre pedidos por prioridad descendente.
    No modifica el stock real del producto.
    """
    registros = []

    for pedido in pedidos:
        consolidados = {}

        for item in pedido.items:
            producto = item.producto
            if producto is None:
                raise ValueError(
                    f"El producto {item.producto_id} del pedido {pedido.id} "
                    "no está asociado a un objeto Product."
                )

            if producto.id != item.producto_id:
                raise ValueError(
                    f"El producto asociado al ítem {item.producto_id} "
                    f"no coincide con {producto.id}."
                )

            if item.cantidad <= 0:
                raise ValueError("Las cantidades solicitadas deben ser positivas.")

            if producto.id not in consolidados:
                consolidados[producto.id] = {
                    "producto": producto,
                    "cantidad": 0,
                }
            consolidados[producto.id]["cantidad"] += item.cantidad

        for datos in consolidados.values():
            registros.append(
                RegistroProductoPedido(
                    producto=datos["producto"],
                    pedido=pedido,
                    id_pedido=pedido.id,
                    prioridad=pedido.prioridad,
                    cantidad=datos["cantidad"],
                )
            )

    # Stock disponible compartido entre pedidos que solicitan el mismo producto.
    registros.sort(key=lambda r: (-r.prioridad, r.id_pedido, r.producto.id))

    stock_restante = {}
    disponibles = []

    for registro in registros:
        producto = registro.producto

        if producto.id not in stock_restante:
            stock_restante[producto.id] = producto.stock

        asignada = min(registro.cantidad, stock_restante[producto.id])
        stock_restante[producto.id] -= asignada

        if asignada:
            disponibles.append(
                RegistroProductoPedido(
                    producto=producto,
                    pedido=registro.pedido,
                    id_pedido=registro.id_pedido,
                    prioridad=registro.prioridad,
                    cantidad=asignada,
                )
            )

    # Orden estable y reproducible para K-means.
    disponibles.sort(key=lambda r: (r.id_pedido, r.producto.id))
    return disponibles
