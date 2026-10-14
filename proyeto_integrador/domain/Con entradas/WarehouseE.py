import graphlib
from validation import validate_positive_int
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
        puertas=None,
        dispatch_zones=None,
        racks=None,
        aisles=None,
        pickers=None,
        products=None,
        orders=None,
        graph=None
    ):
        self.ancho_x = ancho_x
        self.largo_y = largo_y

        self._puertas = {}
        self._zonas_despacho = {}
        self._racks = {}
        self._pasillos = {}
        self._pickers = {}
        self._productos = {}
        self._pedidos = {}

        self.puertas = puertas if puertas is not None else {}
        self.dispatch_zones = dispatch_zones if dispatch_zones is not None else {}
        self.racks = racks if racks is not None else {}
        self.aisles = aisles if aisles is not None else {}
        self.pickers = pickers if pickers is not None else {}
        self.products = products if products is not None else {}
        self.orders = orders if orders is not None else {}
        self.graph = graph if graph is not None else {}

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
        if not isinstance(value, dict):
            raise TypeError("puertas debe ser un diccionario.")
        for door in value.values():
            self.add_door(door)

    def add_door(self, door):
        if not isinstance(door, Door):
            raise TypeError("El elemento debe ser una instancia de Door.")
        if door.id in self._puertas:
            raise ValueError(f"Ya existe una puerta con id '{door.id}'.")
        self.validate_inside_warehouse(door.ubicacion)
        x, y = door.ubicacion
        if not (x == 0 or x == self._ancho_x - 1 or y == 0 or y == self._largo_y - 1):
            raise ValueError("La puerta debe estar en el borde del almacén.")
        self._puertas[door.id] = door

    # Zonas de despacho
    @property
    def dispatch_zones(self):
        return self._zonas_despacho

    @dispatch_zones.setter
    def dispatch_zones(self, value):
        if not isinstance(value, dict):
            raise TypeError("dispatch_zones debe ser un diccionario.")
        for zone in value.values():
            self.add_dispatch_zone(zone)

    def add_dispatch_zone(self, zone):

        if not isinstance(zone, DispatchZone):
            raise TypeError("El elemento debe ser una zona de despacho.")
        if zone.id in self._zonas_despacho:
            raise ValueError("Ya se registró esta zona de despacho")
            
        self.validate_element_bounds(zone)

        try:
            door = self._puertas[zone.puerta_id]
        except KeyError:
            raise ValueError("La zona de despacho referencia una puerta que no existe en el warehouse.")

        if not(zone.contains(door.ubicacion)):
            raise ValueError("La zona de despacho no contiene a la puerta asignada.")

        cells = set(zone.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError("La zona de despacho se superpone con un rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError("La zona de despacho se superpone con otra.")
        if cells & self._occupied_by(self._pasillos):
            raise ValueError("La zona de despacho se superpone con un pasillo.")
    
        self._zonas_despacho[zone.id] = zone

    # Racks
    @property
    def racks(self):
        return self._racks

    @racks.setter
    def racks(self, value):
        if not isinstance(value, dict):
            raise TypeError("racks debe ser un diccionario.")
        for rack in value.values():
            self.add_rack(rack)

    def add_rack(self, rack):
        if not isinstance(rack, Rack):
            raise TypeError("El elemento debe ser una instancia de Rack.")
        if rack.id in self._racks:
            raise ValueError("Ya se registró este rack.")

        self.validate_element_bounds(rack)

        cells = set(rack.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError("El rack se superpone con otro rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError("El rack se superpone con una zona de despacho.")
        if cells & self._occupied_by(self._pasillos):
            raise ValueError("El rack se superpone con un pasillo.")

        self._racks[rack.id] = rack

    # Pasillos
    @property
    def pasillos(self):
        return self._pasillos

    @pasillos.setter
    def pasillos(self, value):
        if not isinstance(value, dict):
            raise TypeError("pasillos debe ser un diccionario.")
        for aisle in value.values():
            self.add_aisle(aisle)

    def add_aisle(self, aisle):
        if not isinstance(aisle, Aisle):
            raise TypeError("El elemento debe ser una instancia de Aisle.")
        if aisle.id in self._pasillos:
            raise ValueError("Ya existe un pasillo con ese id.")
        self.validate_element_bounds(aisle)

        cells = set(aisle.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError("El pasillo no puede atravesar un rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError(f"El pasillo se superpone con una zona de despacho.")

        self._pasillos[aisle.id] = aisle

    # Pickers
    @property
    def pickers(self):
        return self._pickers

    @pickers.setter
    def pickers(self, value):
        if not isinstance(value, dict):
            raise TypeError("pickers debe ser un diccionario.")
        for picker in value.values():
            self.add_picker(picker)

    def add_picker(self, picker):
        if not isinstance(picker, Picker):
            raise TypeError("El elemento debe ser una instancia de Picker.")
        if picker.id in self._pickers:
            raise ValueError("Ya existe un picker con el mismo id.")
        self.validate_inside_warehouse(picker.posicion)
        if not self.is_aisle(picker.posicion[0], picker.posicion[1]):
            raise ValueError(
                "La posición inicial {picker.posicion} del picker debe ser una celda de pasillo."
            )
        self._pickers[picker.id] = picker

    # Productos
    @property
    def productos(self):
        return self._productos

    @productos.setter
    def productos(self, value):
        if not isinstance(value, dict):
            raise TypeError("productos debe ser un diccionario.")
        for product in value.values():
            self.add_product(product)

    def add_product(self, product):
        if not isinstance(product, Product):
            raise TypeError("El elemento debe ser una instancia de Product.")
        if product.id in self._productos:
            raise ValueError("Ya existe un producto con el mismo id.")
        
        try:
            rack = self._racks[product.rack_id]
        except KeyError:
            raise ValueError("El producto no referencia un rack que exista en el warehouse.")
        
        rack.add_product


    # Pedidos
    @property
    def pedidos(self):
        return self._pedidos

    @pedidos.setter
    def pedidos(self, value):
        if not isinstance(value, dict):
            raise TypeError("pedidos debe ser un diccionario {id: Order}.")
        for order in value.values():
            self.add_order(order)

    def add_order(self, order):
        if not isinstance(order, Order):
            raise TypeError("El elemento debe ser una instancia de Order.")
        if order.id in self._pedidos:
            raise ValueError(f"Ya existe un pedido con id '{order.id}'.")
        self._pedidos[order.id] = order


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
        self.validate_inside_warehouse(element.ubicacion)
        if element.ubicacion[0] + element.ancho > self._ancho_x:
            raise ValueError("El elemento excede el ancho del almacén.")
        if element.ubicacion[1] + element.alto > self._largo_y:
            raise ValueError("El elemento excede el largo del almacén.")

    def _cells_of(self, element):
        return set(element.cells())

    def _occupied_by(self, elements):
        
        cells = set()
        for element in elements.values():
            cells |= set(element.cells())
        return cells
    
    def build_graph_by_cell(self):
        aisle_cells = self._occupied_by(self._aisles)
        for a in self._aisles.values():
            vertices = a.cells()

            for v in vertices:
                x, y = v
                if a.sentido != "N" and (x, y - 1) in aisle_cells:  # ir al S
                    self._agregar_arista((x, y), (x, y - 1), 1)

                if a.sentido != "S" and (x, y + 1) in aisle_cells:  # ir al N
                    self._agregar_arista((x, y), (x, y + 1), 1)

                if a.sentido != "E" and (x - 1, y) in aisle_cells:  # ir al O
                    self._agregar_arista((x, y), (x - 1, y), 1)

                if a.sentido != "O" and (x + 1, y) in aisle_cells:  # ir al E
                    self._agregar_arista((x, y), (x + 1, y), 1)
            


    def build_graph(self):
        aisle_cells = self._occupied_by(self._aisles)
        for a in self._aisles.values():
            x0, y0 = a.ubicacion
            y_sup = y0 + a.alto - 1
            x_der = x0 + a.ancho - 1

            if a.sentido != "N":  # se puede ir al S
                for i in range(a.ancho):
                    x = x0 + i
                    fin = y0 - 1 if (x, y0 - 1) in aisle_cells else y0
                    self.linea_vertical(x, y_sup, fin, -1)

            if a.sentido != "S":  # se puede ir al N
                for i in range(a.ancho):
                    x = x0 + i
                    fin = y_sup + 1 if (x, y_sup + 1) in aisle_cells else y_sup
                    self.linea_vertical(x, y0, fin, 1)

            if a.sentido != "E":  # se puede ir al O
                for j in range(a.alto):
                    y = y0 + j
                    fin = x0 - 1 if (x0 - 1, y) in aisle_cells else x0
                    self.linea_horizontal(y, x_der, fin, -1)

            if a.sentido != "O":  # se puede ir al E
                for j in range(a.alto):
                    y = y0 + j
                    fin = x_der + 1 if (x_der + 1, y) in aisle_cells else x_der
                    self.linea_horizontal(y, x0, fin, 1)

    def linea_vertical(self, x, inicio, fin, incr):
        for y in range(inicio, fin, incr):
            self._agregar_arista((x, y), (x, y + incr))

    def linea_horizontal(self, y, inicio, fin, incr):
        for x in range(inicio, fin, incr):
            self._agregar_arista((x, y), (x + incr, y))

    def _agregar_arista(self, origen, destino, distancia=1):
        self.graph.setdefault(origen, [])
        self.graph.setdefault(destino, [])
        if all(nodo != destino for nodo, _ in self.graph[origen]):
            self.graph[origen].insert(0, (destino, distancia))

            
        





