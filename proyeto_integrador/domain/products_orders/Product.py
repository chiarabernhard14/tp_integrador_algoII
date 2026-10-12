from validation import validate_coordinates, validate_non_negative_int

class Product:
    id_counter = 0

    def __init__(self, name="", stock=0, stack=None, location=None):
        Product.id_counter += 1
        self._id = Product.id_counter
        self.name = name
        self.stack = stack
        self.stock = stock
        self.location = location

    def take_product(self, quantity):
        if self.stack is None:
            raise ValueError("El producto no está en ningún stack.")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("quantity debe ser un entero positivo.")
        if quantity > self.stock:
            raise ValueError("No hay stock suficiente.")

        self.stock -= quantity
        self.stack.update_products(self, quantity)
        if self.stock != 0:
            self.update_location_z(quantity)
        else:
            self.stack.remove_product(self)

    def update_location_z(self, quantity):
        if self.location is None:
            raise ValueError("El producto no tiene ubicación.")
        self.location = (self.location[0], self.location[1], self.location[2]-quantity)

    #Properties y Setters con validación necesaria: stock, name, location

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        validate_coordinates(value, 3)
        if self.stack is not None:
            if value[0] != self.stack.position[0] or value[1] != self.stack.position[1]:
                raise ValueError("La ubicación del producto debe ser la misma que la del stack.")
            if not (0 <= value[2] <= self.stack.height):
                raise ValueError("La altura del producto no está dentro de los límites del stack.")
        self._location = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError("El nombre debe ser una cadena de texto.")
        self._name = value.strip()

    @property
    def stock(self):
        return self._stock

    @stock.setter
    def stock(self, value):
        validate_non_negative_int(value, f"El stock de {self.name}")
        self._stock = value