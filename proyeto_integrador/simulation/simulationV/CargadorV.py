from domain.Entradas.DoorE import Door
from domain.Entradas.DispatchZoneE import DispatchZone
from domain.Entradas.RackE import Rack
from domain.Entradas.AisleE import Aisle
from domain.Entradas.PickerE import Picker
from domain.Entradas.ProductE import Product
from domain.Entradas.OrderE import Order
from domain.Entradas.OrderItemE import OrderItem
from domain.Entradas.WarehouseE import Warehouse


def cargar_warehouse(datos):
    datos_wh = datos["warehouse"]
    dim = datos_wh["dimensiones"]

    warehouse = Warehouse(dim["ancho_x"], dim["largo_y"])

    # Puertas
    for d in datos_wh["puertas"]:
        u = d["ubicacion"]
        warehouse.add_door(
            Door(d["id"], d["tipo"], (u["x"], u["y"]))
        )

    # Zonas de despacho
    for d in datos_wh["zonas_despacho"]:
        u = d["ubicacion"]
        warehouse.add_dispatch_zone(
            DispatchZone(
                d["id"],
                d["puerta_id"],
                (u["x"], u["y"]),
                d["ancho"],
                d["alto"],
                d["peso_max_kg"]
            )
        )

    # Racks
    for d in datos_wh["racks"]:
        u = d["ubicacion"]
        warehouse.add_rack(
            Rack(d["id"], (u["x"], u["y"]), d["ancho"], d["alto"])
        )

    # Pasillos
    for d in datos_wh["pasillos"]:
        u = d["ubicacion"]
        warehouse.add_aisle(
            Aisle(
                d["id"],
                (u["x"], u["y"]),
                d["ancho"],
                d["alto"],
                d["sentido"]
            )
        )

    # Pickers
    for d in datos["pickers"]:
        u = d["posicion_inicial"]
        warehouse.add_picker(
            Picker(
                d["id"],
                (u["x"], u["y"]),
                d["capacidad_carga_kg"],
                current_route=[]
            )
        )

    # Productos: primero los niveles inferiores de cada rack
    productos_ordenados = sorted(
        datos["productos"],
        key=lambda d: (d["rack_id"], d["ubicacion"]["z"])
    )

    for d in productos_ordenados:
        u = d["ubicacion"]

        warehouse.add_product(
            Product(
                d["id"],
                d["nombre"],
                d["rack_id"],
                (u["x"], u["y"], u["z"]),
                peso_kg=d["peso_kg"],
                acceso=None,
                stock=d["cantidad_disponible"]
            )
        )

    # Pedidos
    for d in datos["pedidos"]:
        items = []

        for it in d["items"]:
            producto_id = it["producto_id"].upper()
            producto = warehouse.productos.get(producto_id)

            if producto is None:
                raise ValueError(
                    f"El pedido {d['id']} referencia un producto "
                    f"inexistente: {it['producto_id']}."
                )

            items.append(
                OrderItem(
                    cantidad=it["cantidad"],
                    producto_id=producto_id,
                    producto=producto
                )
            )

        warehouse.add_order(
            Order(d["id"], d["prioridad"], d["estado"], items=items)
        )

    return warehouse