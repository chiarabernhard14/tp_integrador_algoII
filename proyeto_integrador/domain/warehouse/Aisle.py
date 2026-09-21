from Rack import Rack
class Aisle:

    def __init__(self, start_node=(0, 0), end_node=(0, 0), racks=[]):
        self.start_node = start_node
        self.end_node = end_node
        self.racks = racks 

    # Properties y Setters atributos que requieren validacion: start_node, end_node, racks

    @property
    def length(self):
        return abs(self.end_node[0] - self.start_node[0]) if self.end_node[1]  == self.start_node[1] else abs(self.end_node[1] - self.start_node[1])

    @property
    def start_node(self):
        return self._start_node

    @start_node.setter
    def start_node(self, value):
        if not isinstance(value, tuple) or len(value) != 2:
            raise TypeError("Debe ser una tupla de 2 coordenadas (x, y).")
        if not all(isinstance(coord, (int, float)) for coord in value):
            raise TypeError("Las coordenadas deben ser números.")
        if self.end_node is not None and self.end_node[1] != value[1] and self.end_node[0] != value[0]:
            raise ValueError("La posición de comienzo y fin debe estar en la misma fila o columna.")
        self._start_node = value

    @property
    def end_node(self):
        return self._end_node

    @end_node.setter
    def end_node(self, value):
        if not isinstance(value, tuple) or len(value) != 2:
            raise TypeError("Debe ser una tupla de 2 coordenadas (x, y).")
        if not all(isinstance(coord, (int, float)) for coord in value):
            raise TypeError("Las coordenadas deben ser números.")
        if self.start_node is not None and self.start_node[1] != value[1] and self.start_node[0] != value[0]:
            raise ValueError("La posición de comienzo y fin debe estar en la misma fila o columna.")
        
        self._end_node = value

    @property
    def racks(self):
        return self._racks

    @racks.setter
    def racks(self, value):
        if not isinstance(value, list):
            raise TypeError("racks debe ser una lista.")
        for r in value:
            if not isinstance(r, Rack):
                raise TypeError("Todos los elementos de racks deben ser instancias de Rack.")
        self._racks = value

    def add_rack(self, rack):
        if rack is None:
            raise ValueError("No se puede agregar un rack nulo.")
        if not isinstance(rack, Rack):
            raise TypeError("El elemento a agregar debe ser una instancia de Rack.")
        self._racks.append(rack)

    def __repr__(self):
        return f"Aisle(start_node={self.start_node}, end_node={self.end_node}, length={self.length}, racks={len(self.racks)})"
