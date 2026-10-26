"""Widgets simples: Boton y Alerta (una sola definición)."""

import pygame

from . import config as cfg


class Boton:

    def __init__(self, nombre, texto, x, y, ancho, alto, color=None):
        self.nombre = nombre
        self.texto = texto
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.color = color


class Alerta:
    """Cartel que aparece arriba y se cierra solo (o con un clic)."""

    def __init__(self, f_titulo, f_texto):
        self.f_titulo = f_titulo
        self.f_texto = f_texto
        self.titulo = ""
        self.lineas = []
        self.color = cfg.COLOR_ALERTA["Aviso"]
        self.restante = 0.0
        self.rect = pygame.Rect(0, 0, 0, 0)

    def mostrar(self, titulo, mensaje):
        self.titulo = titulo
        self.color = cfg.COLOR_ALERTA.get(titulo, cfg.COLOR_ALERTA["Aviso"])
        self.lineas = self._envolver(mensaje, cfg.ANCHO_ALERTA - 40)
        self.restante = cfg.DURACION_ALERTA
        alto = 16 + 24 + len(self.lineas) * 20 + 12
        self.rect = pygame.Rect((cfg.ANCHO - cfg.ANCHO_ALERTA) // 2, 24, cfg.ANCHO_ALERTA, alto)

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
        pantalla.blit(titulo, (self.rect.x + 20, self.rect.y + 12))
        for i, linea in enumerate(self.lineas):
            img = self.f_texto.render(linea, True, (255, 255, 255))
            pantalla.blit(img, (self.rect.x + 20, self.rect.y + 40 + i * 20))


def dibujar_boton(pantalla, fuente, rect, texto, color=None, activo=False, habilitado=True):
    """Botón redondeado con resaltado al pasar el mouse; lo usan el panel y la pantalla de generar."""
    mx, my = pygame.mouse.get_pos()
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