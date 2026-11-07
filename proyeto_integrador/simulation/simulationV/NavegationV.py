from .RecorridosV import PathFinderV
DIRECCIONES = (
    (0, 1),
    (0, -1),
    (1, 0),
    (-1, 0)
)



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

    def __contains__(self, nodo):
        return nodo in self.base



class Navegacion:

    def __init__(self, warehouse, algoritmo="dijkstra"):
        buscadores = {
            "a_estrella": PathFinderV.a_estrella,
            "dijkstra": PathFinderV.dijkstra,
        }
        if algoritmo not in buscadores:
            raise ValueError(
                f"Algoritmo de camino desconocido: {algoritmo}. "
                f"Opciones: {', '.join(buscadores)}."
            )
        self.algoritmo = algoritmo
        self._buscador = buscadores[algoritmo]
        self.ancho_x = warehouse.ancho_x
        self.largo_y = warehouse.largo_y
        self.busquedas = 0

        # Reutilizar el grafo construido por Warehouse.
        if not warehouse.graph:
            warehouse.build_graph()

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
            celda = tuple(producto.ubicacion[:2])

            if celda not in self.pilas and self.acceso_rack.get(celda):
                self._agregar_pila(celda)

        self.intersecciones = self._calcular_intersecciones()
        self.grafo_reducido, self._tramos_reducidos = (
            self._construir_grafo_reducido(warehouse)
        )

    def _construir_grafo_reducido(self, warehouse):
        """Comprime tramos rectos del grafo sin modificar el warehouse."""
        entrantes = {celda: set() for celda in self.grafo}
        for origen, vecinos in self.grafo.items():
            for vecino, _ in vecinos:
                entrantes.setdefault(vecino, set()).add(origen)

        accesos_producto = {
            tuple(producto.acceso)
            for producto in warehouse.productos.values()
            if producto.acceso is not None
            and tuple(producto.acceso) in self.grafo
        }
        vertices = set(accesos_producto) | set(self.despacho)
        for celda in self.grafo:
            vecinos = {vecino for vecino, _ in self.grafo[celda]}
            vecinos.update(entrantes.get(celda, ()))
            if len(vecinos) != 2:
                vertices.add(celda)
                continue

            primero, segundo = tuple(vecinos)
            dx1, dy1 = primero[0] - celda[0], primero[1] - celda[1]
            dx2, dy2 = segundo[0] - celda[0], segundo[1] - celda[1]
            if dx1 + dx2 != 0 or dy1 + dy2 != 0:
                vertices.add(celda)

        reducido = {celda: [] for celda in vertices}
        tramos = {}
        pendientes = list(vertices)
        while pendientes:
            origen = pendientes.pop()
            for vecino, peso in self.grafo.get(origen, ()):
                camino = [origen, vecino]
                anterior, actual = origen, vecino
                costo = peso
                visitadas = {origen}

                while actual not in vertices:
                    opciones = [
                        (siguiente, peso_siguiente)
                        for siguiente, peso_siguiente in self.grafo.get(actual, ())
                        if siguiente != anterior
                    ]
                    if len(opciones) != 1:
                        vertices.add(actual)
                        reducido.setdefault(actual, [])
                        pendientes.append(actual)
                        break

                    siguiente, peso_siguiente = opciones[0]
                    if siguiente in visitadas:
                        vertices.add(actual)
                        reducido.setdefault(actual, [])
                        pendientes.append(actual)
                        break

                    anterior, actual = actual, siguiente
                    camino.append(actual)
                    costo += peso_siguiente
                    visitadas.add(anterior)

                if actual in vertices and actual != origen:
                    reducido[origen].append((actual, costo))
                    tramos[(origen, actual)] = tuple(camino)

        return reducido, tramos

    def grafo_reducido_con_puntos(self, puntos):
        """Agrega al grafo reducido paradas que caen dentro de tramos rectos."""
        puntos = {tuple(punto) for punto in puntos}
        if not puntos.issubset(self.grafo):
            return None

        reducido = {celda: [] for celda in self.grafo_reducido}
        encontrados = set(self.grafo_reducido)

        for (origen, destino), tramo in self._tramos_reducidos.items():
            indices = [
                (indice, celda)
                for indice, celda in enumerate(tramo)
                if celda in puntos or indice in (0, len(tramo) - 1)
            ]
            for (i, desde), (j, hasta) in zip(indices, indices[1:]):
                reducido.setdefault(desde, [])
                reducido.setdefault(hasta, [])
                reducido[desde].append((hasta, j - i))
                encontrados.update((desde, hasta))

        if not puntos.issubset(encontrados):
            return None
        return reducido

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
        x0, y0 = rack.ubicacion

        for celda in rack.cells():
            x, y = celda

            if rack.ancho == 2:
                candidata = (
                    (x0 - 1, y) if x == x0
                    else (x0 + 2, y)
                )
            else:
                candidata = (
                    (x, y0 - 1) if y == y0
                    else (x, y0 + 2)
                )

            if candidata in self.vecinos:
                self.acceso_rack[celda] = {candidata}
            else:
                self.acceso_rack[celda] = set()

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
    

    def camino(self, origen, destinos, ocupadas=()):
        """Busca el camino de menor costo con el algoritmo seleccionado."""

        if origen not in self.grafo:
            return None

        destinos = set(destinos)
        ocupadas = set(ocupadas)

        if origen in destinos:
            return []

        destinos_validos = destinos.intersection(self.grafo)
        destinos_validos -= ocupadas

        if not destinos_validos:
            return None

        grafo_busqueda = self.grafo

        if ocupadas:
            grafo_busqueda = GrafoFiltrado(self.grafo, ocupadas)

        mejor_costo = float("inf")
        mejor_ruta = None

        for destino in destinos_validos:
            self.busquedas += 1

            costo, ruta, expandidos = self._buscador(
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

