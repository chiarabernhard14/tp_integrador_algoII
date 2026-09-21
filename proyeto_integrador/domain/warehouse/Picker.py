class Picker:

    id = 0
    def __init__(self, current_position=(0, 0), capacity=0.0, current_route=[]):
        Picker.id += 1
        self.id = Picker.id
        self.current_position = current_position
        self.capacity = capacity
        self.current_route = current_route

    #current_route es una lista de items
    def pick(self, item):
        item.pick_item()
        item.product.rack.update_products(item.product, item.quantity)

    #Properties and Setters

    @property
    def current_position(self):
        return self._current_position

    @current_position.setter
    def current_position(self, value):
        if not isinstance(value, (tuple, list)) or len(value) < 2:
            raise TypeError("current_position debe ser una tupla o lista de al menos 2 coordenadas (x, y).")
        if not all(isinstance(coord, (int, float)) for coord in value):
            raise TypeError("Las coordenadas de current_position deben ser numéricas.")
        self._current_position = tuple(value)

    @property
    def capacity(self):
        return self._capacity

    @capacity.setter
    def capacity(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("La capacidad debe ser un valor numérico.")
        if value < 0:
            raise ValueError("La capacidad no puede ser negativa.")
        self._capacity = float(value)

    @property
    def current_route(self):
        return self._current_route

    @current_route.setter
    def current_route(self, value):
        if not isinstance(value, list):
            raise TypeError("current_route debe ser una lista de posiciones o nodos.")
        self._current_route = value