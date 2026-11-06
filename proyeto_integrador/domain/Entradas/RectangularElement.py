from domain.validation import validate_coordinates, validate_positive_int


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

    def adjacent_cells(self, max_x=None, max_y=None):
        """Devuelve el conjunto de celdas vecinas (4-conectadas) al elemento
        a partir de su vértice inferior izquierdo, ancho y alto.
        Opcionalmente se pueden acotar por dimensiones máximas (max_x, max_y)."""
        x0, y0 = self._ubicacion
        ancho, alto = self._ancho, self._alto
        neighbors = set()

        for x in range(x0, x0 + ancho):
            if max_x is None or 0 <= x < max_x:
                if max_y is None or 0 <= y0 - 1 < max_y:
                    neighbors.add((x, y0 - 1))
                if max_y is None or 0 <= y0 + alto < max_y:
                    neighbors.add((x, y0 + alto))

        for y in range(y0, y0 + alto):
            if max_y is None or 0 <= y < max_y:
                if max_x is None or 0 <= x0 - 1 < max_x:
                    neighbors.add((x0 - 1, y))
                if max_x is None or 0 <= x0 + ancho < max_x:
                    neighbors.add((x0 + ancho, y))

        return neighbors


    



