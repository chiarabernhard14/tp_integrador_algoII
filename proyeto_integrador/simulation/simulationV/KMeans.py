import random
from collections import Counter


MAX_ITERACIONES = 300
SEMILLA_PREDETERMINADA = 42


def _coordenadas(registro):
    ubicacion = tuple(registro.producto.ubicacion)
    if len(ubicacion) != 3:
        raise ValueError("Cada producto debe tener coordenadas tridimensionales.")
    return ubicacion


def distancia_cuadrada(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def calcular_centroide(registros):
    if not registros:
        raise ValueError("No se puede calcular el centroide de un cluster vacío.")
    puntos = [_coordenadas(r) for r in registros]
    n = len(puntos)
    return tuple(sum(p[i] for p in puntos) / n for i in range(3))


def inicializar_centroides(registros, k, generador):
    """Inicialización K-means++ ponderada por multiplicidad de ubicaciones."""
    frecuencias = Counter(_coordenadas(r) for r in registros)
    ubicaciones = list(frecuencias)
    centroides = [generador.choice(ubicaciones)]

    while len(centroides) < k:
        candidatos = [p for p in ubicaciones if p not in centroides]
        pesos = [
            frecuencias[p] * min(distancia_cuadrada(p, c) for c in centroides)
            for p in candidatos
        ]

        if not candidatos:
            break

        if sum(pesos) == 0:
            elegido = candidatos[0]
        else:
            elegido = generador.choices(candidatos, weights=pesos, k=1)[0]

        centroides.append(elegido)

    return centroides


def asignar_registros(registros, centroides):
    clusters = [[] for _ in centroides]
    indices = []

    for registro in registros:
        punto = _coordenadas(registro)
        indice = min(
            range(len(centroides)),
            key=lambda i: distancia_cuadrada(punto, centroides[i]),
        )
        clusters[indice].append(registro)
        indices.append(indice)

    return clusters, indices


def generar_clusters(
    registros,
    k,
    semilla=SEMILLA_PREDETERMINADA,
    max_iteraciones=MAX_ITERACIONES,
):
    """Retorna clusters de RegistroProductoPedido mediante K-means."""
    if not registros:
        return []

    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("K debe ser un entero.")
    if k <= 0:
        raise ValueError("K debe ser mayor a cero.")
    if not isinstance(max_iteraciones, int) or isinstance(max_iteraciones, bool):
        raise TypeError("max_iteraciones debe ser un entero.")
    if max_iteraciones <= 0:
        raise ValueError("max_iteraciones debe ser mayor a cero.")

    ubicaciones = {_coordenadas(r) for r in registros}
    k = min(k, len(ubicaciones))
    rng = random.Random(semilla)

    centroides = inicializar_centroides(registros, k, rng)
    asignaciones_anteriores = None
    clusters = []

    for _ in range(max_iteraciones):
        clusters, indices = asignar_registros(registros, centroides)

        if indices == asignaciones_anteriores:
            break

        nuevos_centroides = []
        for i, cluster in enumerate(clusters):
            nuevos_centroides.append(
                calcular_centroide(cluster) if cluster else centroides[i]
            )

        centroides = nuevos_centroides
        asignaciones_anteriores = indices

    # Eliminar clusters que permanezcan vacíos al finalizar.
    return [cluster for cluster in clusters if cluster]
