from domain.validation import validate_positive_int
from .DoorE import Door
from .DispatchZoneE import DispatchZone
from .RackE import Rack
from .AisleE import Aisle
from .PickerE import Picker
from .ProductE import Product
from .OrderE import Order


class Warehouse:

    def __init__(
        self,
        ancho_x,
        largo_y,
        puertas=None,
        zonas_despacho=None,
        racks=None,
        pasillos=None,
        pickers=None,
        productos=None,
        pedidos=None,
        graph=None
    ):
        self.ancho_x = ancho_x
        self.largo_y = largo_y

        self._puertas = {}
        self._zonas_despacho = {}
        self._racks = {}
        self._pasillos = {}
        self._pickers = {}
        self._productos = {}
        self._pedidos = {}

        self.puertas = puertas if puertas is not None else {}
        self.zonas_despacho = zonas_despacho if zonas_despacho is not None else {}
        self.racks = racks if racks is not None else {}
        self.pasillos = pasillos if pasillos is not None else {}
        self.pickers = pickers if pickers is not None else {}
        self.productos = productos if productos is not None else {}
        self.pedidos = pedidos if pedidos is not None else {}
        self.graph = graph if graph is not None else {}

    # Dimensiones
    @property
    def ancho_x(self):
        return self._ancho_x

    @ancho_x.setter
    def ancho_x(self, value):
        validate_positive_int(value, "El ancho del warehouse")
        self._ancho_x = value

    @property
    def largo_y(self):
        return self._largo_y

    @largo_y.setter
    def largo_y(self, value):
        validate_positive_int(value, "El largo del warehouse")
        self._largo_y = value

    # Puertas
    @property
    def puertas(self):
        return self._puertas

    @puertas.setter
    def puertas(self, value):
        if not isinstance(value, dict):
            raise TypeError("puertas debe ser un diccionario.")
        for door in value.values():
            self.add_door(door)

    def add_door(self, door):
        if not isinstance(door, Door):
            raise TypeError("El elemento debe ser una instancia de Door.")
        if door.id in self._puertas:
            raise ValueError(f"Ya existe una puerta con id '{door.id}'.")
        self.validate_inside_warehouse(door.ubicacion)
        x, y = door.ubicacion
        if not (x == 0 or x == self._ancho_x - 1 or y == 0 or y == self._largo_y - 1):
            raise ValueError("La puerta debe estar en el borde del almacén.")
        self._puertas[door.id] = door

    # Zonas de despacho
    @property
    def zonas_despacho(self):
        return self._zonas_despacho

    @zonas_despacho.setter
    def zonas_despacho(self, value):
        if not isinstance(value, dict):
            raise TypeError("zonas_despacho debe ser un diccionario.")
        for zone in value.values():
            self.add_dispatch_zone(zone)

    def add_dispatch_zone(self, zone):

        if not isinstance(zone, DispatchZone):
            raise TypeError("El elemento debe ser una zona de despacho.")
        if zone.id in self._zonas_despacho:
            raise ValueError("Ya se registró esta zona de despacho")
            
        self.validate_element_bounds(zone)

        try:
            door = self._puertas[zone.puerta_id]
        except KeyError:
            raise ValueError("La zona de despacho referencia una puerta que no existe en el warehouse.")

        # La puerta debe ser adyacente a la zona (vecina, no estar dentro de ella)
        if door.ubicacion not in self._adjacent_cells_of(zone):
            raise ValueError(
                "La puerta asignada debe estar en una celda adyacente a la zona de despacho."
            )

        cells = set(zone.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError("La zona de despacho se superpone con un rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError("La zona de despacho se superpone con otra.")
        if cells & self._occupied_by(self._pasillos):
            raise ValueError("La zona de despacho se superpone con un pasillo.")
    
        self._zonas_despacho[zone.id] = zone

    # Racks
    @property
    def racks(self):
        return self._racks

    @racks.setter
    def racks(self, value):
        if not isinstance(value, dict):
            raise TypeError("racks debe ser un diccionario.")
        for rack in value.values():
            self.add_rack(rack)

    def add_rack(self, rack):
        if not isinstance(rack, Rack):
            raise TypeError("El elemento debe ser una instancia de Rack.")
        if rack.id in self._racks:
            raise ValueError("Ya se registró este rack.")

        self.validate_element_bounds(rack)

        cells = set(rack.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError("El rack se superpone con otro rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError("El rack se superpone con una zona de despacho.")
        if cells & self._occupied_by(self._pasillos):
            raise ValueError("El rack se superpone con un pasillo.")

        # Las caras de acceso del rack no pueden quedar fuera del warehouse
        # (el rack no puede estar pegado a una pared)
        x0, y0 = rack.ubicacion
        if rack.ancho == 2:
            if x0 - 1 < 0:
                raise ValueError(f"El rack '{rack.id}' está pegado a la pared izquierda del almacén.")
            if x0 + 2 >= self._ancho_x:
                raise ValueError(f"El rack '{rack.id}' está pegado a la pared derecha del almacén.")
        else:  # rack.alto == 2
            if y0 - 1 < 0:
                raise ValueError(f"El rack '{rack.id}' está pegado a la pared inferior del almacén.")
            if y0 + 2 >= self._largo_y:
                raise ValueError(f"El rack '{rack.id}' está pegado a la pared superior del almacén.")

        # Las celdas de acceso al rack (adyacentes a las caras que contienen productos)
        # no deben estar ocupadas por ningún otro elemento
        occupied = (
            self._occupied_by(self._racks)
            | self._occupied_by(self._zonas_despacho)
            | self._occupied_by(self._pasillos)
        )
        blocked = self._rack_access_cells(rack) & occupied
        if blocked:
            raise ValueError(
                f"Las celdas de acceso al rack '{rack.id}' están bloqueadas "
                f"por otro elemento: {blocked}."
            )

        self._racks[rack.id] = rack


    # Pasillos
    @property
    def pasillos(self):
        return self._pasillos

    @pasillos.setter
    def pasillos(self, value):
        if not isinstance(value, dict):
            raise TypeError("pasillos debe ser un diccionario.")
        for aisle in value.values():
            self.add_aisle(aisle)

    def add_aisle(self, aisle):
        if not isinstance(aisle, Aisle):
            raise TypeError("El elemento debe ser una instancia de Aisle.")
        if aisle.id in self._pasillos:
            raise ValueError("Ya existe un pasillo con ese id.")
        self.validate_element_bounds(aisle)

        cells = set(aisle.cells())
        if cells & self._occupied_by(self._racks):
            raise ValueError("El pasillo no puede atravesar un rack.")
        if cells & self._occupied_by(self._zonas_despacho):
            raise ValueError(f"El pasillo se superpone con una zona de despacho.")

        self._pasillos[aisle.id] = aisle

    # Pickers
    @property
    def pickers(self):
        return self._pickers

    @pickers.setter
    def pickers(self, value):
        if not isinstance(value, dict):
            raise TypeError("pickers debe ser un diccionario.")
        for picker in value.values():
            self.add_picker(picker)

    def add_picker(self, picker):
        if not isinstance(picker, Picker):
            raise TypeError("El elemento debe ser una instancia de Picker.")
        if picker.id in self._pickers:
            raise ValueError("Ya existe un picker con el mismo id.")
        self.validate_inside_warehouse(picker.posicion)
        
        self._pickers[picker.id] = picker

    # Productos
    @property
    def productos(self):
        return self._productos

    @productos.setter
    def productos(self, value):
        if not isinstance(value, dict):
            raise TypeError("productos debe ser un diccionario.")
        for product in value.values():
            self.add_product(product)

    def add_product(self, product):
        if not isinstance(product, Product):
            raise TypeError("El elemento debe ser una instancia de Product.")
        if product.id in self._productos:
            raise ValueError("Ya existe un producto con el mismo id.")
        
        try:
            rack = self._racks[product.rack_id]
            rack.add_product(product)
        except KeyError:
            raise ValueError("El producto no referencia un rack que exista en el warehouse.")

        self._productos[product.id] = product


    # Pedidos
    @property
    def pedidos(self):
        return self._pedidos

    @pedidos.setter
    def pedidos(self, value):
        if not isinstance(value, dict):
            raise TypeError("pedidos debe ser un diccionario.")
        for order in value.values():
            self.add_order(order)

    def add_order(self, order):
        if not isinstance(order, Order):
            raise TypeError("El elemento debe ser una instancia de Order.")
        if order.id in self._pedidos:
            raise ValueError(f"Ya existe un pedido con ese id.")
        self._pedidos[order.id] = order


    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("El grafo debe ser un diccionario o lista de adyacencia.")
        self._graph = value

    # Métodos de validación y consultas espaciales
    def validate_inside_warehouse(self, node):
        x, y = node[0], node[1]
        if not (0 <= x < self._ancho_x and 0 <= y < self._largo_y):
            raise ValueError("El elemento debe estar dentro de los límites del almacén.")

    def validate_element_bounds(self, element):
        self.validate_inside_warehouse(element.ubicacion)
        if element.ubicacion[0] + element.ancho > self._ancho_x:
            raise ValueError("El elemento excede el ancho del almacén.")
        if element.ubicacion[1] + element.alto > self._largo_y:
            raise ValueError("El elemento excede el largo del almacén.")

    def _zones_perimeter(self, zones):
        
        cells = set()
        for zone in zones.values():
            cells |= set(zone.perimeter_cells())
        return cells

    def _cells_of(self, element):
        return set(element.cells())

    def _occupied_by(self, elements):
        
        cells = set()
        for element in elements.values():
            cells |= set(element.cells())
        return cells

    def _adjacent_cells_of(self, element):
        """Devuelve el conjunto de celdas vecinas (4-conectadas) del elemento
        que están dentro del warehouse y no pertenecen al elemento mismo."""
        element_cells = set(element.cells())
        neighbors = set()
        for (x, y) in element_cells:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                candidate = (x + dx, y + dy)
                if candidate not in element_cells:
                    cx, cy = candidate
                    if 0 <= cx < self._ancho_x and 0 <= cy < self._largo_y:
                        neighbors.add(candidate)
        return neighbors

    def _rack_access_cells(self, rack):
        """Devuelve las celdas adyacentes a las filas del rack que pueden
        contener productos (las dos caras largas del rack).
        Un rack tiene siempre un lado de tamaño 2; las celdas de acceso
        son las que quedan fuera de ese lado de 2."""
        x0, y0 = rack.ubicacion
        access = set()
        if rack.ancho == 2:
            # Las dos caras largas son la izquierda (x0-1) y la derecha (x0+2)
            for j in range(rack.alto):
                left = (x0 - 1, y0 + j)
                right = (x0 + 2, y0 + j)
                if 0 <= left[0] < self._ancho_x:
                    access.add(left)
                if 0 <= right[0] < self._ancho_x:
                    access.add(right)
        else:
            # rack.alto == 2: las dos caras largas son la inferior (y0-1) y la superior (y0+2)
            for i in range(rack.ancho):
                bottom = (x0 + i, y0 - 1)
                top = (x0 + i, y0 + 2)
                if 0 <= bottom[1] < self._largo_y:
                    access.add(bottom)
                if 0 <= top[1] < self._largo_y:
                    access.add(top)
        return access

 

    def generar_pasillos_faltantes(self):
        """Crea pasillos de sentido 'AMBOS' para cubrir todas las celdas
        que en este momento no estén ocupadas por ningún elemento.

        Celdas contiguas que formen un rectángulo se agrupan en un único
        pasillo.  El algoritmo es greedy: en cada iteración busca el
        rectángulo libre más grande (por área) usando la técnica de
        histograma + pila sobre toda la grilla, lo registra como pasillo
        y lo marca como ocupado; repite hasta que no quedan celdas libres.
        """
        occupied = (
            self._occupied_by(self._racks)
            | self._occupied_by(self._zonas_despacho)
            | self._occupied_by(self._pasillos)
        )

        W, H = self._ancho_x, self._largo_y

        # Grilla mutable: free[y][x] = True si la celda está libre
        free = [[((x, y) not in occupied) for x in range(W)] for y in range(H)]

        next_id = self._next_auto_aisle_id()

        while True:
            rect = self._largest_free_rectangle(free, W, H)
            if rect is None:
                break

            x0, y0, ancho, alto = rect

            # Marcar celdas como ocupadas
            for dy in range(alto):
                for dx in range(ancho):
                    free[y0 + dy][x0 + dx] = False

            aisle_id = f"PAS_AUTO_{next_id}"
            next_id += 1
            aisle = Aisle(aisle_id, (x0, y0), ancho, alto, "AMBOS")
            self.add_aisle(aisle)

    def _next_auto_aisle_id(self):
        prefix = "PAS_AUTO_"
        max_n = -1
        for pid in self._pasillos:
            if pid.startswith(prefix):
                try:
                    n = int(pid[len(prefix):])
                    if n > max_n:
                        max_n = n
                except ValueError:
                    pass
        return max_n + 1

    def _largest_free_rectangle(self, free, W, H):
    
        hist = [0] * W          # hist[x] = altura libre acumulada hasta la fila actual
        best_area = 0
        best_rect = None

        for y in range(H):
            # Actualizar histograma
            for x in range(W):
                hist[x] = hist[x] + 1 if free[y][x] else 0

            # Algoritmo de pila para el mayor rectángulo en el histograma
            stack = []   # (x_inicio, altura)
            for x in range(W + 1):
                h = hist[x] if x < W else 0
                x_start = x
                while stack and stack[-1][1] > h:
                    sx, sh = stack.pop()
                    ancho = x - sx
                    area = ancho * sh
                    if area > best_area:
                        best_area = area
                        # y es la fila inferior; y0 = fila superior del rectángulo
                        best_rect = (sx, y - sh + 1, ancho, sh)
                    x_start = sx
                stack.append((x_start, h))

        return best_rect

    def build_graph(self):
        aisle_cells = self._occupied_by(self._pasillos)
        zones_perimeter_cells = self._zones_perimeter(self._zonas_despacho)
        for a in self._pasillos.values():
            vertices = a.cells()

            for v in vertices:
                x, y = v
                if a.sentido != "N" and (x, y - 1) in aisle_cells :  # ir al S
                    self._agregar_arista((x, y), (x, y - 1), 1)

                if a.sentido != "S" and (x, y + 1) in aisle_cells:  # ir al N
                    self._agregar_arista((x, y), (x, y + 1), 1)

                if a.sentido != "E" and (x - 1, y) in aisle_cells:  # ir al O
                    self._agregar_arista((x, y), (x - 1, y), 1)

                if a.sentido != "O" and (x + 1, y) in aisle_cells:  # ir al E
                    self._agregar_arista((x, y), (x + 1, y), 1)
    
    def _agregar_arista(self, origen, destino, distancia=1):
        self.graph.setdefault(origen, [])
        self.graph.setdefault(destino, [])
        
        self.graph[origen].insert(0, (destino, distancia))
            

    """
    def build_graph(self):
        aisle_cells = self._occupied_by(self._pasillos)
        for a in self._pasillos.values():
            x0, y0 = a.ubicacion
            y_sup = y0 + a.alto - 1
            x_der = x0 + a.ancho - 1

            if a.sentido != "N":  # se puede ir al S
                for i in range(a.ancho):
                    x = x0 + i
                    fin = y0 - 1 if (x, y0 - 1) in aisle_cells else y0
                    self.linea_vertical(x, y_sup, fin, -1)

            if a.sentido != "S":  # se puede ir al N
                for i in range(a.ancho):
                    x = x0 + i
                    fin = y_sup + 1 if (x, y_sup + 1) in aisle_cells else y_sup
                    self.linea_vertical(x, y0, fin, 1)

            if a.sentido != "E":  # se puede ir al O
                for j in range(a.alto):
                    y = y0 + j
                    fin = x0 - 1 if (x0 - 1, y) in aisle_cells else x0
                    self.linea_horizontal(y, x_der, fin, -1)

            if a.sentido != "O":  # se puede ir al E
                for j in range(a.alto):
                    y = y0 + j
                    fin = x_der + 1 if (x_der + 1, y) in aisle_cells else x_der
                    self.linea_horizontal(y, x0, fin, 1)

    def linea_vertical(self, x, inicio, fin, incr):
        for y in range(inicio, fin, incr):
            self._agregar_arista((x, y), (x, y + incr))

    def linea_horizontal(self, y, inicio, fin, incr):
        for x in range(inicio, fin, incr):
            self._agregar_arista((x, y), (x + incr, y))
    """

    