from domain.products_orders.Product import Product
class Rack:

    def __init__(self, x=0, y=0, height=0, products=[], position=None, aisle=None, blocked=False):
        if position is not None:
            self.position = position
        else:
            self.x = x
            self.y = y
            self.position = (self.x, self.y)
        self.aisle = aisle
        self.products = products
        self.blocked = blocked

    def block(self):
        self.blocked = True

    def unblock(self):
        self.blocked = False

    # Properties and Setters con validacion necesaria: position, products

    @property
    def products(self):
        return self._products

    @products.setter
    def products(self, value):
        if not isinstance(value, list):
            raise TypeError("products debe ser una lista.")
        self._products = []
        if len(value)!=0:
            for p in value:
                self.add_product(p)

    def add_product(self, product):
        if product is None:
            raise ValueError("No se puede agregar un producto nulo.")
        if not isinstance(product, Product):
            raise TypeError("El elemento a agregar debe ser una instancia de Product.")

        self._products.append(product)
        self.height += product.stock
        product.rack = self
        product.location = (self.x, self.y, self.height)

    def update_products(self, product, quantity):
        product_index = self._products.index(product)
        self.height -= quantity

        for p in self._products[product_index:]:
            p.update_location_z(quantity)

        if product.stock==0:
            self._products.pop(product_index)
        

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("La posición debe ser una tupla o lista de 2 coordenadas (x, y).")
        if not all(isinstance(coord, (int, float)) for coord in value):
            raise TypeError("Todas las coordenadas de la posición deben ser numéricas.")
        self._position = tuple(value)
        self.x = self._position[0]
        self.y = self._position[1]
