"""Servicios de accesibilidad, distancias y cálculo de recorridos del generador."""
from functools import lru_cache
from domain.pathFinding import PathFinder


def _crear_servicios_navegacion(navegacion, productos, tareas, pickers, despacho):
    """Prepara accesos y funciones reutilizables para distancias y recorridos."""
    grafo = navegacion.grafo
    ids_producto_pendientes = sorted({tarea["producto_id"] for tarea in tareas})
    accesos = {}
    for pid in ids_producto_pendientes:
        ubicacion = productos[pid]["ubicacion"]
        accesos[pid] = tuple(sorted(navegacion.accesos(ubicacion["x"], ubicacion["y"])))

    cache_distancias = {}

    def distancia(origen, destino):
        clave = (origen, destino)
        if clave not in cache_distancias:
            if origen not in grafo or destino not in grafo:
                cache_distancias[clave] = float("inf")
            else:
                cache_distancias[clave] = PathFinder.dijkstra(grafo, origen, destino)[0]
        return cache_distancias[clave]

    def distancia_productos(pid_origen, pid_destino):
        """Mínima distancia dirigida entre accesos transitables de dos productos."""
        return min((distancia(a, b)
                    for a in accesos.get(pid_origen, ())
                    for b in accesos.get(pid_destino, ())), default=float("inf"))

    posiciones_iniciales = [
        (picker["posicion_inicial"]["x"], picker["posicion_inicial"]["y"])
        for picker in pickers
    ]

    def accesible_desde_un_origen(pid):
        # El recorrido debe poder llegar al producto desde despacho o desde una posición inicial válida y, además, regresar desde su acceso al despacho por el grafo dirigido.
        origenes = despacho + posiciones_iniciales
        return bool(accesos.get(pid)) and any(
            distancia(origen, acceso) < float("inf")
            and any(distancia(acceso, destino) < float("inf") for destino in despacho)
            for origen in origenes for acceso in accesos[pid]
        )

    # Comprueba si existe algún orden de visita válido para los productos de la wave.
    cache_factibilidad = {}
    def existe_secuencia_factible(ids_productos):
        ids = tuple(sorted(set(ids_productos), key=str))
        if not ids:
            return True
        if ids in cache_factibilidad:
            return cache_factibilidad[ids]
        origenes = tuple(sorted(set(despacho + posiciones_iniciales)))
        memo = set()

        def visitar(visitados, acceso_actual):
            estado = (visitados, acceso_actual)
            if estado in memo:
                return False
            memo.add(estado)
            if len(visitados) == len(ids):
                # La ruta solo es válida si desde el último acceso existe un camino dirigido hasta alguna celda del despacho.
                return any(distancia(acceso_actual, d) < float("inf") for d in despacho)
            for pid in ids:
                if pid in visitados:
                    continue
                for acceso in accesos.get(pid, ()):
                    if distancia(acceso_actual, acceso) < float("inf"):
                        if visitar(visitados | {pid}, acceso):
                            return True
            return False

        factible = any(visitar(frozenset(), origen) for origen in origenes)
        cache_factibilidad[ids] = factible
        return factible

    def calcular_recorrido(productos_asignados, origenes):
        """Encuentra un recorrido dirigido que visite los productos y termine en despacho.
        
        """
        ids = tuple(sorted(set(productos_asignados), key=str))
        if not ids:
            origen = min(origenes, key=str)
            return [origen], 0
        accesos_por_producto = [tuple(sorted(accesos.get(pid, ()))) for pid in ids]
        if any(not opciones for opciones in accesos_por_producto):
            raise ValueError("No hay acceso transitable para un producto asignado")

        @lru_cache(maxsize=None)
        def mejor(mask, actual):
            if mask == (1 << len(ids)) - 1:
                finales = [(distancia(actual, d), d) for d in despacho]
                costo, destino = min(finales, key=lambda x: (x[0], str(x[1])))
                if costo == float("inf"):
                    return (float("inf"), ())
                return (costo, (destino,))
            mejor_costo = float("inf")
            mejor_secuencia = ()
            for i, opciones in enumerate(accesos_por_producto):
                if mask & (1 << i):
                    continue
                for acceso in opciones:
                    tramo = distancia(actual, acceso)
                    if tramo == float("inf"):
                        continue
                    resto_costo, resto = mejor(mask | (1 << i), acceso)
                    total = tramo + resto_costo
                    secuencia = (acceso,) + resto
                    if (total, tuple(map(str, secuencia))) < (mejor_costo, tuple(map(str, mejor_secuencia))):
                        mejor_costo, mejor_secuencia = total, secuencia
            return mejor_costo, mejor_secuencia

        candidatos = []
        for origen in sorted(set(origenes), key=str):
            costo, secuencia = mejor(0, origen)
            if costo < float("inf") and secuencia:
                candidatos.append((costo, str(origen), origen, secuencia))
        if not candidatos:
            raise ValueError("No existe un recorrido dirigido que termine en el despacho para la asignación")
        costo_total, _, origen, secuencia = min(candidatos, key=lambda x: (x[0], x[1], tuple(map(str, x[3]))))
        ruta = [origen]
        actual = origen
        for destino in secuencia:
            _, tramo = PathFinder.dijkstra(grafo, actual, destino)
            if not tramo:
                raise ValueError(f"No hay camino dirigido entre {actual} y {destino}")
            ruta.extend(tramo[1:])
            actual = destino
        return ruta, costo_total
    return {
        "accesos": accesos,
        "posiciones_iniciales": posiciones_iniciales,
        "distancia": distancia,
        "distancia_productos": distancia_productos,
        "accesible_desde_un_origen": accesible_desde_un_origen,
        "existe_secuencia_factible": existe_secuencia_factible,
        "calcular_recorrido": calcular_recorrido,
    }
