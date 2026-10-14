import json
import os

from ScenarioV import validar_escenario   

VERSION_PARTIDA = 1


def guardar_escenario(ruta, datos):
    """Valida el escenario y lo guarda."""
    validar_escenario(datos)
    _escribir_json(ruta, datos)


def cargar_escenario(ruta):
    """Lee un escenario, lo valida y devuelve el dict."""
    datos = _leer_json(ruta)
    validar_escenario(datos)
    return datos


def guardar_partida(ruta, simulacion):
    """Guarda el escenario y el estado actual de la simulación."""
    partida = {
        "version": VERSION_PARTIDA,
        "datos": simulacion.datos,
        "estado_simulacion": simulacion.estado(),
    }
    _escribir_json(ruta, partida)


def cargar_partida(ruta):
    """Devuelve (datos, estado). Para continuar:
        sim = Simulacion(datos)
        sim.restaurar(estado)"""
    partida = _leer_json(ruta)

    if not isinstance(partida, dict):
        raise ValueError("El archivo no es una partida guardada.")
    if partida.get("version") != VERSION_PARTIDA:
        raise ValueError(
            f"La versión de la partida ({partida.get('version')}) no es compatible."
        )
    if "datos" not in partida or "estado_simulacion" not in partida:
        raise ValueError("La partida está incompleta: faltan 'datos' o 'estado_simulacion'.")

    validar_escenario(partida["datos"])
    return partida["datos"], partida["estado_simulacion"]


def _escribir_json(ruta, contenido):
    ruta = os.fspath(ruta)
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    # Primero a un temporal; se reemplaza el anterior recién cuando el nuevo está completo.
    ruta_temporal = ruta + ".tmp"
    try:
        with open(ruta_temporal, "w", encoding="utf-8") as archivo:
            json.dump(contenido, archivo, ensure_ascii=False, indent=4)
        os.replace(ruta_temporal, ruta)
    except Exception:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)
        raise


def _leer_json(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except json.JSONDecodeError as error:
        raise ValueError(f"El archivo {ruta} no es un JSON válido: {error}") from error