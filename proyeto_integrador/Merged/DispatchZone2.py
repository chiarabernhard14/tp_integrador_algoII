from domain.warehouse.validation import validate_coordinates, validate_segment


class DispatchZone:

    def __init__(self, nodes, door, width, height):
        self.start_node, self.end_node = validate_segment(nodes[0], nodes[1])
        validate_coordinates(door)
        self.door = door
        self.width = width
        self.height = height

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("width debe ser un entero.")
        if value <= 0:
            raise ValueError("width debe ser mayor que cero.")
        self._width = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("height debe ser un entero.")
        if value <= 0:
            raise ValueError("height debe ser mayor que cero.")
        self._height = value