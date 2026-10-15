from domain.pathFinding import PathFinder

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
        resultado = []
        for vecino, peso in lista:
            if vecino not in self.ocupadas:
                resultado.append((vecino, peso))
        return resultado


class Navegacion:
    
    def __init__(self, warehouse):
        self.ancho_x = warehouse.ancho_x
        self.largo_y = warehouse.largo_y
        self.busquedas = 0

        self.bloqueadas = set()
        self.zonas = set()
        for rack in warehouse.racks.values():
            self.bloqueadas |= set(rack.cells())
        for zona in warehouse.zonas_despacho.values():
            self.zonas |= set(zona.cells())
        self.bloqueadas |= self.zonas
        for puerta in warehouse.puertas.values():
            self.bloqueadas.add((puerta.ubicacion[0], puerta.ubicacion[1]))

        self.sentido = {}
        self.eje = {}
        for pasillo in warehouse.pasillos.values():
            eje = self._eje_de(pasillo)
            for celda in pasillo.cells():
                self.sentido[celda] = (pasillo.sentido, pasillo.id)
                self.eje[celda] = eje

        self.vecinos = {}
        self.grafo = {}
        for x in range(self.ancho_x):
            for y in range(self.largo_y):
                if (x, y) not in self.bloqueadas:
                    self.vecinos[(x, y)] = self._calcular_vecinos((x, y))
        for celda, lista in self.vecinos.items():
            self.grafo[celda] = [(vecino, 1) for vecino in lista]

        self.despacho = set()
        for celda in self.vecinos:
            if self._adyacentes(celda) & self.zonas:
                self.despacho.add(celda)

        self.acceso_rack = {}
        for rack in warehouse.racks.values():
            self._registrar_accesos(rack)

        self.pilas = set()
        self.grafo_rutas = dict(self.grafo)
        for producto in warehouse.productos.values():
            celda = (producto.ubicacion[0], producto.ubicacion[1])
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

    def _calcular_vecinos(self, celda):
        lista = []
        for dx, dy in DIRECCIONES:
            destino = (celda[0] + dx, celda[1] + dy)
            if destino not in self.bloqueadas and self._en_limites(destino):
                if self._permite(celda, destino, (dx, dy)):
                    lista.append(destino)
        return lista

    def _en_limites(self, celda):
        return 0 <= celda[0] < self.ancho_x and 0 <= celda[1] < self.largo_y

    def _permite(self, origen, destino, direccion):
        return (self._permite_en(origen, destino, direccion)
                and self._permite_en(destino, origen, direccion))

    def _permite_en(self, celda, otra, direccion):
        info = self.sentido.get(celda)
        if info is None or info[0] == "AMBOS":
            return True
        avance = AVANCE[info[0]]
        if direccion == avance:
            return True
        producto_punto = direccion[0] * avance[0] + direccion[1] * avance[1]
        info_otra = self.sentido.get(otra)
        mismo_pasillo = info_otra is not None and info_otra[1] == info[1]
        return producto_punto == 0 and mismo_pasillo

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

    def camino(self, origen, destinos, ocupadas=()):
        if origen in destinos:
            return []
        grafo = self.grafo
        if ocupadas:
            grafo = GrafoFiltrado(self.grafo, ocupadas)
        ordenados = []
        for destino in destinos:
            if destino in self.grafo and destino not in ocupadas:
                ordenados.append((PathFinder.manhattan_distance(origen, destino), destino))
        ordenados.sort()
        mejor_costo = float("inf")
        mejor_ruta = None
        for cota, destino in ordenados:
            if cota >= mejor_costo:
                break
            self.busquedas += 1
            costo, ruta = PathFinder.aEstrella(grafo, origen, destino)
            if costo < mejor_costo:
                mejor_costo = costo
                mejor_ruta = ruta[1:]
        return mejor_ruta