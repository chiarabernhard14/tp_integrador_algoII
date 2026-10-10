from domain.products_orders.Product import Product
from validation import validate_coordinates as validate_node
class Stack:

    def __init__(self, x=0, y=0, height=0, products=[], position=None, rack=None, blocked=False):
        if position is not None:
            self.position = position
        else:
            self.x = x
            self.y = y
            self.position = (self.x, self.y)
        self.rack = rack
        self.products = products
        self.blocked = blocked

    def block(self):
        self.blocked = True

    def unblock(self):
        self.blocked = False

    # Properties y Setters con validacion necesaria: position, products

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

        self._products.insert(0, product)
        self.height += product.stock
        product.stack = self
        product.location = (self.x, self.y, self.height)

    def update_products(self, product, quantity):
        self.height -= quantity
        index = self.products.index(product)

        for i in range(index):
            #No se actualiza el producto porque eso ya se maneja desde Product.take_product()
            self.products[i].update_location_z(quantity)
        
    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        validate_node(value)
        self._position = value
        self.x = self._position[0]
        self.y = self._position[1]
