from RectangularElement import RectangularElement

class Aisle(RectangularElement):

    def __init__(self, id, ubicacion, ancho, alto, sentido="AMBOS"):
        
        super().__init__(ubicacion, ancho, alto)
        self.id = id
        self.sentido = sentido

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        
        if not isinstance(value, str):
            raise TypeError("El id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:4] != "PAS_":
            raise ValueError("El id debe empezar con 'PAS_")
        self._id = norm

    @property
    def sentido(self):
        return self._sentido

    @sentido.setter
    def sentido(self, value):
        valid_sentidos = {"N", "S", "E", "O", "AMBOS"}
        if not isinstance(value, str):
            raise TypeError("El sentido debe ser una cadena de texto.")
        normalized = value.strip().upper()
        if normalized not in valid_sentidos:
            raise ValueError(
                f"Sentido '{value}' no válido. Opciones permitidas: {', '.join(valid_sentidos)}."
            )
        self._sentido = normalized

