from domain.validation import validate_coordinates
class Vertice:

    def __init__(self, ubicacion, sentido, v_acceso=False):
        self.ubicacion = ubicacion
        self.sentido = sentido
        self.v_acceso = v_acceso
        self.ady = []

    @property
    def ubicacion(self):
        return self._ubicacion

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

    @property
    def v_acceso(self):
        return self._v_acceso

    @v_acceso.setter
    def v_acceso(self, value):
        if not isinstance(value, bool):
            raise TypeError("v_acceso debe ser un booleano.")
        self._v_acceso = value