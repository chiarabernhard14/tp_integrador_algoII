from domain.validation import validate_coordinates

class Door:

    def __init__(self, id, tipo, ubicacion):
        self.tipo = tipo
        self.id = id
        self.ubicacion = ubicacion

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if not isinstance(value, str):
            raise TypeError("El id debe ser una cadena de texto.")

        norm = value.upper()
        if self.tipo == "OUTBOUND" and norm[0:10] != "PUERTA_OUT":
            raise ValueError("El id de la puerta debe comenzar con PUERTA_OUT.")
        if self.tipo == "INBOUND" and norm[0:9] != "PUERTA_IN":
            raise ValueError("El id de la puerta debe comenzar con PUERTA_IN.")
        if self.tipo == "AMBOS" and norm[0:10] != "PUERTA_MIX":
            raise ValueError("El id de la puerta debe comenzar con PUERTA_OUT o PUERTA_IN.")
        self._id = norm

    @property
    def tipo(self):
        return self._tipo

    @tipo.setter
    def tipo(self, value):
        valid_tipos = {"INBOUND", "OUTBOUND", "AMBOS"}
        if not isinstance(value, str):
            raise TypeError("El tipo de puerta debe ser una cadena de texto.")
        normalized = value.strip().upper()
        if normalized not in valid_tipos:
            raise ValueError(
                f"Tipo '{value}' no válido. Opciones permitidas: {', '.join(valid_tipos)}."
            )
        self._tipo = normalized

    @property
    def ubicacion(self):
        return self._ubicacion

    @ubicacion.setter
    def ubicacion(self, value):
        validate_coordinates(value)
        self._ubicacion = value

