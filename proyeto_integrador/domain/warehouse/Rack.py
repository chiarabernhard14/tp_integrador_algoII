from Stack import Stack
class Rack:
    # length es la cantidad máxima de stacks que puede contener el rack

    def __init__(self, start_node=(0, 0), end_node=(0, 0), stacks=[]):
        self.start_node = start_node
        self.end_node = end_node

        # Los nodos ya están validados en este punto:

        if self.end_node[1] == self.start_node[1]:
            self.length = abs(self.end_node[0] - self.start_node[0])
            self.direction = "HORIZONTAL"
        else:
            self.length = abs(self.end_node[1] - self.start_node[1])
            self.direction = "VERTICAL"

        self.stacks = stacks


    # Properties y Setters atributos que requieren validacion: stacks

    @property
    def stacks(self):
        return self._stacks

    @stacks.setter
    def stacks(self, value):
        if not isinstance(value, list):
            raise TypeError("stacks debe ser una lista.")
        if len(value) > self.length:
            raise ValueError(f"La cantidad de stacks ({len(value)}) no puede exceder la longitud del rack ({self.length}).")
        for s in value:
            if not isinstance(s, Stack):
                raise TypeError("Todos los elementos de stacks deben ser instancias de Stack.")
        self._stacks = value

    def add_stack(self, stack):
        if stack is None:
            raise ValueError("No se puede agregar un stack nulo.")
        if not isinstance(stack, Stack):
            raise TypeError("El elemento a agregar debe ser una instancia de Stack.")
        if len(self._stacks) >= self.length:
            raise ValueError(f"El rack está lleno. Capacidad máxima: {self.length} stacks.")
        self._stacks.append(stack)
