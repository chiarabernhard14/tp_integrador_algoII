
import os
import sys

# Configurar automáticamente la ruta del proyecto.
CARPETA_PROYECTO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, CARPETA_PROYECTO)

from simulation.simulationV.ScenarioV import generar_escenario
from simulation.simulationV.CargadorV import cargar_warehouse


def probar_backend():
    print("Generando escenario...")
    datos = generar_escenario()

    print("Cargando warehouse...")
    warehouse = cargar_warehouse(datos)

    print("\n--- RESULTADO ---")
    print("Racks:", len(warehouse.racks))
    print("Productos:", len(warehouse.productos))
    print("Pickers:", len(warehouse.pickers))
    print("Pasillos:", len(warehouse.pasillos))
    print("Puertas:", len(warehouse.puertas))
    print("Zonas de despacho:", len(warehouse.zonas_despacho))

    print("\nBackend cargado correctamente.")


if __name__ == "__main__":
    probar_backend()
