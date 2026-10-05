from domain.warehouse import DispatchZone
from domain.warehouse import Aisle
from domain.warehouse import Rack
from validation import validate_start_end, validate_coordinates

class Warehouse:

    def __init__(self, width=0, height=0, dispatch_zones=[], racks=[], aisles=[], graph=None):
        self.width = width
        self.height = height
        self.graph = graph
        self.aisles = aisles
        self.racks = racks
        self.dispatch_zones = dispatch_zones

    def validate_inside_warehouse(self, node):
        if not (0 <= node[0] <= self.width and 0 <= node[1] <= self.height):
            raise ValueError("El nodo debe estar dentro de los límites del almacén.")

    def validate_node(self, node, second=None):

        self.validate_inside_warehouse(node)

        if second is not None:
            self.validate_inside_warehouse(second)
            return validate_start_end(node, second)
        
        validate_coordinates(node)
            

    def validate_door(self, nodo_constante, nodo1_var, nodo2_var, max_constante, door_constante, door_var):
        if nodo1_var > door_var or nodo2_var < door_var:
            raise ValueError("La puerta debe estar dentro de la zona de despacho")
        zone_constante = abs(nodo1_var-nodo2_var)

        if nodo_constante < max_constante/2:
            if door_constante!=0:
                raise ValueError("La puerta debe estar en el perímetro del almacén")
            zone_variable = nodo_constante
        else:
            if door_constante!=max_constante:
                raise ValueError("La puerta debe estar en el perímetro del almacén")
            zone_variable = max_constante-nodo_constante
        
        return zone_constante, zone_variable
        

    def add_dispatch_zone(self, nodes, door):
        
        nodes[0], nodes[1] = self.validate_node(nodes[0], nodes[1])

        self.validate_node(door)

        if nodes[0][0]==nodes[1][0]:
            zone_h, zone_w = self.validate_door(nodes[0][0], nodes[0][1], nodes[1][1], self.width, door[0], door[1])     
        else:
            zone_w, zone_h = self.validate_door(nodes[0][1], nodes[0][0], nodes[1][0], self.height, door[1], door[0])
        
        zone = DispatchZone(nodes, door)
        
        self._dispatch_zones.append(zone)

    def add_aisle(self, aisle):
        if not isinstance(aisle, Aisle):
            raise TypeError("El elemento a agregar debe ser una instancia de Aisle.")

    def add_rack(self, rack):
        if not isinstance(rack, Rack):
            raise TypeError("El elemento a agregar debe ser una instancia de Rack.")

    #Properties y Setters

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("El grafo debe ser un diccionario o lista de adyacencia.")
        self._graph = value

    @property
    def aisles(self):
        return self._aisles

    @aisles.setter
    def aisles(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("aisles debe ser un diccionario o lista de pasillos.")
        self._aisles = value

    @property
    def stacks(self):
        return self._stacks

    @stacks.setter
    def stacks(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("stacks debe ser un diccionario o lista de estanterías.")
        self._stacks = value

    @property
    def products(self):
        return self._products

    @products.setter
    def products(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("products debe ser un diccionario o lista de productos.")
        self._products = value

    @property
    def dispatch_zones(self):
        return self._dispatch_zones

    @dispatch_zones.setter
    def dispatch_zones(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("dispatch_zones debe ser un diccionario o lista de zonas de despacho.")
        self._dispatch_zones = value



    def get_intersections(self):
        intersections = []

        horizontales = [a for a in self.aisles if a.direction == "HORIZONTAL"]
        verticales   = [a for a in self.aisles if a.direction == "VERTICAL"]

        for h in horizontales:
            x_min = min(h.start_node[0], h.end_node[0])
            x_max = max(h.start_node[0], h.end_node[0])
            y_h   = h.start_node[1]  # y fijo del pasillo horizontal

            for v in verticales:
                y_min = min(v.start_node[1], v.end_node[1])
                y_max = max(v.start_node[1], v.end_node[1])
                x_v   = v.start_node[0]  # x fijo del pasillo vertical

                if x_min <= x_v <= x_max and y_min <= y_h <= y_max:
                    intersections.append((x_v, y_h))

        return intersections