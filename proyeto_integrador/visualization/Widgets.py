"""Widgets simples: Boton y Alerta (una sola definición)."""

import pygame

from . import Config as cfg

_MOUSE_POS_LOGICA = (0, 0)
_MOUSE_PRESIONADO = False


def actualizar_pos_mouse(pos):
    global _MOUSE_POS_LOGICA
    _MOUSE_POS_LOGICA = pos


def actualizar_presionado(presionado):
    global _MOUSE_PRESIONADO
    _MOUSE_PRESIONADO = presionado


def pos_mouse():
    return _MOUSE_POS_LOGICA


class Boton:

    def __init__(self, nombre, texto, x, y, ancho, alto, color=None):
        self.nombre = nombre
        self.texto = texto
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.color = color


class Alerta:
    """Cartel que aparece arriba y se cierra solo (o con un clic o su X)."""

    MARGEN_SUP = 16
    MARGEN_INF = 20
    MARGEN_IZQ = 22
    MARGEN_DER = 16
    ICONO = 36
    HUECO_ICONO = 14
    ALTO_CERRAR = 22
    HUECO_CERRAR = 14
    RADIO = 14
    GROSOR_FRANJA = 6
    FONDO = (30, 34, 44)

    def __init__(self, f_titulo, f_texto):
        self.f_titulo = f_titulo
        self.f_texto = f_texto
        self.titulo = ""
        self.lineas = []
        self.color = cfg.COLOR_ALERTA["Aviso"]
        self.acento = self.color
        self.restante = 0.0
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.rect_cerrar = pygame.Rect(0, 0, 0, 0)
        self.alto_titulo = 0
        self.paso_linea = 0
        self.fila = 0
        self.x_texto = 0
        self.y_cuerpo = 0

    def mostrar(self, titulo, mensaje):
        self.titulo = titulo
        self.color = cfg.COLOR_ALERTA.get(titulo, cfg.COLOR_ALERTA["Aviso"])
        # El color base de COLOR_ALERTA es oscuro; sobre la tarjeta oscura se aclara un poco.
        self.acento = tuple(min(255, int(v * 1.2) + 25) for v in self.color)
        self.alto_titulo = self.f_titulo.get_height()
        self.paso_linea = self.f_texto.get_linesize()

        # La fila del título (ícono + título + X) tiene el alto del elemento más alto,
        # y todo se centra verticalmente dentro de ella.
        self.fila = max(self.alto_titulo, self.ICONO)
        self.x_texto = self.MARGEN_IZQ + self.ICONO + self.HUECO_ICONO
        reserva_der = self.HUECO_CERRAR + self.ALTO_CERRAR + self.MARGEN_DER

        ancho_util = cfg.ANCHO_ALERTA - self.x_texto - reserva_der
        self.lineas = self._envolver(mensaje, ancho_util)
        self.restante = cfg.DURACION_ALERTA

        ancho_texto = max(
            [self.f_titulo.size(self.titulo)[0]]
            + [self.f_texto.size(linea)[0] for linea in self.lineas]
        )
        ancho = min(
            cfg.ANCHO_ALERTA,
            max(cfg.ANCHO_ALERTA_MIN, ancho_texto + self.x_texto + reserva_der),
        )
        self.y_cuerpo = self.MARGEN_SUP + self.fila + 4
        alto = self.y_cuerpo + len(self.lineas) * self.paso_linea + self.MARGEN_INF
        self.rect = pygame.Rect((cfg.ANCHO - ancho) // 2, 24, ancho, alto)
        self.rect_cerrar = pygame.Rect(
            self.rect.right - self.MARGEN_DER - self.ALTO_CERRAR,
            self.rect.y + self.MARGEN_SUP + (self.fila - self.ALTO_CERRAR) // 2,
            self.ALTO_CERRAR,
            self.ALTO_CERRAR,
        )

    def cerrar(self):
        self.restante = 0.0

    def clic(self, pos):
        if self.visible() and self.rect.collidepoint(pos):
            self.cerrar()

    def visible(self):
        return self.restante > 0.0

    def actualizar(self, dt):
        if self.restante > 0.0:
            self.restante = max(0.0, self.restante - dt)

    def _envolver(self, texto, ancho):
        lineas = []
        actual = ""
        for palabra in texto.split():
            prueba = palabra if not actual else actual + " " + palabra
            if self.f_texto.size(prueba)[0] <= ancho:
                actual = prueba
            else:
                if actual:
                    lineas.append(actual)
                actual = palabra
        if actual:
            lineas.append(actual)
        if not lineas:
            lineas.append("")
        return lineas

    # ---------- dibujo ----------

    def dibujar(self, pantalla):
        if not self.visible():
            return
        r = self.rect

        # Sombra suave (tres capas cada vez más chicas y más oscuras).
        for grosor, alfa in ((10, 18), (6, 26), (3, 38)):
            sombra = pygame.Surface((r.w + grosor * 2, r.h + grosor * 2), pygame.SRCALPHA)
            pygame.draw.rect(sombra, (0, 0, 0, alfa), sombra.get_rect(),
                             border_radius=self.RADIO + grosor)
            pantalla.blit(sombra, (r.x - grosor, r.y - grosor + 5))

        # Tarjeta oscura con borde del color del aviso.
        pygame.draw.rect(pantalla, self.FONDO, r, border_radius=self.RADIO)
        borde = tuple(int(v * 0.6) for v in self.acento)
        pygame.draw.rect(pantalla, borde, r, 1, border_radius=self.RADIO)

        # Franja de color a la izquierda: se dibuja el rect completo pero recortado
        # a los primeros píxeles, así hereda las esquinas redondeadas.
        pantalla.set_clip(pygame.Rect(r.x, r.y, self.GROSOR_FRANJA, r.h))
        pygame.draw.rect(pantalla, self.acento, r, border_radius=self.RADIO)
        pantalla.set_clip(None)

        # Ícono centrado verticalmente en la fila del título.
        cx = r.x + self.MARGEN_IZQ + self.ICONO // 2
        cy = r.y + self.MARGEN_SUP + self.fila // 2
        pygame.draw.circle(pantalla, self.acento, (cx, cy), self.ICONO // 2)
        self._dibujar_glifo(pantalla, cx, cy)

        # Título centrado en la misma fila.
        titulo = self.f_titulo.render(self.titulo, True, (255, 255, 255))
        y_titulo = r.y + self.MARGEN_SUP + (self.fila - self.alto_titulo) // 2
        pantalla.blit(titulo, (r.x + self.x_texto, y_titulo))

        # Cuerpo alineado con el título.
        for i, linea in enumerate(self.lineas):
            img = self.f_texto.render(linea, True, cfg.TEXTO_SUAVE)
            pantalla.blit(img, (r.x + self.x_texto,
                                r.y + self.y_cuerpo + i * self.paso_linea))

        self._dibujar_progreso(pantalla)
        self._dibujar_cerrar(pantalla)

    def _dibujar_glifo(self, pantalla, cx, cy):
        """Símbolo blanco dentro del círculo: tilde, exclamación o cruz según el título."""
        blanco = (255, 255, 255)
        if self.titulo == "Listo":
            pygame.draw.lines(pantalla, blanco, False,
                              [(cx - 7, cy), (cx - 2, cy + 5), (cx + 7, cy - 5)], 3)
        elif self.titulo.endswith("Error"):
            pygame.draw.line(pantalla, blanco, (cx - 6, cy - 6), (cx + 6, cy + 6), 3)
            pygame.draw.line(pantalla, blanco, (cx + 6, cy - 6), (cx - 6, cy + 6), 3)
        else:
            pygame.draw.line(pantalla, blanco, (cx, cy - 9), (cx, cy + 1), 3)
            pygame.draw.circle(pantalla, blanco, (cx, cy + 7), 2)

    def _dibujar_progreso(self, pantalla):
        """Barrita fina abajo que se vacía hasta que el cartel se cierra solo."""
        r = self.rect
        proporcion = max(0.0, min(1.0, self.restante / cfg.DURACION_ALERTA))
        x = r.x + self.x_texto
        ancho = r.right - self.MARGEN_DER - x
        y = r.bottom - 10
        pygame.draw.rect(pantalla, (46, 52, 66), (x, y, ancho, 3), border_radius=1)
        if proporcion > 0:
            pygame.draw.rect(pantalla, self.acento,
                             (x, y, int(ancho * proporcion), 3), border_radius=1)

    def _dibujar_cerrar(self, pantalla):
        """Botón X centrado en la fila del título."""
        sobre = self.rect_cerrar.collidepoint(_MOUSE_POS_LOGICA)
        fondo = (74, 82, 100) if sobre else (48, 54, 68)
        color_x = (255, 255, 255) if sobre else (190, 198, 214)
        cx, cy = self.rect_cerrar.center
        pygame.draw.circle(pantalla, fondo, (cx, cy), self.ALTO_CERRAR // 2)
        d = 4
        pygame.draw.line(pantalla, color_x, (cx - d, cy - d), (cx + d, cy + d), 2)
        pygame.draw.line(pantalla, color_x, (cx + d, cy - d), (cx - d, cy + d), 2)


# =====================================================================
# COMPONENTES REUTILIZABLES - PANTALLA GENERAR ESCENARIO
# =====================================================================


def _sobre(rect):
    return rect.collidepoint(_MOUSE_POS_LOGICA)


class Button:
    """Botón con estados hover / pressed / disabled y variantes visuales.

    Variantes:
        - "primary": fondo de acento, texto blanco.
        - "secondary": fondo gris oscuro, texto blanco.
        - "outline": fondo transparente, borde de acento, texto de acento.
        - "danger": fondo rojo oscuro, borde rojo, texto rojo.
    """

    def __init__(self, nombre, texto, rect, variante="primary", habilitado=True):
        self.nombre = nombre
        self.texto = texto
        self.rect = pygame.Rect(rect)
        self.variante = variante
        self.habilitado = habilitado
        self.presionado = False

    def _colores(self):
        sobre = _sobre(self.rect) and self.habilitado
        presionado = self.presionado and self.habilitado

        if self.variante == "primary":
            if not self.habilitado:
                fondo = (58, 62, 72)
                borde = (80, 84, 94)
                texto = cfg.BOTON_TEXTO_DESCATIVADO
            elif presionado:
                fondo = tuple(max(0, v - 25) for v in cfg.BOTON_PRIMARIO_FONDO)
                borde = cfg.BOTON_PRIMARIO_FONDO
                texto = cfg.BOTON_PRIMARIO_TEXTO
            elif sobre:
                fondo = cfg.BOTON_PRIMARIO_FONDO_SOBRE
                borde = cfg.BOTON_PRIMARIO_FONDO
                texto = cfg.BOTON_PRIMARIO_TEXTO
            else:
                fondo = cfg.BOTON_PRIMARIO_FONDO
                borde = cfg.BOTON_PRIMARIO_FONDO
                texto = cfg.BOTON_PRIMARIO_TEXTO

        elif self.variante == "secondary":
            if not self.habilitado:
                fondo = (58, 62, 72)
                borde = (80, 84, 94)
                texto = cfg.BOTON_TEXTO_DESCATIVADO
            elif presionado:
                fondo = cfg.BOTON_SECUNDARIO_FONDO_SOBRE
                borde = cfg.BOTON_SECUNDARIO_FONDO
                texto = cfg.BOTON_SECUNDARIO_TEXTO
            elif sobre:
                fondo = cfg.BOTON_SECUNDARIO_FONDO_SOBRE
                borde = cfg.BOTON_SECUNDARIO_FONDO
                texto = cfg.BOTON_SECUNDARIO_TEXTO
            else:
                fondo = cfg.BOTON_SECUNDARIO_FONDO
                borde = cfg.BOTON_SECUNDARIO_FONDO
                texto = cfg.BOTON_SECUNDARIO_TEXTO

        elif self.variante == "outline":
            if not self.habilitado:
                fondo = cfg.BOTON_OUTLINE_FONDO
                borde = (80, 84, 94)
                texto = cfg.BOTON_TEXTO_DESCATIVADO
            elif presionado:
                fondo = cfg.BOTON_OUTLINE_FONDO_SOBRE
                borde = cfg.BOTON_OUTLINE_BORDE
                texto = cfg.BOTON_OUTLINE_TEXTO
            elif sobre:
                fondo = cfg.BOTON_OUTLINE_FONDO_SOBRE
                borde = cfg.BOTON_OUTLINE_BORDE
                texto = cfg.BOTON_OUTLINE_TEXTO
            else:
                fondo = cfg.BOTON_OUTLINE_FONDO
                borde = cfg.BOTON_OUTLINE_BORDE
                texto = cfg.BOTON_OUTLINE_TEXTO

        elif self.variante == "danger":
            if not self.habilitado:
                fondo = (58, 62, 72)
                borde = (80, 84, 94)
                texto = cfg.BOTON_TEXTO_DESCATIVADO
            elif presionado:
                fondo = tuple(max(0, v - 25) for v in cfg.BOTON_PELIGRO_FONDO)
                borde = cfg.BOTON_PELIGRO_BORDE
                texto = cfg.BOTON_PELIGRO_TEXTO
            elif sobre:
                fondo = cfg.BOTON_PELIGRO_FONDO_SOBRE
                borde = cfg.BOTON_PELIGRO_BORDE
                texto = cfg.BOTON_PELIGRO_TEXTO
            else:
                fondo = cfg.BOTON_PELIGRO_FONDO
                borde = cfg.BOTON_PELIGRO_BORDE
                texto = cfg.BOTON_PELIGRO_TEXTO

        else:
            fondo = cfg.BOTON_FONDO
            borde = cfg.BOTON_BORDE
            texto = cfg.BOTON_TEXTO

        return fondo, borde, texto

    def dibujar(self, pantalla, fuente):
        fondo, borde, texto_color = self._colores()
        pygame.draw.rect(pantalla, fondo, self.rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(pantalla, borde, self.rect, 2, border_radius=cfg.RADIO_M)
        img = fuente.render(self.texto, True, texto_color)
        pantalla.blit(img, img.get_rect(center=self.rect.center))

    def clic(self, pos):
        """Devuelve True si el clic está dentro del rect y está habilitado."""
        return self.habilitado and self.rect.collidepoint(pos)


class Stepper:
    """Control de valor numérico con botones − y +."""

    def __init__(self, rect_menos, rect_valor, rect_mas, valor, minimo, maximo,
                 fuente, paso=1, paso_shift=5):
        self.rect_menos = pygame.Rect(rect_menos)
        self.rect_valor = pygame.Rect(rect_valor)
        self.rect_mas = pygame.Rect(rect_mas)
        self.valor = valor
        self.minimo = minimo
        self.maximo = maximo
        self.fuente = fuente
        self.paso = paso
        self.paso_shift = paso_shift

    def puede_menos(self):
        return self.valor > self.minimo

    def puede_mas(self):
        return self.valor < self.maximo

    def decrementar(self):
        mod = pygame.key.get_mods()
        paso = self.paso_shift if mod & pygame.KMOD_SHIFT else self.paso
        self.valor = max(self.minimo, self.valor - paso)

    def incrementar(self):
        mod = pygame.key.get_mods()
        paso = self.paso_shift if mod & pygame.KMOD_SHIFT else self.paso
        self.valor = min(self.maximo, self.valor + paso)

    def clic_menos(self, pos):
        return self.puede_menos() and self.rect_menos.collidepoint(pos)

    def clic_mas(self, pos):
        return self.puede_mas() and self.rect_mas.collidepoint(pos)

    def dibujar(self, pantalla):
        unido = self.rect_menos.union(self.rect_valor).union(self.rect_mas)
        pygame.draw.rect(pantalla, cfg.STEPPER_FONDO, unido, border_radius=cfg.RADIO_M)

        puede_menos = self.puede_menos()
        puede_mas = self.puede_mas()

        for rect, simbolo, habilitado in (
            (self.rect_menos, "−", puede_menos),
            (self.rect_mas, "+", puede_mas),
        ):
            color = cfg.TEXTO if habilitado else cfg.APAGADO
            img = self.fuente.render(simbolo, True, color)
            pantalla.blit(img, img.get_rect(center=rect.center))

        pygame.draw.line(
            pantalla, cfg.STEPPER_DIVISOR,
            (self.rect_valor.left, self.rect_valor.top + 7),
            (self.rect_valor.left, self.rect_valor.bottom - 7), 1,
        )
        pygame.draw.line(
            pantalla, cfg.STEPPER_DIVISOR,
            (self.rect_valor.right, self.rect_valor.top + 7),
            (self.rect_valor.right, self.rect_valor.bottom - 7), 1,
        )

        img = self.fuente.render(str(self.valor), True, (255, 255, 255))
        pantalla.blit(img, img.get_rect(center=self.rect_valor.center))


class ToolButton:
    """Botón de herramienta con ícono simple, nombre y atajo de teclado."""

    def __init__(self, clave, nombre, atajo, rect, activo=False):
        self.clave = clave
        self.nombre = nombre
        self.atajo = atajo
        self.rect = pygame.Rect(rect)
        self.activo = activo

    def dibujar(self, pantalla, fuente):
        if self.activo:
            fondo = cfg.TOOL_BUTTON_FONDO_ACTIVO
            borde = cfg.TOOL_BUTTON_BORDE_ACTIVO
            texto_color = cfg.TOOL_BUTTON_TEXTO_ACTIVO
        elif _sobre(self.rect):
            fondo = cfg.TOOL_BUTTON_FONDO_SOBRE
            borde = cfg.TOOL_BUTTON_BORDE
            texto_color = cfg.TEXTO_PRINCIPAL
        else:
            fondo = cfg.TOOL_BUTTON_FONDO
            borde = cfg.TOOL_BUTTON_BORDE
            texto_color = cfg.TOOL_BUTTON_TEXTO

        pygame.draw.rect(pantalla, fondo, self.rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(pantalla, borde, self.rect, 2 if self.activo else 1,
                         border_radius=cfg.RADIO_M)

        img_texto = fuente.render(self.nombre, True, texto_color)
        pantalla.blit(img_texto, img_texto.get_rect(center=self.rect.center))

        # Línea de acento abajo en la herramienta activa.
        if self.activo:
            y = self.rect.bottom - 5
            pygame.draw.line(pantalla, (255, 255, 255),
                             (self.rect.centerx - 10, y),
                             (self.rect.centerx + 10, y), 2)

    def clic(self, pos):
        return self.rect.collidepoint(pos)


class StatusBar:
    """Barra de estado del editor: herramienta, coordenada, tamaño del mapa."""

    def __init__(self, rect, fuente):
        self.rect = pygame.Rect(rect)
        self.fuente = fuente
        self.herramienta = "rack"
        self.coordenada = "(0, 0)"
        self.tamano = "8 × 8"

    def actualizar(self, herramienta, coordenada, tamano):
        self.herramienta = herramienta
        self.coordenada = coordenada
        self.tamano = tamano

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, cfg.TARJETA_FONDO_OSCURO, self.rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(pantalla, cfg.TARJETA_BORDE, self.rect, 1, border_radius=cfg.RADIO_M)

        texto = f"{self.herramienta}   ·   {self.coordenada}   ·   {self.tamano} celdas"
        img = self.fuente.render(texto, True, cfg.TEXTO_PRINCIPAL)
        pantalla.blit(img, (self.rect.x + 12, self.rect.centery - img.get_height() // 2))


class ListaPickersScroll:
    """Lista de pickers con scroll por rueda del mouse y botón de eliminar por fila."""

    MARGEN = 6          # espacio entre el borde de la lista y las filas
    BOTON = 22          # lado del botón de eliminar
    BORDE_DER = 16      # distancia del botón al borde derecho (deja lugar a la barra de scroll)

    def __init__(self, rect, fuente, modelo_pickers, colores_picker):
        self.rect = pygame.Rect(rect)
        self.fuente = fuente
        self.modelo_pickers = modelo_pickers
        self.colores_picker = colores_picker
        self.scroll_offset = 0
        self.scroll_max = 0
        self.item_alto = cfg.LISTA_PICKERS_ITEM_ALTO_CON_BOTON

    @classmethod
    def alto_para(cls, cantidad):
        """Alto que ocupa la lista: justo para sus filas, hasta el máximo."""
        if cantidad == 0:
            return 0
        return min(cfg.LISTA_PICKERS_ALTO_MAX,
                   cantidad * cfg.LISTA_PICKERS_ITEM_ALTO_CON_BOTON + 2 * cls.MARGEN)

    def actualizar(self, modelo_pickers):
        self.modelo_pickers = modelo_pickers
        self._recalcular_scroll()

    def _recalcular_scroll(self):
        """El scroll depende del alto real con el que se dibuja la lista."""
        total = len(self.modelo_pickers) * self.item_alto + 2 * self.MARGEN
        self.scroll_max = max(0, total - self.rect.h)
        self.scroll_offset = max(0, min(self.scroll_offset, self.scroll_max))

    def scroll(self, pasos):
        """Desplaza la lista por `pasos` (positivo = hacia abajo)."""
        self.scroll_offset = max(0, min(self.scroll_max, self.scroll_offset + pasos))

    def _y_fila(self, indice):
        return self.rect.top + self.MARGEN + indice * self.item_alto - self.scroll_offset

    def _rect_eliminar(self, indice):
        y = self._y_fila(indice)
        return pygame.Rect(
            self.rect.right - self.BORDE_DER - self.BOTON,
            y + (self.item_alto - self.BOTON) // 2,
            self.BOTON,
            self.BOTON,
        )

    def clic_eliminar(self, pos):
        """Devuelve el índice del picker a eliminar, o -1 si no se clickeó ningún botón."""
        if not self.rect.collidepoint(pos):   # las filas fuera de la vista no se pueden clickear
            return -1
        for indice in range(len(self.modelo_pickers)):
            if self._rect_eliminar(indice).collidepoint(pos):
                return indice
        return -1

    def dibujar(self, pantalla):
        self._recalcular_scroll()
        if not self.modelo_pickers or self.rect.h <= 0:
            return
        pygame.draw.rect(pantalla, cfg.TARJETA_FONDO_OSCURO, self.rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(pantalla, cfg.TARJETA_BORDE, self.rect, 1, border_radius=cfg.RADIO_M)

        pantalla.set_clip(self.rect.inflate(-2, -2))
        mouse = _MOUSE_POS_LOGICA

        for indice, picker in enumerate(self.modelo_pickers):
            y = self._y_fila(indice)
            if y + self.item_alto < self.rect.top or y > self.rect.bottom:
                continue

            color = self.colores_picker[indice % len(self.colores_picker)]
            fila = pygame.Rect(self.rect.x + 6, y + 1, self.rect.w - 12, self.item_alto - 2)
            cy = fila.centery

            # Fondo de la fila (un poco más claro en las pares)
            fondo = (60, 66, 80) if indice % 2 == 0 else (54, 60, 74)
            pygame.draw.rect(pantalla, fondo, fila, border_radius=cfg.RADIO_S)

            # Punto de color del picker
            cx = fila.x + 16
            pygame.draw.circle(pantalla, (16, 22, 34), (cx, cy), 7)
            pygame.draw.circle(pantalla, color, (cx, cy), 5)

            # Nombre, centrado verticalmente en la fila
            img = self.fuente.render(str(picker["id"]), True, cfg.TEXTO_PRINCIPAL)
            pantalla.blit(img, img.get_rect(midleft=(cx + 16, cy)))

            # Botón eliminar: discreto, se pone rojo al pasar el mouse
            btn = self._rect_eliminar(indice)
            sobre = btn.collidepoint(mouse) and self.rect.collidepoint(mouse)
            pygame.draw.rect(pantalla, (108, 46, 58) if sobre else (74, 82, 100),
                             btn, border_radius=6)
            pygame.draw.rect(pantalla, cfg.ROJO if sobre else (104, 112, 130),
                             btn, 1, border_radius=6)
            m = 7
            trazo = (255, 255, 255) if sobre else (214, 220, 232)
            pygame.draw.line(pantalla, trazo, (btn.x + m, btn.y + m),
                             (btn.right - m - 1, btn.bottom - m - 1), 2)
            pygame.draw.line(pantalla, trazo, (btn.right - m - 1, btn.y + m),
                             (btn.x + m, btn.bottom - m - 1), 2)

        pantalla.set_clip(None)

        # Barra de scroll (solo si hay filas fuera de la vista)
        if self.scroll_max > 0:
            pista = pygame.Rect(self.rect.right - 9, self.rect.top + 8, 4, self.rect.h - 16)
            alto_barra = max(20, int(pista.h * self.rect.h /
                                     (self.rect.h + self.scroll_max)))
            y_barra = pista.y + int(self.scroll_offset / self.scroll_max * (pista.h - alto_barra))
            pygame.draw.rect(pantalla, (46, 52, 66), pista, border_radius=2)
            pygame.draw.rect(pantalla, (120, 130, 150),
                             (pista.x, y_barra, pista.w, alto_barra), border_radius=2)


class PanelValidacion:
    """Panel de resultados de validación: sin validar / válido / N errores."""

    def __init__(self, rect, fuente):
        self.rect = pygame.Rect(rect)
        self.fuente = fuente
        self.estado = "sin_validar"  # sin_validar | valido | error
        self.errores = []  # lista de strings
        self.mensaje = ""

    def actualizar(self, estado, errores=None, mensaje=""):
        self.estado = estado
        self.errores = errores or []
        self.mensaje = mensaje

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, cfg.TARJETA_FONDO_OSCURO, self.rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(pantalla, cfg.TARJETA_BORDE, self.rect, 1, border_radius=cfg.RADIO_M)

        if self.estado == "sin_validar":
            color = cfg.VALIDACION_SIN_VALIDAR
            estado_texto = "Sin validar"
        elif self.estado == "valido":
            color = cfg.VALIDACION_VALIDO
            estado_texto = "Mapa válido"
        else:
            color = cfg.VALIDACION_ERROR
            estado_texto = f"{len(self.errores)} error(es)"

        # Título de estado
        img_estado = self.fuente.render(estado_texto, True, color)
        pantalla.blit(img_estado, (self.rect.x + 12, self.rect.y + 10))

        # Mensaje o errores
        y = self.rect.y + 34
        if self.estado == "error" and self.errores:
            for i, error in enumerate(self.errores[:4]):
                img_err = self.fuente.render("• " + error, True, cfg.TEXTO_DESCATIVADO)
                pantalla.blit(img_err, (self.rect.x + 12, y + i * 18))
        elif self.mensaje:
            img_msg = self.fuente.render(self.mensaje, True, cfg.TEXTO_DESCATIVADO)
            pantalla.blit(img_msg, (self.rect.x + 12, y))

        # Indicador visual a la derecha
        punto_x = self.rect.right - 18
        punto_y = self.rect.centery
        pygame.draw.circle(pantalla, color, (punto_x, punto_y), 6)
        pygame.draw.circle(pantalla, (255, 255, 255), (punto_x, punto_y), 2)


def dibujar_boton(pantalla, fuente, rect, texto, color=None, activo=False, habilitado=True):
    """Botón redondeado con resaltado al pasar el mouse; lo usan el panel y la pantalla de generar."""
    mx, my = _MOUSE_POS_LOGICA
    sobre = habilitado and rect.collidepoint((mx, my))
    if not habilitado:
        relleno = (58, 62, 72)
    elif color is not None:
        relleno = tuple(min(255, v + 30) for v in color) if sobre else color
    elif activo:
        relleno = (58, 112, 190)
    elif sobre:
        relleno = (100, 110, 130)
    else:
        relleno = (75, 82, 99)
    pygame.draw.rect(pantalla, relleno, rect, border_radius=10)
    if activo and habilitado:
        borde = cfg.ACENTO
    elif sobre:
        borde = (160, 170, 190)
    else:
        borde = (110, 120, 140) if habilitado else (80, 84, 94)
    pygame.draw.rect(pantalla, borde, rect, 2, border_radius=10)
    img = fuente.render(texto, True, (255, 255, 255) if habilitado else (130, 136, 150))
    pantalla.blit(img, img.get_rect(center=rect.center))


# =====================================================================
# CÓDIGO MUERTO — REVISAR (no se usa desde ningún archivo vivo)
# =====================================================================
class Badge:
    """Etiqueta compacta para estados y valores definidos por el usuario."""

    def __init__(self, rect, texto, color=None):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.color = color or cfg.ACENTO

    def dibujar(self, pantalla, fuente):
        fondo = tuple(round(valor * 0.18) for valor in self.color)
        pygame.draw.rect(pantalla, fondo, self.rect, border_radius=self.rect.h // 2)
        pygame.draw.rect(pantalla, self.color, self.rect, 1,
                         border_radius=self.rect.h // 2)
        imagen = fuente.render(self.texto, True, self.color)
        pantalla.blit(imagen, imagen.get_rect(center=self.rect.center))
# =====================================================================
# FIN CÓDIGO MUERTO
# =====================================================================