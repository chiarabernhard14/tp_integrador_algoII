import sys
from collections import deque
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ProductoInaccesible import ProductoInaccesible
from domain.validation import validate_positive_int
from .DoorE import Door
from .DispatchZoneE import DispatchZone
from .RackE import Rack
from .AisleE import Aisle
from .PickerE import Picker
from .ProductE import Product
from .OrderE import Order
from .Vertice import Vertice


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
        self.celdas = set()

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
        self._acceso_cargados = set()
        self._pasillos_bloqueados = set()
        self._next_auto_aisle_id = 0

#region
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
        self.celdas.update(
            Vertice(ubicacion=celda, pasillo=aisle)
            for celda in cells
        )

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
            if product.acceso is not None:
                self._acceso_cargados.add(product.acceso)

        except KeyError:
            raise ValueError("El producto no referencia un rack que exista en el warehouse.")

        self._productos[product.id] = product

    def _eliminar_productos_inaccesibles(self, productos):
        """Quita productos inválidos del rack, del almacén y de sus pedidos."""
        ids = {producto.id for producto in productos}
        for producto in productos:
            if producto.rack is not None:
                producto.rack.remove_product(producto)
            self._productos.pop(producto.id, None)

        for pedido_id, pedido in list(self._pedidos.items()):
            pedido.items = [
                item for item in pedido.items
                if item.producto_id not in ids
                and getattr(item.producto, "id", None) not in ids
            ]
            if not pedido.items:
                del self._pedidos[pedido_id]

        self._acceso_cargados = {
            producto.acceso
            for producto in self._productos.values()
            if producto.acceso is not None
        }


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
#endregion
    # Métodos de validación y consultas espaciales
#region
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
#endregion
    
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


    def _particion_voraz_mixta(self, grid, W, H):
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

                    yy += 1

                rectangulo = (x0, y, mejor_ancho, mejor_alto)

                for yy in range(y, y + mejor_alto):
                    for xx in range(x0, x0 + mejor_ancho):
                        grid[yy][xx] = False

                rects.append(rectangulo)
                x = x0 + mejor_ancho

        return rects

    def build_reduced_graph_v2(self):
        """Construye un grafo reducido con esquinas, accesos y proyecciones rectas."""

        if not self.graph:
            self.build_graph()
            return self.reduced_graph

        directions = ((1, 0), (-1, 0), (0, 1), (0, -1))
        vertice_por_celda = {
            vertice.ubicacion: vertice for vertice in self.celdas
        }
        aisle_cells = self._aisle_cell

        def has_edge(origin, destination):
            return any(neighbor == destination
                       for neighbor, _ in self.graph.get(origin, ()))

        product_access = self._acceso_cargados
     
        vertices = {cell for cell in product_access}

        corners = set()
        for aisle in self._pasillos.values():
            x0, y0 = aisle.ubicacion
            x1, y1 = x0 + aisle.ancho - 1, y0 + aisle.alto - 1
            corners.update(((x0, y0), (x0, y1), (x1, y0), (x1, y1)))
        vertices.update(corners)

        # Si una esquina toca otro pasillo, conserva ambos lados del contacto
        # cuando el grafo permite atravesarlo en al menos uno de los sentidos.
        corner_contacts = set()
        for corner in corners:
            vertice_esquina = vertice_por_celda.get(corner)
            if vertice_esquina is None:
                continue
            pasillo = vertice_esquina.pasillo
            pasillos_adyacentes = set(pasillo.salida) | set(pasillo.entrada)


            for pasillo_id in pasillos_adyacentes:
                otro_pasillo = self._pasillos.get(pasillo_id)
                if otro_pasillo is None:
                    continue

                salidas_desde_esquina = corner in pasillo.salida.get(
                    pasillo_id, ()
                )
                origenes_de_entrada = set(
                    pasillo.entrada.get(pasillo_id, ())
                )
                for dx, dy in directions:
                    neighbor = (corner[0] + dx, corner[1] + dy)
                    vertice_vecino = vertice_por_celda.get(neighbor)
                    if (vertice_vecino is None
                            or vertice_vecino.pasillo is not otro_pasillo):
                        continue
                    if (
                        salidas_desde_esquina and has_edge(corner, neighbor)
                    ) or (
                        neighbor in origenes_de_entrada
                        and has_edge(neighbor, corner)
                    ):
                        corner_contacts.update((corner, neighbor))
        vertices.update(corner_contacts)

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
                if nxt not in aisle_cells or not has_edge(current, nxt):
                    break
                current = nxt
            if current != access:
                if current not in vertices:
                    vertices.add(current)
                    

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
                current_aisle = vertice_por_celda[source].pasillo
                while True:
                    nxt = (current[0] + dx, current[1] + dy)
                    vertice_siguiente = vertice_por_celda.get(nxt)
                    if vertice_siguiente is None or not has_edge(current, nxt):
                        break
                    nxt_aisle = vertice_siguiente.pasillo
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

        # Conserva las dos celdas exteriores de cada esquina de despacho,
        # excepto las dos del lado donde está la puerta.
        for zone in self._zonas_despacho.values():
            x0, y0 = zone.ubicacion
            x1, y1 = x0 + zone.ancho - 1, y0 + zone.alto - 1
            puerta = self._puertas[zone.puerta_id]
            px, py = puerta.ubicacion

            celdas_exteriores = {
                (x0, y0 - 1), (x0 - 1, y0),
                (x1, y0 - 1), (x1 + 1, y0),
                (x0 - 1, y1), (x0, y1 + 1),
                (x1 + 1, y1), (x1, y1 + 1),
            }

            if py == y0 - 1:  # puerta al norte
                celdas_exteriores.difference_update(
                    {(x0, y0 - 1), (x1, y0 - 1)}
                )
            elif py == y1 + 1:  # puerta al sur
                celdas_exteriores.difference_update(
                    {(x0, y1 + 1), (x1, y1 + 1)}
                )
            elif px == x0 - 1:  # puerta al oeste
                celdas_exteriores.difference_update(
                    {(x0 - 1, y0), (x0 - 1, y1)}
                )
            elif px == x1 + 1:  # puerta al este
                celdas_exteriores.difference_update(
                    {(x1 + 1, y0), (x1 + 1, y1)}
                )

            vertices.update(
                cell for cell in celdas_exteriores if cell in aisle_cells
            )

        reduced = {vertex: [] for vertex in vertices}
        for origin in vertices:
            for dx, dy in directions:
                current = origin
                distancia = 0
                while True:
                    nxt = (current[0] + dx, current[1] + dy)
                    if not has_edge(current, nxt):
                        break
                    distancia += 1
                    current = nxt
                    if current in vertices:
                        reduced[origin].append((current, distancia))
                        break
       
        self.reduced_graph = reduced
        self.bloquear_pasillos_sin_salida()
        self.validar_acceso_despacho_a_producto()
        self.validar_acceso_productos_a_despacho()
        

    def build_graph(self):
        self.generar_pasillos_faltantes()
        
        vertice_por_celda = {
            vertice.ubicacion: vertice for vertice in self.celdas
        }

        def agregar_arista(origen, destino, pasillo_origen, pasillo_destino):
            self._agregar_arista(origen, destino, 1)
            if pasillo_origen is pasillo_destino:
                return

            salidas = pasillo_origen.salida.setdefault(pasillo_destino.id, [])
            if origen not in salidas:
                salidas.append(origen)

            entradas = pasillo_destino.entrada.setdefault(pasillo_origen.id, [])
            if origen not in entradas:
                entradas.append(origen)

        for a in self._pasillos.values():
            vertices = a.cells()

            for v in vertices:
                x, y = v
                destino = (x, y - 1)
                vertice_destino = vertice_por_celda.get(destino)
                if (a.sentido != "N" and vertice_destino is not None
                        and vertice_destino.pasillo.sentido != "N"):
                    agregar_arista(v, destino, a, vertice_destino.pasillo)

                destino = (x, y + 1)
                vertice_destino = vertice_por_celda.get(destino)
                if (a.sentido != "S" and vertice_destino is not None
                        and vertice_destino.pasillo.sentido != "S"):
                    agregar_arista(v, destino, a, vertice_destino.pasillo)

                destino = (x - 1, y)
                vertice_destino = vertice_por_celda.get(destino)
                if (a.sentido != "E" and vertice_destino is not None
                        and vertice_destino.pasillo.sentido != "E"):
                    agregar_arista(v, destino, a, vertice_destino.pasillo)

                destino = (x + 1, y)
                vertice_destino = vertice_por_celda.get(destino)
                if (a.sentido != "O" and vertice_destino is not None
                        and vertice_destino.pasillo.sentido != "O"):
                    agregar_arista(v, destino, a, vertice_destino.pasillo)
        self.build_reduced_graph_v2()

    @staticmethod
    def _celdas_rectangulo(vertice_a, vertice_b, vertice_c=None, vertice_d=None):
        """Devuelve las celdas entre dos extremos de línea o cuatro esquinas."""
        if vertice_c is None and vertice_d is None:
            x_a, y_a = vertice_a
            x_b, y_b = vertice_b
            if x_a == x_b:
                return {(x_a, y) for y in range(min(y_a, y_b), max(y_a, y_b) + 1)}
            return {
                (x, y_a)
                for x in range(min(x_a, x_b), max(x_a, x_b) + 1)
            }

        vertices = (vertice_a, vertice_b, vertice_c, vertice_d)
        x_min = min(vertice[0] for vertice in vertices)
        x_max = max(vertice[0] for vertice in vertices)
        y_min = min(vertice[1] for vertice in vertices)
        y_max = max(vertice[1] for vertice in vertices)

        return {
            (x, y)
            for x in range(x_min, x_max + 1)
            for y in range(y_min, y_max + 1)
        }

    def bloquear_pasillos_sin_salida(self):
        """Quita sectores atrapados, analizándolos sobre el grafo reducido."""
        celdas_eliminadas = set()
        pasillos_completos_bloqueados = set(self._pasillos_bloqueados)

        # Mapa celda -> pasillo propietario sobre todas las celdas activas.
        # Se mantiene quitando las celdas a medida que se eliminan.
        propietario_por_celda = {
            vertice.ubicacion: vertice.pasillo for vertice in self.celdas
        }

        while True:
            # Nodos activos del grafo reducido con su pasillo dueño.
            propietario_por_nodo = {
                nodo: pasillo
                for nodo, pasillo in propietario_por_celda.items()
                if nodo in self.reduced_graph
            }
            nodos_por_pasillo = {}
            for nodo, pasillo in propietario_por_nodo.items():
                nodos_por_pasillo.setdefault(pasillo.id, set()).add(nodo)

            nodos_atrapados = set()
            for pasillo in self._pasillos.values():
                if pasillo.blocked:
                    continue

                nodos = nodos_por_pasillo.get(pasillo.id, set())
                if not nodos:
                    continue

                # --- Salidas directas: usa pasillo.salida (ya guardado) ---
                # pasillo.salida[id_destino] = celdas de este pasillo que
                # conectan hacia el pasillo id_destino.
                salidas_directas = set()
                for id_destino, celdas_origen in pasillo.salida.items():
                    if id_destino not in self._pasillos:
                        continue
                    for origen in celdas_origen:
                        if origen not in nodos:
                            continue
                        for destino, _peso in self.reduced_graph.get(origen, ()):
                            if (
                                propietario_por_nodo.get(destino) is not None
                                and propietario_por_nodo[destino].id == id_destino
                            ):
                                salidas_directas.add(origen)
                                break

                # Predecesores dentro del pasillo (grafo inverso local).
                predecesores = {nodo: set() for nodo in nodos}
                for origen in nodos:
                    for destino, _peso in self.reduced_graph.get(origen, ()):
                        if destino in nodos:
                            predecesores[destino].add(origen)

                # Nodos que pueden seguir hasta una salida registrada.
                pueden_salir = set(salidas_directas)
                pendientes = list(salidas_directas)
                while pendientes:
                    actual = pendientes.pop()
                    for anterior in predecesores[actual]:
                        if anterior not in pueden_salir:
                            pueden_salir.add(anterior)
                            pendientes.append(anterior)

                # --- Entradas: usa pasillo.entrada (ya guardado) ---
                # pasillo.entrada[id_origen] = celdas del pasillo id_origen que
                # conectan hacia este pasillo.
                entradas = set()
                for id_origen, celdas_origen in pasillo.entrada.items():
                    if id_origen not in self._pasillos:
                        continue
                    for origen in celdas_origen:
                        if (
                            origen not in propietario_por_nodo
                            or propietario_por_nodo[origen].id != id_origen
                        ):
                            continue
                        for destino, _peso in self.reduced_graph.get(origen, ()):
                            if destino in nodos:
                                entradas.add(destino)

                alcanzables = set(entradas)
                pendientes = list(entradas)
                while pendientes:
                    actual = pendientes.pop()
                    for vecino, _peso in self.reduced_graph.get(actual, ()):
                        if vecino in nodos and vecino not in alcanzables:
                            alcanzables.add(vecino)
                            pendientes.append(vecino)

                nodos_atrapados.update(alcanzables - pueden_salir)

            if not nodos_atrapados:
                break

            pasillos_afectados = {
                propietario_por_nodo[nodo]
                for nodo in nodos_atrapados
                if nodo in propietario_por_nodo
            }
            celdas_sector = set()
            rectangulos_sector = []

            for pasillo in pasillos_afectados:
                nodos_pasillo = nodos_por_pasillo.get(pasillo.id, set())
                nodos_sector = {
                    nodo for nodo in nodos_atrapados
                    if propietario_por_nodo.get(nodo) is pasillo
                }
                if not nodos_sector:
                    continue

                x0, y0 = pasillo.ubicacion
                x1 = x0 + pasillo.ancho - 1
                y1 = y0 + pasillo.alto - 1

                vecinos_pasillo = {nodo: set() for nodo in nodos_pasillo}
                for origen in nodos_pasillo:
                    for destino, _peso in self.reduced_graph.get(origen, ()):
                        if destino in nodos_pasillo:
                            vecinos_pasillo[origen].add(destino)
                            vecinos_pasillo[destino].add(origen)

                no_procesados = set(nodos_sector)
                while no_procesados:
                    componente = {no_procesados.pop()}
                    pendientes_componente = list(componente)
                    while pendientes_componente:
                        actual = pendientes_componente.pop()
                        for vecino in vecinos_pasillo[actual] & no_procesados:
                            no_procesados.remove(vecino)
                            componente.add(vecino)
                            pendientes_componente.append(vecino)

                    vertices_limite = set(componente)
                    for nodo in componente:
                        vertices_limite.update(
                            vecinos_pasillo[nodo] - nodos_sector
                        )

                    x_min = min(nodo[0] for nodo in vertices_limite)
                    x_max = max(nodo[0] for nodo in vertices_limite)
                    y_min = min(nodo[1] for nodo in vertices_limite)
                    y_max = max(nodo[1] for nodo in vertices_limite)
                    if pasillo.ancho > pasillo.alto:
                        y_min, y_max = y0, y1
                    elif pasillo.alto > pasillo.ancho:
                        x_min, x_max = x0, x1
                    else:
                        x_min, x_max = max(x_min, x0), min(x_max, x1)
                        y_min, y_max = max(y_min, y0), min(y_max, y1)

                    esquinas = {
                        (x_min, y_min), (x_min, y_max),
                        (x_max, y_min), (x_max, y_max),
                    }
                    if len(esquinas) == 4:
                        celdas_rectangulo = self._celdas_rectangulo(*esquinas)
                    else:
                        extremos = tuple(esquinas)
                        if len(extremos) == 1:
                            celdas_rectangulo = set(extremos)
                        else:
                            celdas_rectangulo = self._celdas_rectangulo(*extremos)
                    celdas_rectangulo &= set(pasillo.cells())
                    celdas_sector.update(celdas_rectangulo)
                    rectangulos_sector.append((x_min, y_min, x_max, y_max))

            def arista_cruza_sector(origen, destino):
                x_a, y_a = origen
                x_b, y_b = destino
                for x_min, y_min, x_max, y_max in rectangulos_sector:
                    if x_a == x_b and x_min <= x_a <= x_max:
                        if max(min(y_a, y_b), y_min) <= min(max(y_a, y_b), y_max):
                            return True
                    elif y_a == y_b and y_min <= y_a <= y_max:
                        if max(min(x_a, x_b), x_min) <= min(max(x_a, x_b), x_max):
                            return True
                return False

            # Limpia aristas de entrada hacia sectores removidos usando
            # la relación de origen guardada por cada pasillo destino.
            for pasillo_destino in self._pasillos.values():
                celdas_destino = celdas_sector & set(pasillo_destino.cells())
                if not celdas_destino:
                    continue
                for celdas_origen in pasillo_destino.entrada.values():
                    for origen in celdas_origen:
                        if origen in self.graph:
                            self.graph[origen] = [
                                (destino, peso)
                                for destino, peso in self.graph[origen]
                                if destino not in celdas_destino
                            ]

            self.graph = {
                nodo: [(destino, peso) for destino, peso in aristas
                       if destino not in celdas_sector]
                for nodo, aristas in self.graph.items()
                if nodo not in celdas_sector
            }

            # Modifica el grafo reducido existente: no vuelve a construirlo.
            for nodo in tuple(self.reduced_graph):
                if nodo in celdas_sector:
                    del self.reduced_graph[nodo]
                    continue
                self.reduced_graph[nodo][:] = [
                    (destino, peso)
                    for destino, peso in self.reduced_graph[nodo]
                    if destino in self.reduced_graph
                    and destino not in celdas_sector
                    and not arista_cruza_sector(nodo, destino)
                ]

            self.celdas.difference_update({
                vertice for vertice in self.celdas
                if vertice.ubicacion in celdas_sector
            })
            self._aisle_cell.difference_update(celdas_sector)
            celdas_eliminadas.update(celdas_sector)

            # Mantiene actualizado el mapa celda -> pasillo: solo quita
            # las eliminadas, no recorre todo de nuevo.
            for celda in celdas_sector:
                propietario_por_celda.pop(celda, None)

            # Actualiza entrada/salida filtrando las listas ya guardadas,
            # sin reconstruir índices desde cero recorriendo self.celdas.
            for pasillo_origen in self._pasillos.values():
                for id_destino in tuple(pasillo_origen.salida.keys()):
                    pasillo_destino = self._pasillos.get(id_destino)
                    if pasillo_destino is None:
                        pasillo_origen.salida.pop(id_destino, None)
                        continue
                    destinos_activos = {
                        nodo for nodo, p in propietario_por_celda.items()
                        if p.id == id_destino
                    }
                    origenes_vivos = [
                        origen for origen in pasillo_origen.salida[id_destino]
                        if origen not in celdas_sector
                        and any(
                            destino in destinos_activos
                            for destino, _peso in self.graph.get(origen, ())
                        )
                    ]
                    if origenes_vivos:
                        pasillo_origen.salida[id_destino] = origenes_vivos
                        pasillo_destino.entrada[pasillo_origen.id] = list(
                            origenes_vivos
                        )
                    else:
                        pasillo_origen.salida.pop(id_destino, None)
                        pasillo_destino.entrada.pop(pasillo_origen.id, None)

            for pasillo in self._pasillos.values():
                if (not set(pasillo.cells()) - celdas_eliminadas
                        and not pasillo.blocked):
                    pasillo.blocked = True
                    pasillos_completos_bloqueados.add(pasillo.id)

        self._pasillos_bloqueados = pasillos_completos_bloqueados
        return sorted(celdas_eliminadas)

    def _nodos_despacho_en_grafo(self):
        """Celdas del grafo reducido adyacentes a alguna zona de despacho."""
        nodos = set()
        for zona in self._zonas_despacho.values():
            nodos.update(
                self._adjacent_cells_of(zona) & self.reduced_graph.keys()
            )
        return nodos

    def validar_acceso_productos_a_despacho(self):
        """Valida que cada producto tenga un camino dirigido hacia despacho.

        La búsqueda empieza en la celda de acceso al rack y termina en
        cualquier celda del grafo adyacente a una zona de despacho.
        Devuelve los productos sin ruta; si hay alguno, informa sus IDs.
        """
        if not self._productos:
            return []

        if not self._zonas_despacho:
            raise ValueError(
                "No se puede validar el acceso de los productos: "
                "el warehouse no tiene zonas de despacho."
            )

        nodos_despacho = self._nodos_despacho_en_grafo()

        # resultado_por_nodo: nodo -> True si se sabe que llega a despacho,
        # False si se sabe que NO llega. 
        resultado_por_nodo = {nodo: True for nodo in nodos_despacho}

        accesos_con_ruta = set()
        for origen in self._acceso_cargados:
            if origen in resultado_por_nodo:
                if resultado_por_nodo[origen]:
                    accesos_con_ruta.add(origen)
                # Si se sabe que no llega, o se acaba de confirmar que llega,
                # no hace falta volver a hacer BFS desde este acceso.
                continue
            if origen not in self.reduced_graph:
                resultado_por_nodo[origen] = False
                continue

            padres = {origen: None}
            visitados = {origen}
            pendientes = deque([origen])
            destino = None

            while pendientes and destino is None:
                actual = pendientes.popleft()

                # Si llegamos a un nodo ya resuelto, usamos su resultado
                # en lugar de seguir explorando desde él.
                if actual in resultado_por_nodo:
                    if resultado_por_nodo[actual]:
                        destino = actual
                        break
                    # Se sabe que no llega a despacho: no expandimos este nodo.
                    continue

                if actual in nodos_despacho:
                    destino = actual
                    break

                for vecino, _peso in self.reduced_graph.get(actual, ()):
                    if vecino not in visitados:
                        if vecino in resultado_por_nodo:
                            if resultado_por_nodo[vecino]:
                                padres[vecino] = actual
                                destino = vecino
                                break
                            # Se sabe que no llega: no lo agregamos a la cola.
                            continue
                        padres[vecino] = actual
                        visitados.add(vecino)
                        pendientes.append(vecino)

            if destino is not None:
                # Marca el camino recorrido (origen hasta destino) como que
                # llega a despacho, para reusarlo en futuros BFS.
                actual = destino
                while actual is not None:
                    if actual in self._acceso_cargados:
                        accesos_con_ruta.add(actual)
                    resultado_por_nodo[actual] = True
                    actual = padres[actual]
            else:
                # BFS agotado sin encontrar despacho: ninguno de los nodos
                # visitados llega a despacho, se guarda para no recalcularlo.
                for nodo in visitados:
                    resultado_por_nodo[nodo] = False

        accesos_sin_ruta = self._acceso_cargados - accesos_con_ruta

        inaccesibles = [
            producto for producto in self._productos.values()
            if producto.acceso in accesos_sin_ruta
        ]

        if inaccesibles:
            detalle = ", ".join(
                f"{p.id} ({p.nombre}, acceso={p.acceso})"
                for p in inaccesibles
            )
            self._eliminar_productos_inaccesibles(inaccesibles)
            raise ProductoInaccesible(
                "No existe un camino dirigido desde el acceso de estos "
                f"productos hasta ninguna zona de despacho: {detalle}."
            )

        return []

    def validar_acceso_despacho_a_producto(self):
        """Valida que despacho pueda alcanzar todos los productos.

        Para cada producto, busca un camino dirigido desde las zonas de
        despacho hasta su celda de acceso.
        """
        if not self._productos:
            return []

        if not self._zonas_despacho:
            raise ValueError(
                "No se puede validar el acceso al despacho: "
                "el warehouse no tiene zonas de despacho."
            )

        nodos_despacho = self._nodos_despacho_en_grafo()

        visitados = set(nodos_despacho)
        pendientes = deque(nodos_despacho)

        # Accesos de producto que aún faltan por alcanzar desde despacho.
        # Los que ya están entre los nodos iniciales se dan por alcanzados.
        accesos_restantes = set(self._acceso_cargados)
        accesos_restantes.difference_update(visitados)

        while pendientes and accesos_restantes:
            actual = pendientes.popleft()
            for vecino, _peso in self.reduced_graph.get(actual, ()):
                if vecino not in visitados:
                    visitados.add(vecino)
                    pendientes.append(vecino)
                    if vecino in accesos_restantes:
                        accesos_restantes.discard(vecino)
            if not accesos_restantes:
                # Ya se alcanzaron todas las celdas de acceso: no hace falta
                # seguir explorando el grafo.
                break

        accesos_sin_ruta = accesos_restantes
        inaccesibles = [
            producto for producto in self._productos.values()
            if producto.acceso in accesos_sin_ruta
        ]
        if inaccesibles:
            detalle = ", ".join(
                f"{p.id} ({p.nombre}, acceso={p.acceso})"
                for p in inaccesibles
            )
            self._eliminar_productos_inaccesibles(inaccesibles)
            raise ProductoInaccesible(
                "No existe un camino dirigido desde ninguna zona de "
                f"despacho hasta el acceso de estos productos: {detalle}."
            )

        return []
    
    def _agregar_arista(self, origen, destino, distancia=1):
        self.graph.setdefault(origen, [])
        self.graph.setdefault(destino, [])
        
        self.graph[origen].insert(0, (destino, distancia))

  
