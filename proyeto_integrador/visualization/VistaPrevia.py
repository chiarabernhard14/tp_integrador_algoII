"""Vista previa del escenario automático.

Dibuja el warehouse que generaría generar_escenario con los parámetros actuales
(estantes, pasillos, alto, productos, pickers y modo de ubicación). No arma el
grafo ni valida alcanzabilidad, así que se redibuja apenas cambia un valor y
escala a cualquier tamaño de mapa.
"""

import pygame

from simulation.Scenario import generar_vista_previa

from . import CapaMapa as mapa
from . import Config as cfg

COLOR_CAJA = (214, 168, 102)
COLOR_CAJA_BORDE = (118, 84, 44)


class VistaPreviaEscenario:

    def __init__(self, pincel, fuentes):
        self.pincel = pincel
        self.pantalla = pincel.pantalla
        self.fuentes = fuentes
        self.clave = None
        self.datos = None
        self.error = ""
        # Geometría del último dibujo (celda en píxeles y origen del mapa).
        self.ancho_x = 1
        self.largo_y = 1
        self.celda = 1.0
        self.x0 = 0.0
        self.y0 = 0.0

    def actualizar(self, estantes, pasillos_horizontales, alto_rack, productos,
                   pickers, modo_ubicacion, peso_max_zona_kg=500.0):
        """Regenera la vista previa solo si cambió algún parámetro."""
        clave = (estantes, pasillos_horizontales, alto_rack, productos,
                 pickers, modo_ubicacion, peso_max_zona_kg)
        if clave == self.clave:
            return
        self.clave = clave
        try:
            self.datos = generar_vista_previa(
                *clave[:6], peso_max_zona_kg=peso_max_zona_kg
            )
            self.error = ""
        except ValueError as error:
            self.datos = None
            self.error = str(error)

    def resumen(self):
        if self.datos is None:
            return ""
        warehouse = self.datos["warehouse"]
        dimensiones = warehouse["dimensiones"]
        peso_zona = warehouse["zonas_despacho"][0]["peso_max_kg"]
        return (f"{dimensiones['ancho_x']} × {dimensiones['largo_y']} celdas · "
                f"{len(warehouse['racks'])} estantes · "
                f"{len(warehouse['zonas_despacho'])} zonas · "
                f"{peso_zona:g} kg por zona · "
                f"{len(self.datos['productos'])} productos · "
                f"{len(self.datos['pickers'])} pickers")

    # ---------- geometría ----------

    def _rect(self, x, y, ancho, alto):
        """Rectángulo en pantalla de una región de celdas (y=0 queda abajo)."""
        izquierda = round(self.x0 + x * self.celda)
        derecha = round(self.x0 + (x + ancho) * self.celda)
        arriba = round(self.y0 + (self.largo_y - (y + alto)) * self.celda)
        abajo = round(self.y0 + (self.largo_y - y) * self.celda)
        return pygame.Rect(izquierda, arriba, max(1, derecha - izquierda),
                           max(1, abajo - arriba))

    def _centro(self, x, y):
        return (int(self.x0 + (x + 0.5) * self.celda),
                int(self.y0 + (self.largo_y - y - 0.5) * self.celda))

    # ---------- dibujo ----------

    def dibujar(self, area):
        if self.datos is None:
            self.pincel.texto(self.error or "Sin vista previa", self.fuentes.normal,
                              cfg.ROJO, area.centerx, area.centery, "cc")
            return
        dimensiones = self.datos["warehouse"]["dimensiones"]
        self.ancho_x = dimensiones["ancho_x"]
        self.largo_y = dimensiones["largo_y"]
        self.celda = min(area.w / self.ancho_x, area.h / self.largo_y)
        self.x0 = area.x + (area.w - self.celda * self.ancho_x) / 2
        self.y0 = area.y + (area.h - self.celda * self.largo_y) / 2

        suelo = self._rect(0, 0, self.ancho_x, self.largo_y)
        pygame.draw.rect(self.pantalla, mapa.PASILLO_A, suelo)
        self._dibujar_racks()
        self._dibujar_zonas()
        self._dibujar_puertas()
        self._dibujar_productos()
        self._dibujar_pickers()
        pygame.draw.rect(self.pantalla, cfg.BORDE, suelo.inflate(2, 2), 2)

    def _dibujar_racks(self):
        for rack in self.datos["warehouse"]["racks"]:
            ubicacion = rack["ubicacion"]
            r = self._rect(ubicacion["x"], ubicacion["y"], rack["ancho"], rack["alto"])
            if self.celda >= 6:
                r = r.inflate(-2, -2)
            pygame.draw.rect(self.pantalla, mapa.RACK_FONDO, r)
            if self.celda >= 8:
                for k in range(1, rack["alto"]):
                    y = r.bottom - round(k * self.celda)
                    pygame.draw.line(self.pantalla, mapa.RACK_VIGA,
                                     (r.left + 2, y), (r.right - 3, y), 1)
            pygame.draw.rect(self.pantalla, mapa.RACK_MARCO, r, 1 if self.celda < 10 else 2)

    def _dibujar_zonas(self):
        fuente = self.fuentes.mini
        for numero, zona in enumerate(self.datos["warehouse"]["zonas_despacho"], 1):
            ubicacion = zona["ubicacion"]
            r = self._rect(ubicacion["x"], ubicacion["y"], zona["ancho"], zona["alto"])
            pygame.draw.rect(self.pantalla, mapa.DESPACHO_ABAJO, r)
            pygame.draw.rect(self.pantalla, mapa.DESPACHO_BORDE, r, 2 if r.w > 8 else 1)
            if r.w >= 44 and r.h >= 16:
                self.pincel.texto(f"Zona {numero}", fuente, cfg.BLANCO_SUAVE,
                                  r.centerx, r.centery, "cc")

    def _dibujar_puertas(self):
        for puerta in self.datos["warehouse"]["puertas"]:
            ubicacion = puerta["ubicacion"]
            r = self._rect(ubicacion["x"], ubicacion["y"], 1, 1)
            interior = r.inflate(-r.w // 4, -r.h // 3)
            pygame.draw.rect(self.pantalla, mapa.PUERTA_ARRIBA, interior)
            pygame.draw.rect(self.pantalla, mapa.ESQUINERO, interior, 2)

    def _dibujar_productos(self):
        lado = max(2, int(self.celda * 0.55))
        for producto in self.datos["productos"]:
            ubicacion = producto["ubicacion"]
            caja = pygame.Rect(0, 0, lado, lado)
            caja.center = self._centro(ubicacion["x"], ubicacion["y"])
            pygame.draw.rect(self.pantalla, COLOR_CAJA, caja)
            if lado >= 6:
                pygame.draw.rect(self.pantalla, COLOR_CAJA_BORDE, caja, 1)

    def _dibujar_pickers(self):
        radio = max(3, int(self.celda * 0.38))
        for indice, picker in enumerate(self.datos["pickers"]):
            posicion = picker["posicion_inicial"]
            centro = self._centro(posicion["x"], posicion["y"])
            color = cfg.COLORES_PICKER[indice % len(cfg.COLORES_PICKER)]
            pygame.draw.circle(self.pantalla, (16, 22, 34), centro, radio + 1)
            pygame.draw.circle(self.pantalla, color, centro, radio)
