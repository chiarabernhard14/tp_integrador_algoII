"""Conversión entre celdas del warehouse y píxeles de la pantalla."""

import pygame


class Grilla:

    def __init__(self, ancho_celdas, alto_celdas, area):
        self.ancho_celdas = ancho_celdas
        self.alto_celdas = alto_celdas
        celda = min(area.w // ancho_celdas, area.h // alto_celdas)
        self.celda = max(6, celda)
        ancho_px = self.celda * ancho_celdas
        alto_px = self.celda * alto_celdas
        self.x = area.x + (area.w - ancho_px) // 2
        self.y = area.y + (area.h - alto_px) // 2

    def centro(self, x, y):
        px = self.x + x * self.celda + self.celda / 2
        py = self.y + (self.alto_celdas - 1 - y) * self.celda + self.celda / 2
        return int(px), int(py)

    def rect(self, x, y, ancho, alto):
        izq = self.x + x * self.celda
        arriba = self.y + (self.alto_celdas - (y + alto)) * self.celda
        return pygame.Rect(int(izq), int(arriba), ancho * self.celda, alto * self.celda)

    def celda_en(self, mx, my):
        gx = (mx - self.x) // self.celda
        gy = (my - self.y) // self.celda
        if 0 <= gx < self.ancho_celdas and 0 <= gy < self.alto_celdas:
            return int(gx), int(self.alto_celdas - 1 - gy)
        return None