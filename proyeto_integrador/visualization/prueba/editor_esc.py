"""Editor de mapa con mouse. Solo dibuja y traduce entradas al ModeloEscenario."""

from types import SimpleNamespace

import pygame
import time

from simulation.simulationV.ModeloEsc import ModeloEscenario
from . import config as cfg
from .capa_mapa import CapaMapa
from .grilla import Grilla
from .sprites import FabricaSprites
from .sprites_producto import FabricaProductos

HERRAMIENTAS = {
    pygame.K_1: "rack", pygame.K_2: "despacho", pygame.K_3: "puerta",
    pygame.K_4: "pasillo", pygame.K_5: "picker", pygame.K_6: "borrar",
    pygame.K_7: "producto",
}
SENTIDOS = {pygame.K_n: "N", pygame.K_s: "S", pygame.K_e: "E",
            pygame.K_o: "O", pygame.K_a: "AMBOS"}


class _ElementoVista:
    """Un elemento del modelo con la forma que espera CapaMapa (como los del Warehouse)."""

    def __init__(self, d):
        self.id = d["id"]
        self.puerta_id = d.get("puerta_id")
        self.ubicacion = (d["ubicacion"]["x"], d["ubicacion"]["y"])
        self.ancho = d["ancho"]
        self.alto = d["alto"]
        self.sentido = d.get("sentido", "AMBOS")

    def cells(self):
        celdas = []
        for x in range(self.ubicacion[0], self.ubicacion[0] + self.ancho):
            for y in range(self.ubicacion[1], self.ubicacion[1] + self.alto):
                celdas.append((x, y))
        return celdas


def _elementos(lista):
    resultado = {}
    for d in lista:
        resultado[d["id"]] = _ElementoVista(d)
    return resultado


class CuadroProducto:
    """Mini cuadro modal para pedir z, stock y peso."""

    ETIQUETAS = ("Altura z", "Stock", "Peso (kg)")

    def __init__(self, fuentes, celda, z_inicial):
        self.fuente = fuentes.normal
        self.celda = celda
        self.valores = [str(z_inicial), "20", "1.0"]
        self.activo = 0
        self.rect = pygame.Rect(0, 0, 330, 226)
        # Centrado sobre el área del mapa, no sobre toda la pantalla.
        self.rect.center = (cfg.AREA_X + cfg.AREA_W // 2,
                            cfg.AREA_Y + cfg.AREA_H // 2)
        r = self.rect
        self.cajas = [pygame.Rect(r.x + 150, r.y + 46 + i * 34, 160, 28) for i in range(3)]
        self.boton_ok = pygame.Rect(r.x + 16, r.y + 172, 140, 36)
        self.boton_cancelar = pygame.Rect(r.x + 174, r.y + 172, 140, 36)

    def evento(self, ev):
        """Devuelve "ok", "cancelar" o None."""
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.boton_ok.collidepoint(ev.pos):
                return "ok"
            if self.boton_cancelar.collidepoint(ev.pos):
                return "cancelar"
            for i, caja in enumerate(self.cajas):
                if caja.collidepoint(ev.pos):
                    self.activo = i
            return None
        if ev.type != pygame.KEYDOWN:
            return None
        if ev.key == pygame.K_ESCAPE:
            return "cancelar"
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "ok"
        if ev.key == pygame.K_TAB:
            self.activo = (self.activo + 1) % 3
        elif ev.key == pygame.K_BACKSPACE:
            self.valores[self.activo] = self.valores[self.activo][:-1]
        elif ev.unicode != "" and ev.unicode in "0123456789." and len(self.valores[self.activo]) < 8:
            self.valores[self.activo] += ev.unicode
        return None

    def numeros(self):
        """Lanza ValueError si algún campo no es un número válido."""
        return int(self.valores[0]), int(self.valores[1]), float(self.valores[2])

    def dibujar(self, pantalla):
        rect = self.rect
        pygame.draw.rect(pantalla, (30, 34, 44), rect, border_radius=12)
        pygame.draw.rect(pantalla, cfg.ACENTO, rect, 2, border_radius=12)
        titulo = f"Producto en celda ({self.celda[0]}, {self.celda[1]})"
        pantalla.blit(self.fuente.render(titulo, True, (255, 255, 255)), (rect.x + 16, rect.y + 12))
        for i, caja in enumerate(self.cajas):
            color = cfg.ACENTO if i == self.activo else (110, 120, 140)
            pantalla.blit(self.fuente.render(self.ETIQUETAS[i], True, cfg.TEXTO), (rect.x + 16, caja.y + 4))
            pygame.draw.rect(pantalla, color, caja, 2, border_radius=6)
            pantalla.blit(self.fuente.render(self.valores[i], True, (255, 255, 255)),
                          (caja.x + 8, caja.y + 4))
        for boton, texto, relleno in ((self.boton_ok, "Aceptar", (22, 163, 74)),
                                      (self.boton_cancelar, "Cancelar", (75, 82, 99))):
            pygame.draw.rect(pantalla, relleno, boton, border_radius=10)
            pygame.draw.rect(pantalla, (160, 170, 190), boton, 2, border_radius=10)
            img = self.fuente.render(texto, True, (255, 255, 255))
            pantalla.blit(img, img.get_rect(center=boton.center))


class EditorEscenario:

    def __init__(self, ancho_x, largo_y, pincel, fuentes):
        area = pygame.Rect(cfg.AREA_X, cfg.AREA_Y, cfg.AREA_W, cfg.AREA_H)
        self.modelo = ModeloEscenario(ancho_x, largo_y)
        self.grilla = Grilla(ancho_x, largo_y, area)
        self.pincel = pincel
        self.pantalla = pincel.pantalla
        self.fuentes = fuentes
        self.sprites = FabricaSprites(cfg.ESTILO_PICKER)
        self.cartones = FabricaProductos()
        self.capa = CapaMapa(fuentes)
        self.version_capa = -1
        self.rejilla = self._construir_rejilla()
        self.herramienta = "rack"
        self.sentido = "AMBOS"
        self.inicio = None
        self.actual = None
        self.hover = None
        self.picker_movido = -1       # índice del picker que se está arrastrando, o -1
        self.cuadro = None
        self.mensaje = ""

        # Validación automática con retraso
        self._ultimo_cambio = 0.0
        self._resultado_validacion = []  # lista de strings de error, vacía si válido
        self._esta_vacio = True

    # ---------- acciones (también las usan los botones de la pestaña) ----------

    def seleccionar(self, herramienta):
        self.herramienta = herramienta
        self.inicio = None
        self.picker_movido = -1

    def elegir_sentido(self, sentido):
        self.sentido = sentido

    def deshacer(self):
        self.modelo.deshacer()
        self._marcar_cambio()

    def _marcar_cambio(self):
        """Registra que el modelo cambió; la validación se disparará tras el delay."""
        self._ultimo_cambio = time.perf_counter() * 1000.0

    def actualizar_validacion(self, ahora_ms=None):
        """Si pasó el delay desde el último cambio, revalida el modelo.

        Devuelve True si el resultado cambió.
        """
        if ahora_ms is None:
            ahora_ms = time.perf_counter() * 1000.0
        if ahora_ms - self._ultimo_cambio < cfg.VALIDACION_DELAY_MS:
            return False
        self._ultimo_cambio = ahora_ms + 1e9  # evitar revalidar en cada frame
        self._resultado_validacion = self.modelo.validar()
        m = self.modelo
        self._esta_vacio = not (m.racks or m.zonas or m.puertas or m.pasillos or m.pickers or m.productos)
        return True

    @property
    def errores_validacion(self):
        return list(self._resultado_validacion)

    @property
    def valido(self):
        return not self._resultado_validacion and not self._esta_vacio

    @property
    def esta_vacio(self):
        return self._esta_vacio

    # ---------- eventos ----------

    def evento(self, ev):
        """Devuelve "validar", "terminar", "salir" o None."""
        if self.cuadro is not None:
            self._evento_cuadro(ev)
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self._click(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self.inicio = None
            self.picker_movido = -1
        elif ev.type == pygame.MOUSEMOTION:
            celda = self.grilla.celda_en(*ev.pos)
            self.hover = celda
            if celda is not None and (self.inicio is not None or self.picker_movido != -1):
                self.actual = celda
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self.picker_movido != -1:
                self._soltar_picker()
            elif self.inicio is not None:
                self._soltar()
        elif ev.type == pygame.KEYDOWN:
            return self._tecla(ev)
        return None

    def _click(self, pos):
        celda = self.grilla.celda_en(*pos)
        if celda is None:
            return
        if self.herramienta == "borrar":
            self.modelo.borrar(celda[0], celda[1])
            self.mensaje = ""
            self._marcar_cambio()
        elif self.herramienta == "producto":
            self._abrir_cuadro(celda)
        elif self.herramienta == "picker" and self.modelo.picker_en(celda[0], celda[1]) != -1:
            self.picker_movido = self.modelo.picker_en(celda[0], celda[1])    # agarrar para mover
            self.actual = celda
            self.mensaje = ""
        else:
            self.inicio = celda
            self.actual = celda

    def _abrir_cuadro(self, celda):
        if not self.modelo.rack_en(celda[0], celda[1]):
            self.mensaje = "Hacé click sobre un rack"
            return
        z = self.modelo.siguiente_z(celda[0], celda[1])
        self.cuadro = CuadroProducto(self.fuentes, celda, z)
        self.mensaje = ""

    def _evento_cuadro(self, ev):
        resultado = self.cuadro.evento(ev)
        if resultado == "cancelar":
            self.cuadro = None
        elif resultado == "ok":
            try:
                z, stock, peso = self.cuadro.numeros()
            except ValueError:
                self.mensaje = "Completá z, stock y peso con números válidos"
                return
            x, y = self.cuadro.celda
            self.mensaje = self.modelo.agregar_producto(x, y, z, stock, peso)
            self._marcar_cambio()
            if not self.mensaje:
                self.cuadro = None

    def _soltar(self):
        x, y, w, h = self._rect_arrastre()
        self.mensaje = self.modelo.agregar(self.herramienta, x, y, w, h, self.sentido)
        self._marcar_cambio()
        self.inicio = None

    def _soltar_picker(self):
        x, y = self.actual
        self.mensaje = self.modelo.mover_picker(self.picker_movido, x, y)   # si no se puede, queda donde estaba
        self._marcar_cambio()
        self.picker_movido = -1

    def _tecla(self, ev):
        if ev.key == pygame.K_ESCAPE:
            return "salir"
        if ev.key in HERRAMIENTAS:
            self.seleccionar(HERRAMIENTAS[ev.key])
        elif ev.key in SENTIDOS and self.herramienta == "pasillo":
            self.elegir_sentido(SENTIDOS[ev.key])
        elif ev.key == pygame.K_z and ev.mod & pygame.KMOD_CTRL:
            self.deshacer()
        elif ev.key == pygame.K_v:
            return "validar"
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "terminar"
        return None

    def _rect_arrastre(self):
        x0, y0 = self.inicio
        x1, y1 = self.actual
        dx = abs(x1 - x0) + 1
        dy = abs(y1 - y0) + 1
        if self.herramienta == "rack":
            if dx >= dy:                          # horizontal: alto fijo en 2
                return min(x0, x1), y0, max(dx, 2), 2
            return x0, min(y0, y1), 2, dy         # vertical: ancho fijo en 2
        if self.herramienta in ("despacho", "pasillo"):
            return min(x0, x1), min(y0, y1), dx, dy
        return x0, y0, 1, 1

    # ---------- dibujo ----------

    def _construir_rejilla(self):
        """Líneas finas sobre cada celda, para dibujar con precisión."""
        g = self.grilla
        sup = pygame.Surface((cfg.ANCHO, cfg.ALTO), pygame.SRCALPHA)
        zona = g.rect(0, 0, g.ancho_celdas, g.alto_celdas)
        for i in range(g.ancho_celdas + 1):
            x = g.x + i * g.celda
            pygame.draw.line(sup, (*cfg.MAPA_GRILLA, 28), (x, zona.top), (x, zona.bottom))
        for j in range(g.alto_celdas + 1):
            y = g.y + j * g.celda
            pygame.draw.line(sup, (*cfg.MAPA_GRILLA, 28), (zona.left, y), (zona.right, y))
        return sup

    def _almacen_visual(self):
        m = self.modelo
        return SimpleNamespace(racks=_elementos(m.racks), pasillos=_elementos(m.pasillos),
                               zonas_despacho=_elementos(m.zonas), puertas=_elementos(m.puertas))

    def _actualizar_capa(self):
        """La capa del mapa se vuelve a armar solo cuando el modelo cambió."""
        if self.version_capa != self.modelo.version:
            self.capa.construir(self.grilla, self._almacen_visual())
            self.version_capa = self.modelo.version

    def _radio_picker(self):
        return max(8, min(16, int(self.grilla.celda * 0.5)))

    def _color_picker(self, indice):
        return cfg.COLORES_PICKER[indice % len(cfg.COLORES_PICKER)]

    def dibujar(self):
        self._dibujar_mapa()

    def dibujar_cuadro(self):
        if self.cuadro is not None:
            self.cuadro.dibujar(self.pantalla)

    def _dibujar_mapa(self):
        g = self.grilla
        self._actualizar_capa()
        # Fondo oscuro del lienzo para que resalten celdas y elementos.
        area = g.rect(0, 0, g.ancho_celdas, g.alto_celdas)
        pygame.draw.rect(self.pantalla, cfg.MAPA_FONDO, area)
        self.capa.dibujar(self.pantalla)
        self.pantalla.blit(self.rejilla, (0, 0))

        lado = max(8, int(g.celda * 0.66))
        carton = self.cartones.obtener(lado, "normal")
        for p in self.modelo.productos:
            cx, cy = g.centro(p["ubicacion"]["x"], p["ubicacion"]["y"])
            self.pantalla.blit(carton, carton.get_rect(center=(cx, cy)))

        self._dibujar_pickers()
        if self.inicio is not None:
            x, y, w, h = self._rect_arrastre()
            ok = self.modelo.error(self.herramienta, x, y, w, h) == ""
            r = g.rect(x, y, w, h)
            previa = pygame.Surface(r.size, pygame.SRCALPHA)
            previa.fill((*(cfg.MAPA_PREVIA_VALIDO if ok else cfg.MAPA_PREVIA_INVALIDO)[:3],
                         cfg.MAPA_PREVIA_VALIDO[3] if ok else cfg.MAPA_PREVIA_INVALIDO[3]))
            self.pantalla.blit(previa, r.topleft)
        # Resaltar celda bajo el cursor (solo cuando no se está arrastrando).
        if self.inicio is None and self.hover is not None and self.herramienta != "producto":
            x, y = self.hover
            if self.modelo.error(self.herramienta, x, y, 1, 1) == "":
                r = g.rect(x, y, 1, 1)
                sup = pygame.Surface(r.size, pygame.SRCALPHA)
                sup.fill((*cfg.MAPA_CELDA_HOVER[:3], cfg.MAPA_CELDA_HOVER[3]))
                self.pantalla.blit(sup, r.topleft)
        self._dibujar_texto_estado()

    def _dibujar_picker(self, indice, celda, apagado=False, offset=(0, 0)):
        g = self.grilla
        radio = self._radio_picker()
        color = self._color_picker(indice)
        x, y = g.centro(celda[0], celda[1])
        x += offset[0]
        y += offset[1]
        # Limitar el sprite a su celda para no dibujar cortado en el borde
        radio_efectivo = min(radio, g.celda // 2 - 2)
        fase = (pygame.time.get_ticks() // 400) % 2
        sprite = self.sprites.obtener(color, "N", radio_efectivo, False, apagado, fase)
        if not apagado:
            sombra = self.sprites.sombra(radio_efectivo)
            self.pantalla.blit(sombra, sombra.get_rect(center=(x + 1, y + int(radio_efectivo * 0.55))))
            brillo = self.sprites.resplandor(color, radio_efectivo)
            self.pantalla.blit(brillo, brillo.get_rect(center=(x, y)))
        self.pantalla.blit(sprite, sprite.get_rect(center=(x, y)))

    def _dibujar_pickers(self):
        g = self.grilla
        # Contar pickers por celda para detectar apilamientos
        celdas_pickers = {}
        for indice, picker in enumerate(self.modelo.pickers):
            celda = (picker["ubicacion"]["x"], picker["ubicacion"]["y"])
            celdas_pickers.setdefault(celda, []).append(indice)

        # Calcular offset para pickers que comparten celda o son vecinos
        offsets = {}
        for celda, indices in celdas_pickers.items():
            if len(indices) > 1:
                for i, indice in enumerate(indices):
                    angulo = i * (2 * 3.14159 / len(indices))
                    offset = (int(8 * __import__('math').cos(angulo)),
                              int(8 * __import__('math').sin(angulo)))
                    offsets[indice] = offset
            else:
                offsets[indices[0]] = (0, 0)

        for indice, picker in enumerate(self.modelo.pickers):
            celda = (picker["ubicacion"]["x"], picker["ubicacion"]["y"])
            offset = offsets.get(indice, (0, 0))
            if indice == self.picker_movido:
                self._dibujar_picker(indice, celda, apagado=True, offset=offset)
            else:
                self._dibujar_picker(indice, celda, offset=offset)

        # Mostrar contador si hay pickers apilados en la misma celda
        for celda, indices in celdas_pickers.items():
            if len(indices) > 1:
                x, y = g.centro(celda[0], celda[1])
                img = self.fuentes.chico.render(f"×{len(indices)}", True, (255, 255, 255))
                self.pantalla.blit(img, img.get_rect(center=(x + 6, y - 6)))

        if self.picker_movido != -1 and self.actual is not None:
            x, y = self.actual
            valido = self.modelo.error_mover_picker(self.picker_movido, x, y) == ""
            self._dibujar_picker(self.picker_movido, (x, y), offset=(0, 0))
            self._marco_celda(x, y, cfg.VERDE if valido else cfg.ROJO)
        elif self.herramienta == "picker" and self.hover is not None and self.inicio is None:
            x, y = self.hover
            if self.modelo.picker_en(x, y) == -1:
                siguiente = len(self.modelo.pickers)
                valido = self.modelo.error("picker", x, y, 1, 1) == ""
                if valido:
                    self._dibujar_picker(siguiente, (x, y), apagado=True)
                else:
                    self._marco_celda(x, y, cfg.ROJO)

    def _marco_celda(self, x, y, color):
        rect = self.grilla.rect(x, y, 1, 1)
        pygame.draw.rect(self.pantalla, color, rect, 2, border_radius=4)

    def _dibujar_texto_estado(self):
        g = self.grilla
        texto = f"Herramienta: {self.herramienta}"
        if self.herramienta == "pasillo":
            texto += f" (sentido {self.sentido})"
        if self.herramienta == "picker":
            texto += " (clic para colocar, arrastrá uno para moverlo)"
        if self.mensaje:
            texto += "   |   " + self.mensaje
        fondo = g.rect(0, 0, g.ancho_celdas, g.alto_celdas)
        self.pincel.texto(texto, self.fuentes.normal, cfg.TEXTO, g.x, fondo.bottom + 8)

    # ---------- miniatura (la usa la pestaña Automático) ----------

    def esta_vacio(self):
        m = self.modelo
        return not (m.racks or m.zonas or m.puertas or m.pasillos or m.pickers or m.productos)

    def miniatura(self, destino):
        """Dibuja una versión reducida del mapa dentro del rectángulo `destino`."""
        self._actualizar_capa()
        capa = self.capa.superficie
        escala = min(destino.w / capa.get_width(), destino.h / capa.get_height())
        tam = (max(1, int(capa.get_width() * escala)), max(1, int(capa.get_height() * escala)))
        mini = pygame.transform.smoothscale(capa, tam)
        pos = mini.get_rect(center=destino.center)
        self.pantalla.blit(mini, pos)
        origen = self.capa.origen
        for p in self.modelo.productos:
            cx, cy = self.grilla.centro(p["ubicacion"]["x"], p["ubicacion"]["y"])
            punto = (pos.x + int((cx - origen[0]) * escala), pos.y + int((cy - origen[1]) * escala))
            pygame.draw.circle(self.pantalla, (214, 168, 102), punto, 2)
        for indice, picker in enumerate(self.modelo.pickers):
            cx, cy = self.grilla.centro(picker["ubicacion"]["x"], picker["ubicacion"]["y"])
            punto = (pos.x + int((cx - origen[0]) * escala), pos.y + int((cy - origen[1]) * escala))
            pygame.draw.circle(self.pantalla, (16, 22, 34), punto, 5)
            pygame.draw.circle(self.pantalla, self._color_picker(indice), punto, 4)
