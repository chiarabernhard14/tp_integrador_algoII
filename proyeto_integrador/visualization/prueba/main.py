import argparse
import ctypes
import importlib
import os
import sys

try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass

CARPETA = os.path.dirname(os.path.abspath(__file__))
VISUALIZACION = os.path.abspath(os.path.join(CARPETA, ".."))
RAIZ = os.path.dirname(VISUALIZACION)
for ruta in (VISUALIZACION, RAIZ):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

# Los imports del proyecto van después de armar sys.path.
from simulation.simulationV.ScenarioV import generar_escenario  # noqa: E402
from simulation.simulationV.PersistenceV import (                        # noqa: E402
    cargar_escenario,
    cargar_partida,
    ruta_autoguardado,
)


def main():
    parser = argparse.ArgumentParser(description="Simulador de Wave Picking")
    parser.add_argument("--escenario", type=str, help="Ruta al archivo JSON a cargar", default=None)
    args = parser.parse_args()

    datos_iniciales = None
    partida_guardada = None
    if args.escenario:
        try:
            datos_iniciales = cargar_escenario(args.escenario)
        except ValueError as error:
            print(f"No se pudo cargar el escenario: {error}")
            datos_iniciales = None
    else:
        ruta = ruta_autoguardado()
        if ruta.is_file():
            try:
                datos_iniciales, partida_guardada = cargar_partida(ruta)
            except ValueError as error:
                print(f"No se pudo restaurar la última partida: {error}")

    if datos_iniciales is None:
        datos_iniciales = generar_escenario()

    # El paquete se deduce de la carpeta donde estén estos archivos (real, prueba, etc.).
    paquete = f"visualization.{os.path.basename(CARPETA)}"
    App = importlib.import_module(f"{paquete}.app").App
    # El generador, el cargador de escenarios y el cargador de partidas validan
    # sus datos; no hace falta repetir esa validación al crear la sesión.
    App(
        datos_iniciales,
        partida_guardada=partida_guardada,
        datos_validados=True,
    ).correr()
    sys.exit(0)


if __name__ == "__main__":
    main()
