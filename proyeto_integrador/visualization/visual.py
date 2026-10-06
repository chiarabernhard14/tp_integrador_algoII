"""Capa visual con pygame-ce.

No calcula nada de los algoritmos: reproduce y anima la lista de eventos
que genera el warehouse. Pausar / continuar / reiniciar / paso a paso
son solo controlar cuando se avanza al siguiente evento.

Atajos: ESPACIO pausa/continua, N paso, R reiniciar, + / - velocidad.
"""

import math
import os
import sys
import argparse
import ctypes

try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass

import pygame
from pygame import gfxdraw

from eventos import VISITAR_NODO, RECORRER_ARISTA, ELEGIR_SIGUIENTE, RECOGER_PRODUCTO
from almacen_demo import (
    AlmacenDemo,
    ESTRATEGIA_A,
    ESTRATEGIA_B,
    PENDIENTE,
    EN_WAVE,
    EN_PREPARACION,
    PREPARADO,
)

# IMPORTANTE: Ajusta esta importación según cómo se llame tu función en Persistence.py
try:
    from simulation.Persistence import cargar_escenario
except ImportError:
    cargar_escenario = None

ANCHO = 1280
ALTO = 780
FPS = 60

CELDA = 72
ORIGEN_X = 80
ORIGEN_Y = 125
MEDIO_PASILLO = 12
LADO_PRODUCTO = 27

VELOCIDADES = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)

# Sprite sheet del picker: frames de 48x48, 6 columnas x 10 filas
RUTA_SPRITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "player.png")
FRAME = 48
FRAMES_POR_FILA = 6
ESCALA_SPRITE = 2
ANCLA_X = 24
ANCLA_Y = 32
FILAS_SPRITE = (
    ("idle_abajo", 0),
    ("idle_lado", 1),
    ("idle_arriba", 2),
    ("caminar_abajo", 3),
    ("caminar_lado", 4),
    ("caminar_arriba", 5),
)

BG = (255, 255, 255)
SUELO = (50, 54, 62)
BORDE_SUELO = (88, 94, 106)
PANEL = (44, 48, 56)
TARJETA = (60, 65, 76)
BORDE = (90, 96, 110)
TEXTO = (226, 232, 245)
APAGADO = (139, 150, 176)
ACENTO = (88, 166, 255)
VERDE = (52, 211, 153)
NARANJA = (251, 146, 60)
AMARILLO = (250, 204, 21)
MORADO = (167, 139, 250)
PASILLO = (108, 114, 126)
PASILLO_CENTRO = (156, 162, 174)
RACK = (24, 52, 102)
RACK_BORDE = (59, 130, 246)
CAJA = (214, 160, 90)
CAJA_APAGADA = (92, 76, 60)

COLORES_PEDIDO = (
    (96, 165, 250),
    (244, 114, 182),
    (250, 204, 21),
    (52, 211, 153),
    (167, 139, 250),
    (251, 146, 60),
)

COLOR_ESTADO = {
    PENDIENTE: (120, 130, 150),
    EN_WAVE: (250, 204, 21),
    EN_PREPARACION: (251, 146, 60),
    PREPARADO: (52, 211, 153),
}


class Boton:
    def __init__(self, nombre, texto, x, y, ancho, alto, color=None):
        self.nombre = nombre
        self.texto = texto
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.color = color
        self.activo = False


class App:
    # MODIFICACIÓN: Se añade almacen_personalizado para inyectar el escenario cargado
    def __init__(self, almacen_personalizado=None):
        pygame.init()
        pygame.display.set_caption("Wave Picking - Simulacion")

        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self.reloj = pygame.time.Clock()
        self.glow = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)

        nombres = "segoeui,helveticaneue,helvetica,arial,dejavusans,liberationsans"
        self.f_titulo = pygame.font.SysFont(nombres, 30, bold=True)
        self.f_sub = pygame.font.SysFont(nombres, 20, bold=True)
        self.f_normal = pygame.font.SysFont(nombres, 16)
        self.f_negrita = pygame.font.SysFont(nombres, 16, bold=True)
        self.f_chico = pygame.font.SysFont(nombres, 13)
        self.f_mini = pygame.font.SysFont(nombres, 11, bold=True)

        self.sprites = {}
        self.icono_picker = None
        self._cargar_sprites()

        # Usar el almacén cargado, o el demo si no se pasó nada
        if almacen_personalizado is not None:
            self.almacen = almacen_personalizado
        else:
            self.almacen = AlmacenDemo()
            
        self.color_pedido = {}
        for i, pedido in enumerate(self.almacen.pedidos):
            self.color_pedido[pedido.id] = COLORES_PEDIDO[i % len(COLORES_PEDIDO)]

        self.wave_idx = 0
        self.estrategia = ESTRATEGIA_B
        self.vel_idx = 2
        self.t_anim = 0.0

        self.botones = []
        self._crear_botones()
        self._recargar()

    # ---------- sprites del picker ----------

    def _cargar_sprites(self):
        try:
            hoja = pygame.image.load(RUTA_SPRITE).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return
        tam = FRAME * ESCALA_SPRITE
        for nombre, fila in FILAS_SPRITE:
            lista = []
            for col in range(FRAMES_POR_FILA):
                recorte = hoja.subsurface((col * FRAME, fila * FRAME, FRAME, FRAME))
                lista.append(pygame.transform.scale(recorte, (tam, tam)))
            self.sprites[nombre] = lista
        for base in ("idle_lado", "caminar_lado"):
            espejados = []
            for frame in self.sprites[base]:
                espejados.append(pygame.transform.flip(frame, True, False))
            self.sprites[base + "_izq"] = espejados
        self.icono_picker = hoja.subsurface((14, 20, 20, 24)).copy()

    def _caminando(self):
        return (self.evento is not None
                and self.evento.tipo == RECORRER_ARISTA
                and (self.corriendo or self.paso_pendiente))

    def _frame_picker(self):
        if self.direccion == "lado":
            sufijo = "_lado_izq" if self.mira_izq else "_lado"
        else:
            sufijo = "_" + self.direccion
        if self._caminando():
            lista = self.sprites["caminar" + sufijo]
            indice = int(self.t_sprite * 12) % FRAMES_POR_FILA
        else:
            lista = self.sprites["idle" + sufijo]
            indice = int(self.t_anim * 5) % FRAMES_POR_FILA
        return lista[indice]

    # ---------- botones ----------

    def _crear_botones(self):
        self.botones = []
        x = 900
        # Waves
        for i in range(len(self.almacen.waves)):
            self.botones.append(Boton(f"wave{i}", f"Wave {i + 1}", x + i * 88, 84, 80, 30))
            
        # Estrategias (más anchas)
        self.botones.append(Boton("estA", "A  Orden", 900, 146, 168, 32))
        self.botones.append(Boton("estB", "B  Cercania", 1078, 146, 168, 32))
        
        # Simulación (ancho dinámico según la palabra para que no se aprieten)
        self.botones.append(Boton("iniciar", "Iniciar", 900, 196, 62, 34, (22, 163, 74)))
        self.botones.append(Boton("pausar", "Pausar", 968, 196, 62, 34))
        self.botones.append(Boton("continuar", "Continuar", 1036, 196, 76, 34))
        self.botones.append(Boton("reiniciar", "Reiniciar", 1118, 196, 70, 34))
        self.botones.append(Boton("paso", "Paso", 1194, 196, 52, 34))
        
        # Velocidad
        self.botones.append(Boton("vel_menos", "-", 1160, 240, 36, 26))
        self.botones.append(Boton("vel_mas", "+", 1204, 240, 36, 26))


    def _click(self, nombre):
        if nombre.startswith("wave"):
            self.wave_idx = int(nombre[4:])
            self._recargar()
        elif nombre == "estA":
            self.estrategia = ESTRATEGIA_A
            self._recargar()
        elif nombre == "estB":
            self.estrategia = ESTRATEGIA_B
            self._recargar()
        elif nombre == "iniciar":
            self._recargar()
            self.corriendo = True
        elif nombre == "pausar":
            self.corriendo = False
        elif nombre == "continuar":
            if not self.terminado:
                self.corriendo = True
        elif nombre == "reiniciar":
            self._recargar()
        elif nombre == "paso":
            self.corriendo = False
            self.paso_pendiente = True
        elif nombre == "vel_menos":
            self.vel_idx = max(0, self.vel_idx - 1)
        elif nombre == "vel_mas":
            self.vel_idx = min(len(VELOCIDADES) - 1, self.vel_idx + 1)

    def _sincronizar_botones(self):
        for boton in self.botones:
            if boton.nombre.startswith("wave"):
                boton.activo = boton.nombre == f"wave{self.wave_idx}"
            elif boton.nombre == "estA":
                boton.activo = self.estrategia == ESTRATEGIA_A
            elif boton.nombre == "estB":
                boton.activo = self.estrategia == ESTRATEGIA_B

    # ---------- estado de la simulacion ----------

    def _recargar(self):
        self.resultado = self.almacen.resultados[(self.wave_idx, self.estrategia)]
        self.prods_wave = self.almacen.productos_de_wave(self.wave_idx)
        self.indice = 0
        self.evento = None
        self.t = 0.0
        self.dur = 0.0
        self.corriendo = False
        self.paso_pendiente = False
        self.terminado = False
        despacho = self.almacen.despacho
        self.pick_x, self.pick_y = self.almacen.nodos[despacho]
        self.trail = []
        self.recogidos = []
        self.candidato_prod = None
        self.candidato_nodo = None
        self.dist_live = 0
        self.aristas_live = 0
        self.nodos_live = 0
        self.direccion = "abajo"
        self.mira_izq = False
        self.t_sprite = 0.0

    def _iniciar_evento(self):
        evento = self.resultado.eventos[self.indice]
        self.indice += 1
        self.evento = evento
        self.t = 0.0
        datos = evento.datos
        if evento.tipo == RECORRER_ARISTA:
            self.dur = 0.45 * datos["peso"]
            co, fo = self.almacen.nodos[datos["origen"]]
            cd, fd = self.almacen.nodos[datos["destino"]]
            if fd > fo:
                self.direccion = "abajo"
            elif fd < fo:
                self.direccion = "arriba"
            else:
                self.direccion = "lado"
                self.mira_izq = cd < co
        elif evento.tipo == VISITAR_NODO:
            self.dur = 0.04
        elif evento.tipo == ELEGIR_SIGUIENTE:
            self.dur = 0.8
            self.candidato_prod = datos.get("producto")
            self.candidato_nodo = datos["candidato"]
        elif evento.tipo == RECOGER_PRODUCTO:
            self.dur = 0.7

    def _terminar_evento(self):
        evento = self.evento
        datos = evento.datos
        if evento.tipo == VISITAR_NODO:
            self.nodos_live += 1
            self.pick_x, self.pick_y = self.almacen.nodos[datos["nodo"]]
        elif evento.tipo == RECORRER_ARISTA:
            self.trail.append((datos["origen"], datos["destino"]))
            self.aristas_live += 1
            self.dist_live += datos["peso"]
            self.pick_x, self.pick_y = self.almacen.nodos[datos["destino"]]
        elif evento.tipo == RECOGER_PRODUCTO:
            self.recogidos.append(datos["producto"])
            self.candidato_prod = None
            self.candidato_nodo = None
        elif evento.tipo == ELEGIR_SIGUIENTE and datos.get("producto") is None:
            self.candidato_nodo = None

    def _actualizar(self, dt):
        if not (self.corriendo or self.paso_pendiente):
            return
        if self.evento is None:
            if self.indice >= len(self.resultado.eventos):
                self.corriendo = False
                self.paso_pendiente = False
                self.terminado = True
                return
            self._iniciar_evento()
        self.t += dt * VELOCIDADES[self.vel_idx]
        if self.evento.tipo == RECORRER_ARISTA:
            self.t_sprite += dt * VELOCIDADES[self.vel_idx]
            fraccion = min(self.t / self.dur, 1.0)
            ox, oy = self.almacen.nodos[self.evento.datos["origen"]]
            dx, dy = self.almacen.nodos[self.evento.datos["destino"]]
            self.pick_x = ox + (dx - ox) * fraccion
            self.pick_y = oy + (dy - oy) * fraccion
        if self.t >= self.dur:
            self._terminar_evento()
            self.evento = None
            self.paso_pendiente = False
            if self.indice >= len(self.resultado.eventos):
                self.terminado = True
                self.corriendo = False

    def _estado_pedido(self, pedido):
        ids_wave = []
        for p in self.almacen.waves[self.wave_idx].pedidos:
            ids_wave.append(p.id)
        if pedido.id not in ids_wave:
            return pedido.estado
        if self.indice == 0:
            return EN_WAVE
        for id_producto in pedido.items:
            if id_producto not in self.recogidos:
                return EN_PREPARACION
        return PREPARADO

    # ---------- utilidades de dibujo ----------

    def _px(self, c, f):
        return int(ORIGEN_X + c * CELDA), int(ORIGEN_Y + f * CELDA)

    def _texto(self, texto, fuente, color, x, y, ancla="izq"):
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

    def _circulo(self, x, y, radio, color):
        gfxdraw.filled_circle(self.pantalla, x, y, radio, color)
        gfxdraw.aacircle(self.pantalla, x, y, radio, color)

    def _anillo(self, x, y, radio, color, ancho=2):
        for i in range(ancho):
            gfxdraw.aacircle(self.pantalla, x, y, radio - i, color)

    def _rect_alfa(self, x, y, w, h, color, radio=8):
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(sup, color, (0, 0, w, h), border_radius=radio)
        self.pantalla.blit(sup, (x, y))

    def _linea_punteada(self, x1, y1, x2, y2, color, ancho=2, largo=8, hueco=6):
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

    def _rect_punteado(self, x, y, w, h, color):
        self._linea_punteada(x, y, x + w, y, color)
        self._linea_punteada(x + w, y, x + w, y + h, color)
        self._linea_punteada(x + w, y + h, x, y + h, color)
        self._linea_punteada(x, y + h, x, y, color)

    def _pos_caja(self, id_producto):
        producto = self.almacen.productos[id_producto]
        c, f = producto.columna, producto.fila
        lado = 1 if (c % 2 == 0 and c < self.almacen.columnas - 1) else -1
        x, y = self._px(c, f)
        return x + lado * LADO_PRODUCTO, y

    # ---------- dibujo del warehouse ----------

    def _dibujar(self):
        # 1. Pintamos el fondo y la base del almacén en la superficie virtual
        self.pantalla.fill(BG)
        pygame.draw.rect(self.pantalla, SUELO, (20, 20, 840, 740), border_radius=18)
        pygame.draw.rect(self.pantalla, BORDE_SUELO, (20, 20, 840, 740), 2, border_radius=18)
        
        # 2. Dibujamos todos los componentes
        self._dibujar_encabezado()
        self._dibujar_despacho()
        self._dibujar_racks()
        self._dibujar_pasillos()
        self._dibujar_recorrido()
        self._dibujar_nodos()
        self._dibujar_nodo_despacho()
        self._dibujar_productos()
        self._dibujar_candidato()
        self._dibujar_picker()
        self._dibujar_leyenda()
        self._dibujar_panel()
        self._dibujar_tooltip()

        
        # 4. Actualizar la pantalla
        pygame.display.flip()

    def _dibujar_encabezado(self):
        nombre = "Orden de pedidos" if self.estrategia == ESTRATEGIA_A else "Cercania"
        self._texto(f"Almacen  -  Wave {self.wave_idx + 1}", self.f_titulo, TEXTO, 44, 34)
        self._texto(f"Estrategia {self.estrategia}: {nombre}", self.f_normal, APAGADO, 44, 72)
        if self.evento is not None:
            texto = f"[{self.indice}/{len(self.resultado.eventos)}]  {self.evento.describir()}"
        elif self.terminado:
            texto = "Simulacion terminada: el picker volvio al despacho"
        elif self.indice == 0:
            texto = "Listo. Presiona Iniciar o Paso para comenzar"
        else:
            texto = f"[{self.indice}/{len(self.resultado.eventos)}]  En pausa"
        ancho = 400
        self._rect_alfa(450, 40, ancho, 34, (88, 166, 255, 38), 17)
        self._texto(texto, self.f_chico, TEXTO, 450 + ancho // 2, 49, "centro")

    def _dibujar_racks(self):
        for c0, f0, c1, f1 in self.almacen.racks:
            x0, y0 = self._px(c0, f0)
            x1, y1 = self._px(c1, f1)
            x0 += MEDIO_PASILLO + 4
            y0 += MEDIO_PASILLO + 4
            x1 -= MEDIO_PASILLO + 4
            y1 -= MEDIO_PASILLO + 4
            ancho = x1 - x0
            alto = y1 - y0
            pygame.draw.rect(self.pantalla, RACK, (x0, y0, ancho, alto), border_radius=6)
            pygame.draw.rect(self.pantalla, RACK_BORDE, (x0, y0, ancho, alto), 2, border_radius=6)
            filas = 6
            paso = alto / filas
            for j in range(filas):
                for k in range(2):
                    if (j + k + c0 + f0) % 3 == 0:
                        continue
                    bx = x0 + 5 + k * (ancho / 2 - 2)
                    by = y0 + 4 + j * paso
                    pygame.draw.rect(self.pantalla, (120, 92, 60),
                                     (bx, by, ancho / 2 - 8, paso - 7), border_radius=2)

    def _dibujar_pasillos(self):
        for nodo, lista in self.almacen.vecinos.items():
            c1, f1 = self.almacen.nodos[nodo]
            x1, y1 = self._px(c1, f1)
            for vecino, _peso in lista:
                if vecino > nodo:
                    c2, f2 = self.almacen.nodos[vecino]
                    x2, y2 = self._px(c2, f2)
                    pygame.draw.line(self.pantalla, PASILLO, (x1, y1), (x2, y2), MEDIO_PASILLO * 2)
        for nodo in self.almacen.nodos:
            c, f = self.almacen.nodos[nodo]
            x, y = self._px(c, f)
            self._circulo(x, y, MEDIO_PASILLO, PASILLO)
        for nodo, lista in self.almacen.vecinos.items():
            c1, f1 = self.almacen.nodos[nodo]
            x1, y1 = self._px(c1, f1)
            for vecino, _peso in lista:
                if vecino > nodo:
                    c2, f2 = self.almacen.nodos[vecino]
                    x2, y2 = self._px(c2, f2)
                    self._linea_punteada(x1, y1, x2, y2, PASILLO_CENTRO, 1, 6, 8)

    def _dibujar_nodos(self):
        for nodo, lista in self.almacen.vecinos.items():
            c, f = self.almacen.nodos[nodo]
            x, y = self._px(c, f)
            if nodo == self.almacen.despacho:
                continue
            if len(lista) >= 3:
                self._circulo(x, y, 9, (74, 80, 94))
                self._anillo(x, y, 9, (125, 190, 255), 2)
            else:
                self._circulo(x, y, 3, (80, 86, 100))

    def _dibujar_despacho(self):
        c0, f0 = 0, self.almacen.filas - 1
        x0, y0 = self._px(c0, f0)
        x1, _ = self._px(self.almacen.columnas - 1, f0)
        _, yd = self._px(0, self.almacen.filas)
        zx = x0 - 14
        zy = y0 + 24
        zw = x1 - x0 + 28
        zh = yd + 34 - zy
        self._rect_alfa(zx, zy, zw, zh, (52, 211, 153, 36), 10)
        self._rect_punteado(zx, zy, zw, zh, VERDE)
        self._texto("ZONA DE DESPACHO", self.f_negrita, VERDE, zx + 14, zy + 8)
        for k in (2, 5, 8):
            px, _ = self._px(k, 0)
            pygame.draw.rect(self.pantalla, NARANJA, (px - 26, zy + zh - 6, 52, 12), border_radius=3)
            self._texto("PUERTA", self.f_mini, NARANJA, px, zy + zh + 8, "centro")
        for k in (1, 3, 7, 9):
            px, _ = self._px(k, 0)
            for j in range(2):
                pygame.draw.rect(self.pantalla, (150, 112, 70),
                                 (px - 16 + j * 18, yd - 10, 14, 14), border_radius=2)
                                 
    def _dibujar_nodo_despacho(self):
        dx, dy = self._px(*self.almacen.nodos[self.almacen.despacho])
        self._circulo(dx, dy, 13, VERDE)
        self._anillo(dx, dy, 13, (255, 255, 255), 2)
        self._texto("D", self.f_negrita, (10, 40, 30), dx, dy, "cc")

    def _dibujar_recorrido(self):
        self.glow.fill((0, 0, 0, 0))
        segmentos = []
        for origen, destino in self.trail:
            c1, f1 = self.almacen.nodos[origen]
            c2, f2 = self.almacen.nodos[destino]
            segmentos.append((self._px(c1, f1), self._px(c2, f2)))
        if self.evento is not None and self.evento.tipo == RECORRER_ARISTA:
            co, fo = self.almacen.nodos[self.evento.datos["origen"]]
            segmentos.append((self._px(co, fo), self._px(self.pick_x, self.pick_y)))
        for (xa, ya), (xb, yb) in segmentos:
            pygame.draw.line(self.glow, (88, 166, 255, 70), (xa, ya), (xb, yb), 16)
        self.pantalla.blit(self.glow, (0, 0))
        for (xa, ya), (xb, yb) in segmentos:
            pygame.draw.line(self.pantalla, ACENTO, (xa, ya), (xb, yb), 5)
            self._circulo(xb, yb, 2, ACENTO)

    def _dibujar_productos(self):
        for id_producto, producto in self.almacen.productos.items():
            nx, ny = self._px(producto.columna, producto.fila)
            cx, cy = self._pos_caja(id_producto)
            en_wave = id_producto in self.prods_wave
            recogido = id_producto in self.recogidos
            pygame.draw.line(self.pantalla, (150, 156, 170), (nx, ny), (cx, cy), 2)
            if recogido:
                relleno = (34, 110, 84)
                borde = VERDE
            elif en_wave:
                relleno = CAJA
                borde = (255, 236, 200)
            else:
                relleno = CAJA_APAGADA
                borde = (70, 62, 52)
            pygame.draw.rect(self.pantalla, relleno, (cx - 13, cy - 13, 26, 26), border_radius=5)
            pygame.draw.rect(self.pantalla, borde, (cx - 13, cy - 13, 26, 26), 2, border_radius=5)
            color_z = (60, 40, 20) if en_wave and not recogido else TEXTO
            self._texto(f"z{producto.altura}", self.f_mini, color_z, cx, cy, "cc")
            color_id = TEXTO if en_wave else APAGADO
            self._texto(id_producto, self.f_mini, color_id, cx, cy + 16, "centro")
            if recogido:
                orden = self.recogidos.index(id_producto) + 1
                self._circulo(cx + 13, cy - 13, 9, VERDE)
                self._texto(str(orden), self.f_mini, (8, 40, 30), cx + 13, cy - 13, "cc")
            elif en_wave:
                pedidos = self.almacen.pedidos_de_producto(self.wave_idx, id_producto)
                inicio = cx - (len(pedidos) - 1) * 5
                for i, id_pedido in enumerate(pedidos):
                    self._circulo(inicio + i * 10, cy - 20, 4, self.color_pedido[id_pedido])

    def _dibujar_candidato(self):
        if self.candidato_nodo is None:
            return
        c, f = self.almacen.nodos[self.candidato_nodo]
        tx, ty = self._px(c, f)
        if self.candidato_prod is not None:
            tx, ty = self._pos_caja(self.candidato_prod)
        px, py = self._px(self.pick_x, self.pick_y)
        self._linea_punteada(px, py, tx, ty, MORADO, 2, 6, 6)
        pulso = 4 * math.sin(self.t_anim * 6)
        self._anillo(tx, ty, int(21 + pulso), MORADO, 2)

    def _dibujar_picker(self):
        x, y = self._px(self.pick_x, self.pick_y)
        if self.sprites:
            frame = self._frame_picker()
            self.pantalla.blit(frame, (x - ANCLA_X * ESCALA_SPRITE, y - ANCLA_Y * ESCALA_SPRITE))
            x_badge = x + 18
            y_badge = y - 34
        else:
            self._circulo(x, y, 11, NARANJA)
            self._anillo(x, y, 11, (255, 255, 255), 2)
            self._circulo(x, y, 4, (255, 255, 255))
            x_badge = x + 12
            y_badge = y - 12
        if self.recogidos:
            self._circulo(x_badge, y_badge, 8, VERDE)
            self._texto(str(len(self.recogidos)), self.f_mini, (8, 40, 30), x_badge, y_badge, "cc")

    def _dibujar_leyenda(self):
        y = 724
        x = 44
        pygame.draw.rect(self.pantalla, PASILLO, (x, y + 2, 24, 12), border_radius=6)
        self._texto("Pasillo", self.f_chico, APAGADO, x + 30, y)
        x += 100
        self._circulo(x + 8, y + 8, 8, (74, 80, 94))
        self._anillo(x + 8, y + 8, 8, (125, 190, 255), 2)
        self._texto("Interseccion", self.f_chico, APAGADO, x + 22, y)
        x += 120
        pygame.draw.rect(self.pantalla, CAJA, (x, y, 16, 16), border_radius=4)
        self._texto("Producto <x,y,z>", self.f_chico, APAGADO, x + 22, y)
        x += 140
        pygame.draw.rect(self.pantalla, (34, 90, 70), (x, y + 1, 22, 14), border_radius=3)
        pygame.draw.rect(self.pantalla, VERDE, (x, y + 1, 22, 14), 1, border_radius=3)
        self._texto("Despacho", self.f_chico, APAGADO, x + 28, y)
        x += 100
        pygame.draw.line(self.pantalla, ACENTO, (x, y + 8), (x + 24, y + 8), 5)
        self._texto("Recorrido", self.f_chico, APAGADO, x + 30, y)
        x += 100
        if self.icono_picker is not None:
            self.pantalla.blit(self.icono_picker, (x, y - 4))
        else:
            self._circulo(x + 8, y + 8, 8, NARANJA)
        self._texto("Picker", self.f_chico, APAGADO, x + 22, y)
        x += 80
        self._circulo(x + 4, y + 8, 4, COLORES_PEDIDO[0])
        self._circulo(x + 14, y + 8, 4, COLORES_PEDIDO[1])
        self._texto("Pedidos", self.f_chico, APAGADO, x + 26, y)

    # ---------- panel lateral ----------

    def _dibujar_boton(self, boton):
        
        mx, my = pygame.mouse.get_pos()
        sobre = boton.rect.collidepoint((mx, my))
        
        # Colores con más brillo para contrarrestar la oscuridad
        if boton.activo:
            relleno = (59, 130, 246) # Azul vivo
        elif boton.color is not None:
            relleno = boton.color
        elif sobre:
            relleno = (100, 110, 130) # Gris claro al pasar el mouse
        else:
            relleno = (75, 82, 99) # Base gris más clara
            
        # Iluminación extra al hacer hover sobre botones activos
        if sobre and (boton.activo or boton.color is not None):
            relleno = tuple(min(255, v + 30) for v in relleno)

        radio = 10   
        pygame.draw.rect(self.pantalla, relleno, boton.rect, border_radius=radio)
        
        # Borde dinámico que resalta
        borde = (160, 170, 190) if sobre else (110, 120, 140)
        pygame.draw.rect(self.pantalla, borde, boton.rect, 2, border_radius=radio)
        
        # Fuente más grande (f_normal) y color blanco puro en lugar del texto apagado
        self._texto(boton.texto, self.f_normal, (255, 255, 255), boton.rect.centerx, boton.rect.centery, "cc")

    def _dibujar_panel(self):
        pygame.draw.rect(self.pantalla, PANEL, (880, 20, 380, 740), border_radius=18)
        pygame.draw.rect(self.pantalla, BORDE_SUELO, (880, 20, 380, 740), 2, border_radius=18)
        self._texto("WAVE PICKING", self.f_sub, ACENTO, 900, 32)
        self._texto("Algoritmos II", self.f_chico, APAGADO, 1240, 38, "der")
        self._texto("WAVE", self.f_mini, APAGADO, 900, 68)
        self._texto("ESTRATEGIA", self.f_mini, APAGADO, 900, 130)
        self._texto("SIMULACION", self.f_mini, APAGADO, 900, 180)
        self._sincronizar_botones()
        for boton in self.botones:
            self._dibujar_boton(boton)
        self._texto(f"Velocidad  x{VELOCIDADES[self.vel_idx]:g}", self.f_chico, TEXTO, 900, 246)
        self._dibujar_waves()
        self._dibujar_pedidos()
        self._dibujar_metricas()

    def _dibujar_waves(self):
        self._texto("WAVES", self.f_mini, APAGADO, 900, 276)
        for i, wave in enumerate(self.almacen.waves):
            y = 295 + i * 26
            activa = i == self.wave_idx
            fondo = (37, 99, 235) if activa else (68, 73, 85)
            pygame.draw.rect(self.pantalla, fondo, (900, y, 64, 22), border_radius=11)
            self._texto(f"Wave {wave.id}", self.f_chico, TEXTO, 932, y + 11, "cc")
            for j, pedido in enumerate(wave.pedidos):
                color = self.color_pedido[pedido.id]
                px = 974 + j * 54
                pygame.draw.rect(self.pantalla, color, (px, y, 48, 22), 2, border_radius=11)
                self._texto(pedido.id, self.f_chico, color, px + 24, y + 11, "cc")

    def _dibujar_pedidos(self):
        self._texto("PEDIDOS", self.f_mini, APAGADO, 900, 352)
        ids_wave = []
        for p in self.almacen.waves[self.wave_idx].pedidos:
            ids_wave.append(p.id)
        for i, pedido in enumerate(self.almacen.pedidos):
            y = 372 + i * 40
            en_wave = pedido.id in ids_wave
            color = self.color_pedido[pedido.id]
            pygame.draw.rect(self.pantalla, TARJETA, (900, y, 340, 36), border_radius=8)
            borde = color if en_wave else BORDE
            pygame.draw.rect(self.pantalla, borde, (900, y, 340, 36), 2 if en_wave else 1,
                             border_radius=8)
            pygame.draw.rect(self.pantalla, color if en_wave else BORDE, (900, y + 6, 5, 24),
                             border_radius=2)
            texto_color = TEXTO if en_wave else APAGADO
            self._texto(pedido.id, self.f_negrita, texto_color, 914, y + 3)
            for k in range(5):
                relleno = AMARILLO if k < pedido.prioridad else (96, 102, 116)
                if not en_wave and k < pedido.prioridad:
                    relleno = (150, 138, 70)
                self._circulo(962 + k * 11, y + 12, 3, relleno)
            items = "  ".join(f"{pid}x{cant}" for pid, cant in pedido.items.items())
            self._texto(items, self.f_mini, APAGADO, 914, y + 21)
            estado = self._estado_pedido(pedido)
            col_estado = COLOR_ESTADO[estado]
            ancho = self.f_mini.size(estado)[0] + 16
            self._rect_alfa(1232 - ancho, y + 6, ancho, 20, (col_estado[0], col_estado[1], col_estado[2], 50), 10)
            self._texto(estado, self.f_mini, col_estado, 1232 - ancho // 2, y + 16, "cc")

    def _dibujar_metricas(self):
        resultado_a = self.almacen.resultados[(self.wave_idx, ESTRATEGIA_A)]
        resultado_b = self.almacen.resultados[(self.wave_idx, ESTRATEGIA_B)]
        self._texto("METRICAS (wave seleccionada)", self.f_mini, APAGADO, 900, 620)
        columnas_x = (900, 1010, 1085, 1160)
        cabeceras = ("", "A Orden", "B Cercania", "En vivo")
        for x, texto in zip(columnas_x, cabeceras):
            self._texto(texto, self.f_mini, ACENTO, x, 640)
        filas = (
            ("Distancia", resultado_a.distancia, resultado_b.distancia, self.dist_live),
            ("Nodos visitados", resultado_a.nodos_visitados, resultado_b.nodos_visitados, self.nodos_live),
            ("Aristas", resultado_a.aristas, resultado_b.aristas, self.aristas_live),
            ("Tiempo (ms)", resultado_a.tiempo_ms, resultado_b.tiempo_ms, None),
        )
        for i, (nombre, a, b, vivo) in enumerate(filas):
            y = 660 + i * 22
            pygame.draw.line(self.pantalla, BORDE, (900, y - 3), (1240, y - 3), 1)
            self._texto(nombre, self.f_chico, APAGADO, columnas_x[0], y)
            col_a = VERDE if a < b else TEXTO
            col_b = VERDE if b < a else TEXTO
            fmt_a = f"{a:.3f}" if isinstance(a, float) else str(a)
            fmt_b = f"{b:.3f}" if isinstance(b, float) else str(b)
            self._texto(fmt_a, self.f_chico, col_a, columnas_x[1], y)
            self._texto(fmt_b, self.f_chico, col_b, columnas_x[2], y)
            if vivo is not None:
                self._texto(str(vivo), self.f_chico, NARANJA, columnas_x[3], y)
            else:
                total = len(self.prods_wave)
                self._texto(f"{len(self.recogidos)}/{total} prod.", self.f_chico, NARANJA, columnas_x[3], y)

    def _dibujar_tooltip(self):
        mx, my = pygame.mouse.get_pos()

        for id_producto in self.almacen.productos:
            cx, cy = self._pos_caja(id_producto)
            if abs(mx - cx) <= 14 and abs(my - cy) <= 14:
                p = self.almacen.productos[id_producto]
                lineas = [
                    f"{p.id}  {p.nombre}",
                    f"Ubicacion <{p.columna},{p.fila},{p.altura}>",
                    f"Stock {p.stock}",
                ]
                pedidos = self.almacen.pedidos_de_producto(self.wave_idx, id_producto)
                if pedidos:
                    lineas.append("Pedidos: " + " ".join(pedidos))
                alto = 12 + len(lineas) * 20
                x = min(mx + 16, 860 - 190)
                y = min(my + 12, 750 - alto)
                pygame.draw.rect(self.pantalla, (10, 14, 24), (x, y, 180, alto), border_radius=8)
                pygame.draw.rect(self.pantalla, ACENTO, (x, y, 180, alto), 1, border_radius=8)
                for i, linea in enumerate(lineas):
                    fuente = self.f_negrita if i == 0 else self.f_chico
                    self._texto(linea, fuente, TEXTO if i == 0 else APAGADO, x + 10, y + 8 + i * 20)
                return

    # ---------- bucle principal ----------

    def _teclado(self, tecla):
        if tecla == pygame.K_SPACE:
            if self.corriendo:
                self.corriendo = False
            elif not self.terminado:
                self.corriendo = True
        elif tecla == pygame.K_n:
            self._click("paso")
        elif tecla == pygame.K_r:
            self._click("reiniciar")
        elif tecla in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self._click("vel_mas")
        elif tecla in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._click("vel_menos")

    def correr(self):
        activo = True
        while activo:
            dt = self.reloj.tick(FPS) / 1000.0
            self.t_anim += dt
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    activo = False
                elif ev.type == pygame.KEYDOWN:
                    self._teclado(ev.key)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for boton in self.botones:
                        if boton.rect.collidepoint(ev.pos):
                            self._click(boton.nombre)
                            break
            self._actualizar(dt)
            self._dibujar()
        pygame.quit()

# MODIFICACIÓN: Bloque principal para atrapar argumentos de consola
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de Wave Picking")
    parser.add_argument(
        "--escenario", 
        type=str, 
        help="Ruta al archivo JSON del escenario a cargar",
        default=None
    )
    args = parser.parse_args()

    almacen_cargado = None
    if args.escenario:
        if cargar_escenario:
            try:
                almacen_cargado = cargar_escenario(args.escenario)
                print(f"Escenario '{args.escenario}' cargado exitosamente.")
            except Exception as e:
                print(f"Error al intentar cargar el escenario: {e}")
                sys.exit(1)
        else:
            print("Advertencia: No se encontró la función 'cargar_escenario' en simulation.Persistence.")
            print("Ejecutando con el AlmacenDemo por defecto...")

    app = App(almacen_cargado)
    app.correr()
    sys.exit(0)