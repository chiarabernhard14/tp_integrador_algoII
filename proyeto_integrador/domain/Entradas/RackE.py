from .RectangularElement import RectangularElement
from .ProductE import Product


class Rack(RectangularElement):

    def __init__(self, id, ubicacion, ancho, alto):
        self._validate_dimensions(ancho, alto)
        super().__init__(ubicacion, ancho, alto)
        self.id = id

    def _validate_dimensions(self,ancho,alto):
        if ancho != 2 and alto != 2:
            raise ValueError("Uno de los dos lados del rack (ancho o alto) debe tener valor 2.")

    def init_stacks(self, not_acc=0):                             
        stacks = [[], 
                  []]
        mayor_dim = max(self.ancho, self.alto)
        for _ in range(mayor_dim):
            if not_acc != 1:
                stacks[0].append([])
            
            if not_acc != 2:
                stacks[1].append([])
        return stacks

    @property
    def stacks(self):
        return self._stacks

    @stacks.setter
    def stacks(self, value):
        if not isinstance(value, list):
            raise TypeError("stacks debe ser una lista.")

        for line in value:
            if not isinstance(line, list):
                raise TypeError("Cada lado del rack debe ser una lista.")
            for pila in line:
                if not isinstance(pila, list):
                    raise TypeError("Cada pila debe ser una lista.")
                for prod in pila:
                    self.add_product(prod)
            
        self._stacks = value

    def acc_stack(self,x,y):
        if self.ancho == 2 and (stack_y := y - self.ubicacion[1]) >= 0:
            if self.ubicacion[0] == x:
                try:
                    return self.stacks[0][stack_y]
                except IndexError:
                    raise ValueError("Esa posición no pertenece al rack.")
            elif self.ubicacion[0] + 1 == x:
                try:
                    return self.stacks[1][stack_y]
                except IndexError:
                    raise ValueError("Esa posición no pertenece al rack.")

        elif self.alto == 2 and (stack_x := x - self.ubicacion[0]) >= 0:
            if self.ubicacion[1] == y:
                try:
                    return self.stacks[stack_x][0]
                except IndexError:
                    raise ValueError("Esa posición no pertenece al rack.")
            elif self.ubicacion[1] + 1 == y:
                try:
                    return self.stacks[stack_x][1]
                except IndexError:
                    raise ValueError("Esa posición no pertenece al rack.")
        
        raise ValueError("Esa posición no pertenece al rack.")

    def acc_stack_desde(self, x, y, desde_x, desde_y):
        if (abs(desde_x - x) == 1 and desde_y == y) or (desde_x == x and abs(desde_y - y) == 1): 
            return self.acc_stack(x,y)
        
        raise ValueError("No se puede acceder al estante desde esa posición.")
    
    def add_product(self, product):
        if product is None:
            raise ValueError("No se puede agregar un producto nulo.")
        if not isinstance(product, Product):
            raise TypeError("El elemento a agregar debe ser un producto.")

        px, py = product.ubicacion[0], product.ubicacion[1]

        stack = self.acc_stack(px, py)

        if len(stack) > product.ubicacion[2]:
            raise ValueError("No se puede agregar el producto en esa posición porque hay otros productos arriba.")

        if len(stack) < product.ubicacion[2]:
            product.ubicacion = (product.ubicacion[0], product.ubicacion[1], len(stack))

        stack.insert(0, product)
        product.rack = self

        x0, y0 = self.ubicacion

        if self.ancho == 2:
            # Rack vertical: las dos columnas (x0 y x0+1) se acceden
            # desde la izquierda (x0-1) o desde la derecha (x0+2)
            if px == x0:
                acceso = (x0 - 1, py)
            else:  # px == x0 + 1
                acceso = (x0 + 2, py)
        else:
            # Rack horizontal (alto == 2): las dos filas (y0 y y0+1)
            # se acceden desde abajo (y0-1) o desde arriba (y0+2)
            if py == y0:
                acceso = (px, y0 - 1)
            else:  # py == y0 + 1
                acceso = (px, y0 + 2)

        product.acceso = acceso

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
