"""Construye el modelo de dominio usado por la simulación desde un escenario."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.Entradas.AisleE import Aisle
from domain.Entradas.DispatchZoneE import DispatchZone
from domain.Entradas.DoorE import Door
from domain.Entradas.OrderE import Order
from domain.Entradas.OrderItemE import OrderItem
from domain.Entradas.PickerE import Picker
from domain.Entradas.ProductE import Product
from domain.Entradas.RackE import Rack
from domain.Entradas.WarehouseE import Warehouse


def _nivel_producto(datos_producto):
    return datos_producto["rack_id"], datos_producto["ubicacion"]["z"]


def cargar_warehouse(datos):
    """Convierte los datos serializados del escenario en objetos de dominio."""
    datos_warehouse = datos["warehouse"]
    dimensiones = datos_warehouse["dimensiones"]
    warehouse = Warehouse(dimensiones["ancho_x"], dimensiones["largo_y"])

    for dato in datos_warehouse["puertas"]:
        ubicacion = dato["ubicacion"]
        warehouse.add_door(
            Door(dato["id"], dato["tipo"], (ubicacion["x"], ubicacion["y"]))
        )

    for dato in datos_warehouse["zonas_despacho"]:
        ubicacion = dato["ubicacion"]
        warehouse.add_dispatch_zone(
            DispatchZone(
                dato["id"],
                dato["puerta_id"],
                (ubicacion["x"], ubicacion["y"]),
                dato["ancho"],
                dato["alto"],
                dato["peso_max_kg"],
            )
        )

    for dato in datos_warehouse["racks"]:
        ubicacion = dato["ubicacion"]
        warehouse.add_rack(
            Rack(
                dato["id"],
                (ubicacion["x"], ubicacion["y"]),
                dato["ancho"],
                dato["alto"],
            )
        )

    for dato in datos_warehouse["pasillos"]:
        ubicacion = dato["ubicacion"]
        warehouse.add_aisle(
            Aisle(
                dato["id"],
                (ubicacion["x"], ubicacion["y"]),
                dato["ancho"],
                dato["alto"],
                dato["sentido"],
            )
        )

    for dato in datos["pickers"]:
        ubicacion = dato["posicion_inicial"]
        warehouse.add_picker(
            Picker(
                dato["id"],
                (ubicacion["x"], ubicacion["y"]),
                dato["capacidad_carga_kg"],
                current_route=[],
            )
        )

    # Los productos se insertan desde los niveles inferiores de cada rack.
    for dato in sorted(datos["productos"], key=_nivel_producto):
        ubicacion = dato["ubicacion"]
        warehouse.add_product(
            Product(
                dato["id"],
                dato["nombre"],
                dato["rack_id"],
                (ubicacion["x"], ubicacion["y"], ubicacion["z"]),
                peso_kg=dato["peso_kg"],
                acceso=None,
                stock=dato["cantidad_disponible"],
            )
        )

    for dato in datos["pedidos"]:
        items = []
        for item in dato["items"]:
            producto_id = item["producto_id"].upper()
            producto = warehouse.productos.get(producto_id)
            if producto is None:
                raise ValueError(
                    f"El pedido {dato['id']} referencia un producto "
                    f"inexistente: {item['producto_id']}."
                )
            items.append(
                OrderItem(
                    cantidad=item["cantidad"],
                    producto_id=producto_id,
                    producto=producto,
                )
            )
        warehouse.add_order(
            Order(dato["id"], dato["prioridad"], dato["estado"], items=items)
        )

    return warehouse
