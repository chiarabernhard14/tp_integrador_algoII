"""Recomendación de cantidad de pickers.

Es solo una SUGERENCIA: no cambia ni limita nada de lo que el usuario configure.

Corre la simulación completa, sin pantalla, con 1, 2, ... pickers y compara:
    - ticks totales (qué tan rápido termina),
    - pasos totales (esfuerzo),
    - ticks de espera (congestión: pickers esperando a que otro libere el paso),
    - pickers bloqueados.

Los pickers que se prueban salen de los que configuró el usuario (los primeros
k de su lista). Si prueba más de los que configuró, se completan con COPIAS de
los suyos (misma capacidad) que parten desde celdas libres del despacho.

No toca la simulación que está en pantalla: cada corrida crea la suya.
"""

from .SimutionV import Simulacion

# Un picker más se considera inútil si mejora el tiempo menos que esto.
TOLERANCIA_TIEMPO = 0.05

# Congestión: fracción del tiempo de los pickers que pasan esperando.
UMBRAL_ESPERA = 0.10

MAX_TICKS = 10000


def _con_pickers(datos, pickers):
    """Copia superficial del escenario con otra lista de pickers (no modifica datos)."""
    nuevo = dict(datos)
    nuevo["pickers"] = list(pickers)
    return nuevo


def _capacidad(picker):
    return picker["capacidad_carga_kg"]


def _celdas_ocupadas(pickers):
    ocupadas = set()
    for picker in pickers:
        inicio = picker["posicion_inicial"]
        ocupadas.add((inicio["x"], inicio["y"]))
    return ocupadas


def _picker_clon(modelo, numero, celda):
    clon = dict(modelo)
    clon["id"] = f"PK_{numero:02d}"
    clon["posicion_inicial"] = {"x": celda[0], "y": celda[1]}
    return clon


def _armar_pickers(pool, cantidad, despacho):
    """Devuelve (lista de pickers, cuántos son copias).

    Usa los primeros 'cantidad' del pool; si hacen falta más, agrega copias
    de los del pool en celdas libres del despacho."""

    pickers = list(pool[:cantidad])
    if len(pickers) == cantidad:
        return pickers, 0

    usados = set()
    for picker in pickers:
        usados.add(picker["id"])
    libres = []
    ocupadas = _celdas_ocupadas(pickers)
    for celda in sorted(despacho):
        if celda not in ocupadas:
            libres.append(celda)

    numero = len(pool)
    agregados = 0
    while len(pickers) < cantidad:
        if not libres:
            raise ValueError(
                "No hay más celdas libres en el despacho para agregar pickers de prueba."
            )
        numero += 1
        while f"PK_{numero:02d}" in usados:
            numero += 1
        modelo = pool[agregados % len(pool)]
        clon = _picker_clon(modelo, numero, libres.pop(0))
        pickers.append(clon)
        usados.add(clon["id"])
        agregados += 1

    return pickers, agregados


def _simular(datos, waves, pickers, agregados):
    cantidad = len(pickers)
    resultado = {
        "pickers": cantidad,
        "agregados": agregados,
        "viable": True,
        "motivo": "",
    }

    try:
        sim = Simulacion(_con_pickers(datos, pickers), waves)
    except ValueError as error:
        resultado["viable"] = False
        resultado["motivo"] = str(error)
        return resultado

    sim.ejecutar(MAX_TICKS)
    estado = sim.estado()

    pasos = 0
    bloqueados = 0
    for picker in estado["pickers"]:
        pasos += len(picker["trail"]) - 1
        if picker["estado"] == "bloqueado":
            bloqueados += 1

    congestion = 0.0
    if sim.tick > 0:
        congestion = sim.ticks_espera / (sim.tick * cantidad)

    resultado["ticks"] = sim.tick
    resultado["pasos"] = pasos
    resultado["esperas"] = sim.ticks_espera
    resultado["bloqueados"] = bloqueados
    resultado["terminada"] = sim.terminada
    resultado["congestion"] = congestion
    return resultado


def recomendar_pickers(datos, waves=None, max_probar=8):
    """Simula con 1..k pickers y devuelve un dict con:

        resultados:           una fila por cantidad de pickers probada
                              (pickers, agregados, viable, ticks, pasos, esperas,
                               bloqueados, congestion, terminada, motivo).
        recomendado:          menor cantidad cuyo tiempo está a menos de un 5 %
                              del mejor y sin bloqueos (None si ninguna sirve).
        tope_congestion:      mayor cantidad antes de que las esperas superen el
                              10 % del tiempo de los pickers (None si ninguna).
        pickers_recomendados: la lista de pickers (dicts) del recomendado.
        waves:                cantidad de waves (máximo posible de pickers).
        pickers_configurados: cuántos pickers había en el escenario.
    """

    pool = datos.get("pickers", [])
    if not pool:
        raise ValueError("No hay pickers configurados para usar como modelo.")
    if max_probar < 1:
        raise ValueError("max_probar debe ser al menos 1.")

    # Simulación base con el picker más grande: sirve para saber cuántas waves hay
    # y dónde queda el despacho, sin fallar si el usuario configuró de más.
    mayor = pool[0]
    for picker in pool:
        if _capacidad(picker) > _capacidad(mayor):
            mayor = picker
    base = Simulacion(_con_pickers(datos, [mayor]), waves)
    cantidad_waves = len(base.waves)
    despacho = base.nav.despacho

    limite = min(max_probar, cantidad_waves)

    resultados = []
    for cantidad in range(1, limite + 1):
        try:
            pickers, agregados = _armar_pickers(pool, cantidad, despacho)
        except ValueError as error:
            resultados.append({
                "pickers": cantidad, "agregados": 0, "viable": False,
                "motivo": str(error),
            })
            break
        resultados.append(_simular(datos, waves, pickers, agregados))

    # Recomendado: el menor k cuyo tiempo está cerca del mejor, sin bloqueos.
    validos = []
    for resultado in resultados:
        if resultado["viable"] and resultado["terminada"] and resultado["bloqueados"] == 0:
            validos.append(resultado)

    recomendado = None
    if validos:
        mejor = min(r["ticks"] for r in validos)
        for resultado in validos:
            if resultado["ticks"] <= mejor * (1 + TOLERANCIA_TIEMPO):
                recomendado = resultado["pickers"]
                break

    # Tope de congestión: hasta dónde las esperas siguen siendo razonables.
    tope = None
    for resultado in resultados:
        if not resultado["viable"]:
            continue
        if resultado["congestion"] > UMBRAL_ESPERA or resultado["bloqueados"] > 0:
            break
        tope = resultado["pickers"]

    pickers_recomendados = []
    if recomendado is not None:
        pickers_recomendados, _ = _armar_pickers(pool, recomendado, despacho)

    return {
        "resultados": resultados,
        "recomendado": recomendado,
        "tope_congestion": tope,
        "pickers_recomendados": pickers_recomendados,
        "waves": cantidad_waves,
        "pickers_configurados": len(pool),
    }