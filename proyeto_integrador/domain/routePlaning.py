import time
from pathFinding import PathFinder
import heapq

class RouteFinder:

    @staticmethod
    def productOrder(startNode,wave,picker,wareHouse):
        startTime = time.perf_counter()

        stops = [startNode]

        for order in wave.orders:
            for item in order.items:
                if(item.product and item.product.location):
                    stops.append(item.product.location)

        stops.append(startNode)

        fullRoute = []
        totalDistance = 0.0

        for i in range(len(stops)-1):
            origen = stops[i]
            destino = stops[i+1]

            dist, path = PathFinder.dijkstra(wareHouse.graph,origen,destino)

            totalDistance += dist

            if(not fullRoute):
                fullRoute.extend(path)
            else:
                fullRoute.extend(path[1:])  


        finishTime = (time.perf_counter() - startTime) * 1000
        wave.route = fullRoute
        picker.current_route = fullRoute

        return {
            "total_distance": totalDistance,
            "route": fullRoute,
            "execution_time_ms": finishTime
        }


    @staticmethod
    def nearestNeighbor(startNode,wave,picker,warehouse):
        startTime = time.perf_counter()
        
        pendientes = set()
        
        for order in wave.orders:
            for item in order.items:
                if(item.product and item.product.location):
                    pendientes.add(item.product.location)

        currentNode = startNode
        fullRoute = [currentNode]
        totalDistance = 0.0

        while(pendientes):
            bestDist = float('inf')
            bestPath = []
            nextNode = None

            for target in pendientes:
                dist, path = PathFinder.dijkstra(warehouse.graph, currentNode, target)
                if dist < bestDist:
                    bestDist = dist
                    bestPath = path
                    nextNode = target          

            if nextNode is None:
                break

            totalDistance += bestDist
            fullRoute.extend(bestPath[1:])

            currentNode = nextNode
            pendientes.remove(nextNode)

        return totalDistance, fullRoute    

    
    @staticmethod
    def zonas(startNode, wave, picker, warehouse):
    startTime = time.perf_counter()
        
    zonaVertical = []
    zonaHorizontal = []
        
    for order in wave.orders:
        for item in order.items:
            if(item.product and item.product.rack_id):
                rack = warehouse.racks.get(item.product.rack_id)
                    
                if(rack):
                    loc = item.product.ubicacion[:2] # Coordenada (x, y) del producto
                       
                    if(rack.ancho > rack.alto):
                        zonaHorizontal.append(loc)
                    else:
                        zonaVertical.append(loc)

    stops = [startNode]

    if(zonaVertical):
        zonaVertical.sort(key=lambda c: (c[0], c[1]))
        stops.extend(zonaVertical)

    if(zonaHorizontal):
        zonaHorizontal.sort(key=lambda c: (c[1], c[0]))
        stops.extend(zonaHorizontal)

    stops.append(startNode) 

    fullRoute = []
    totalDistance = 0.0

    for i in range(len(stops) - 1):
        origen = stops[i]
        destino = stops[i+1]

        dist, path = PathFinder.dijkstra(warehouse.graph, origen, destino)
        totalDistance += dist

        if(not fullRoute):
            fullRoute.extend(path)
        else:
            fullRoute.extend(path[1:]) 

    finishTime = (time.perf_counter() - startTime) * 1000
    wave.route = fullRoute
    picker.current_route = fullRoute

    return {
        "total_distance": totalDistance,
        "route": fullRoute,
        "execution_time_ms": finishTime
    }
