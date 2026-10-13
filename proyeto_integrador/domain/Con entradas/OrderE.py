from OrderItemE import OrderItem

class Order:

    def __init__(self, id, prioridad=1, estado="PENDIENTE", items=[]):
        self.id = id
        self.prioridad = prioridad
        self.estado = estado
        self.items = items

    def add_item(self, cantidad, producto_id, producto=None):
        item = OrderItem(cantidad=cantidad, producto_id=producto_id, producto=producto, order=self)
        self._items.append(item)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if not isinstance(value, str):
            raise TypeError("El id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:4] != "PED_":
            raise ValueError("El id debe empezar con 'PED_'")
        self._id = norm

    @property
    def prioridad(self):
        return self._prioridad

    @prioridad.setter
    def prioridad(self, value):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("La prioridad debe ser un número entero.")
        if not (1 <= value <= 5):
            raise ValueError("La prioridad debe ser un valor entero entre 1 y 5.")
        self._prioridad = value

    @property
    def priority(self):
        return self.prioridad

    @priority.setter
    def priority(self, value):
        self.prioridad = value

    @property
    def estado(self):
        return self._estado

    @estado.setter
    def estado(self, value):
        valid_statuses = {"PENDIENTE", "EN_WAVE", "EN_PREPARACION", "PREPARADO"}
        if not isinstance(value, str):
            raise TypeError("El estado debe ser una cadena de texto.")
        normalized = value.strip().upper()
        if normalized not in valid_statuses:
            raise ValueError(
                f"Estado '{value}' no válido. Opciones permitidas: {', '.join(valid_statuses)}."
            )
        self._estado = normalized

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, value):
        if not isinstance(value, list):
            raise TypeError("items debe ser una lista.")
        for it in value:
            if not isinstance(it, OrderItem):
                raise TypeError("Todos los elementos de items deben ser instancias de OrderItem.")
            it.order = self
        self._items = value
