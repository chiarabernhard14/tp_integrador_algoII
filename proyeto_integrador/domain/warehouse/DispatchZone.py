from LinearElement import LinearElement
from validation import validate_positive_int

class DispatchZone(LinearElement):

    def __init__(self, nodes, door, width, height):
        super().__init__(nodes[0], nodes[1])
        self.width = width
        self.height = height
        self.door = door


    #Nodes y door ya están validados según las propiedades
    #del warehouse desde el que fueron creados

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        validate_positive_int(value, "El ancho de la zona de despacho")
        self._width = value


    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        validate_positive_int(value, "La altura de la zona de despacho")
        self._height = value