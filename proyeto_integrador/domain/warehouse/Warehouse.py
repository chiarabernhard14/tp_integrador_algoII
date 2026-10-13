from domain.warehouse import Aisle2
from domain.warehouse import DispatchZone
from domain.warehouse import Aisle
from domain.warehouse import Rack
from validation import validate_start_end, validate_coordinates, validate_positive_int

class Warehouse:

    def __init__(self, width, height, dispatch_zones=[], racks=[], aisles=[], graph={}):
        self.width = width
        self.height = height
        self.graph = graph
        self.aisles = aisles
        self.racks = racks
        self.dispatch_zones = dispatch_zones

    """
    Si dejamos esto nos aseguramos que pase por las validaciones de abajo, 
    si no no lo haia, el estante entraba directo. 
    def __init__(self, width, height, graph=None):
        self.width = width
        self.height = height
        self.graph = graph if graph is not None else {}
        self._aisles = []
        self._racks = []
        self._dispatch_zones = []
    """
    

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
        
        if len(nodes) != 2:
            raise TypeError("nodes debe contener exactamente dos puntos.")

        start, end = self.validate_node(nodes[0], nodes[1])
        self.validate_node(door)

        if start[0] == end[0]:
            zone_h, zone_w = self.validate_door(start[0], start[1], end[1], self.width, door[0], door[1])
        else:
            zone_w, zone_h = self.validate_door(start[1], start[0], end[0], self.height, door[1], door[0])

        if zone_w <= 0 or zone_h <= 0:
            raise ValueError("La zona de despacho debe tener área mayor que cero.")
        
        zone = DispatchZone([start, end], door, zone_w, zone_h)

        zone_cells = self._zone_cells(zone)

        if zone_cells & self._occupied_by(self._racks):
            raise ValueError("La zona de despacho no puede superponerse con un estante.")
        if zone_cells & self._occupied_by_zones():
            raise ValueError("La zona de despacho no puede superponerse con otra zona.")
        
        self._dispatch_zones.append(zone)
    
    def add_rack(self, start, end):

        start, end = self.validate_node(start, end)

        rack = Rack(start, end)

        cells = self._cells_of(rack)

        if cells & self._occupied_by(self._racks):
            raise ValueError("El estante se superpone con otro estante.")
        if cells & self._occupied_by(self._aisles):
            raise ValueError("El estante no puede estar sobre un pasillo.")
        if cells & self._occupied_by_zones():
            raise ValueError("El estante no puede estar dentro de una zona de despacho.")
        if not self._touches_aisle(cells):
            raise ValueError("El estante debe estar junto a un pasillo para ser alcanzable.")

        self._racks.append(rack)


    def add_aisle(self, start_node, end_node):
            
        start_node, end_node = self.validate_node(start_node, end_node)

        aisle = Aisle(start_node, end_node)
        cells = self._cells_of(aisle)

        if cells & self._occupied_by(self._racks):
            raise ValueError("El pasillo no puede atravesar un estante.")


        for other in self._aisles:
            if other.direction == aisle.direction and cells & self._cells_of(other):
                raise ValueError("El pasillo se superpone con otro pasillo de la misma dirección.")

        self._aisles.append(aisle)

    def get_intersections(self):
        intersections = []
        horizontales = []
        verticales = []

        for a in self.aisles:
            if a.direction == "HORIZONTAL":
                horizontales.append(a)
            else:
                verticales.append(a)

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

    
    #Validación estantes 

    def _cells_of(self, element):
        return set(element.cells())

    def _zone_cells(self, zone):
        x1, y1 = zone.start_node
        x2, y2 = zone.end_node
        if x1 == x2:
            x_min, x_max = (0, x1) if x1 < self.width / 2 else (x1, self.width)
            y_min, y_max = y1, y2
        else:
            y_min, y_max = (0, y1) if y1 < self.height / 2 else (y1, self.height)
            x_min, x_max = x1, x2
        return {(x, y) for x in range(x_min, x_max + 1)
                    for y in range(y_min, y_max + 1)}

    def _start_end_cells(self, start, end):
        x1, y1 = start
        x2, y2 = end

        if x1 == x2:
            x_min, x_max = (0, x1) if x1 < self.width / 2 else (x1, self.width)
            y_min, y_max = y1, y2
        else:
            y_min, y_max = (0, y1) if y1 < self.height / 2 else (y1, self.height)
            x_min, x_max = x1, x2
        return {(x, y) for x in range(x_min, x_max + 1)
                    for y in range(y_min, y_max + 1)}
        

    def _occupied_by(self, elements):
        cells = set()
        for element in elements:
            cells |= self._cells_of(element)
        return cells

    def _occupied_by_zones(self):
        cells = set()
        for zone in self._dispatch_zones:
            cells |= self._zone_cells(zone)
        return cells

    def _touches_aisle(self, cells):
        aisle_cells = self._occupied_by(self._aisles)
        for x, y in cells:
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in aisle_cells:
                    return True
        return False


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
            raise TypeError("Los pasillos deben ser un diccionario o lista de pasillos.")
        if len(self.aisles)>0:
            for aisle in value:
                if not isinstance(aisle, Aisle):
                    raise TypeError("El elemento no es un pasillo.")
                
        self._aisles = value

    @property
    def racks(self):
        return self._stacks

    @racks.setter
    def stacks(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("Los racks deben ser un diccionario o lista de racks.")
        if len(self.racks)>0:
            for rack in value:
                if not isinstance(rack, Rack):
                    raise TypeError("El elemento no es un rack.")
                
        self._racks = value

    @property
    def dispatch_zones(self):
        return self._dispatch_zones

    @dispatch_zones.setter
    def dispatch_zones(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("Las zonas de despacho deben ser un diccionario o lista de zonas de despacho.")
        if len(self.dispatch_zones)>0:
            for zone in value:
                if not isinstance(zone, DispatchZone):
                    raise TypeError("El elemento no es una zona de despacho.")
                
        self._dispatch_zones = value

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        validate_positive_int(value, "El ancho del warehouse")
        self._width = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        validate_positive_int(value, "El alto del warehouse")
        self._height = value