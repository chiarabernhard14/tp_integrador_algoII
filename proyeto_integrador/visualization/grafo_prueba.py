from collections import deque

from eventos import (
    Evento,
    VISITAR_NODO,
    RECORRER_ARISTA,
    ELEGIR_SIGUIENTE,
    RECOGER_PRODUCTO,
)


class GrafoDemo:
    def __init__(self, filas=5, columnas=7):
        self.filas = filas
        self.columnas = columnas
        self.nodos = {}
        self.vecinos = {}
        self.despacho = 0
        self.productos = {}
        self.eventos = []
        self.pendientes = []
        self.actual = 0
        self._construir_grilla()
        self._cargar_productos_de_ejemplo()

    def _construir_grilla(self):
        for f in range(self.filas):
            for c in range(self.columnas):
                nodo = f * self.columnas + c
                self.nodos[nodo] = (c, f)
                self.vecinos[nodo] = []
        for f in range(self.filas):
            for c in range(self.columnas):
                nodo = f * self.columnas + c
                if c + 1 < self.columnas:
                    self._conectar(nodo, nodo + 1, 1)
                if f + 1 < self.filas:
                    self._conectar(nodo, nodo + self.columnas, 1)
        self.despacho = (self.filas - 1) * self.columnas

    def _conectar(self, a, b, peso):
        self.vecinos[a].append((b, peso))
        self.vecinos[b].append((a, peso))

    def _cargar_productos_de_ejemplo(self):
        self.productos = {
            2: "P001",
            11: "P002",
            16: "P003",
            20: "P004",
            6: "P005",
        }

    def distancia(self, a, b):
    
        xa, ya = self.nodos[a]
        xb, yb = self.nodos[b]
        return abs(xa - xb) + abs(ya - yb)

    def camino(self, origen, destino):

        padre = {origen: None}
        cola = deque([origen])
        while cola:
            actual = cola.popleft()
            if actual == destino:
                break
            for vecino, _peso in self.vecinos[actual]:
                if vecino not in padre:
                    padre[vecino] = actual
                    cola.append(vecino)
        ruta = []
        nodo = destino
        while nodo is not None:
            ruta.append(nodo)
            nodo = padre[nodo]
        ruta.reverse()
        return ruta

    def _caminar_hasta(self, destino, actual):
        ruta = self.camino(actual, destino)
        for i in range(1, len(ruta)):
            self.eventos.append(
                Evento(RECORRER_ARISTA, origen=ruta[i - 1], destino=ruta[i], peso=1)
            )
            self.eventos.append(Evento(VISITAR_NODO, nodo=ruta[i]))
        return destino

    def _mas_cercano(self):
        mejor = None
        mejor_distancia = None
        for nodo in self.pendientes:
            d = self.distancia(self.actual, nodo)
            if mejor is None or d < mejor_distancia:
                mejor = nodo
                mejor_distancia = d
        return mejor

    def generar_eventos_cercania(self):
        self.eventos = []
        self.pendientes = list(self.productos.keys())
        self.actual = self.despacho
        self.eventos.append(Evento(VISITAR_NODO, nodo=self.actual))
        while self.pendientes:
            mejor = self._mas_cercano()
            self.eventos.append(
                Evento(ELEGIR_SIGUIENTE, candidato=mejor,
                       distancia=self.distancia(self.actual, mejor))
            )
            self.actual = self._caminar_hasta(mejor, self.actual)
            self.eventos.append(
                Evento(RECOGER_PRODUCTO, nodo=self.actual,
                       producto=self.productos[self.actual])
            )
            self.pendientes.remove(self.actual)
        self._caminar_hasta(self.despacho, self.actual)