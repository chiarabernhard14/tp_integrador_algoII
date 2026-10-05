import heapq
import math
import time

class PathFinder:

    @staticmethod
    def dijkstra(graph,starNode,targetNode):
        """ Los nodos del grafo estaran representado de la siguiente manera: (nodoDestino,peso)
            Esto se hara a traves de una lista de adyacencia.  """

        dist = {}
        pi = {}

        for nodo in graph:
            dist[nodo] = float('inf')
            pi[nodo] = None

        dist[starNode] = 0

        pq = [(0,starNode)]
        visitados = set()

        while(len(pq) > 0):
            distActual, nodoActual = heapq.heappop(pq)

            if(nodoActual in visitados):
                continue
            visitados.add(nodoActual)

            if(nodoActual == targetNode):
                break

            for vecino, peso in graph[nodoActual]:
                if(vecino not in visitados):
                    if(dist[vecino]>dist[nodoActual] + peso):
                        dist[vecino] = dist[nodoActual] + peso
                        pi[vecino] = nodoActual
                        heapq.heappush(pq,(dist[vecino],vecino))

        path = []
        current = targetNode

        if(dist.get(targetNode,float('inf'))==float('inf')):
            return float('inf'), []

        while(current is not None):
            path.append(current)
            current = pi.get(current)

        path.reverse()

        return dist[targetNode], path    




    @staticmethod
    def manhattan_distance(node_a, node_b):
        return abs(node_a[0] - node_b[0]) + abs(node_a[1] - node_b[1])

    @staticmethod
    def aEstrella(graph, startNode, targetNode, heuristica=None):
       
        if(heuristica is None):
            heuristica = PathFinder.manhattan_distance

        def eval_h(node):
            if(callable(heuristica)):
                return heuristica(node, targetNode)
            elif(isinstance(heuristica, dict)):
                return heuristica.get(node, 0)
            return 0

        openSet = []
        heapq.heappush(openSet, (eval_h(startNode), startNode))

        costoAcumulado = {startNode: 0}
        padres = {startNode: None}
        visitados = set()

        while(openSet):
            _, nodoActual = heapq.heappop(openSet)

            if(nodoActual == targetNode):
                path = []
                mientras = nodoActual
                while(mientras is not None):
                    path.append(mientras)
                    mientras = padres[mientras]
                path.reverse()
                return costoAcumulado[targetNode], path

            if(nodoActual in visitados):
                continue
            visitados.add(nodoActual)

            for vecino, peso in graph.get(nodoActual, []):
                if(vecino in visitados):
                    continue

                tentativo = costoAcumulado[nodoActual] + peso

                if(vecino not in costoAcumulado or tentativo < costoAcumulado[vecino]):
                    padres[vecino] = nodoActual
                    costoAcumulado[vecino] = tentativo
                    costoVecino = tentativo + eval_h(vecino)
                    heapq.heappush(openSet, (costoVecino, vecino))

        return float('inf'), []