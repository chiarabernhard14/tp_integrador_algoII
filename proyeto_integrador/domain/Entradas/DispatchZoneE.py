from .RectangularElement import RectangularElement

class DispatchZone(RectangularElement):

    def __init__(self, id, puerta_id, ubicacion, ancho, alto, peso_max_kg):
        super().__init__(ubicacion, ancho, alto)
        self.id = id
        self.puerta_id = puerta_id
        self.peso_max_kg = peso_max_kg

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if not isinstance(value, str):
            raise TypeError("El id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:5] != "ZONA_":
            raise ValueError("El id de la zona de despacho debe empezar con 'ZONA_'")
        self._id = norm

    @property
    def puerta_id(self):
        return self._puerta_id

    @puerta_id.setter
    def puerta_id(self, value):
        if not isinstance(value, str):
            raise TypeError("El puerta_id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:7] != "PUERTA_":
            raise ValueError("El puerta_id debe empezar con 'PUERTA_'")
        self._puerta_id = norm

    @property
    def peso_max_kg(self):
        return self._peso_max_kg

    @peso_max_kg.setter
    def peso_max_kg(self, value):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("El peso máximo debe ser un valor numérico.")
        if value <= 0:
            raise ValueError("El peso máximo debe ser mayor a 0.")
        self._peso_max_kg = float(value)

    def contains(self, point):
        x0, y0 = self._ubicacion
        return x0 <= point[0] < x0 + self._ancho and y0 <= point[1] < y0 + self._alto