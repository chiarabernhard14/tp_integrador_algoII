import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
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
        graph=None,
        reduced_graph=None
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
        self.reduced_graph = reduced_graph if reduced_graph is not None else {}
        self._rack_cell = set()
        self._aisle_cell = set()
        self._dispatch_zone_cell = set() #No usar para la parte de visualización
        self._puntos_acc=set()
        self._next_auto_aisle_id = 0

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
            raise ValueError("Ya existe una puerta con ese id.")
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

        # La puerta debe ser adyacente a la zona
        if door.ubicacion not in self._adjacent_cells_of(zone):
            raise ValueError(
                "La puerta asignada debe estar en una celda adyacente a la zona de despacho."
            )

        cells = set(zone.cells())
        if cells & self._rack_cell:
            raise ValueError("La zona de despacho se superpone con un rack.")
        if cells & self._dispatch_zone_cell:
            raise ValueError("La zona de despacho se superpone con otra.")
        if cells & self._aisle_cell:
            raise ValueError("La zona de despacho se superpone con un pasillo.")

            
        x0, y0 = zone.ubicacion
        px, py = door.ubicacion
        lado_puerta = set()
        if py == y0 - 1:  # Puerta adyacente al borde inferior
            lado_puerta = {(x, y0-1) for x in range(x0, x0 + zone.ancho)}
        elif py == y0 + zone.alto:  # Puerta adyacente al borde superior
            lado_puerta = {(x, y0 + zone.alto) for x in range(x0, x0 + zone.ancho)}
        elif px == x0 - 1:  # Puerta adyacente al borde izquierdo
            lado_puerta = {(x0-1, y) for y in range(y0, y0 + zone.alto)}
        elif px == x0 + zone.ancho:  # Puerta adyacente al borde derecho
            lado_puerta = {(x0 + zone.ancho, y) for y in range(y0, y0 + zone.alto)}


        #NO USAR EL ATRIBUTO DISPATCH_ZONE_CELL EN REPRESENTACIÓN VISUAL 
        self._zonas_despacho[zone.id] = zone
        self._dispatch_zone_cell.update(cells|lado_puerta)

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
        if cells & self._rack_cell:
            raise ValueError("El rack se superpone con otro rack.")
        if cells & self._dispatch_zone_cell:
            raise ValueError("El rack se superpone con una zona de despacho.")
        if cells & self._aisle_cell:
            raise ValueError("El rack se superpone con un pasillo.")

        # Las caras de acceso del rack no pueden quedar fuera del warehouse
        # (el rack no puede estar pegado a una pared)
        x0, y0 = rack.ubicacion
        if rack.ancho == 2:
            if x0 - 1 < 0:
                raise ValueError("El rack está pegado a la pared izquierda del almacén.")
            if x0 + 2 >= self._ancho_x:
                raise ValueError("El rack está pegado a la pared derecha del almacén.")
        else:  # rack.alto == 2
            if y0 - 1 < 0:
                raise ValueError("El rack está pegado a la pared inferior del almacén.")
            if y0 + 2 >= self._largo_y:
                raise ValueError("El rack está pegado a la pared superior del almacén.")

        # Las celdas de acceso al rack (adyacentes a las caras que contienen productos)
        # no deben estar ocupadas por ningún otro elemento
        occupied = (
            self._rack_cell
            | self._dispatch_zone_cell
            | self._aisle_cell
        )
        blocked = self._rack_access_cells(rack) & occupied
        if blocked:
            raise ValueError(
                "Las celdas de acceso al rack están bloqueadas por otro elemento."
            )

        self._racks[rack.id] = rack
        self._rack_cell.update(cells)

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
        if cells & self._rack_cell:
            raise ValueError("El pasillo no puede atravesar un rack.")
        if cells & self._dispatch_zone_cell:
            raise ValueError(f"El pasillo se superpone con una zona de despacho.")
        if cells & self._aisle_cell:
            raise ValueError("El pasillo se superpone con otro pasillo.")

        self._pasillos[aisle.id] = aisle
        self._aisle_cell.update(cells)

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
            rack.add_product_rack(product)
            self._puntos_acc.update(product.acceso)
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

        x0, y0 = element.ubicacion
        ancho, alto = element.ancho, element.alto
        neighbors = set()

        for x in range(x0, x0 + ancho):
            if 0 <= x < self._ancho_x:
                if 0 <= y0 - 1 < self._largo_y:
                    neighbors.add((x, y0 - 1))
                if 0 <= y0 + alto < self._largo_y:
                    neighbors.add((x, y0 + alto))

        for y in range(y0, y0 + alto):
            if 0 <= y < self._largo_y:
                if 0 <= x0 - 1 < self._ancho_x:
                    neighbors.add((x0 - 1, y))
                if 0 <= x0 + ancho < self._ancho_x:
                    neighbors.add((x0 + ancho, y))

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
        """Genera pasillos con la partición voraz de mayor área.

        La partición avanza hasta la primera celda que queda fuera de cada
        rectángulo, y la grilla marca como ocupadas las celdas ya cubiertas.
        """
        occupied = (
            self._rack_cell
            | self._dispatch_zone_cell
            | self._aisle_cell
        )
        W, H = self._ancho_x, self._largo_y
        free = [[(x, y) not in occupied for x in range(W)] for y in range(H)]

        rectangles = self._particion_voraz_mixta(grid=free, W=W, H=H)

        for x0, y0, ancho, alto in rectangles:
            aisle_id = f"PAS_AUTO_{self._next_auto_aisle_id}"
            aisle = Aisle(aisle_id, (x0, y0), ancho, alto, "AMBOS")
            self.add_aisle(aisle)
            self._next_auto_aisle_id += 1

    


    def _particion_voraz_mixta(self, grid, W, H, on_step=None):
        """Elige el rectángulo de mayor área desde la primera celda libre.

        Modifica grid marcando las celdas usadas. Si se proporciona on_step,
        lo llama con un evento cada vez que evalúa un candidato, cuando elige
        el mejor y después de ocuparlo, para visualizar la ejecución sin
        duplicar el algoritmo.
        """
        rects = []

        for y in range(H):
            x = 0
            while x < W:
                if not grid[y][x]:
                    x += 1
                    continue

                x0 = x
                ancho_comun = W - x0
                mejor_ancho = 1
                mejor_alto = 1
                mejor_area = 1

                yy = y
                while yy < H and grid[yy][x0]:
                    ancho_fila = 0
                    while (
                        x0 + ancho_fila < W
                        and grid[yy][x0 + ancho_fila]
                    ):
                        ancho_fila += 1

                    ancho_comun = min(ancho_comun, ancho_fila)
                    alto = yy - y + 1
                    area = ancho_comun * alto
                    if area > mejor_area:
                        mejor_area = area
                        mejor_ancho = ancho_comun
                        mejor_alto = alto

                    if on_step is not None:
                        on_step({
                            "tipo": "candidato",
                            "origen": (x0, y),
                            "rectangulo": (x0, y, ancho_comun, alto),
                            "area": area,
                            "mejor_rectangulo": (x0, y, mejor_ancho, mejor_alto),
                            "mejor_area": mejor_area,
                        })

                    yy += 1

                rectangulo = (x0, y, mejor_ancho, mejor_alto)
                if on_step is not None:
                    on_step({
                        "tipo": "elegido",
                        "origen": (x0, y),
                        "rectangulo": rectangulo,
                        "area": mejor_area,
                    })

                for yy in range(y, y + mejor_alto):
                    for xx in range(x0, x0 + mejor_ancho):
                        grid[yy][xx] = False

                if on_step is not None:
                    on_step({
                        "tipo": "ocupado",
                        "origen": (x0, y),
                        "rectangulo": rectangulo,
                        "area": mejor_area,
                    })

                rects.append(rectangulo)
                x = x0 + mejor_ancho

        return rects

    def build_reduced_graph_v2(self):
        """Construye un grafo reducido con esquinas, accesos y proyecciones rectas."""
        if not self.reduced_graph:
            self.build_graph()
        else:
            return

        full_graph = self.reduced_graph

        directions = ((1, 0), (-1, 0), (0, 1), (0, -1))
        aisle_by_cell = {
            cell: aisle
            for aisle in self._pasillos.values()
            for cell in aisle.cells()
        }
        aisle_cells = set(aisle_by_cell)

        def has_edge(origin, destination):
            return any(neighbor == destination
                       for neighbor, _ in full_graph.get(origin, ()))

        def can_traverse(a, b):
            return has_edge(a, b)

        # Product.acceso puede ser una coordenada (x, y); _puntos_acc
        # también puede contener coordenadas mal cargadas como valores separados.
        product_access = {
            tuple(product.acceso)
            for product in self._productos.values()
            if product.acceso is not None
        }
        if product_access:
            self._puntos_acc = set(product_access)
        else:
            product_access = {
                tuple(cell) for cell in self._puntos_acc
                if isinstance(cell, (tuple, list)) and len(cell) == 2
            }
        vertices = {cell for cell in product_access if cell in aisle_cells}

        corners = set()
        for aisle in self._pasillos.values():
            x0, y0 = aisle.ubicacion
            x1, y1 = x0 + aisle.ancho - 1, y0 + aisle.alto - 1
            corners.update(((x0, y0), (x0, y1), (x1, y0), (x1, y1)))
        #corners &= aisle_cells
        vertices.update(corners)

        # Si una esquina toca otro pasillo, conserva ambos lados del contacto
        # cuando el grafo permite atravesarlo en al menos uno de los sentidos.
        corner_contacts = set()
        for corner in corners:
            for dx, dy in directions:
                neighbor = (corner[0] + dx, corner[1] + dy)
                if (neighbor in aisle_cells
                        and aisle_by_cell[neighbor] is not aisle_by_cell[corner]
                        and (has_edge(corner, neighbor)
                             or has_edge(neighbor, corner))):
                    corner_contacts.update((corner, neighbor))
        vertices.update(corner_contacts)
        """"
        # Los accesos a despacho son las celdas vecinas transitables a la zona.
        for zone in self._zonas_despacho.values():
            x0, y0 = zone.ubicacion
            x1, y1 = x0 + zone.ancho - 1, y0 + zone.alto - 1
            boundary = (
                [(x, y0 - 1) for x in range(x0, x1 + 1)]
                + [(x, y1 + 1) for x in range(x0, x1 + 1)]
                + [(x0 - 1, y) for y in range(y0, y1 + 1)]
                + [(x1 + 1, y) for y in range(y0, y1 + 1)]
            )
            vertices.update(cell for cell in boundary if cell in aisle_cells)"""

        # Proyecta esquinas y accesos en línea recta por cada pasillo. Al
        # cruzar a otro pasillo conserva ambos extremos del tramo de unión.
        pending = list(vertices)
        processed = set()
        while pending:
            source = pending.pop()
            if source in processed:
                continue
            processed.add(source)
            for dx, dy in directions:
                current = source
                current_aisle = aisle_by_cell[source]
                while True:
                    nxt = (current[0] + dx, current[1] + dy)
                    nxt_aisle = aisle_by_cell.get(nxt)
                    if nxt_aisle is None or not can_traverse(current, nxt):
                        break
                    if nxt_aisle is not current_aisle:
                        for projected in (current, nxt):
                            if projected not in vertices:
                                vertices.add(projected)
                                pending.append(projected)
                        current_aisle = nxt_aisle
                    current = nxt
                if current != source and current not in vertices:
                    vertices.add(current)
                    pending.append(current)

        # Proyecta accesos de producto al otro extremo cuando las aristas
        # dirigidas permiten recorrer ese tramo recto.
        for access in product_access:
            if access not in aisle_cells:
                continue
            product = next((p for p in self._productos.values()
                            if p.acceso is not None and tuple(p.acceso) == access), None)
            rack = (product.rack or self._racks.get(product.rack_id)) if product else None
            if rack is None:
                continue
            x0, y0 = rack.ubicacion
            dx, dy = ((-1 if access[0] < x0 else 1, 0) if rack.ancho == 2
                      else (0, -1 if access[1] < y0 else 1))
            current = access
            while True:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt not in aisle_cells or not can_traverse(current, nxt):
                    break
                current = nxt
            if current != access:
                if current not in vertices:
                    vertices.add(current)
                    pending.append(current)

        # Las proyecciones opuestas de productos también pueden habilitar
        # nuevas proyecciones entre pasillos; procesa las que aún quedaron pendientes.
        while pending:
            source = pending.pop()
            if source in processed:
                continue
            processed.add(source)
            for dx, dy in directions:
                current = source
                current_aisle = aisle_by_cell[source]
                while True:
                    nxt = (current[0] + dx, current[1] + dy)
                    nxt_aisle = aisle_by_cell.get(nxt)
                    if nxt_aisle is None or not can_traverse(current, nxt):
                        break
                    if nxt_aisle is not current_aisle:
                        for projected in (current, nxt):
                            if projected not in vertices:
                                vertices.add(projected)
                                pending.append(projected)
                        current_aisle = nxt_aisle
                    current = nxt

        reduced = {vertex: [] for vertex in vertices}
        edge_paths = {}
        for origin in vertices:
            for dx, dy in directions:
                current = origin
                path = [origin]
                while True:
                    nxt = (current[0] + dx, current[1] + dy)
                    if not has_edge(current, nxt):
                        break
                    path.append(nxt)
                    current = nxt
                    if current in vertices:
                        reduced[origin].append((current, len(path) - 1))
                        edge_paths[(origin, current)] = tuple(path)
                        break
       
        self.reduced_graph = reduced
        

    def build_graph(self):
        #cant_pasillos=self.generar_pasillos_faltantes()
        self.generar_pasillos_faltantes()
        aisle_cells = self._occupied_by(self._pasillos)
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
        #return cant_pasillos
    
    def _agregar_arista(self, origen, destino, distancia=1):
        self.graph.setdefault(origen, [])
        self.graph.setdefault(destino, [])
        self.reduced_graph.setdefault(origen, [])
        self.reduced_graph.setdefault(destino, [])
        
        self.graph[origen].insert(0, (destino, distancia))
        self.reduced_graph[origen].insert(0, (destino, distancia))

  
