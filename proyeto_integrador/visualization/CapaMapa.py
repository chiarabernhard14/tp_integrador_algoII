"""Capa estática del warehouse: piso, pasillos, despacho, puertas y racks.

Se dibuja una sola vez cada vez que cambia el escenario (VistaMapa.recalcular) y después
es un único blit por cuadro. Lo que se mueve o cambia (productos, pickers, recorridos)
se dibuja encima, en VistaMapa.
"""

import pygame

from . import Config as cfg
from .Pincel import Pincel

PISO_A = (64, 70, 84)
PISO_B = (68, 74, 88)
PASILLO_A = (116, 122, 136)
PASILLO_B = (111, 117, 131)
CHEVRON = (184, 190, 205)
RACK_FONDO = (18, 40, 84)
RACK_FONDO_BAJO = (12, 28, 62)
RACK_VIGA = (255, 159, 67)
RACK_DIVISOR = (8, 20, 46)
RACK_MARCO = (59, 130, 246)
RACK_BRILLO = (132, 184, 255)
DESPACHO_ARRIBA = (38, 98, 90)
DESPACHO_ABAJO = (30, 78, 76)
DESPACHO_RAYA = (52, 128, 114)
DESPACHO_BORDE = (118, 232, 196)
ESQUINERO = (250, 204, 21)
PUERTA_MARCO = (30, 36, 48)
PUERTA_ARRIBA = (218, 225, 236)
PUERTA_ABAJO = (122, 133, 152)
PUERTA_NERVIO = (96, 106, 126)
PUERTA_LUZ = (110, 240, 170)
TOPE_NEGRO = (24, 28, 36)
BORDE_MAPA = (58, 61, 69)


def _degradado(ancho, alto, inicio, fin, horizontal=False):
    sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    pasos = ancho if horizontal else alto
    for i in range(pasos):
        t = i / max(1, pasos - 1)
        color = (int(inicio[0] + (fin[0] - inicio[0]) * t),
                 int(inicio[1] + (fin[1] - inicio[1]) * t),
                 int(inicio[2] + (fin[2] - inicio[2]) * t), 255)
        if horizontal:
            pygame.draw.line(sup, color, (i, 0), (i, alto))
        else:
            pygame.draw.line(sup, color, (0, i), (ancho, i))
    return sup


def _rect_degradado(sup, rect, inicio, fin, radio, horizontal=False):
    relleno = _degradado(rect.w, rect.h, inicio, fin, horizontal)
    mascara = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=radio)
    relleno.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    sup.blit(relleno, rect.topleft)


class CapaMapa:

    def __init__(self, fuentes):
        self.fuentes = fuentes
        self.superficie = None
        self.origen = (0, 0)

    def construir(self, grilla, warehouse):
        total = pygame.Surface((cfg.ANCHO, cfg.ALTO), pygame.SRCALPHA)
        self.total = total
        self.pincel = Pincel(total)
        self.g = grilla
        self.wh = warehouse

        self._resplandor()
        self._piso()
        self._pasillos()
        self._despacho()
        self._borde()
        self._puertas()
        self._racks()

        region = grilla.rect(0, 0, grilla.ancho_celdas, grilla.alto_celdas).inflate(48, 48)
        region = region.clip(total.get_rect())
        self.superficie = total.subsurface(region).copy().convert_alpha()
        self.origen = region.topleft
        self.total = self.pincel = self.g = self.wh = None   # se libera lo temporal

    def dibujar(self, pantalla):
        pantalla.blit(self.superficie, self.origen)

    # ---------- piso y pasillos ----------

    def _resplandor(self):
        """Halo oscuro y discreto alrededor del warehouse."""
        g = self.g
        base = g.rect(0, 0, g.ancho_celdas, g.alto_celdas)
        for i in range(4, 0, -1):
            r = base.inflate(i * 4, i * 4)
            self.pincel.rect_alfa(r.x, r.y, r.w, r.h, (18, 20, 25, 12), 10 + i * 2)

    def _piso(self):
        g = self.g
        for x in range(g.ancho_celdas):
            for y in range(g.alto_celdas):
                color = PISO_A if (x + y) % 2 == 0 else PISO_B
                pygame.draw.rect(self.total, color, g.rect(x, y, 1, 1))

    def _pasillos(self):
        g = self.g
        # La consigna considera pasillo toda celda libre que no sea rack,
        # despacho o puerta, aunque el editor no tenga un pasillo explícito.
        ocupadas = set()
        for grupo in (self.wh.racks, self.wh.zonas_despacho):
            for elemento in grupo.values():
                ocupadas.update(elemento.cells())
        # Las puertas son puntos, no elementos rectangulares, y por eso no
        # implementan cells(). Cada puerta ocupa únicamente su celda.
        ocupadas.update(tuple(puerta.ubicacion) for puerta in self.wh.puertas.values())
        for x in range(g.ancho_celdas):
            for y in range(g.alto_celdas):
                if (x, y) in ocupadas:
                    continue
                color = PASILLO_A if (x + y) % 2 == 0 else PASILLO_B
                pygame.draw.rect(self.total, color, g.rect(x, y, 1, 1))
        s = max(3, int(g.celda * 0.17))
        for pasillo in self.wh.pasillos.values():
            if pasillo.sentido not in ("N", "S", "E", "O"):
                continue
            for x, y in pasillo.cells():
                cx, cy = g.centro(x, y)
                self._chevron(cx, cy, pasillo.sentido, s, CHEVRON)

    def _chevron(self, cx, cy, sentido, s, color):
        h = int(s * 0.65)
        if sentido == "N":
            puntos = [(-s, h), (0, -h), (s, h)]
        elif sentido == "S":
            puntos = [(-s, -h), (0, h), (s, -h)]
        elif sentido == "E":
            puntos = [(-h, -s), (h, 0), (-h, s)]
        else:
            puntos = [(h, -s), (-h, 0), (h, s)]
        trazo = [(cx + dx, cy + dy) for dx, dy in puntos]
        pygame.draw.lines(self.total, color, False, trazo, 2)

    # ---------- despacho y puertas ----------

    def _despacho(self):
        g = self.g
        for zona in self.wh.zonas_despacho.values():
            x0, y0 = zona.ubicacion
            x1, y1 = x0 + zona.ancho, y0 + zona.alto
            puerta = next((p for p in self.wh.puertas.values()
                           if getattr(zona, "puerta_id", None) == p.id), None)
            if puerta is not None:
                px, py = puerta.ubicacion
                if py == y0 - 1:
                    y0 -= 1
                elif py == y1:
                    y1 += 1
                elif px == x0 - 1:
                    x0 -= 1
                elif px == x1:
                    x1 += 1
            # El área verde llega hasta la celda del portón; el portón se
            # superpone después sobre el borde exterior del warehouse.
            rect = g.rect(x0, y0, x1 - x0, y1 - y0)
            self.total.blit(_degradado(rect.w, rect.h, DESPACHO_ARRIBA, DESPACHO_ABAJO), rect.topleft)
            rayas = pygame.Surface(rect.size, pygame.SRCALPHA)
            for k in range(-rect.h, rect.w, 20):
                pygame.draw.line(rayas, (*DESPACHO_RAYA, 120), (k, rect.h), (k + rect.h, 0), 2)
            self.total.blit(rayas, rect.topleft)
            pygame.draw.rect(self.total, DESPACHO_BORDE, rect, 2)
            self._esquineros(rect)

    def _esquineros(self, rect):
        """Marcas amarillas en las cuatro esquinas, como las de un área señalizada."""
        largo = max(8, min(16, rect.width // 5, rect.height // 3))
        esquinas = (
            (rect.left, rect.top, 1, 1),
            (rect.right - 1, rect.top, -1, 1),
            (rect.left, rect.bottom - 1, 1, -1),
            (rect.right - 1, rect.bottom - 1, -1, -1),
        )
        for x, y, sx, sy in esquinas:
            pygame.draw.line(self.total, ESQUINERO, (x, y), (x + sx * largo, y), 4)
            pygame.draw.line(self.total, ESQUINERO, (x, y), (x, y + sy * largo), 4)

    def _puertas(self):
        """Portón de muelle metido en el muro: panel de acero, topes de seguridad y luz de estado."""
        g = self.g
        for puerta in self.wh.puertas.values():
            px, py = puerta.ubicacion[0], puerta.ubicacion[1]
            celda = g.rect(px, py, 1, 1)
            zona = next((z for z in self.wh.zonas_despacho.values()
                         if getattr(z, "puerta_id", None) == puerta.id), None)
            adentro = self._hacia_zona(puerta, zona) or self._hacia_adentro(px, py)
            horizontal = adentro in ("N", "S")
            largo = int(celda.w * 0.96)
            grosor = max(10, int(celda.w * 0.46))
            r = pygame.Rect(0, 0, largo if horizontal else grosor, grosor if horizontal else largo)
            # El símbolo cruza la línea del muro en la celda exterior, en vez
            # de quedar centrado dentro del área de despacho.
            centro_borde = self._centro_perimetro(celda, px, py)
            r.center = centro_borde
            self._porton(r, horizontal, adentro)

    @staticmethod
    def _hacia_zona(puerta, zona):
        if zona is None:
            return None
        zx, zy = zona.ubicacion
        px, py = puerta.ubicacion
        if py == zy - 1:
            return "N"
        if py == zy + zona.alto:
            return "S"
        if px == zx - 1:
            return "E"
        if px == zx + zona.ancho:
            return "O"
        return None

    def _centro_perimetro(self, celda, px, py):
        """Centro del portón sobre el muro exterior correspondiente."""
        if py == 0:
            return celda.centerx, celda.bottom
        if py == self.g.alto_celdas - 1:
            return celda.centerx, celda.top
        if px == 0:
            return celda.left, celda.centery
        return celda.right, celda.centery

    def _porton(self, r, horizontal, adentro):
        self.pincel.rect_alfa(r.x + 2, r.y + 3, r.w, r.h, (0, 0, 0, 100), 5)
        pygame.draw.rect(self.total, PUERTA_MARCO, r.inflate(4, 4), border_radius=5)
        _rect_degradado(self.total, r, PUERTA_ARRIBA, PUERTA_ABAJO, 4, horizontal=not horizontal)

        tope = max(5, int((r.w if horizontal else r.h) * 0.18))
        # nervaduras a lo largo del portón
        for k in (1, 2):
            if horizontal:
                y = r.top + r.h * k // 3
                pygame.draw.line(self.total, PUERTA_NERVIO, (r.left + tope + 2, y), (r.right - tope - 2, y), 1)
            else:
                x = r.left + r.w * k // 3
                pygame.draw.line(self.total, PUERTA_NERVIO, (x, r.top + tope + 2), (x, r.bottom - tope - 2), 1)

        # topes de seguridad amarillos y negros en los dos extremos
        if horizontal:
            topes = (pygame.Rect(r.left, r.top, tope, r.h), pygame.Rect(r.right - tope, r.top, tope, r.h))
        else:
            topes = (pygame.Rect(r.left, r.top, r.w, tope), pygame.Rect(r.left, r.bottom - tope, r.w, tope))
        for bloque in topes:
            pygame.draw.rect(self.total, ESQUINERO, bloque, border_radius=2)
            self.total.set_clip(bloque)
            paso = 5
            for k in range(-bloque.h, bloque.w + bloque.h, paso * 2):
                pygame.draw.line(self.total, TOPE_NEGRO, (bloque.left + k, bloque.bottom),
                                 (bloque.left + k + bloque.h, bloque.top), 2)
            self.total.set_clip(None)

        # luz de estado del lado de adentro
        ux, uy = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "O": (-1, 0)}[adentro]
        luz = (r.centerx + ux * int(min(r.w, r.h) * 0.2), r.centery + uy * int(min(r.w, r.h) * 0.2))
        self.pincel.circulo_alfa(luz[0], luz[1], 5, PUERTA_LUZ, 90)
        pygame.draw.circle(self.total, PUERTA_LUZ, luz, 2)

    def _hacia_adentro(self, px, py):
        g = self.g
        if py == 0:
            return "N"
        if py == g.alto_celdas - 1:
            return "S"
        if px == 0:
            return "E"
        return "O"

    # ---------- racks ----------

    def _racks(self):
        g = self.g
        for rack in self.wh.racks.values():
            x0, y0 = rack.ubicacion
            r = g.rect(x0, y0, rack.ancho, rack.alto).inflate(-2, -2)
            self.pincel.rect_alfa(r.x + 3, r.y + 5, r.w, r.h, (0, 0, 0, 95), 6)
        for rack in self.wh.racks.values():
            self._rack(rack)

    def _rack(self, rack):
        g = self.g
        x0, y0 = rack.ubicacion
        base = g.rect(x0, y0, rack.ancho, rack.alto)
        r = base.inflate(-2, -2)
        pygame.draw.rect(self.total, RACK_FONDO, r, border_radius=5)
        pygame.draw.rect(self.total, RACK_FONDO_BAJO, (r.x + 2, r.centery, r.w - 4, r.h // 2 - 2),
                         border_radius=4)
        if rack.alto >= rack.ancho:
            for k in range(1, rack.alto):
                y = base.top + k * g.celda
                pygame.draw.line(self.total, RACK_VIGA, (r.left + 3, y), (r.right - 4, y), 2)
            if rack.ancho >= 2:
                pygame.draw.line(self.total, RACK_DIVISOR, (base.centerx, r.top + 3),
                                 (base.centerx, r.bottom - 4), 2)
        else:
            for k in range(1, rack.ancho):
                x = base.left + k * g.celda
                pygame.draw.line(self.total, RACK_VIGA, (x, r.top + 3), (x, r.bottom - 4), 2)
            pygame.draw.line(self.total, RACK_DIVISOR, (r.left + 3, base.centery),
                             (r.right - 4, base.centery), 2)
        pygame.draw.rect(self.total, RACK_MARCO, r, 2, border_radius=5)
        pygame.draw.line(self.total, RACK_BRILLO, (r.left + 6, r.top + 2), (r.right - 7, r.top + 2), 1)

    def _borde(self):
        g = self.g
        rect = g.rect(0, 0, g.ancho_celdas, g.alto_celdas)
        pygame.draw.rect(self.total, BORDE_MAPA, rect.inflate(2, 2), 1, border_radius=8)
