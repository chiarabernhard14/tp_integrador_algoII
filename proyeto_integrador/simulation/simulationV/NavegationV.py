#from domain.pathFinding import PathFinder
from domain.RecorridosV import PathFinderV

AVANCE = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "O": (-1, 0)}
DIRECCIONES = ((0, 1), (0, -1), (1, 0), (-1, 0))



class GrafoFiltrado:
    def __init__(self, base, ocupadas):
        self.base = base
        self.ocupadas = ocupadas

    def get(self, nodo, defecto=None):
        lista = self.base.get(nodo)

        if lista is None:
            return defecto

        return [
            (vecino, peso)
            for vecino, peso in lista
            if vecino not in self.ocupadas
        ]

    def __getitem__(self, nodo):
        if nodo not in self.base:
            raise KeyError(nodo)

        return self.get(nodo, [])



class Navegacion:

    def __init__(self, warehouse):
        self.ancho_x = warehouse.ancho_x
        self.largo_y = warehouse.largo_y
        self.busquedas = 0

        # Reutilizar el grafo construido por Warehouse.
        if not warehouse.graph:
            warehouse.build_graph_by_cell()

        if not isinstance(warehouse.graph, dict):
            raise TypeError(
                "Navegacion necesita un grafo en formato diccionario."
            )

        self.grafo = warehouse.graph

        # Mantener las celdas de los elementos físicos.
        self.bloqueadas = set()
        self.zonas = set()

        for rack in warehouse.racks.values():
            self.bloqueadas.update(rack.cells())

        for zona in warehouse.zonas_despacho.values():
            self.zonas.update(zona.cells())

        self.bloqueadas.update(self.zonas)

        for puerta in warehouse.puertas.values():
            self.bloqueadas.add(tuple(puerta.ubicacion))

        # Información auxiliar para reconocer pasillos e intersecciones.
        self.sentido = {}
        self.eje = {}

        for pasillo in warehouse.pasillos.values():
            eje = self._eje_de(pasillo)

            for celda in pasillo.cells():
                self.sentido[celda] = (pasillo.sentido, pasillo.id)
                self.eje[celda] = eje

        # Obtener los vecinos del grafo existente, sin recalcularlos.
        self.vecinos = {
            celda: [vecino for vecino, _ in lista]
            for celda, lista in self.grafo.items()
        }

        # Celdas de circulación desde las que se llega al despacho.
        self.despacho = set()

        for celda in self.grafo:
            if self._adyacentes(celda) & self.zonas:
                self.despacho.add(celda)

        # Accesos a racks.
        self.acceso_rack = {}

        for rack in warehouse.racks.values():
            self._registrar_accesos(rack)

        # Conservar el grafo auxiliar con nodos de productos.
        self.pilas = set()
        self.grafo_rutas = {
            celda: list(lista)
            for celda, lista in self.grafo.items()
        }

        for producto in warehouse.productos.values():
            celda = tuple(producto.ubicacion)

            if celda not in self.pilas and self.acceso_rack.get(celda):
                self._agregar_pila(celda)

        self.intersecciones = self._calcular_intersecciones()

    def _eje_de(self, pasillo):
        if pasillo.sentido in ("N", "S"):
            return "V"
        if pasillo.sentido in ("E", "O"):
            return "H"
        if pasillo.alto > pasillo.ancho:
            return "V"
        if pasillo.ancho > pasillo.alto:
            return "H"
        return "X"

    def _adyacentes(self, celda):
        resultado = set()
        for dx, dy in DIRECCIONES:
            resultado.add((celda[0] + dx, celda[1] + dy))
        return resultado


    def _registrar_accesos(self, rack):
        x0 = rack.ubicacion[0]
        y0 = rack.ubicacion[1]
        for celda in rack.cells():
            x, y = celda
            candidatas = []
            if rack.ancho == 2:
                candidatas.append((x - 1, y) if x == x0 else (x + 1, y))
            if rack.alto == 2:
                candidatas.append((x, y - 1) if y == y0 else (x, y + 1))
            accesos = set()
            for candidata in candidatas:
                if candidata in self.vecinos:
                    accesos.add(candidata)
            self.acceso_rack[celda] = accesos

    def _agregar_pila(self, celda):
        accesos = sorted(self.acceso_rack[celda])
        self.grafo_rutas[celda] = [(acceso, 1) for acceso in accesos]
        for acceso in accesos:
            self.grafo_rutas[acceso] = self.grafo_rutas[acceso] + [(celda, 1)]
        self.pilas.add(celda)

    def _calcular_intersecciones(self):
        resultado = set()
        for celda, lista in self.vecinos.items():
            if celda not in self.eje:
                continue
            for destino in lista:
                if destino not in self.eje:
                    continue
                if self.sentido[celda][1] == self.sentido[destino][1]:
                    continue
                if self.eje[celda] != self.eje[destino] or self.eje[celda] == "X":
                    resultado.add(celda)
                    resultado.add(destino)
        return resultado

    def accesos(self, x, y):
        return self.acceso_rack.get((x, y), set())
    

    def camino(self, origen, destinos, ocupadas=(), algoritmo="astar"):
        if algoritmo == "astar":
            buscador = PathFinderV.a_estrella
        elif algoritmo == "dijkstra":
            buscador = PathFinderV.dijkstra
        else:
            raise ValueError(
                "Algoritmo no válido. Usá 'astar' o 'dijkstra'."
            )

        if origen not in self.grafo:
            return None

        destinos = set(destinos)
        ocupadas = set(ocupadas)

        if origen in destinos:
            return []

        destinos_validos = destinos.intersection(self.grafo.keys())
        destinos_validos -= ocupadas

        if not destinos_validos:
            return None

        grafo_busqueda = self.grafo

        if ocupadas:
            grafo_busqueda = GrafoFiltrado(self.grafo, ocupadas)

        ordenados = sorted(
            (
                PathFinderV.manhattan(origen, destino),
                destino
            )
            for destino in destinos_validos
        )

        mejor_costo = float("inf")
        mejor_ruta = None

        for distancia_minima, destino in ordenados:
            if distancia_minima >= mejor_costo:
                break

            self.busquedas += 1

            costo, ruta, expandidos = buscador(
                grafo_busqueda,
                origen,
                destino
            )

            if not ruta or costo == float("inf"):
                continue

            if costo < mejor_costo:
                mejor_costo = costo
                mejor_ruta = ruta[1:]

        return mejor_ruta

