class OrderItem:

    def __init__(self, product=None, quantity=0, picked=False):
        self.product = product
        self.quantity = quantity
        self.picked = picked

    def pick_item(self):
        self.product.take_product(self.quantity)
        self.picked = True

    #Properties y Setters: quantity

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        if not isinstance(value, int):
            raise TypeError("La cantidad debe ser un número entero.")
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0.")
        self._quantity = value

