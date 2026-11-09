"""Constantes de la visualización (colores, tamaños, tiempos)."""

ANCHO = 1760
ALTO = 900
FPS = 60

# Zona donde se dibuja el mapa del almacén (dentro del tablero oscuro).
AREA_X = 40
AREA_Y = 96
AREA_W = 800
AREA_H = 740
AREA_SIM_W = 880
AREA_SIM_H = 700   # el mapa termina en y=796: debajo queda lugar para los carteles de las zonas; la leyenda empieza en 852

# Distribución de la ventana: mapa y paneles comparten el ancho disponible.
MARCO_MAPA_W = 920
PANEL_SIM_X = 960
PANEL_SIM_W = 400
PANEL_WAVES_X = 1380
PANEL_WAVES_W = 360

TICK_SEG = 0.30
VELOCIDADES = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
VEL_INICIAL = 2

# Pausa entre pasos de la vista previa de pickers antes de iniciar.
DEMORA_DEAMBULAR = 0.18

MAX_TARJETAS = 4
# CÓDIGO MUERTO — REVISAR (no se lee desde ningún archivo vivo)
# MAX_PEDIDOS = 4
# LINEAS_LOG = 4

DURACION_ALERTA = 7.0
ANCHO_ALERTA = 640
ANCHO_ALERTA_MIN = 300

# Aspecto de los pickers en el mapa: "montacargas" o "robot".
ESTILO_PICKER = "montacargas"

FUENTES = "segoeui,helveticaneue,helvetica,arial,dejavusans,liberationsans"

BG = (32, 36, 44)
SUELO = (50, 54, 62)
BORDE_SUELO = (88, 94, 106)
BORDE_SUTIL = (58, 61, 69)
PANEL = (44, 48, 56)
TARJETA = (60, 65, 76)
TARJETA_METRICA = (52, 57, 68)
TARJETA_PANEL = (42, 45, 53)
PISTA_PROGRESO = (36, 40, 48)
BORDE = (90, 96, 110)
TEXTO = (226, 232, 245)
TEXTO_SUAVE = (212, 221, 238)
BLANCO_SUAVE = (246, 249, 255)
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
    "deambulando": APAGADO,
    "yendo_a_producto": ACENTO,
    "regresando": ACENTO,
    "esperando": AMARILLO,
    "terminado": VERDE,
    "bloqueado": ROJO,
}

NOMBRE_ESTADO_PICKER = {
    "disponible": "Disponible",
    "deambulando": "Sin trabajo",
    "yendo_a_producto": "Yendo a producto",
    "regresando": "Regresando",
    "esperando": "Esperando",
    "terminado": "Terminado",
    "bloqueado": "Bloqueado",
}

# =====================================================================
# TEMA OSCURO - ESTILO JUEGO (solo UI / pantalla Generar escenario)
# =====================================================================

# Colores de superficie (fondo del panel, tarjetas, etc.)
PANEL_FONDO = (44, 48, 56)        # fondo del panel derecho
PANEL_BORDE = (88, 94, 106)       # borde del panel derecho
TARJETA_FONDO_OSCURO = (52, 57, 68)  # fondo de tarjetas internas
TARJETA_BORDE = (90, 96, 110)     # borde de tarjetas
SOMBRA_BOTON = (0, 0, 0, 90)

# Texto (contraste mínimo 4.5:1 sobre fondo del panel)
TEXTO_PRINCIPAL = (232, 236, 244)   # casi blanco (#E8ECF4) para etiquetas, estado, botones
TEXTO_SECUNDARIO = (216, 224, 238)  # gris muy claro para ayuda, atajos, secundario
TEXTO_DESCATIVADO = (154, 165, 184) # gris medio-bajo para deshabilitados (máx #9AA5B8)
TEXTO_CUERPO = (216, 224, 238)      # gris claro para texto de cuerpo / secundario

# Botones
BOTON_FONDO = (75, 82, 99)        # fondo normal
BOTON_FONDO_SOBRE = (100, 110, 130)  # hover
BOTON_FONDO_PRESIONADO = (58, 65, 80)  # pressed
BOTON_BORDE = (110, 120, 140)     # borde normal
BOTON_BORDE_SOBRE = (160, 170, 190)  # borde hover
BOTON_TEXTO = (255, 255, 255)     # texto botón
BOTON_TEXTO_DESCATIVADO = (130, 136, 150)

# Botón primario (acento)
BOTON_PRIMARIO_FONDO = (58, 112, 190)
BOTON_PRIMARIO_FONDO_SOBRE = (78, 134, 215)
BOTON_PRIMARIO_TEXTO = (255, 255, 255)

# Botón secundario
BOTON_SECUNDARIO_FONDO = (90, 96, 110)
BOTON_SECUNDARIO_FONDO_SOBRE = (110, 120, 140)
BOTON_SECUNDARIO_TEXTO = (255, 255, 255)

# Botón outline (solo borde)
BOTON_OUTLINE_FONDO = (44, 48, 56)
BOTON_OUTLINE_FONDO_SOBRE = (60, 66, 80)
BOTON_OUTLINE_BORDE = ACENTO
BOTON_OUTLINE_TEXTO = ACENTO

# Botón peligro (Nuevo mapa en blanco)
BOTON_PELIGRO_FONDO = (84, 38, 48)
BOTON_PELIGRO_FONDO_SOBRE = (118, 50, 64)
BOTON_PELIGRO_BORDE = (226, 92, 92)
BOTON_PELIGRO_TEXTO = (255, 226, 226)

# Toolbar de herramientas
TOOLBAR_FONDO = (52, 57, 68)
TOOLBAR_BORDE = (70, 76, 90)
TOOL_BUTTON_FONDO = (60, 66, 80)
TOOL_BUTTON_FONDO_ACTIVO = (58, 112, 190)      # mismo azul que las pestañas
TOOL_BUTTON_BORDE_ACTIVO = (140, 188, 255)
TOOL_BUTTON_FONDO_SOBRE = (80, 88, 105)
TOOL_BUTTON_BORDE = (90, 96, 110)
TOOL_BUTTON_TEXTO = (230, 236, 250)
TOOL_BUTTON_TEXTO_ACTIVO = (255, 255, 255)

# Sentidos del pasillo (flechas)
SENTIDO_FONDO = (60, 66, 80)
SENTIDO_FONDO_SOBRE = (80, 88, 105)
SENTIDO_FONDO_ACTIVO = ACENTO
SENTIDO_TEXTO = (230, 236, 250)

# Mapa del editor
MAPA_FONDO = (26, 30, 38)         # fondo oscuro del lienzo del mapa
MAPA_GRILLA = (55, 62, 74)        # color de la grilla sutil
MAPA_CELDA_HOVER = (88, 166, 255, 40)   # resaltado celda bajo cursor
MAPA_PREVIA_VALIDO = (52, 211, 153, 90)  # vista previa verde
MAPA_PREVIA_INVALIDO = (239, 68, 68, 90) # vista previa roja

# Espaciado (múltiplos de 8)
ESPACIO_XS = 4
ESPACIO_S = 8
ESPACIO_M = 16
ESPACIO_L = 24
ESPACIO_XL = 32

# Radios
RADIO_S = 6
RADIO_M = 8
RADIO_L = 12

# Altura de la barra de acciones al pie
BARRA_ACCIONES_ALTO = 56
BARRA_ACCIONES_PADDING = 16

# Lista de pickers (scroll)
LISTA_PICKERS_ALTO_MAX = 140   # 4 filas completas (4 x 32 + márgenes)
LISTA_PICKERS_ITEM_ALTO = 24
LISTA_PICKERS_ITEM_ALTO_CON_BOTON = 32

# Scroll con rueda del mouse
SCROLL_PASO = 30

# Colores de validación
VALIDACION_VALIDO = (52, 211, 153)            # verde
VALIDACION_ERROR = (239, 68, 68)              # rojo
VALIDACION_VACIO = (180, 190, 210)            # gris

# Temporizador de validación automática (ms)
VALIDACION_DELAY_MS = 500

# Altura de la línea de estado de validación (arriba de barra de acciones)
LINEA_ESTADO_ALTO = 24

# Panel derecho (controles del editor / resumen)
PANEL_DERECHO_X = 880
PANEL_DERECHO_Y = 20
PANEL_DERECHO_W = 860
PANEL_DERECHO_H = 860
PANEL_PADDING = 24

# Barra de acciones al pie del panel derecho (dentro del borde del panel)
BARRA_ACCIONES_ALTO = 40
BARRA_ACCIONES_PADDING = 16

# Área de contenido del panel derecho (entre título y barra de acciones)
CONTENIDO_PADDING_TOP = 40   # espacio bajo el título del panel
CONTENIDO_PADDING_BOTTOM = 24  # espacio sobre la barra de acciones
ESPACIO_ENTRE_SECCIONES = 16
ESPACIO_TITULO_CONTENIDO = 8

# Ancho disponible para controles dentro del panel derecho
PANEL_CONTENIDO_W = PANEL_DERECHO_W - 2 * PANEL_PADDING

# Stepper (controles numéricos − y +)
STEPPER_FONDO = (36, 40, 49)
STEPPER_DIVISOR = (68, 73, 84)

# Tarjetas con contraste (pantalla Generar escenario)
CARD_FONDO = (34, 38, 48)
CARD_BORDE = (78, 86, 102)
CARD_DIVISOR = (58, 64, 78)
CONTROL_FONDO = (56, 62, 78)
CONTROL_BORDE = (96, 106, 126)
CONTROL_BOTON = (78, 88, 110)
CONTROL_BOTON_SOBRE = (58, 112, 190)

COLOR_ALERTA = {
    "ValueError": (185, 40, 40),
    "TypeError": (200, 100, 20),
    "Aviso": (170, 130, 10),
    "Listo": (22, 130, 90),
}