"""Warehouse de PRUEBA para desarrollar la visual.

Es un placeholder. Cuando el equipo tenga el modelo real, la visual solo
necesita que exponga lo mismo que esta clase:

    columnas, filas        tamano de la grilla de pasillos
    nodos                  dict  id -> (columna, fila)
    vecinos                dict  id -> lista de (id_vecino, peso)
    despacho               id del nodo de despacho
    racks                  lista de (c0, f0, c1, f1) para dibujar estanterias
    productos              dict  id -> Producto
    pedidos                lista de Pedido
    waves                  lista de Wave
    resultados             dict  (indice_wave, "A" | "B") -> Resultado
    productos_de_wave(i)   lista de ids de productos de la wave i
    pedidos_de_producto(i, id_producto)

Lo que la visual NO necesita saber es como se calculan los eventos.
"""

import heapq
import time

from eventos import (
    Evento,
    VISITAR_NODO,
    RECORRER_ARISTA,
    ELEGIR_SIGUIENTE,
    RECOGER_PRODUCTO,
)

ESTRATEGIA_A = "A"
ESTRATEGIA_B = "B"

PENDIENTE = "PENDIENTE"
EN_WAVE = "EN_WAVE"
EN_PREPARACION = "EN_PREPARACION"
PREPARADO = "PREPARADO"


class Producto:
    def __init__(self, id_producto, nombre, columna, fila, altura, stock, nodo):
        self.id = id_producto
        self.nombre = nombre
        self.columna = columna      # x
        self.fila = fila            # y
        self.altura = altura        # z
        self.stock = stock
        self.nodo = nodo


class Pedido:
    def __init__(self, id_pedido, items, prioridad):
        self.id = id_pedido
        self.items = items          # dict id_producto -> cantidad
        self.prioridad = prioridad  # 1..5, mayor = mas prioridad
        self.estado = EN_WAVE

    def clave_prioridad(self):
        return (-self.prioridad, self.id)


class Wave:
    def __init__(self, id_wave, pedidos):
        self.id = id_wave
        self.pedidos = pedidos


class Resultado:
    """Eventos de una corrida y las metricas que pide el enunciado."""

    def __init__(self, eventos, tiempo_ms):
        self.eventos = eventos
        self.tiempo_ms = tiempo_ms
        self.distancia = 0
        self.nodos_visitados = 0
        self.aristas = 0
        for evento in eventos:
            if evento.tipo == RECORRER_ARISTA:
                self.distancia += evento.datos["peso"]
                self.aristas += 1
            elif evento.tipo == VISITAR_NODO:
                self.nodos_visitados += 1


class AlmacenDemo:
    COLUMNAS = 11
    FILAS = 7
    FILAS_CRUCE = (0, 3, 6)     # pasillos transversales
    CAPACIDAD_WAVE = 3

    def __init__(self):
        self.columnas = self.COLUMNAS
        self.filas = self.FILAS
        self.nodos = {}
        self.vecinos = {}
        self.racks = []
        self.productos = {}
        self.pedidos = []
        self.waves = []
        self.resultados = {}
        self.despacho = 0

        self._dist = {}
        self._prev = {}
        self._eventos = []
        self._pos = 0
        self._pendientes = []
        self._wave = 0

        self._construir_grafo()
        self._construir_racks()
        self._cargar_productos()
        self._cargar_pedidos()
        self._armar_waves()
        self._calcular_todo()

    # ---------- construccion ----------

    def _nodo(self, columna, fila):
        return fila * self.columnas + columna

    def _conectar(self, a, b, peso):
        self.vecinos[a].append((b, peso))
        self.vecinos[b].append((a, peso))

    def _construir_grafo(self):
        for f in range(self.filas):
            for c in range(self.columnas):
                nodo = self._nodo(c, f)
                self.nodos[nodo] = (c, f)
                self.vecinos[nodo] = []
        for c in range(self.columnas):
            for f in range(self.filas - 1):
                self._conectar(self._nodo(c, f), self._nodo(c, f + 1), 1)
        for f in self.FILAS_CRUCE:
            for c in range(self.columnas - 1):
                self._conectar(self._nodo(c, f), self._nodo(c + 1, f), 1)
        # nodo de despacho debajo del ultimo pasillo transversal
        self.despacho = self.filas * self.columnas
        columna_despacho = self.columnas // 2
        self.nodos[self.despacho] = (columna_despacho, self.filas)
        self.vecinos[self.despacho] = []
        self._conectar(self.despacho, self._nodo(columna_despacho, self.filas - 1), 1)

    def _construir_racks(self):
        bloques = ((0, 3), (3, 6))
        for c in range(self.columnas - 1):
            for f0, f1 in bloques:
                self.racks.append((c, f0, c + 1, f1))

    def _cargar_productos(self):
        datos = (
            ("P001", "Auriculares", 1, 1, 2, 20),
            ("P002", "Teclado", 3, 2, 1, 15),
            ("P003", "Mouse", 5, 1, 3, 30),
            ("P004", "Monitor", 7, 2, 1, 10),
            ("P005", "Cable HDMI", 2, 4, 2, 25),
            ("P006", "Webcam", 4, 5, 1, 12),
            ("P007", "Parlante", 6, 4, 3, 8),
            ("P008", "Notebook", 9, 5, 2, 18),
            ("P009", "Tablet", 3, 5, 2, 22),
            ("P010", "Cargador", 8, 1, 1, 40),
        )
        for id_producto, nombre, c, f, z, stock in datos:
            self.productos[id_producto] = Producto(
                id_producto, nombre, c, f, z, stock, self._nodo(c, f)
            )

    def _cargar_pedidos(self):
        self.pedidos = [
            Pedido("O01", {"P001": 2, "P004": 1, "P005": 3}, 5),
            Pedido("O02", {"P002": 1, "P003": 2}, 3),
            Pedido("O03", {"P001": 1, "P003": 1, "P005": 2}, 4),
            Pedido("O04", {"P006": 1, "P008": 2}, 2),
            Pedido("O05", {"P007": 1, "P009": 1, "P010": 1}, 5),
            Pedido("O06", {"P002": 2, "P006": 1}, 1),
        ]

    def _armar_waves(self):
        """Placeholder: por prioridad y en grupos de CAPACIDAD_WAVE.

        La estrategia real (prioridad + cercania) la define el equipo.
        """
        ordenados = sorted(self.pedidos, key=Pedido.clave_prioridad)
        cap = self.CAPACIDAD_WAVE
        for i in range(0, len(ordenados), cap):
            self.waves.append(Wave(len(self.waves) + 1, ordenados[i:i + cap]))

    # ---------- consultas para la visual ----------

    def productos_de_wave(self, indice_wave):
        lista = []
        for pedido in self.waves[indice_wave].pedidos:
            for id_producto in pedido.items:
                if id_producto not in lista:
                    lista.append(id_producto)
        return lista

    def pedidos_de_producto(self, indice_wave, id_producto):
        ids = []
        for pedido in self.waves[indice_wave].pedidos:
            if id_producto in pedido.items:
                ids.append(pedido.id)
        return ids

    # ---------- algoritmos (placeholder) ----------

    def _calcular_todo(self):
        for i in range(len(self.waves)):
            for estrategia in (ESTRATEGIA_A, ESTRATEGIA_B):
                self._simular(i, estrategia)

    def _simular(self, indice_wave, estrategia):
        inicio = time.perf_counter()
        self._wave = indice_wave
        self._eventos = []
        self._pos = self.despacho
        self._eventos.append(Evento(VISITAR_NODO, nodo=self._pos))
        self._pendientes = self.productos_de_wave(indice_wave)
        if estrategia == ESTRATEGIA_A:
            self._recorrer_en_orden()
        else:
            self._recorrer_por_cercania()
        self._ir_a(self.despacho, None)
        tiempo_ms = (time.perf_counter() - inicio) * 1000
        self.resultados[(indice_wave, estrategia)] = Resultado(self._eventos, tiempo_ms)

    def _dijkstra(self, origen):
        self._dist = {n: float("inf") for n in self.nodos}
        self._prev = {n: None for n in self.nodos}
        self._dist[origen] = 0
        cola = [(0, origen)]
        while cola:
            d, u = heapq.heappop(cola)
            if d > self._dist[u]:
                continue
            for v, peso in self.vecinos[u]:
                nueva = d + peso
                if nueva < self._dist[v]:
                    self._dist[v] = nueva
                    self._prev[v] = u
                    heapq.heappush(cola, (nueva, v))

    def _peso(self, a, b):
        for vecino, peso in self.vecinos[a]:
            if vecino == b:
                return peso
        return 0

    def _ir_a(self, nodo, id_producto):
        """Camino minimo desde self._pos hasta nodo, emitiendo eventos."""
        self._dijkstra(self._pos)
        self._eventos.append(
            Evento(ELEGIR_SIGUIENTE, candidato=nodo,
                   distancia=self._dist[nodo], producto=id_producto)
        )
        ruta = []
        actual = nodo
        while actual is not None:
            ruta.append(actual)
            actual = self._prev[actual]
        ruta.reverse()
        for i in range(1, len(ruta)):
            peso = self._peso(ruta[i - 1], ruta[i])
            self._eventos.append(
                Evento(RECORRER_ARISTA, origen=ruta[i - 1], destino=ruta[i], peso=peso)
            )
            self._eventos.append(Evento(VISITAR_NODO, nodo=ruta[i]))
        self._pos = nodo

    def _recoger(self, id_producto):
        self._eventos.append(
            Evento(RECOGER_PRODUCTO, nodo=self.productos[id_producto].nodo,
                   producto=id_producto,
                   pedidos=self.pedidos_de_producto(self._wave, id_producto))
        )

    def _recorrer_en_orden(self):
        """Estrategia A: ubicaciones en el orden en que aparecen los pedidos."""
        for id_producto in self._pendientes:
            self._ir_a(self.productos[id_producto].nodo, id_producto)
            self._recoger(id_producto)

    def _recorrer_por_cercania(self):
        """Estrategia B: siempre la ubicacion no visitada mas cercana."""
        restantes = list(self._pendientes)
        while restantes:
            self._dijkstra(self._pos)
            mejor = restantes[0]
            for id_producto in restantes:
                if self._dist[self.productos[id_producto].nodo] < \
                        self._dist[self.productos[mejor].nodo]:
                    mejor = id_producto
            self._ir_a(self.productos[mejor].nodo, mejor)
            self._recoger(mejor)
            restantes.remove(mejor)