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
        if value < 0:
            raise ValueError("La cantidad no puede ser negativa.")
        self._quantity = value

    def __repr__(self):
        prod_id = getattr(self.product, 'id', self.product)
        return f"OrderItem(product={prod_id}, quantity={self.quantity}, picked={self.picked})"
