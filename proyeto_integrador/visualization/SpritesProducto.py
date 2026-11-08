"""Cartones de los productos sobre los racks (sprites con degradado y cinta).

Tres estados: "normal" (stock que no se toca), "pendiente" (a recoger, naranja vivo) y
"recogido" (verde con tilde). Se dibujan en alta resolución, se reducen con suavizado y
se guardan en caché.
"""

import pygame

ESCALA = 4

# (color claro, color oscuro, borde)
ESTADOS = {
    "normal": ((184, 152, 108), (132, 104, 72), (78, 58, 38)),
    "pendiente": ((255, 190, 100), (240, 120, 32), (255, 240, 214)),
    "recogido": ((92, 214, 160), (30, 128, 94), (52, 211, 153)),
}


def _degradado(ancho, alto, inicio, fin):
    sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    for fila in range(alto):
        t = fila / max(1, alto - 1)
        color = (int(inicio[0] + (fin[0] - inicio[0]) * t),
                 int(inicio[1] + (fin[1] - inicio[1]) * t),
                 int(inicio[2] + (fin[2] - inicio[2]) * t), 255)
        pygame.draw.line(sup, color, (0, fila), (ancho, fila))
    return sup


class FabricaProductos:

    def __init__(self):
        self.cache = {}

    def obtener(self, lado, estado):
        clave = (lado, estado)
        sprite = self.cache.get(clave)
        if sprite is None:
            sprite = self._crear(lado, estado)
            self.cache[clave] = sprite
        return sprite

    def _crear(self, lado, estado):
        claro, oscuro, borde = ESTADOS[estado]
        n = lado * ESCALA
        sup = pygame.Surface((n, n), pygame.SRCALPHA)
        radio = int(n * 0.16)
        caja = pygame.Rect(int(n * 0.04), int(n * 0.04), int(n * 0.92), int(n * 0.92))

        pygame.draw.rect(sup, borde, caja, border_radius=radio)
        interior = caja.inflate(-int(n * 0.12), -int(n * 0.12))
        relleno = _degradado(interior.w, interior.h, claro, oscuro)
        mascara = pygame.Surface(interior.size, pygame.SRCALPHA)
        pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=int(radio * 0.7))
        relleno.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        sup.blit(relleno, interior.topleft)

        # cinta y pliegue de la tapa (el recogido lleva solo el tilde)
        if estado != "recogido":
            pygame.draw.line(sup, (250, 236, 200), (n // 2, interior.top), (n // 2, interior.bottom),
                             max(2, int(n * 0.12)))
            pygame.draw.line(sup, _mezclar(oscuro, 0.75), (interior.left + 2, interior.top + int(n * 0.2)),
                             (interior.right - 2, interior.top + int(n * 0.2)), max(2, int(n * 0.04)))
        # reflejo
        brillo = pygame.Surface(interior.size, pygame.SRCALPHA)
        pygame.draw.ellipse(brillo, (255, 255, 255, 70),
                            pygame.Rect(int(interior.w * 0.1), int(interior.h * 0.04),
                                        int(interior.w * 0.55), int(interior.h * 0.2)))
        sup.blit(brillo, interior.topleft)

        if estado == "recogido":
            tilde = [(int(n * 0.28), int(n * 0.54)), (int(n * 0.44), int(n * 0.70)),
                     (int(n * 0.74), int(n * 0.34))]
            pygame.draw.lines(sup, (10, 60, 44), False, tilde, max(3, int(n * 0.14)))
            pygame.draw.lines(sup, (240, 255, 248), False, tilde, max(2, int(n * 0.08)))
        return pygame.transform.smoothscale(sup, (lado, lado))

    def aura(self, lado, intensidad):
        clave = ("aura", lado, intensidad)
        sprite = self.cache.get(clave)

        if sprite is None:
            margen = max(2, lado // 3)
            tamano = lado + margen * 2

            sprite = pygame.Surface(
                (tamano, tamano),
                pygame.SRCALPHA
            )

            centro = tamano // 2
            radio = lado // 2 + margen // 2

            alpha = max(0, min(110, intensidad * 28))

            for i in range(4, 0, -1):
                radio_actual = radio + i * 2
                alpha_actual = alpha // (i + 1)

                pygame.draw.circle(
                    sprite,
                    (255, 170, 65, alpha_actual),
                    (centro, centro),
                    radio_actual
                )

            self.cache[clave] = sprite

        return sprite

def _mezclar(color, factor):
    return (int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))