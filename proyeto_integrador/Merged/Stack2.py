from domain.products_orders.Product2 import Product
from domain.warehouse.validation import validate_coordinates as validate_node
class Stack:

    def __init__(self, x=0, y=0, products=None, position=None, blocked=False):
        self.rack = None
        self._products = []
        self._height = 0
        self.position = position if position is not None else (x, y)
        self.blocked = blocked
        self.products = products if products is not None else []

    def block(self):
        self.blocked = True

    def unblock(self):
        self.blocked = False

    # Properties y Setters

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        validate_node(value)
        if self.rack is not None:
            raise ValueError("No se puede mover un stack que ya está en un rack.")
        if self._products:
            raise ValueError("No se puede mover un stack que ya contiene productos.")
        self._position = value

    @property
    def x(self):
        return self._position[0]

    @property
    def y(self):
        return self._position[1]

    @property
    def height(self):
        return self._height

    @property
    def blocked(self):
        return self._blocked

    @blocked.setter
    def blocked(self, value):
        if not isinstance(value, bool):
            raise TypeError("blocked debe ser un booleano.")
        self._blocked = value

    @property
    def products(self):
        return tuple(self._products)

    @products.setter
    def products(self, value):
        if not isinstance(value, list):
            raise TypeError("products debe ser una lista.")
        self._products = []
        self._height = 0
        for p in value:
            self.add_product(p)

    def add_product(self, product):
        if product is None:
            raise ValueError("No se puede agregar un producto nulo.")
        if not isinstance(product, Product):
            raise TypeError("El elemento a agregar debe ser una instancia de Product.")
        if product in self._products:
            raise ValueError("El producto ya está en el stack.")

        # ---- las dos nuevas ----
        if product.stack is not None and product.stack is not self:
            raise ValueError("El producto ya está en otro stack.")
        if product.stock <= 0:
            raise ValueError("No se puede agregar un producto sin stock.")
        # ------------------------

        self._products.insert(0, product)
        self._height += product.stock
        product.stack = self
        product.location = (self.x, self.y, self._height)

    def remove_product(self, product):
        if product not in self._products:
            raise ValueError("El producto no pertenece a este stack.")
        self._products.remove(product)
        product.stack = None
        product.location = None

    def update_products(self, product, quantity):
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("quantity debe ser un entero positivo.")
        if product not in self._products:
            raise ValueError("El producto no pertenece a este stack.")
        if quantity > self._height:
            raise ValueError("No se puede retirar más de la altura del stack.")

        self._height -= quantity
        index = self._products.index(product)

        for i in range(index):
            # No se actualiza el producto porque eso ya se maneja desde Product.take_product()
            self._products[i].update_location_z(quantity)