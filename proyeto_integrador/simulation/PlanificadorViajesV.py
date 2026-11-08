"""Estima y ordena viajes de pickers para la simulación."""

from .RecorridosV import PathFinderV, RouteFinderV


ESTRATEGIAS = {
    "orden": RouteFinderV.orden_pedidos,
    "cercania": RouteFinderV.cercania,
    "zonas": RouteFinderV.zonas,
}

ALGORITMOS_CAMINO = {
    "a_estrella": PathFinderV.a_estrella,
    "dijkstra": PathFinderV.dijkstra,
}


class PlanificadorViajesV:
    """Calcula costos y secuencias de visita hasta una zona de despacho.

    El asignador le consulta el costo de cada alternativa del backtracking.
    Esta clase aplica la estrategia y el algoritmo seleccionados, y devuelve
    también el orden que la simulación entregará al picker para ejecutar.
    """

    def __init__(self, nav, productos, racks, algoritmo_camino, estrategia):
        if algoritmo_camino not in ALGORITMOS_CAMINO:
            raise ValueError(
                f"Algoritmo de camino desconocido: {algoritmo_camino}. "
                f"Opciones: {', '.join(ALGORITMOS_CAMINO)}."
            )
        if estrategia not in ESTRATEGIAS:
            raise ValueError(
                f"Estrategia de recorrido desconocida: {estrategia}. "
                f"Opciones: {', '.join(ESTRATEGIAS)}."
            )
        self.nav = nav
        self.productos = productos
        self.racks = racks
        self.algoritmo_camino = algoritmo_camino
        self.estrategia = estrategia
        self._buscador = ALGORITMOS_CAMINO[algoritmo_camino]
        self._cache_grafos = {}
        self._cache_recorrido = {}
        self.busquedas = 0
        self.nodos_expandidos = 0

    def _buscar_con_cache(self, grafo, origen, destino):
        origen, destino = tuple(origen), tuple(destino)
        clave = (id(grafo), origen, destino)
        if clave not in self._cache_recorrido:
            if origen not in grafo or destino not in grafo:
                self._cache_recorrido[clave] = (float("inf"), [], 0)
            else:
                resultado = self._buscador(
                    grafo, origen, destino
                )
                self._cache_recorrido[clave] = resultado
                self.busquedas += 1
                self.nodos_expandidos += resultado[2]
        return self._cache_recorrido[clave]

    def evaluar_viaje(
        self, picker, producto_ids, orden_wave, zona_id, celdas_zona, accesos
    ):
        """Devuelve distancia, destino final y orden de productos, o None."""
        productos_por_acceso = {}
        rack_por_acceso = {}

        for producto_id in orden_wave:
            if producto_id not in producto_ids:
                continue
            producto = self.productos[producto_id]
            acceso = accesos.get(producto_id)
            if acceso is None:
                return None
            acceso = tuple(acceso)
            productos_por_acceso.setdefault(acceso, []).append(producto_id)
            if acceso not in rack_por_acceso:
                rack_por_acceso[acceso] = self.racks.get(producto.rack_id)

        if not productos_por_acceso:
            return None

        if self.estrategia == "zonas":
            if any(rack is None for rack in rack_por_acceso.values()):
                return None
            nodos = [(acceso, rack) for acceso, rack in rack_por_acceso.items()]
        else:
            nodos = list(productos_por_acceso)

        estrategia = ESTRATEGIAS[self.estrategia]
        mejor = None
        celdas_zona = frozenset(tuple(celda) for celda in celdas_zona)
        clave_grafo = (tuple(picker.pos), celdas_zona)
        grafo_planificacion = self._cache_grafos.get(clave_grafo)
        if grafo_planificacion is None:
            puntos_ruta = {tuple(picker.pos)}
            puntos_ruta.update(
                tuple(acceso) for acceso in accesos.values()
                if acceso is not None
            )
            puntos_ruta.update(celdas_zona)
            grafo_planificacion = self.nav.grafo_reducido_con_puntos(puntos_ruta)
            if grafo_planificacion is None:
                # Mantener la planificación disponible para nodos que no hayan
                # podido representarse en la compresión del grafo.
                grafo_planificacion = self.nav.grafo
            self._cache_grafos[clave_grafo] = grafo_planificacion

        for destino in sorted(celdas_zona):
            try:
                plan = estrategia(
                    grafo_planificacion,
                    picker.pos,
                    nodos,
                    buscador=self._buscar_con_cache,
                    destino_final=destino,
                )
            except ValueError:
                continue

            orden_productos = []
            agregados = set()
            for acceso in plan["order"]:
                for producto_id in productos_por_acceso.get(acceso, ()):
                    if producto_id not in agregados:
                        agregados.add(producto_id)
                        orden_productos.append(producto_id)
            if len(orden_productos) != len(producto_ids):
                continue

            candidato = dict(plan)
            candidato["zona"] = zona_id
            candidato["destino_final"] = destino
            candidato["orden_productos"] = orden_productos
            clave = (candidato["total_distance"], destino)
            if mejor is None or clave < mejor[0]:
                mejor = (clave, candidato)

        return mejor[1] if mejor is not None else None
