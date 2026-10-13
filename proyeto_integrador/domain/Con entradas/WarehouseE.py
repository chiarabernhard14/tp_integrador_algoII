from validation import validate_positive_int, validate_coordinates
from DoorE import Door
from DispatchZoneE import DispatchZone
from RackE import Rack
from AisleE import Aisle
from PickerE import Picker
from ProductE import Product
from OrderE import Order


class Warehouse:

    def __init__(
        self,
        ancho_x,
        largo_y,
        puertas={},
        dispatch_zones={},
        racks={},
        aisles={},
        pickers={},
        products={},
        orders={},
        configuracion={},
        graph={}
    ):
        self.ancho_x = ancho_x
        self.largo_y = largo_y

        self.puertas = puertas
        self.dispatch_zones = dispatch_zones
        self.racks = racks
        self.aisles = aisles
        self.pickers = pickers
        self.products = products
        self.orders = orders
        self.configuracion = configuracion
        self.graph = graph

    # Dimensiones
    @property
    def ancho_x(self):
        return self._ancho_x

    @ancho_x.setter
    def ancho_x(self, value):
        validate_positive_int(value, "El ancho del warehouse")
        self._ancho_x = value

    @property
    def largo_y(self):
        return self._largo_y

    @largo_y.setter
    def largo_y(self, value):
        validate_positive_int(value, "El largo del warehouse")
        self._largo_y = value

    # Puertas
    @property
    def puertas(self):
        return self._puertas

    @puertas.setter
    def puertas(self, value):
        if not isinstance(value, list):
            raise TypeError("puertas debe ser una lista.")
        self._puertas = []
        for p in value:
            self.add_door(p)

    def add_door(self, door):
        if not isinstance(door, Door):
            raise TypeError("El elemento debe ser una instancia de Door.")
        self.validate_inside_warehouse(door.ubicacion)
        x, y = door.ubicacion
        if not (x == 0 or x == self._ancho_x - 1 or y == 0 or y == self._largo_y - 1):
            raise ValueError(f"La puerta {door.id} debe estar en el borde del almacén.")
        self._puertas.append(door)


    @property
    def dispatch_zones(self):
        return self._zonas_despacho

    @dispatch_zones.setter
    def dispatch_zones(self, value):
        if not isinstance(value, list):
            raise TypeError("dispatch_zones debe ser una lista.")
        self._zonas_despacho = []
        for z in value:
            self.add_dispatch_zone(z)

    def add_dispatch_zone(self, zone):
        if not isinstance(zone, DispatchZone):
            raise TypeError("El elemento debe ser una instancia de DispatchZone.")
        self.validate_element_bounds(zone)

        # Validar que puerta_id exista en las puertas registradas
        puerta_ids = [d.id for d in self._puertas]
        if zone.puerta_id not in puerta_ids:
            raise ValueError(
                f"La zona de despacho {zone.id} referencia la puerta '{zone.puerta_id}' que no existe en el warehouse."
            )

        cells = set(zone.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError(f"La zona de despacho {zone.id} se superpone con un rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError(f"La zona de despacho {zone.id} se superpone con otra zona.")
        if any(d.ubicacion in cells for d in self._puertas):
            raise ValueError(f"La zona de despacho {zone.id} se superpone con una puerta.")

        self._zonas_despacho.append(zone)

    # Racks
    @property
    def racks(self):
        return self._racks

    @racks.setter
    def racks(self, value):
        if not isinstance(value, list):
            raise TypeError("racks debe ser una lista.")
        self._racks = []
        for r in value:
            self.add_rack(r)

    def add_rack(self, rack):
        if not isinstance(rack, Rack):
            raise TypeError("El elemento debe ser una instancia de Rack.")
        self.validate_element_bounds(rack)

        cells = set(rack.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError(f"El rack {rack.id} se superpone con otro rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError(f"El rack {rack.id} se superpone con una zona de despacho.")
        if any(d.ubicacion in cells for d in self._puertas):
            raise ValueError(f"El rack {rack.id} se superpone con una puerta.")
        if cells & self._occupied_by(self._pasillos):
            raise ValueError(f"El rack {rack.id} se superpone con un pasillo.")

        self._racks.append(rack)

    # Pasillos
    @property
    def pasillos(self):
        return self._pasillos

    @pasillos.setter
    def pasillos(self, value):
        if not isinstance(value, list):
            raise TypeError("pasillos debe ser una lista.")
        self._pasillos = []
        for a in value:
            self.add_aisle(a)

    @property
    def aisles(self):
        return self.pasillos

    @aisles.setter
    def aisles(self, value):
        self.pasillos = value

    def add_aisle(self, aisle):
        if not isinstance(aisle, Aisle):
            raise TypeError("El elemento debe ser una instancia de Aisle.")
        self.validate_element_bounds(aisle)

        cells = set(aisle.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError(f"El pasillo {aisle.id} no puede atravesar un rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError(f"El pasillo {aisle.id} se superpone con una zona de despacho.")
        if any(d.ubicacion in cells for d in self._puertas):
            raise ValueError(f"El pasillo {aisle.id} se superpone con una puerta.")
        for other in self._pasillos:
            if cells & set(other.cells()):
                raise ValueError(f"El pasillo {aisle.id} se superpone con el pasillo {other.id}.")

        self._pasillos.append(aisle)

    # Pickers
    @property
    def pickers(self):
        return self._pickers

    @pickers.setter
    def pickers(self, value):
        if not isinstance(value, list):
            raise TypeError("pickers debe ser una lista.")
        self._pickers = []
        for pk in value:
            self.add_picker(pk)

    def add_picker(self, picker):
        if not isinstance(picker, Picker):
            raise TypeError("El elemento debe ser una instancia de Picker.")
        self.validate_inside_warehouse(picker.posicion)
        if not self.is_aisle(picker.posicion[0], picker.posicion[1]):
            raise ValueError(
                f"La posición inicial {picker.posicion} del picker debe ser una celda de pasillo."
            )
        self._pickers.append(picker)

    # Productos
    @property
    def productos(self):
        return self._productos

    @productos.setter
    def productos(self, value):
        if not isinstance(value, list):
            raise TypeError("productos debe ser una lista.")
        self._productos = []
        for pr in value:
            self.add_product(pr)

    @property
    def products(self):
        return self.productos

    @products.setter
    def products(self, value):
        self.productos = value

    def add_product(self, product):
        if not isinstance(product, Product):
            raise TypeError("El elemento debe ser una instancia de Product.")
        px, py, _ = product.ubicacion
        self.validate_inside_warehouse((px, py))
        self._productos.append(product)

    # Pedidos
    @property
    def pedidos(self):
        return self._pedidos

    @pedidos.setter
    def pedidos(self, value):
        if not isinstance(value, list):
            raise TypeError("pedidos debe ser una lista.")
        self._pedidos = []
        for pe in value:
            self.add_order(pe)

    @property
    def orders(self):
        return self.pedidos

    @orders.setter
    def orders(self, value):
        self.pedidos = value

    def add_order(self, order):
        if not isinstance(order, Order):
            raise TypeError("El elemento debe ser una instancia de Order.")
        self._pedidos.append(order)

    # Configuración y Grafo
    @property
    def configuracion(self):
        return self._configuracion

    @configuracion.setter
    def configuracion(self, value):
        if not isinstance(value, dict):
            raise TypeError("configuracion debe ser un diccionario.")
        self._configuracion = value

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("El grafo debe ser un diccionario o lista de adyacencia.")
        self._graph = value

    # Métodos de validación y consultas espaciales
    def validate_inside_warehouse(self, node):
        x, y = node[0], node[1]
        if not (0 <= x < self._ancho_x and 0 <= y < self._largo_y):
            raise ValueError(f"El nodo ({x}, {y}) debe estar dentro de los límites del almacén.")

    def validate_element_bounds(self, element):
        for cell in element.cells():
            self.validate_inside_warehouse(cell)

    def _cells_of(self, element):
        return set(element.cells())

    def _occupied_by(self, elements):
        cells = set()
        for element in elements:
            cells |= self._cells_of(element)
        return cells

    def is_aisle(self, x, y):
        if not (0 <= x < self._ancho_x and 0 <= y < self._largo_y):
            return False
        point = (x, y)
        if point in self._occupied_by(self._racks):
            return False
        if point in self._occupied_by(self._zonas_despacho):
            return False
        if any(d.ubicacion == point for d in self._puertas):
            return False
        return True

    def get_intersections(self):
        intersections = []
        horizontales = [a for a in self._pasillos if a.ancho >= a.alto]
        verticales = [a for a in self._pasillos if a.alto > a.ancho]

        for h in horizontales:
            h_cells = set(h.cells())
            for v in verticales:
                common = h_cells & set(v.cells())
                for cell in common:
                    if cell not in intersections:
                        intersections.append(cell)
        return intersections
