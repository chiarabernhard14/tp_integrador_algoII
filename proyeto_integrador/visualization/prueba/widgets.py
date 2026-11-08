"""Widgets simples: Boton y Alerta (una sola definición)."""

import pygame

from . import config as cfg

_MOUSE_POS_LOGICA = (0, 0)
_MOUSE_PRESIONADO = False


def actualizar_pos_mouse(pos):
    global _MOUSE_POS_LOGICA
    _MOUSE_POS_LOGICA = pos


def actualizar_presionado(presionado):
    global _MOUSE_PRESIONADO
    _MOUSE_PRESIONADO = presionado


class Boton:

    def __init__(self, nombre, texto, x, y, ancho, alto, color=None):
        self.nombre = nombre
        self.texto = texto
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.color = color


class Alerta:
    """Cartel que aparece arriba y se cierra solo (o con un clic o su X)."""

    MARGEN = 20
    ALTO_CERRAR = 18
    HUECO_CERRAR = 12

    def __init__(self, f_titulo, f_texto):
        self.f_titulo = f_titulo
        self.f_texto = f_texto
        self.titulo = ""
        self.lineas = []
        self.color = cfg.COLOR_ALERTA["Aviso"]
        self.restante = 0.0
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.rect_cerrar = pygame.Rect(0, 0, 0, 0)
        self.alto_titulo = 0
        self.paso_linea = 0
        self.y_cuerpo = 0

    def mostrar(self, titulo, mensaje):
        self.titulo = titulo
        self.color = cfg.COLOR_ALERTA.get(titulo, cfg.COLOR_ALERTA["Aviso"])
        self.alto_titulo = self.f_titulo.get_height()
        self.paso_linea = self.f_texto.get_linesize()
        ancho_util = (
            cfg.ANCHO_ALERTA
            - 2 * self.MARGEN
            - self.ALTO_CERRAR
            - self.HUECO_CERRAR
        )
        self.lineas = self._envolver(mensaje, ancho_util)
        self.restante = cfg.DURACION_ALERTA
        ancho_texto = max(
            [self.f_titulo.size(self.titulo)[0]]
            + [self.f_texto.size(linea)[0] for linea in self.lineas]
        )
        ancho = min(
            cfg.ANCHO_ALERTA,
            max(
                cfg.ANCHO_ALERTA_MIN,
                ancho_texto + 2 * self.MARGEN
                + self.ALTO_CERRAR + self.HUECO_CERRAR,
            ),
        )
        self.y_cuerpo = 14 + self.alto_titulo + 6
        alto = self.y_cuerpo + len(self.lineas) * self.paso_linea + 16
        self.rect = pygame.Rect((cfg.ANCHO - ancho) // 2, 24, ancho, alto)
        self.rect_cerrar = pygame.Rect(
            self.rect.right - self.MARGEN - self.ALTO_CERRAR,
            self.rect.y + 12,
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

    def dibujar(self, pantalla):
        if not self.visible():
            return
        pygame.draw.rect(pantalla, self.color, self.rect, border_radius=12)
        pygame.draw.rect(pantalla, (255, 255, 255), self.rect, 2, border_radius=12)
        titulo = self.f_titulo.render(self.titulo, True, (255, 255, 255))
        pantalla.blit(titulo, (self.rect.x + self.MARGEN, self.rect.y + 12))
        for i, linea in enumerate(self.lineas):
            img = self.f_texto.render(linea, True, (255, 255, 255))
            pantalla.blit(
                img,
                (self.rect.x + self.MARGEN,
                 self.rect.y + self.y_cuerpo + i * self.paso_linea),
            )
        self._dibujar_cerrar(pantalla)

    def _dibujar_cerrar(self, pantalla):
        """Botón X en la esquina superior derecha."""
        sobre = self.rect_cerrar.collidepoint(_MOUSE_POS_LOGICA)
        fondo = tuple(min(255, v + 45) for v in self.color) if sobre else (
            min(255, self.color[0] + 20),
            min(255, self.color[1] + 20),
            min(255, self.color[2] + 20),
        )
        pygame.draw.circle(
            pantalla, fondo, self.rect_cerrar.center, self.ALTO_CERRAR // 2
        )
        m = 5
        pygame.draw.line(
            pantalla, (255, 255, 255),
            (self.rect_cerrar.x + m, self.rect_cerrar.y + m),
            (self.rect_cerrar.right - m, self.rect_cerrar.bottom - m), 2,
        )
        pygame.draw.line(
            pantalla, (255, 255, 255),
            (self.rect_cerrar.right - m, self.rect_cerrar.y + m),
            (self.rect_cerrar.x + m, self.rect_cerrar.bottom - m), 2,
        )


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
            borde = cfg.TOOL_BUTTON_FONDO_ACTIVO
            texto_color = cfg.TEXTO_PRINCIPAL
        elif _sobre(self.rect):
            fondo = cfg.TOOL_BUTTON_FONDO_SOBRE
            borde = cfg.TOOL_BUTTON_BORDE
            texto_color = cfg.TEXTO_PRINCIPAL
        else:
            fondo = cfg.TOOL_BUTTON_FONDO
            borde = cfg.TOOL_BUTTON_BORDE
            texto_color = cfg.TEXTO_PRINCIPAL

        pygame.draw.rect(pantalla, fondo, self.rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(pantalla, borde, self.rect, 1, border_radius=cfg.RADIO_M)

        # Nombre + atajo (atajo a la derecha)
        img_texto = fuente.render(self.nombre, True, texto_color)
        pantalla.blit(img_texto, (self.rect.x + 10, self.rect.centery - img_texto.get_height() // 2))
        img_atajo = fuente.render(self.atajo, True, cfg.TEXTO_DESCATIVADO)
        pantalla.blit(img_atajo, (self.rect.right - 20, self.rect.centery - img_atajo.get_height() // 2))

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

    def __init__(self, rect, fuente, modelo_pickers, colores_picker):
        self.rect = pygame.Rect(rect)
        self.fuente = fuente
        self.modelo_pickers = modelo_pickers
        self.colores_picker = colores_picker
        self.scroll_offset = 0
        self.scroll_max = 0
        self.item_alto = cfg.LISTA_PICKERS_ITEM_ALTO_CON_BOTON
        self.btn_eliminar_w = 24

    def actualizar(self, modelo_pickers):
        self.modelo_pickers = modelo_pickers
        total = len(modelo_pickers) * self.item_alto
        disponible = self.rect.h - 20  # margen interno
        self.scroll_max = max(0, total - disponible)

    def scroll(self, pasos):
        """Desplaza la lista por `pasos` (positivo = hacia abajo)."""
        self.scroll_offset = max(0, min(self.scroll_max, self.scroll_offset + pasos))

    def _rect_eliminar(self, indice):
        y = self.rect.top + 10 + indice * self.item_alto - self.scroll_offset
        return pygame.Rect(
            self.rect.right - 10 - self.btn_eliminar_w,
            y + (self.item_alto - 20) // 2,
            self.btn_eliminar_w,
            20,
        )

    def clic_eliminar(self, pos):
        """Devuelve el índice del picker a eliminar, o -1 si no se clickeó ningún botón."""
        for indice in range(len(self.modelo_pickers)):
            if self._rect_eliminar(indice).collidepoint(pos):
                return indice
        return -1

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, cfg.TARJETA_FONDO_OSCURO, self.rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(pantalla, cfg.TARJETA_BORDE, self.rect, 1, border_radius=cfg.RADIO_M)

        recorte = pygame.Rect(self.rect)
        pantalla.set_clip(recorte)

        for indice, picker in enumerate(self.modelo_pickers):
            y = self.rect.top + 10 + indice * self.item_alto - self.scroll_offset
            if y + self.item_alto < self.rect.top or y > self.rect.bottom:
                continue

            color = self.colores_picker[indice % len(self.colores_picker)]
            cx = self.rect.x + 10
            cy = y + self.item_alto // 2

            # Fondo alternado por fila
            if indice % 2 == 0:
                sup = pygame.Surface((self.rect.w - 20, self.item_alto - 4), pygame.SRCALPHA)
                sup.fill((255, 255, 255, 8))
                pantalla.blit(sup, (self.rect.x + 10, y + 2))

            # Ícono del picker
            pygame.draw.circle(pantalla, (16, 22, 34), (cx, cy), 6)
            pygame.draw.circle(pantalla, color, (cx, cy), 4)

            # Nombre del picker
            img = self.fuente.render(picker["id"], True, cfg.TEXTO_PRINCIPAL)
            pantalla.blit(img, (cx + 14, y + 4))

            # Botón eliminar (pequeña X)
            btn_elim = self._rect_eliminar(indice)
            pygame.draw.rect(pantalla, (90, 96, 110), btn_elim, border_radius=4)
            pygame.draw.rect(pantalla, cfg.ROJO, btn_elim, 1, border_radius=4)
            m = 4
            pygame.draw.line(
                pantalla, (255, 255, 255),
                (btn_elim.x + m, btn_elim.y + m),
                (btn_elim.right - m, btn_elim.bottom - m), 2,
            )
            pygame.draw.line(
                pantalla, (255, 255, 255),
                (btn_elim.right - m, btn_elim.y + m),
                (btn_elim.x + m, btn_elim.bottom - m), 2,
            )

        pantalla.set_clip(None)

        # Barra de scroll si es necesario
        if self.scroll_max > 0:
            x_scroll = self.rect.right - 6
            alto_barra = max(20, int(self.rect.h * self.rect.h / (self.rect.h + self.scroll_max)))
            y_scroll = self.rect.top + int(self.scroll_offset / self.scroll_max * (self.rect.h - alto_barra))
            pygame.draw.rect(pantalla, (80, 88, 104), (x_scroll, y_scroll, 6, alto_barra), border_radius=3)


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
