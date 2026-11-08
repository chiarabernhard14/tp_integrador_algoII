from DoorE import Door
from DispatchZoneE import DispatchZone
from RackE import Rack
from AisleE import Aisle
from PickerE import Picker
from ProductE import Product
from OrderE import Order
from OrderItemE import OrderItem
from WarehouseE import Warehouse

class WarehouseEscenario(Warehouse):

    """def add_product(self, product):
        if not isinstance(product, Product):
            raise TypeError("El elemento debe ser una instancia de Product.")
        if product.id in self._productos:
            raise ValueError("Ya existe un producto con el mismo id.")
        rack = self._racks.get(product.rack_id)
        if rack is None:
            raise ValueError("El producto no referencia un rack que exista en el warehouse.")

        x, y, z = product.ubicacion
        pila = rack.acc_stack(x, y)
        if z <= len(pila):
            raise ValueError(f"{product.id}: la posicion ({x},{y},{z}) ya esta ocupada.")
        if z > len(pila) + 1:
            product.ubicacion = (x, y, len(pila) + 1)

        pila.insert(0, product)
        product.rack = rack
        self._productos[product.id] = product"""

def _z_del_producto(datos_producto):
    return datos_producto["ubicacion"]["z"]
def cargar_warehouse(datos):
    datos_wh = datos["warehouse"]
    dim = datos_wh["dimensiones"]
    warehouse = Warehouse(dim["ancho_x"], dim["largo_y"])

    for d in datos_wh["puertas"]:
        u = d["ubicacion"]
        warehouse.add_door(Door(d["id"], d["tipo"], (u["x"], u["y"])))

    for d in datos_wh["zonas_despacho"]:
        u = d["ubicacion"]
        warehouse.add_dispatch_zone(DispatchZone(
            d["id"], d["puerta_id"], (u["x"], u["y"]),
            d["ancho"], d["alto"], d["peso_max_kg"]))

    for d in datos_wh["racks"]:
        u = d["ubicacion"]
        warehouse.add_rack(Rack(d["id"], (u["x"], u["y"]), d["ancho"], d["alto"]))

    for d in datos_wh["pasillos"]:
        u = d["ubicacion"]
        warehouse.add_aisle(Aisle(
            d["id"], (u["x"], u["y"]), d["ancho"], d["alto"], d["sentido"]))

    for d in datos["pickers"]:
        u = d["posicion_inicial"]
        warehouse.add_picker(Picker(
            d["id"], (u["x"], u["y"]), d["capacidad_carga_kg"], current_route=[]))

    for d in sorted(datos["productos"], key=_z_del_producto):
        u = d["ubicacion"]
        warehouse.add_product(Product(
            d["id"], d["nombre"], d["rack_id"], (u["x"], u["y"], u["z"]),
            acceso=None, stock=d["cantidad_disponible"], peso_kg=d["peso_kg"]))

    for d in datos["pedidos"]:
        items = []
        for it in d["items"]:
            producto = warehouse.productos.get(it["producto_id"].upper())
            if producto is None:
                raise ValueError(
                    f"El pedido {d['id']} referencia un producto inexistente: {it['producto_id']}.")
            items.append(OrderItem(
                cantidad=it["cantidad"], producto_id=it["producto_id"], producto=producto))
        warehouse.add_order(Order(d["id"], d["prioridad"], d["estado"], items=items))

    return warehouse

    if __name__ == "__main__":
        import json
        from time import perf_counter

        ruta = "domain/Entradas/escenario_grande.json"

        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)

        def medir(nombre, cargar_parte):
            inicio = perf_counter()
            resultado = cargar_parte()
            tiempo = perf_counter() - inicio
            print(f"{nombre}: {tiempo * 1000:.3f} ms")
            return resultado

        datos_wh = datos["warehouse"]
        dimensiones = datos_wh["dimensiones"]

        warehouse = medir(
            "Crear warehouse",
            lambda: WarehouseEscenario(
                dimensiones["ancho_x"],
                dimensiones["largo_y"],
            ),
        )

        medir("Cargar puertas", lambda: [
            warehouse.add_door(
                Door(d["id"], d["tipo"], (d["ubicacion"]["x"], d["ubicacion"]["y"]))
            )
            for d in datos_wh["puertas"]
        ])

        medir("Cargar zonas de despacho", lambda: [
            warehouse.add_dispatch_zone(DispatchZone(
                d["id"],
                d["puerta_id"],
                (d["ubicacion"]["x"], d["ubicacion"]["y"]),
                d["ancho"],
                d["alto"],
                d["peso_max_kg"],
            ))
            for d in datos_wh["zonas_despacho"]
        ])

        medir("Cargar racks", lambda: [
            warehouse.add_rack(Rack(
                d["id"],
                (d["ubicacion"]["x"], d["ubicacion"]["y"]),
                d["ancho"],
                d["alto"],
            ))
            for d in datos_wh["racks"]
        ])

        medir("Cargar pasillos", lambda: [
            warehouse.add_aisle(Aisle(
                d["id"],
                (d["ubicacion"]["x"], d["ubicacion"]["y"]),
                d["ancho"],
                d["alto"],
                d["sentido"],
            ))
            for d in datos_wh["pasillos"]
        ])

        medir("Cargar pickers", lambda: [
            warehouse.add_picker(Picker(
                d["id"],
                (d["posicion_inicial"]["x"], d["posicion_inicial"]["y"]),
                d["capacidad_carga_kg"],
                current_route=[],
            ))
            for d in datos["pickers"]
        ])

        def cargar_productos():
            for d in sorted(datos["productos"], key=_z_del_producto):
                u = d["ubicacion"]
                warehouse.add_product(Product(
                    d["id"],
                    d["nombre"],
                    d["rack_id"],
                    (u["x"], u["y"], u["z"]),
                    acceso=None,
                    stock=d["cantidad_disponible"],
                    peso_kg=d["peso_kg"],
                ))

        medir("Cargar productos", cargar_productos)

        def cargar_pedidos():
            for d in datos["pedidos"]:
                items = []
                for it in d["items"]:
                    producto = warehouse.productos.get(it["producto_id"].upper())
                    if producto is None:
                        raise ValueError(
                            f"El pedido {d['id']} referencia un producto inexistente: "
                            f"{it['producto_id']}."
                        )
                    items.append(OrderItem(
                        cantidad=it["cantidad"],
                        producto_id=it["producto_id"],
                        producto=producto,
                    ))
                warehouse.add_order(Order(
                    d["id"], d["prioridad"], d["estado"], items=items
                ))

        medir("Cargar pedidos e ítems", cargar_pedidos)

        print(
            "Objetos cargados:",
            f"{len(warehouse.racks)} racks,",
            f"{len(warehouse.productos)} productos,",
            f"{len(warehouse.pedidos)} pedidos,",
            f"{len(warehouse.pickers)} pickers",
        )