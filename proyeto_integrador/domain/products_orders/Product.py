
class Product:
    id_counter = 0

    def __init__(self, name="", rack=None, location=None, stock=0):
        Product.id_counter += 1
        self._id = Product.id_counter
        self.name = name
        self.rack = rack
        self.stock = stock
        self.location = location

    def take_product(self, quantity):
        self.stock -= quantity
        if self.stock != 0:
            self.update_location_z(quantity)
        else:
            self.rack = None
            self.location = None

    def update_location_z(self, quantity):
        self.location = (self.location[0], self.location[1], self.location[2]-quantity)

    #Properties y Setters con validación necesaria: stock

    @property
    def stock(self):
        return self._stock

    @stock.setter
    def stock(self, value):
        if not isinstance(value, int):
            raise TypeError("El stock debe ser un número entero.")
        if value < 0:
            raise ValueError("El stock no puede ser negativo.")
        self._stock = value