from RectangularElement import RectangularElement
from ProductE import Product


class Rack(RectangularElement):

    def __init__(self, id, ubicacion, ancho, alto):
        self._validate_dimensions(ancho, alto)
        super().__init__(ubicacion, ancho, alto)
        self.id = id
        self.init_stacks()

    def _validate_dimensions(self,ancho,alto):
        if ancho != 2 and alto != 2:
            raise ValueError("Uno de los dos lados del rack (ancho o alto) debe tener valor 2.")

    def init_stacks(self):
        stacks = [[], []]
        mayor_dim = max(self.ancho, self.alto)
        for _ in range(mayor_dim):
            stacks[0].append([])
            stacks[1].append([])
        self._stacks = stacks

    @property
    def stacks(self):
        return self._stacks

    @stacks.setter
    def stacks(self, value):
        if not isinstance(value, list):
            raise TypeError("stacks debe ser una lista.")
        self._stacks = value

    def acc_stack(self,x,y):
        if self.ancho == 2 and (stack_y := y - self.ubicacion[1]) >= 0:
            if self.ubicacion[0] == x:
                return self.stacks[0][stack_y]
            elif self.ubicacion[0] + 1 == x:
                return self.stacks[1][stack_y]
            else:
                raise ValueError("No se puede acceder al estante desde esa posición.")

        elif self.alto == 2 and (stack_x := x - self.ubicacion[0]) >= 0:
            if self.ubicacion[1] == y:
                return self.stacks[stack_x][0]
            elif self.ubicacion[1] + 1 == y:
                return self.stacks[stack_x][1]
            else:
                raise ValueError("No se puede acceder al estante desde esa posición.")

    def acc_stack_desde(self, x, y, desde_x, desde_y):
        if (abs(desde_x - x) == 1 and abs(desde_y - y) == 0) or (abs(desde_x - x) == 0 and abs(desde_y - y) == 1): 
            return self.acc_stack(x,y)
        else: 
            raise ValueError("No se puede acceder al estante desde esa posición.")
    
    def add_product(self, product):
        if product is None:
            raise ValueError("No se puede agregar un producto nulo.")
        if not isinstance(product, Product):
            raise TypeError("El elemento a agregar debe ser una instancia de Product.")

        stack = self.acc_stack(product.ubicacion[0], product.ubicacion[1])

        if len(stack) > product.ubicacion[2]:
            raise ValueError("No se puede agregar el producto en esa posición porque hay otros productos arriba.")

        if len(stack) < product.ubicacion[2]:
            product.ubicacion = (product.ubicacion[0], product.ubicacion[1], len(stack))

        stack.insert(0, product)
        product.rack = self
        product.rack_id = self.id

    def remove_product(self, product):
        if product is None:
            raise ValueError("No se puede eliminar un producto nulo.")
        if not isinstance(product, Product):
            raise TypeError("El elemento a eliminar debe ser una instancia de Product.")

        stack = self.acc_stack(product.ubicacion[0], product.ubicacion[1])
        if product in stack:
            idx = stack.index(product)
            for i in range(idx):
                p = stack[i]
                p.ubicacion = (p.ubicacion[0], p.ubicacion[1], p.ubicacion[2] - 1)

            stack.remove(product)
            product.rack = None
            product.rack_id = None


    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if not isinstance(value, str):
            raise TypeError("El id debe ser una cadena de texto.")
        norm = value.upper()
        if norm[0:1] != "R":
            raise ValueError("El id debe empezar con 'R'")
        self._id = norm
