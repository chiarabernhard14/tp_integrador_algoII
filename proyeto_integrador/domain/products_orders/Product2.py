class Product:
    id_counter = 0

    def __init__(self, name="", stock=0):
        Product.id_counter += 1
        self._id = Product.id_counter
        self.name = name
        self.stock = stock
        self.stack = None
        self.location = None

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
        self.location = (self.location[0], self.location[1], self.location[2] - quantity)

    # Properties y Setters

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
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("El stock debe ser un número entero.")
        if value < 0:
            raise ValueError("El stock no puede ser negativo.")
        self._stock = value