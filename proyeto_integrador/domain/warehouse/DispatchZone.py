class DispatchZone:

    def __init__(self, access_node=(0, 0), width=0, height=0):
        self.access_node = access_node
        self.width = width
        self.height = height


    # Properties y Setters atributos que requieren validacion: access_node, width, height

    @property
    def access_node(self):
        return self._access_node

    @access_node.setter
    def access_node(self, value):
        if not isinstance(value, (tuple, list)) or len(value) < 2:
            raise TypeError("access_node debe ser una tupla o lista de al menos 2 coordenadas (x, y).")
        if not all(isinstance(coord, (int, float)) for coord in value):
            raise TypeError("Las coordenadas de access_node deben ser numéricas.")
        self._access_node = tuple(value)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("width debe ser un valor numérico.")
        if value < 0:
            raise ValueError("width no puede ser negativo.")
        self._width = float(value)

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("height debe ser un valor numérico.")
        if value < 0:
            raise ValueError("height no puede ser negativo.")
        self._height = float(value)
