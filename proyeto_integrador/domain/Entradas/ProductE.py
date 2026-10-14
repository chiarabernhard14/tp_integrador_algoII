from validation import (
    validate_coordinates,
    validate_non_negative_int,
    validate_positive_int,
)


class Product:

    def __init__(
        self,
        id,
        nombre,
        rack_id,
        ubicacion,
        acc_por,
        stock=0,
        peso_kg=1.0
    ):  
        self.id = id
        self.nombre = nombre
        self.rack_id = rack_id
        self.rack= None
        self.ubicacion = ubicacion
        self.stock = stock
        self.peso_kg = peso_kg

    def take_product(self, quantity):

        validate_positive_int(quantity, "La cantidad")
        if quantity > self.stock:
            raise ValueError("No hay stock suficiente.")

        self.stock -= quantity

        if self.stock == 0:
            self.rack.remove_product(self)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if not isinstance(value, str):
            raise TypeError("El id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:1] != "P":
            raise ValueError("El id debe empezar con 'P'")
        self._id = norm

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, value):
        if not isinstance(value, str):
            raise TypeError("El nombre debe ser una cadena de texto.")
        self._nombre = value.strip()

    @property
    def rack_id(self):
        return self._rack_id

    @rack_id.setter
    def rack_id(self, value):
        if value is not None:
            if not isinstance(value, str):
                raise TypeError("El rack_id debe ser una cadena de texto.")
            norm = value.upper()
            if norm[0:1] != "R":
                raise ValueError("El rack_id debe empezar con 'R'")
            self._rack_id = norm
        else:   
            self._rack_id = None

    @property
    def rack(self):
        return self._rack

    @rack.setter
    def rack(self, value):
        self._rack = value

    @property
    def ubicacion(self):
        return self._ubicacion

    @ubicacion.setter
    def ubicacion(self, value):
        validate_coordinates(value, 3)
        
        self._ubicacion = value



    @property
    def stock(self):
        return self._stock

    @stock.setter
    def stock(self, value):
        validate_non_negative_int(value, f"El stock")
        self._stock = value

    @property
    def peso_kg(self):
        return self._peso_kg

    @peso_kg.setter
    def peso_kg(self, value):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("El peso debe ser un valor numérico.")
        if value <= 0:
            raise ValueError("El peso debe ser mayor a 0.")
        self._peso_kg = float(value)
