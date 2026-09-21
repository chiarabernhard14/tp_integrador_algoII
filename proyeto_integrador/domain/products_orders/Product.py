class Product:
    id_counter = 0

    def __init__(self, name="", location=(0, 0, 0), stock=0):
        Product.id_counter += 1
        self._id = Product.id_counter
        self.name = name
        self.location = location
        self.stock = stock

    def take_product(self, quantity):
        self.stock -= quantity

    #Properties y Setters con validación necesaria: location, stock

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        if not isinstance(value, (tuple, list)):
            raise TypeError("La ubicación debe ser una tupla o lista de coordenadas.")
        if len(value) not in (2, 3):
            raise ValueError("La ubicación debe tener 2 o 3 coordenadas (x, y[, z]).")
        if not all(isinstance(coord, (int, float)) for coord in value):
            raise TypeError("Todas las coordenadas de la ubicación deben ser numéricas.")
        self._location = tuple(value)

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

    def __repr__(self):
        return f"Product(id={self.id}, name='{self.name}', location={self.location}, stock={self.stock})"
