from domain.warehouse.LinearElement import LinearElement
from domain.warehouse.Stack2 import Stack

class Rack(LinearElement):        
    def __init__(self, start_node, end_node, stacks=None):
        super().__init__(start_node, end_node)
        self._stacks = []
        self.stacks = stacks if stacks is not None else []

    @property
    def capacity(self):
        return self.length + 1

    @property
    def stacks(self):
        return tuple(self._stacks)

    @stacks.setter
    def stacks(self, value):
        if not isinstance(value, list):
            raise TypeError("stacks debe ser una lista.")
        for old in self._stacks:
            old.rack = None
        self._stacks = []
        for s in value:
            self.add_stack(s)

    def add_stack(self, stack):
        if stack is None:
            raise ValueError("No se puede agregar un stack nulo.")
        if not isinstance(stack, Stack):
            raise TypeError("El elemento a agregar debe ser una instancia de Stack.")
        if stack.rack is not None:
            raise ValueError("El stack ya pertenece a un rack.")
        if stack.position not in self.cells():
            raise ValueError("El stack debe estar dentro del rack.")
        for other in self._stacks:
            if other.position == stack.position:
                raise ValueError("Ya hay un stack en esa posición del rack.")

        self._stacks.append(stack)
        stack.rack = self