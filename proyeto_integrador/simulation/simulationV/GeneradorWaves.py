from simulation.simulationV.PreparacionRegistros import preparar_registros
from simulation.simulationV.CalculoK import calcular_k
from simulation.simulationV.KMeans import generar_clusters
from simulation.simulationV.ConstruccionWaves import construir_waves
from simulation.simulationV.OrdenamientoWaves import ordenar_waves


def generar_waves(pedidos, max_pedidos, max_unidades, semilla=42):
    """
    Orquesta preparación, cálculo de K, clustering, construcción y ordenamiento.
    No modifica el stock real, no asigna pickers y no calcula recorridos.
    """
    registros = preparar_registros(pedidos)
    if not registros:
        return []

    k = calcular_k(registros, max_unidades, max_pedidos)
    if k == 0:
        return []

    clusters = generar_clusters(registros, k, semilla=semilla)
    waves = construir_waves(clusters, max_pedidos, max_unidades)
    return ordenar_waves(waves)
