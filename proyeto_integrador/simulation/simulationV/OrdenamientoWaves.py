from collections import Counter


def calcular_perfil_prioridades(wave):
    """
    Perfil lexicográfico (P5, P4, P3, P2, P1).
    Se cuenta cada registro producto-pedido, no la cantidad de unidades.
    """
    conteo = Counter(item["order"].prioridad for item in wave.products)
    return tuple(conteo[p] for p in (5, 4, 3, 2, 1))


def ordenar_waves(waves):
    """Ordena por perfil descendente; los empates conservan el orden original."""
    return sorted(waves, key=calcular_perfil_prioridades, reverse=True)
