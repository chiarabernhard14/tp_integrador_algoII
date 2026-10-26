"""Constantes de la visualización (colores, tamaños, tiempos)."""

ANCHO = 1280
ALTO = 780
FPS = 60

# Zona donde se dibuja el mapa del almacén (dentro del tablero oscuro).
AREA_X = 40
AREA_Y = 96
AREA_W = 800
AREA_H = 620

TICK_SEG = 0.30
VELOCIDADES = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
VEL_INICIAL = 2

MAX_TARJETAS = 5
MAX_PEDIDOS = 4
LINEAS_LOG = 4

DURACION_ALERTA = 7.0
ANCHO_ALERTA = 720

# Aspecto de los pickers en el mapa: "montacargas" o "robot".
ESTILO_PICKER = "montacargas"

FUENTES = "segoeui,helveticaneue,helvetica,arial,dejavusans,liberationsans"

BG = (255, 255, 255)
SUELO = (50, 54, 62)
BORDE_SUELO = (88, 94, 106)
PANEL = (44, 48, 56)
TARJETA = (60, 65, 76)
BORDE = (90, 96, 110)
TEXTO = (226, 232, 245)
APAGADO = (139, 150, 176)
ACENTO = (88, 166, 255)
VERDE = (52, 211, 153)
NARANJA = (251, 146, 60)
AMARILLO = (250, 204, 21)
ROJO = (239, 68, 68)
PASILLO = (108, 114, 126)
PASILLO_FLECHA = (156, 162, 174)
RACK = (24, 52, 102)
RACK_BORDE = (59, 130, 246)
CAJA = (214, 160, 90)
CAJA_APAGADA = (92, 76, 60)

COLORES_PICKER = (
    (59, 130, 246),    # azul
    (147, 102, 250),   # violeta
    (250, 204, 21),    # amarillo
    (52, 211, 153),    # verde
    (34, 211, 238),    # celeste
    (163, 230, 53),    # lima
    (244, 114, 182),   # rosa
    (232, 121, 249),   # fucsia
)

COLOR_ESTADO_PICKER = {
    "disponible": TEXTO,
    "yendo_a_producto": ACENTO,
    "regresando": ACENTO,
    "esperando": AMARILLO,
    "terminado": VERDE,
    "bloqueado": ROJO,
}

NOMBRE_ESTADO_PICKER = {
    "disponible": "Disponible",
    "yendo_a_producto": "Yendo a producto",
    "regresando": "Regresando",
    "esperando": "Esperando",
    "terminado": "Terminado",
    "bloqueado": "Bloqueado",
}

COLOR_ESTADO_PEDIDO = {
    "PENDIENTE": (120, 130, 150),
    "EN_PREPARACION": NARANJA,
    "PREPARADO": VERDE,
}

COLOR_ALERTA = {
    "ValueError": (185, 40, 40),
    "TypeError": (200, 100, 20),
    "Aviso": (170, 130, 10),
    "Listo": (22, 130, 90),
}