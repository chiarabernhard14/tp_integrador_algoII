from OrderItem import OrderItem

class Order:
    id_counter = 0

    def __init__(self, items=[], priority=1, status="PENDIENTE"):
        Order.id_counter += 1
        self._id = Order.id_counter
        self.items = items
        self.priority = priority
        self.status = status

    
    def add_item(self, item):
        if item is None or not isinstance(item, OrderItem):
            raise ValueError("No se puede agregar un ítem nulo o no válido.")
        self._items.append(item)

    #Properties y Setters con validación necesaria: priority, status

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, value):
        if not isinstance(value, int):
            raise TypeError("La prioridad debe ser un número entero.")
        if not (1 <= value <= 5):
            raise ValueError("La prioridad debe ser un valor entero entre 1 y 5.")
        self._priority = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        valid_statuses = {"PENDIENTE", "EN_WAVE", "EN_PREPARACION", "PREPARADO"}
        if not isinstance(value, str):
            raise TypeError("El estado debe ser una cadena de texto.")
        normalized = value.strip().upper()
        if normalized not in valid_statuses:
            raise ValueError(f"Estado '{value}' no válido. Opciones permitidas: {', '.join(valid_statuses)}.")
        self._status = normalized

    def __repr__(self):
        return f"Order(id={self.id}, items={len(self.items)}, priority={self.priority}, status='{self.status}')"
