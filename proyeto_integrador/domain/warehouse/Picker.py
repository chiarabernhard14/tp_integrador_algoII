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

    #Properties and Setters

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