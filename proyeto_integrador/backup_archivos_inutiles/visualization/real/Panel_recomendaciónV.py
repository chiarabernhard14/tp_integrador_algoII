"""Panel (pygame) que muestra la recomendación de cantidad de pickers.

Es modal: mientras está visible, absorbe los clics. Solo sugiere; el botón
"Usar recomendado" es opcional y el usuario puede cerrarlo sin cambiar nada.
"""

import pygame

ANCHO_VENTANA = 1280
ALTO_VENTANA = 780

PANEL = (44, 48, 56)
TARJETA = (60, 65, 76)
BORDE = (90, 96, 110)
TEXTO = (226, 232, 245)
APAGADO = (139, 150, 176)
ACENTO = (88, 166, 255)
VERDE = (52, 211, 153)
AMARILLO = (250, 204, 21)
ROJO = (239, 68, 68)

ANCHO_PANEL = 660
MAX_FILAS = 8
ALTO_FILA = 26

COLUMNAS = (
    ("Pickers", 24),
    ("Ticks", 150),
    ("Pasos", 235),
    ("Esperas", 320),
    ("Bloq.", 415),
    ("Congestion", 490),
)


class PanelRecomendacion:

    def __init__(self, f_titulo, f_normal, f_chico, f_mini):
        self.f_titulo = f_titulo
        self.f_normal = f_normal
        self.f_chico = f_chico
        self.f_mini = f_mini

        self.resultado = None
        self.pickers_recomendados = []
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.boton_usar = pygame.Rect(0, 0, 0, 0)
        self.boton_cerrar = pygame.Rect(0, 0, 0, 0)

    # ---------- estado ----------

    def mostrar(self, resultado):
        self.resultado = resultado
        self.pickers_recomendados = list(resultado["pickers_recomendados"])

        filas = min(len(resultado["resultados"]), MAX_FILAS)
        alto = 150 + 30 + filas * ALTO_FILA + 90
        x = (ANCHO_VENTANA - ANCHO_PANEL) // 2
        y = (ALTO_VENTANA - alto) // 2
        self.rect = pygame.Rect(x, y, ANCHO_PANEL, alto)
        self.boton_cerrar = pygame.Rect(self.rect.right - 24 - 130, self.rect.bottom - 56, 130, 36)
        self.boton_usar = pygame.Rect(self.boton_cerrar.x - 12 - 190, self.rect.bottom - 56, 190, 36)

    def cerrar(self):
        self.resultado = None
        self.pickers_recomendados = []

    def visible(self):
        return self.resultado is not None

    def clic(self, pos):
        """Devuelve 'usar', 'cerrar' o '' (el panel absorbe cualquier clic)."""
        if not self.visible():
            return ""
        if self.resultado["recomendado"] is not None and self.boton_usar.collidepoint(pos):
            return "usar"
        if self.boton_cerrar.collidepoint(pos):
            self.cerrar()
            return "cerrar"
        return ""

    # ---------- dibujo ----------

    def _texto(self, pantalla, texto, fuente, color, x, y, ancla="izq"):
        img = fuente.render(texto, True, color)
        rect = img.get_rect()
        if ancla == "izq":
            rect.topleft = (x, y)
        elif ancla == "der":
            rect.topright = (x, y)
        else:
            rect.center = (x, y)
        pantalla.blit(img, rect)

    def _recortar(self, texto, fuente, ancho):
        if fuente.size(texto)[0] <= ancho:
            return texto
        while len(texto) > 1 and fuente.size(texto + "...")[0] > ancho:
            texto = texto[:-1]
        return texto + "..."

    def _boton(self, pantalla, rect, texto, color):
        mx, my = pygame.mouse.get_pos()
        relleno = tuple(min(255, v + 30) for v in color) if rect.collidepoint((mx, my)) else color
        pygame.draw.rect(pantalla, relleno, rect, border_radius=10)
        pygame.draw.rect(pantalla, (160, 170, 190), rect, 2, border_radius=10)
        self._texto(pantalla, texto, self.f_normal, (255, 255, 255), rect.centerx, rect.centery, "cc")

    def dibujar(self, pantalla):
        if not self.visible():
            return

        velo = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 150))
        pantalla.blit(velo, (0, 0))

        pygame.draw.rect(pantalla, PANEL, self.rect, border_radius=18)
        pygame.draw.rect(pantalla, BORDE, self.rect, 2, border_radius=18)

        r = self.resultado
        x0 = self.rect.x
        y0 = self.rect.y

        self._texto(pantalla, "RECOMENDACION DE PICKERS", self.f_titulo, ACENTO, x0 + 24, y0 + 18)
        self._texto(
            pantalla,
            f"Waves: {r['waves']} (maximo de pickers)   |   Configurados: {r['pickers_configurados']}",
            self.f_chico, APAGADO, x0 + 24, y0 + 54)

        if r["recomendado"] is not None:
            self._texto(pantalla, f"Recomendado: {r['recomendado']} pickers", self.f_titulo,
                        VERDE, x0 + 24, y0 + 78)
        else:
            self._texto(pantalla, "Ninguna cantidad termino sin bloqueos", self.f_normal,
                        ROJO, x0 + 24, y0 + 82)

        if r["tope_congestion"] is not None:
            tope = (f"Tope de congestion: {r['tope_congestion']} pickers "
                    f"(con mas, las esperas pasan del 10 % del tiempo)")
        else:
            tope = "Tope de congestion: no se pudo calcular"
        self._texto(pantalla, tope, self.f_chico, APAGADO, x0 + 24, y0 + 114)

        # Tabla
        y_tabla = y0 + 150
        for nombre, dx in COLUMNAS:
            self._texto(pantalla, nombre, self.f_mini, ACENTO, x0 + dx, y_tabla)

        hay_copias = False
        filas = r["resultados"][:MAX_FILAS]
        for i, fila in enumerate(filas):
            y = y_tabla + 22 + i * ALTO_FILA
            es_recomendado = fila["pickers"] == r["recomendado"]
            if es_recomendado:
                pygame.draw.rect(pantalla, (34, 90, 70),
                                 (x0 + 12, y - 3, ANCHO_PANEL - 24, ALTO_FILA - 2), border_radius=6)

            etiqueta = str(fila["pickers"])
            if fila["agregados"] > 0:
                etiqueta += f" (+{fila['agregados']})"
                hay_copias = True
            color = VERDE if es_recomendado else TEXTO
            self._texto(pantalla, etiqueta, self.f_chico, color, x0 + COLUMNAS[0][1], y)

            if not fila["viable"]:
                motivo = self._recortar(fila["motivo"], self.f_chico, ANCHO_PANEL - 200)
                self._texto(pantalla, motivo, self.f_chico, ROJO, x0 + COLUMNAS[1][1], y)
                continue

            valores = (
                str(fila["ticks"]), str(fila["pasos"]), str(fila["esperas"]),
                str(fila["bloqueados"]), f"{fila['congestion'] * 100:.0f} %",
            )
            for (nombre, dx), valor in zip(COLUMNAS[1:], valores):
                color_valor = color
                if nombre == "Bloq." and fila["bloqueados"] > 0:
                    color_valor = ROJO
                if nombre == "Congestion" and fila["congestion"] > 0.10:
                    color_valor = AMARILLO
                self._texto(pantalla, valor, self.f_chico, color_valor, x0 + dx, y)

        if hay_copias:
            self._texto(
                pantalla,
                "(+n) = pickers de prueba: copias de los tuyos que parten del despacho.",
                self.f_mini, APAGADO, x0 + 24, self.rect.bottom - 82)

        if r["recomendado"] is not None:
            self._boton(pantalla, self.boton_usar, "Usar recomendado", (22, 163, 74))
        self._boton(pantalla, self.boton_cerrar, "Cerrar", (75, 82, 99))