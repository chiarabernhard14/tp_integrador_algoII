import json
import os
from pathlib import Path

from .Scenario import validar_escenario
from .Simulation import Simulacion

VERSION_PARTIDA = 1
CLAVES_ESTADO = ("tick", "terminada", "pickers", "waves")
CLAVES_PICKER = ("id", "posicion", "ruta", "estado", "trail",
                 "recogidos", "pendientes", "objetivo")
CLAVES_WAVE = ("id", "estado", "productos")


def ruta_autoguardado():
    """Ruta fija del checkpoint automático, fuera de la carpeta del proyecto."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        carpeta = Path(base) if base else Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_STATE_HOME")
        carpeta = Path(base) if base else Path.home() / ".local" / "state"
    return carpeta / "WavePicking" / "ultima_partida.json"


def guardar_escenario(ruta, datos):
    """Valida el escenario y lo guarda."""
    validar_escenario(datos)
    _escribir_json(ruta, datos)


def cargar_escenario(ruta):
    """Lee un escenario, lo valida y devuelve el dict."""
    datos = _leer_json(ruta)

    if isinstance(datos, dict) and "estado_simulacion" in datos:
        raise ValueError("El archivo es una partida guardada, no un escenario.")

    validar_escenario(datos)
    return datos


def guardar_partida(ruta, simulacion: Simulacion, velocidad_idx=None):
    """Guarda el escenario y el estado actual de la simulación."""
    estado = simulacion.estado()
    if velocidad_idx is not None:
        estado["visualizacion"] = {"velocidad_idx": velocidad_idx}
    partida = {
        "version": VERSION_PARTIDA,
        "datos": simulacion.datos,
        "estado_simulacion": estado,
    }
    _escribir_json(ruta, partida)


def cargar_partida(ruta):
    """Devuelve (datos, estado). Para continuar:
        sim = Simulacion(datos)
        sim.restaurar(estado)"""
    partida = _leer_json(ruta)

    if not isinstance(partida, dict):
        raise ValueError("El archivo no es una partida guardada.")
    if "warehouse" in partida:
        raise ValueError("El archivo es un escenario, no una partida guardada.")
    if partida.get("version") != VERSION_PARTIDA:
        raise ValueError(
            f"La versión de la partida ({partida.get('version')}) no es compatible."
        )
    if "datos" not in partida or "estado_simulacion" not in partida:
        raise ValueError("La partida está incompleta: faltan 'datos' o 'estado_simulacion'.")

    validar_escenario(partida["datos"])
    _validar_estado(partida["estado_simulacion"])
    return partida["datos"], partida["estado_simulacion"]


def _validar_estado(estado):
    """Comprueba que el estado tenga todo lo que Simulacion.restaurar necesita."""
    if not isinstance(estado, dict):
        raise ValueError("El estado de la simulación guardado no es válido.")

    for clave in CLAVES_ESTADO:
        if clave not in estado:
            raise ValueError(f"El estado de la simulación está incompleto: falta '{clave}'.")

    if not isinstance(estado["pickers"], list) or not isinstance(estado["waves"], list):
        raise ValueError("El estado de la simulación está dañado: 'pickers' y 'waves' deben ser listas.")

    for picker in estado["pickers"]:
        if not isinstance(picker, dict):
            raise ValueError("El estado de la simulación está dañado: un picker no es válido.")
        for clave in CLAVES_PICKER:
            if clave not in picker:
                raise ValueError(f"Un picker guardado está incompleto: falta '{clave}'.")

    for wave in estado["waves"]:
        if not isinstance(wave, dict):
            raise ValueError("El estado de la simulación está dañado: una wave no es válida.")
        for clave in CLAVES_WAVE:
            if clave not in wave:
                raise ValueError(f"Una wave guardada está incompleta: falta '{clave}'.")


def _escribir_json(ruta, contenido):
    ruta = os.fspath(ruta)
    ruta_temporal = ruta + ".tmp"

    # Primero a un temporal; se reemplaza el anterior recién cuando el nuevo está completo.
    # Los errores de archivo se convierten en ValueError para que la interfaz los muestre.
    try:
        carpeta = os.path.dirname(ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        with open(ruta_temporal, "w", encoding="utf-8") as archivo:
            json.dump(contenido, archivo, ensure_ascii=False, indent=4)
        os.replace(ruta_temporal, ruta)
    except (OSError, TypeError, ValueError) as error:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)
        raise ValueError(f"No se pudo guardar {ruta}: {error}") from error


def _leer_json(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError as error:
        raise ValueError(f"No se encontró el archivo {ruta}.") from error
    except OSError as error:
        raise ValueError(f"No se pudo leer {ruta}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"El archivo {ruta} no es un JSON válido: {error}") from error
