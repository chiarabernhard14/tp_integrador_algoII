import json
import sys
import time
import cProfile
import pstats
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from simulation import Scenario
from simulation.AsignadorPickers import Asignador
from simulation.Scenario import validar_escenario
from simulation.Simulation import Simulacion

TRABAJOS_REGISTRADOS = []
UMBRAL_FORZADO = None
INIT_ASIGNADOR_ORIGINAL = Asignador.__init__
ASIGNAR_ORIGINAL = Asignador.asignar


def init_asignador_con_umbral(
    self, nav, zonas, waves, productos, racks,
    algoritmo_camino="a_estrella", estrategia="cercania",
    max_combinaciones_exactas=5000,
):
    return INIT_ASIGNADOR_ORIGINAL(
        self,
        nav,
        zonas,
        waves,
        productos,
        racks,
        algoritmo_camino=algoritmo_camino,
        estrategia=estrategia,
        max_combinaciones_exactas=UMBRAL_FORZADO,
    )


def asignar_y_registrar(self, libres):
    resultado = ASIGNAR_ORIGINAL(self, libres)
    TRABAJOS_REGISTRADOS.extend(dict(trabajo) for trabajo in resultado)
    return resultado


def leer_datos(ruta):
    inicio = time.perf_counter()
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return datos, time.perf_counter() - inicio


def escenario_chico():
    generador_random = Scenario.random.Random
    Scenario.random.Random = lambda *args, **kwargs: generador_random(42)
    try:
        return Scenario.generar_escenario(
            estantes=3,
            pasillos_horizontales=2,
            productos=8,
            pedidos=2,
            max_productos_pedido=2,
            pickers=2,
            modo_ubicacion="cerca_despacho",
        )
    finally:
        Scenario.random.Random = generador_random


def ejecutar(datos, etiqueta, umbral=None):
    global TRABAJOS_REGISTRADOS, UMBRAL_FORZADO
    TRABAJOS_REGISTRADOS = []
    if umbral is not None:
        UMBRAL_FORZADO = umbral
        Asignador.__init__ = init_asignador_con_umbral
    Asignador.asignar = asignar_y_registrar
    try:
        inicio = time.perf_counter()
        validar_escenario(datos)
        validacion = time.perf_counter() - inicio
        inicio = time.perf_counter()
        sim = Simulacion(datos)
        inicializacion = time.perf_counter() - inicio
    finally:
        Asignador.asignar = ASIGNAR_ORIGINAL
        Asignador.__init__ = INIT_ASIGNADOR_ORIGINAL

    reparto = {}
    for trabajo in TRABAJOS_REGISTRADOS:
        picker = trabajo["picker"]
        productos = reparto.setdefault(picker, Counter())
        for item in trabajo["productos"]:
            productos[item["producto_id"]] += item["cantidad"]
    print(json.dumps({
        "caso": etiqueta,
        "warehouse": sim.warehouse.ancho_x,
        "pickers": len(sim.pickers),
        "waves": len(sim.waves),
        "unidades_pedidas": sum(sum(w["solicitados"].values()) for w in sim.waves),
        "validacion_s": validacion,
        "inicializacion_s": inicializacion,
        "asignacion_s": sim.tiempo_asignacion_ms / 1000,
        "busquedas": sim.planificador.busquedas,
        "nodos_expandidos": sim.planificador.nodos_expandidos,
        "tiempo_asignacion_ms_sim": sim.tiempo_asignacion_ms,
        "distancia_total": sum(t["distancia_estimada"] for t in TRABAJOS_REGISTRADOS),
        "reparto": {p: dict(sorted(c.items())) for p, c in sorted(reparto.items())},
        "trabajos": [
            {
                "picker": t["picker"],
                "distancia": t["distancia_estimada"],
                "productos": t["productos"],
            }
            for t in TRABAJOS_REGISTRADOS
        ],
    }, ensure_ascii=False))
    if validacion > 5:
        perfil = cProfile.Profile()
        perfil.runcall(validar_escenario, datos)
        print(f"cProfile validación {etiqueta}:")
        pstats.Stats(perfil).sort_stats("cumulative").print_stats(15)
    if inicializacion > 5 or sim.tiempo_asignacion_ms / 1000 > 5:
        perfil = cProfile.Profile()
        perfil.runcall(Simulacion, datos)
        print(f"cProfile inicialización {etiqueta}:")
        pstats.Stats(perfil).sort_stats("cumulative").print_stats(15)


if __name__ == "__main__":
    for ruta_fuente in (
        ROOT / "simulation/PlanificadorViajes.py",
        ROOT / "simulation/AsignadorPickers.py",
        ROOT / "simulation/Simulation.py",
        ROOT / "visualization/App.py",
    ):
        compile(ruta_fuente.read_text(encoding="utf-8"), str(ruta_fuente), "exec")
    print(json.dumps({"fase": "sintaxis", "resultado": "correcta"}))
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        datos_chicos = escenario_chico()
        ejecutar(datos_chicos, "small-exacto")
        ejecutar(datos_chicos, "small-voraz", umbral=0)
        ruta = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\Chiara\Downloads\escenario_pesado.json"
        datos, tiempo_json = leer_datos(ruta)
        print(json.dumps({"fase": "parseo_json", "segundos": tiempo_json}, ensure_ascii=False))
        ejecutar(datos, "heavy")
    elif len(sys.argv) > 1 and sys.argv[1] == "small":
        ejecutar(escenario_chico(), "small")
    elif len(sys.argv) > 1 and sys.argv[1] == "small-greedy":
        ejecutar(escenario_chico(), "small-greedy", umbral=0)
    elif len(sys.argv) > 1 and sys.argv[1] == "heavy-repeat":
        ruta = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\Chiara\Downloads\escenario_pesado.json"
        datos, tiempo_json = leer_datos(ruta)
        print(json.dumps({"fase": "parseo_json", "segundos": tiempo_json}, ensure_ascii=False))
        for indice in range(1, 4):
            ejecutar(datos, f"heavy-{indice}")
    else:
        ruta = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Chiara\Downloads\escenario_pesado.json"
        datos, tiempo_json = leer_datos(ruta)
        print(json.dumps({"fase": "parseo_json", "segundos": tiempo_json}, ensure_ascii=False))
        ejecutar(datos, "heavy")
