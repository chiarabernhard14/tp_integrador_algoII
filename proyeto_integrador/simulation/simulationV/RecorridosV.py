import heapq
import time

INFINITO = float("inf")

class PathFinderV:
    @staticmethod
    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def _reconstruir(padre, destino):
        camino = []
        actual = destino
        while actual is not None:
            camino.append(actual)
            actual = padre[actual]
        camino.reverse()
        return camino

    @staticmethod
    def dijkstra(grafo, inicio, destino):
        if inicio not in grafo:
            raise ValueError(f"El nodo {inicio} no existe en el grafo.")
        if destino not in grafo:
            raise ValueError(f"El nodo {destino} no existe en el grafo.")

        dist = {inicio: 0}
        padre = {inicio: None}
        cola = [(0, inicio)]
        cerrados = set()
        expandidos = 0

        while cola:
            dist_actual, actual = heapq.heappop(cola)

            if actual in cerrados:
                continue
            cerrados.add(actual)

            if actual == destino:
                return dist_actual, PathFinderV._reconstruir(padre, destino), expandidos

            expandidos += 1

            for vecino, peso in grafo[actual]:
                if vecino in cerrados:
                    continue

                nueva = dist_actual + peso
                if nueva < dist.get(vecino, INFINITO):
                    dist[vecino] = nueva
                    padre[vecino] = actual
                    heapq.heappush(cola, (nueva, vecino))

        return INFINITO, [], expandidos

    @staticmethod
    def a_estrella(grafo, inicio, destino):
        """A* con heurística de Manhattan. Es correcta si cada arista pesa al
        menos la distancia Manhattan entre sus extremos."""

        if inicio not in grafo:
            raise ValueError(f"El nodo {inicio} no existe en el grafo.")
        if destino not in grafo:
            raise ValueError(f"El nodo {destino} no existe en el grafo.")

        costo = {inicio: 0}
        padre = {inicio: None}
        abiertos = [(PathFinderV.manhattan(inicio, destino), inicio)]
        cerrados = set()
        expandidos = 0

        while abiertos:
            _, actual = heapq.heappop(abiertos)

            if actual in cerrados:
                continue

            if actual == destino:
                return costo[destino], PathFinderV._reconstruir(padre, destino), expandidos

            cerrados.add(actual)
            expandidos += 1

            for vecino, peso in grafo[actual]:
                if vecino in cerrados:
                    continue

                nuevo = costo[actual] + peso
                if nuevo < costo.get(vecino, INFINITO):
                    costo[vecino] = nuevo
                    padre[vecino] = actual
                    estimado = nuevo + PathFinderV.manhattan(vecino, destino)
                    heapq.heappush(abiertos, (estimado, vecino))

        return INFINITO, [], expandidos


class RouteFinderV:

    @staticmethod
    def _tramo(grafo, buscador, origen, destino):
        distancia, camino, expandidos = buscador(grafo, origen, destino)

        if distancia == INFINITO:
            raise ValueError(f"No hay camino de {origen} a {destino}.")

        return distancia, camino, expandidos

    @staticmethod
    def orden_pedidos(grafo, inicio, nodos, buscador=PathFinderV.dijkstra):
        """Estrategia A: visita los nodos en el orden en que aparecen."""

        reloj = time.perf_counter()

        orden = list(dict.fromkeys(nodos))
        paradas = [inicio] + orden + [inicio]

        ruta = [inicio]
        total = 0.0
        expandidos = 0

        for i in range(len(paradas) - 1):
            distancia, camino, exp = RouteFinderV._tramo(
                grafo, buscador, paradas[i], paradas[i + 1])
            total += distancia
            expandidos += exp
            ruta.extend(camino[1:])

        return {
            "total_distance": total,
            "route": ruta,
            "order": orden,
            "expanded_nodes": expandidos,
            "execution_time_ms": (time.perf_counter() - reloj) * 1000,
        }

    @staticmethod
    def cercania(grafo, inicio, nodos, buscador=PathFinderV.dijkstra):

        reloj = time.perf_counter()

        pendientes = list(dict.fromkeys(nodos))
        actual = inicio
        ruta = [inicio]
        orden = []
        total = 0.0
        expandidos = 0

        while pendientes:
            mejor = None
            mejor_distancia = INFINITO
            mejor_camino = []

            for destino in pendientes:
                distancia, camino, exp = buscador(grafo, actual, destino)
                expandidos += exp

                if distancia < mejor_distancia:
                    mejor = destino
                    mejor_distancia = distancia
                    mejor_camino = camino

            if mejor is None:
                raise ValueError(f"No hay camino desde {actual} a ningún producto pendiente.")

            total += mejor_distancia
            ruta.extend(mejor_camino[1:])
            orden.append(mejor)
            pendientes.remove(mejor)
            actual = mejor

        if actual != inicio:
            distancia, camino, exp = RouteFinderV._tramo(grafo, buscador, actual, inicio)
            total += distancia
            expandidos += exp
            ruta.extend(camino[1:])

        return {
            "total_distance": total,
            "route": ruta,
            "order": orden,
            "expanded_nodes": expandidos,
            "execution_time_ms": (time.perf_counter() - reloj) * 1000,
        }