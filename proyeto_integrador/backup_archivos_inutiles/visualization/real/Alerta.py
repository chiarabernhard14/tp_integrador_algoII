"""Cartel de alerta (pygame): más grande, con una cruz para cerrar.

Se cierra con la cruz, con ESC (llamando a cerrar()) o solo a los segundos.
Mientras el mouse está encima, la cuenta regresiva se detiene para poder leerlo.
"""

import pygame

ANCHO_VENTANA = 1280

ANCHO_ALERTA = 800
DURACION_ALERTA = 8.0

COLOR_ALERTA = {
    "ValueError": (185, 40, 40),
    "TypeError": (200, 100, 20),
    "Aviso": (170, 130, 10),
    "Listo": (22, 130, 90),
}

BLANCO = (255, 255, 255)


class Alerta:

    def __init__(self, f_titulo, f_texto):
        self.f_titulo = f_titulo
        self.f_texto = f_texto
        self.titulo = ""
        self.lineas = []
        self.color = COLOR_ALERTA["Aviso"]
        self.restante = 0.0
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.rect_cerrar = pygame.Rect(0, 0, 0, 0)

    def mostrar(self, titulo, mensaje):
        self.titulo = titulo
        self.color = COLOR_ALERTA.get(titulo, COLOR_ALERTA["Aviso"])
        # Se deja lugar a la derecha para la cruz.
        self.lineas = self._envolver(mensaje, ANCHO_ALERTA - 28 - 90)
        self.restante = DURACION_ALERTA

        alto_titulo = self.f_titulo.get_linesize()
        alto_linea = self.f_texto.get_linesize() + 4
        alto = 22 + alto_titulo + 10 + len(self.lineas) * alto_linea + 24

        self.rect = pygame.Rect((ANCHO_VENTANA - ANCHO_ALERTA) // 2, 24, ANCHO_ALERTA, alto)
        self.rect_cerrar = pygame.Rect(self.rect.right - 20 - 40, self.rect.y + 16, 40, 40)

    def cerrar(self):
        self.restante = 0.0

    def visible(self):
        return self.restante > 0.0

    def actualizar(self, dt):
        """Cuenta regresiva; se detiene mientras el mouse está sobre el cartel."""
        if not self.visible():
            return
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            return
        self.restante = max(0.0, self.restante - dt)

    def clic(self, pos):
        """Cierra solo si se hizo clic en la cruz. Devuelve True si cerró."""
        if self.visible() and self.rect_cerrar.collidepoint(pos):
            self.cerrar()
            return True
        return False

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

        # Sombra
        sombra = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 90), (0, 0, self.rect.width, self.rect.height),
                         border_radius=16)
        pantalla.blit(sombra, (self.rect.x, self.rect.y + 6))

        pygame.draw.rect(pantalla, self.color, self.rect, border_radius=16)
        pygame.draw.rect(pantalla, BLANCO, self.rect, 2, border_radius=16)

        alto_titulo = self.f_titulo.get_linesize()
        alto_linea = self.f_texto.get_linesize() + 4

        titulo = self.f_titulo.render(self.titulo, True, BLANCO)
        pantalla.blit(titulo, (self.rect.x + 28, self.rect.y + 22))

        for i, linea in enumerate(self.lineas):
            img = self.f_texto.render(linea, True, BLANCO)
            pantalla.blit(img, (self.rect.x + 28, self.rect.y + 22 + alto_titulo + 10 + i * alto_linea))

        self._dibujar_cruz(pantalla)

    def _dibujar_cruz(self, pantalla):
        sobre = self.rect_cerrar.collidepoint(pygame.mouse.get_pos())
        if sobre:
            relleno = (255, 255, 255)
            trazo = self.color
        else:
            relleno = tuple(min(255, c + 45) for c in self.color)
            trazo = BLANCO

        pygame.draw.rect(pantalla, relleno, self.rect_cerrar, border_radius=12)
        pygame.draw.rect(pantalla, BLANCO, self.rect_cerrar, 2, border_radius=12)

        r = self.rect_cerrar
        margen = 12
        pygame.draw.line(pantalla, trazo, (r.x + margen, r.y + margen),
                         (r.right - margen, r.bottom - margen), 4)
        pygame.draw.line(pantalla, trazo, (r.right - margen, r.y + margen),
                         (r.x + margen, r.bottom - margen), 4)