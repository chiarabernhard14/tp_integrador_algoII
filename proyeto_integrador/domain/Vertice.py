from domain.Validation import validate_coordinates
class Vertice:

    def __init__(self, ubicacion, pasillo):
        self.ubicacion = ubicacion
        self.pasillo = pasillo

    @property
    def ubicacion(self):
        return self._ubicacion
    
    @ubicacion.setter

    def ubicacion(self, value):
        validate_coordinates(value)
        self._ubicacion = value

    @property
    def pasillo(self):
        return self._pasillo

    @pasillo.setter
    def pasillo(self, value):
        self._pasillo = value