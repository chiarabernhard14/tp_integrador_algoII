from domain.validation import validate_positive_int

class OrderItem:

    def __init__(self, cantidad, producto_id, producto=None, order=None):
        self.cantidad = cantidad
        self.order = order
        self.producto = producto
        self.producto_id = producto_id
        self.picked = False

    def pick_item(self):
        if self.picked:
            raise ValueError("Este item ya fue recogido.")
        if self.producto is not None:
            self.producto.take_product(self.cantidad)
            self.picked = True

    @property
    def producto_id(self):
        return self._producto_id

    @producto_id.setter
    def producto_id(self, value):
        if not isinstance(value, str):
            raise TypeError("El producto_id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:1] != "P":
            raise ValueError("El producto_id debe empezar con 'P'")
        self._producto_id = norm

    @property
    def cantidad(self):
        return self._cantidad

    @cantidad.setter
    def cantidad(self, value):
        validate_positive_int(value, "La cantidad de unidades")
        self._cantidad = value

    @property
    def quantity(self):
        return self.cantidad

    @quantity.setter
    def quantity(self, value):
        self.cantidad = value
