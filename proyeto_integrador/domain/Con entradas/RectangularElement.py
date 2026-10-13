from validation import validate_coordinates, validate_positive_int


class RectangularElement:

    def __init__(self, ubicacion, ancho, alto):
        self.ubicacion = ubicacion
        self.ancho = ancho
        self.alto = alto

    @property
    def ubicacion(self):
        return self._ubicacion

    @ubicacion.setter
    def ubicacion(self, value):
        validate_coordinates(value)
        self._ubicacion = value

    @property
    def ancho(self):
        return self._ancho

    @ancho.setter
    def ancho(self, value):
        validate_positive_int(value, "El ancho")
        self._ancho = value

    @property
    def alto(self):
        return self._alto

    @alto.setter
    def alto(self, value):
        validate_positive_int(value, "El alto")
        self._alto = value

    def cells(self):
        x0, y0 = self._ubicacion
        return [(x0 + i, y0 + j) for i in range(self._ancho) for j in range(self._alto)]

    def __contains__(self, point):
        x0, y0 = self._ubicacion
        return x0 <= point[0] < x0 + self._ancho and y0 <= point[1] < y0 + self._alto



