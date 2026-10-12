from domain.products_orders.Product import Product
from validation import validate_coordinates as validate_node
class Stack:

    def __init__(self, rack, x=0, y=0, position=None, products=[]):
        self.rack = rack
        self._products = []
        self._height = 0
        self.position = position if position is not None else (x, y)
        self.blocked = False
        self.products = products

    # Properties y Setters con validacion necesaria: position, products
    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        validate_node(value)
        if len(self._products)>0:
            raise ValueError("No se puede mover un stack que ya contiene productos.")
        self.x = self._position[0]
        self.y = self._position[1]
        self._position = value
        

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
        if product.stack is not None:
            raise ValueError("El producto ya está en otro stack.")

        self._products.insert(0, product)
        self.height += product.stock
        product.stack = self
        product.location = (self.x, self.y, self.height)

    def remove_product(self, product):
        if product not in self._products:
            raise ValueError("El producto no pertenece a este stack.")
        self._products.remove(product)
        product.stack = None
        product.location = None

    def update_products(self, product, quantity):

        if quantity > self._height:
            raise ValueError("No se puede retirar más de la altura del stack.")

        self.height -= quantity
        index = self.products.index(product)

        for i in range(index):
            #No se actualiza el producto porque eso ya se maneja desde Product.take_product()
            self.products[i].update_location_z(quantity)
        
    def block(self):
        self.blocked = True

    def unblock(self):
        self.blocked = False
