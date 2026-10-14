import json
from RectangularElement import RectangularElement
from DoorE import Door
from DispatchZoneE import DispatchZone
from RackE import Rack
from AisleE import Aisle
from PickerE import Picker
from ProductE import Product
from OrderItemE import OrderItem
from OrderE import Order
from Warehouse import Warehouse


class ScenarioParser:

    @staticmethod
    def load_from_json(filepath: str) -> dict:
        """
        Lee un escenario en formato JSON y construye las instancias exactas
        de las clases del dominio respetando sus validaciones y setters.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. Instanciar Warehouse principal
        wh_raw = data.get("warehouse", {})
        dims = wh_raw.get("dimensiones", {})
        
        warehouse = Warehouse(
            ancho_x=dims.get("ancho_x", 0),
            largo_y=dims.get("largo_y", 0)
        )

        # 2. Cargar Puertas (Door)
        for door_data in wh_raw.get("puertas", []):
            loc = (door_data["ubicacion"]["x"], door_data["ubicacion"]["y"])
            door_obj = Door(
                id=door_data["id"],
                tipo=door_data["tipo"],
                ubicacion=loc
            )
            warehouse.add_door(door_obj)

        # 3. Cargar Zonas de Despacho (DispatchZone)
        for zd_data in wh_raw.get("zonas_despacho", []):
            loc = (zd_data["ubicacion"]["x"], zd_data["ubicacion"]["y"])
            zone_obj = DispatchZone(
                id=zd_data["id"],
                puerta_id=zd_data["puerta_id"],
                ubicacion=loc,
                ancho=zd_data["ancho"],
                alto=zd_data["alto"],
                peso_max_kg=float(zd_data["peso_max_kg"])
            )
            warehouse.add_dispatch_zone(zone_obj)

        # 4. Cargar Racks
        for rack_data in wh_raw.get("racks", []):
            loc = (rack_data["ubicacion"]["x"], rack_data["ubicacion"]["y"])
            rack_obj = Rack(
                id=rack_data["id"],
                ubicacion=loc,
                ancho=rack_data["ancho"],
                alto=rack_data["alto"]
            )
            warehouse.add_rack(rack_obj)

        # 5. Cargar Pasillos (Aisle)
        for aisle_data in wh_raw.get("pasillos", []):
            loc = (aisle_data["ubicacion"]["x"], aisle_data["ubicacion"]["y"])
            aisle_obj = Aisle(
                id=aisle_data["id"],
                ubicacion=loc,
                ancho=aisle_data["ancho"],
                alto=aisle_data["alto"],
                sentido=aisle_data.get("sentido", "AMBOS")
            )
            warehouse.add_aisle(aisle_obj)

        # 6. Cargar Pickers
        pickers_dict = {}
        for pk_data in data.get("pickers", []):
            pos = (pk_data["posicion_inicial"]["x"], pk_data["posicion_inicial"]["y"])
            picker_obj = Picker(
                id=pk_data["id"],
                posicion=pos,
                capacidad_carga_kg=float(pk_data["capacidad_carga_kg"])
            )
            warehouse.add_picker(picker_obj)
            pickers_dict[picker_obj.id] = picker_obj

        # 7. Cargar Productos (Product) y asociarlos con add_product
        products_dict = {}
        for prod_data in data.get("productos", []):
            loc = (prod_data["ubicacion"]["x"],prod_data["ubicacion"]["y"],prod_data["ubicacion"]["z"])
            prod_obj = Product(
                id=prod_data["id"],
                nombre=prod_data["nombre"],
                rack_id=prod_data["rack_id"],
                ubicacion=loc,
                stock=prod_data.get("cantidad_disponible", 0),
                peso_kg=float(prod_data.get("peso_kg", 1.0))
            )
            # warehouse.add_product busca el rack internamente por rack_id
            # y ejecuta rack.add_product(prod_obj)
            warehouse.add_product(prod_obj)
            products_dict[prod_obj.id] = prod_obj

        # 8. Cargar Pedidos (Order) y sus Ítems (OrderItem)
        for ord_data in data.get("pedidos", []):
            order_obj = Order(
                id=ord_data["id"],
                prioridad=ord_data.get("prioridad", 1),
                estado=ord_data.get("estado", "PENDIENTE")
            )
            
            for item_data in ord_data.get("items", []):
                prod_id = item_data["producto_id"]
                cant = item_data["cantidad"]
                prod_ref = products_dict.get(prod_id)
                
                # order.add_item vincula internamente OrderItem con la orden
                order_obj.add_item(
                    cantidad=cant,
                    producto_id=prod_id,
                    producto=prod_ref
                )
            
            warehouse.add_order(order_obj)

        # 9. Generar automáticamente el grafo de navegabilidad
        warehouse.build_graph()  

        config = data.get("configuracion", {})

        return {
            "warehouse": warehouse,
            "pickers": pickers_dict,
            "products": products_dict,
            "config": config
        }
