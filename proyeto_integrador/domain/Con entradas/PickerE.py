from validation import validate_coordinates

class Picker:
    def __init__(self, id, posicion, capacidad_carga_kg, current_route=[]):
        self.id = id
        self.posicion = posicion
        self.capacidad_carga_kg = capacidad_carga_kg
        self.current_route = current_route

    def move_x(self, value):
        if abs(value) != 1:
            raise ValueError("No se puede mover más de una casilla")
        self_posicion = (self._posicion[0] + value, self._posicion[1])

    def move_y(self, value):
        if abs(value) != 1:
            raise ValueError("No se puede mover más de una casilla")
        self_posicion = (self._posicion[0], self._posicion[1] + value)
        

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if not isinstance(value, str):
            raise TypeError("El id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:3] != "PK_":
            raise ValueError("El id debe empezar con 'PK_'")
        self._id = norm

    @property
    def posicion(self):
        return self._posicion

    @posicion.setter
    def posicion(self, value):
        validate_coordinates(value)
        self._posicion = value

    @property
    def capacidad_carga_kg(self):
        return self._capacidad_carga_kg

    @capacidad_carga_kg.setter
    def capacidad_carga_kg(self, value):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("La capacidad de carga debe ser un valor numérico.")
        if value <= 0:
            raise ValueError("La capacidad de carga debe ser mayor a 0.")
        self._capacidad_carga_kg = float(value)

    @property
    def current_route(self):
        return self._current_route

    @current_route.setter
    def current_route(self, value):
        if not isinstance(value, list):
            raise TypeError("current_route debe ser una lista.")
        self._current_route = value

    def pick(self, item):
        item.pick_item()
