from validation import validate_positive_int

class OrderItem:

    def __init__(self, product=None, quantity=0, order=None, picked=False):
        self.product = product
        self.quantity = quantity
        self.picked = picked
        self.order = order

    def pick_item(self):
        self.product.take_product(self.quantity)
        self.picked = True

    #Properties y Setters: quantity

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        validate_positive_int(value,"La cantidad de unidades")
        self._quantity = value

