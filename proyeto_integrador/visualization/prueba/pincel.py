"""Fuentes y primitivas de dibujo compartidas por todas las vistas."""

import math

import pygame
from pygame import gfxdraw

from . import config as cfg


class Fuentes:

    def __init__(self):
        nombres = cfg.FUENTES
        self.titulo = pygame.font.SysFont(nombres, 30, bold=True)
        self.sub = pygame.font.SysFont(nombres, 20, bold=True)
        self.normal = pygame.font.SysFont(nombres, 16)
        self.negrita = pygame.font.SysFont(nombres, 16, bold=True)
        self.chico = pygame.font.SysFont(nombres, 13)
        self.mini = pygame.font.SysFont(nombres, 11, bold=True)
        self.alerta_titulo = pygame.font.SysFont(nombres, 24, bold=True)
        self.alerta_texto = pygame.font.SysFont(nombres, 19)


class Pincel:

    def __init__(self, pantalla):
        self.pantalla = pantalla

    def texto(self, texto, fuente, color, x, y, ancla="izq"):
        img = fuente.render(texto, True, color)
        rect = img.get_rect()
        if ancla == "izq":
            rect.topleft = (x, y)
        elif ancla == "centro":
            rect.midtop = (x, y)
        elif ancla == "der":
            rect.topright = (x, y)
        else:
            rect.center = (x, y)
        self.pantalla.blit(img, rect)
        return rect.width

    def recortar(self, texto, fuente, ancho):
        if fuente.size(texto)[0] <= ancho:
            return texto
        while len(texto) > 1 and fuente.size(texto + "...")[0] > ancho:
            texto = texto[:-1]
        return texto + "..."

    def circulo(self, x, y, radio, color):
        gfxdraw.filled_circle(self.pantalla, x, y, radio, color)
        gfxdraw.aacircle(self.pantalla, x, y, radio, color)

    def circulo_alfa(self, x, y, radio, color, alfa):
        sup = pygame.Surface((radio * 2 + 2, radio * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(sup, (color[0], color[1], color[2], alfa), (radio + 1, radio + 1), radio)
        self.pantalla.blit(sup, (x - radio - 1, y - radio - 1))

    def anillo(self, x, y, radio, color, ancho=2):
        for i in range(ancho):
            gfxdraw.aacircle(self.pantalla, x, y, radio - i, color)

    def rect_alfa(self, x, y, w, h, color, radio=8):
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(sup, color, (0, 0, w, h), border_radius=radio)
        self.pantalla.blit(sup, (x, y))

    def linea_punteada(self, x1, y1, x2, y2, color, ancho=2, largo=8, hueco=6):
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        ux = dx / dist
        uy = dy / dist
        pos = 0.0
        while pos < dist:
            fin = min(pos + largo, dist)
            pygame.draw.line(self.pantalla, color,
                             (x1 + ux * pos, y1 + uy * pos),
                             (x1 + ux * fin, y1 + uy * fin), ancho)
            pos += largo + hueco

    def rect_punteado(self, x, y, w, h, color):
        self.linea_punteada(x, y, x + w, y, color)
        self.linea_punteada(x + w, y, x + w, y + h, color)
        self.linea_punteada(x + w, y + h, x, y + h, color)
        self.linea_punteada(x, y + h, x, y, color)