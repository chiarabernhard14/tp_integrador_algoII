"""Dibujo del warehouse: pasillos, racks, productos, recorridos y pickers."""

import math

import pygame

from . import config as cfg
from . import capa_mapa as mapa
from .capa_mapa import CapaMapa
from .grilla import Grilla
from .sprites import FabricaSprites
from .sprites_producto import FabricaProductos


def _z_de_producto(producto):
    return producto.ubicacion[2]


class VistaMapa:

    def __init__(self, pincel, fuentes, sesion, animacion):
        self.pincel = pincel
        self.pantalla = pincel.pantalla
        self.fuentes = fuentes
        self.sesion = sesion
        self.anim = animacion
        self.glow = pygame.Surface((cfg.ANCHO, cfg.ALTO), pygame.SRCALPHA)
        self.mostrar_intersecciones = True
        self.sprites = FabricaSprites(cfg.ESTILO_PICKER)
        self.cartones = FabricaProductos()
        self.capa = CapaMapa(fuentes)
        self.fondo = self._construir_fondo()
        self.recalcular()

    def alternar_intersecciones(self):
        self.mostrar_intersecciones = not self.mostrar_intersecciones

    def recalcular(self):
        """Hay que llamarlo cada vez que cambia el warehouse de la sesión."""
        almacen = self.sesion.sim.warehouse
        area = pygame.Rect(cfg.AREA_X, cfg.AREA_Y, cfg.AREA_W, cfg.AREA_H)
        self.grilla = Grilla(almacen.ancho_x, almacen.largo_y, area)
        self.capa.construir(self.grilla, almacen)

    def _color_picker(self, indice):
        return cfg.COLORES_PICKER[indice % len(cfg.COLORES_PICKER)]

    # ---------- conjunto ----------

    def _construir_fondo(self):
        fondo = pygame.Surface((cfg.ANCHO, cfg.ALTO))
        fondo.fill(cfg.BG)
        pygame.draw.rect(fondo, cfg.SUELO, (20, 20, 840, 740), border_radius=18)
        for x in range(44, 860, 24):
            for y in range(44, 760, 24):
                pygame.draw.circle(fondo, (62, 68, 82), (x, y), 1)
        pygame.draw.rect(fondo, cfg.BORDE_SUELO, (20, 20, 840, 740), 2, border_radius=18)
        return fondo

    def dibujar_fondo(self):
        self.pantalla.blit(self.fondo, (0, 0))

    def dibujar(self):
        self._dibujar_encabezado()
        self.capa.dibujar(self.pantalla)
        self._dibujar_intersecciones()
        self._dibujar_productos()
        self._dibujar_recorridos()
        self._dibujar_objetivos()
        self._dibujar_pickers()
        self._dibujar_leyenda()

    # ---------- encabezado ----------

    def _texto_estado(self):
        sesion = self.sesion
        if sesion.sim.terminada:
            for p in sesion.estado["pickers"]:
                if p["estado"] == "bloqueado":
                    return "Terminada con pickers bloqueados"
            return "Simulacion terminada"
        if sesion.corriendo:
            return "En curso"
        if sesion.estado["tick"] == 0:
            return "Listo. Presiona Iniciar o Paso"
        return "En pausa"

    def _dibujar_encabezado(self):
        sesion = self.sesion
        preparados = 0
        for pedido in sesion.sim.pedidos_wave:
            if pedido.estado == "PREPARADO":
                preparados += 1
        pasos = 0
        for p in sesion.estado["pickers"]:
            pasos += len(p["trail"]) - 1
        self.pincel.texto("Almacen", self.fuentes.titulo, cfg.TEXTO, 44, 30)
        resumen = (f"Tick {sesion.estado['tick']}   |   Pickers {len(sesion.estado['pickers'])}   |   "
                   f"Pedidos listos {preparados}/{len(sesion.sim.pedidos_wave)}   |   Pasos {pasos}")
        self.pincel.texto(resumen, self.fuentes.normal, cfg.APAGADO, 44, 68)
        ancho = 300
        self.pincel.rect_alfa(540, 36, ancho, 30, (88, 166, 255, 38), 15)
        self.pincel.texto(self._texto_estado(), self.fuentes.chico, cfg.TEXTO,
                          540 + ancho // 2, 44, "centro")

    # ---------- elementos del warehouse ----------

    def _dibujar_intersecciones(self):
        """Celdas donde se cruzan pasillos distintos (las calcula Navegacion)."""
        if not self.mostrar_intersecciones:
            return
        g = self.grilla
        radio = max(2, int(g.celda * 0.16))
        for celda in self.sesion.sim.nav.intersecciones:
            cx, cy = g.centro(celda[0], celda[1])
            self.pincel.circulo_alfa(cx, cy, radio, (255, 255, 255), 90)

    def _dibujar_productos(self):
        g = self.grilla
        sesion = self.sesion
        lado = max(8, int(g.celda * 0.66))
        pulso = 0.5 + 0.5 * math.sin(self.anim.t * 4)
        for celda, pila in sesion.pilas.items():
            cx, cy = g.centro(celda[0], celda[1])
            pendiente = False
            recogido = False
            for producto in pila:
                if producto.id in sesion.pendientes_ids:
                    pendiente = True
                if producto.id in sesion.recogidos_ids:
                    recogido = True
            if pendiente:
                estado = "pendiente"
                aura = self.cartones.aura(lado, int(pulso * 3.99))
                self.pantalla.blit(aura, aura.get_rect(center=(cx, cy)),
                                   special_flags=pygame.BLEND_RGB_ADD)
            elif recogido:
                estado = "recogido"
            else:
                estado = "normal"
            sprite = self.cartones.obtener(lado, estado)
            self.pantalla.blit(sprite, sprite.get_rect(center=(cx, cy)))
            if len(pila) > 1 and g.celda >= 20:
                self._insignia_pila(len(pila), cx + lado // 2, cy - lado // 2)

    def _insignia_pila(self, cantidad, x, y):
        self.pincel.circulo(x, y, 7, (16, 22, 34))
        self.pincel.anillo(x, y, 7, (226, 232, 245), 1)
        self.pincel.texto(str(cantidad), self.fuentes.mini, (255, 255, 255), x, y, "cc")

    # ---------- pickers ----------

    def _dibujar_recorridos(self):
        g = self.grilla
        self.glow.fill((0, 0, 0, 0))
        ancho = max(2, g.celda // 6)
        pickers = self.sesion.estado["pickers"]
        for i, p in enumerate(pickers):
            color = self._color_picker(i)
            puntos = []
            for celda in p["trail"]:
                puntos.append(g.centro(celda[0], celda[1]))
            if len(puntos) >= 2:
                pygame.draw.lines(self.glow, (color[0], color[1], color[2], 110),
                                  False, puntos, ancho)
        self.pantalla.blit(self.glow, (0, 0))
        for i, p in enumerate(pickers):
            color = self._color_picker(i)
            for celda in p["ruta"]:
                cx, cy = g.centro(celda[0], celda[1])
                pygame.draw.circle(self.pantalla, color, (cx, cy), 2)

    def _dibujar_objetivos(self):
        g = self.grilla
        pulso = 2 * math.sin(self.anim.t * 6)
        radio = int(g.celda * 0.55 + pulso)
        for i, p in enumerate(self.sesion.estado["pickers"]):
            if p["objetivo"] is None:
                continue
            producto = self.sesion.sim.productos.get(p["objetivo"])
            if producto is None:
                continue
            cx, cy = g.centro(producto.ubicacion[0], producto.ubicacion[1])
            self.pincel.anillo(cx, cy, radio, self._color_picker(i), 2)

    def _radio_picker(self):
        return max(8, min(16, int(self.grilla.celda * 0.5)))

    def _direccion_picker(self, p):
        """N, S, E u O según el último paso del picker (arriba si todavía no se movió)."""
        anterior = p.get("anterior")
        actual = p["posicion"]
        if anterior is None or tuple(anterior) == tuple(actual):
            return "N"
        dx = actual[0] - anterior[0]
        dy = actual[1] - anterior[1]
        if abs(dx) >= abs(dy):
            return "E" if dx > 0 else "O"
        return "N" if dy > 0 else "S"

    def _lleva_carga(self, p):
        """True si ya recogió algo de la wave que está ejecutando (y no la entregó)."""
        wave_id = p.get("wave_id")
        if wave_id is None:
            return False
        for wave in self.sesion.estado.get("waves", []):
            if wave["id"] != wave_id:
                continue
            pedidos_de_la_wave = set(wave["pedidos"])
            for recogido in p["recogidos"]:
                if recogido["pedido_id"] in pedidos_de_la_wave:
                    return True
        return False

    def _dibujar_pickers(self):
        pickers = self.sesion.estado["pickers"]
        # Primero los que ya terminaron (apagados), así no tapan a los activos.
        for i, p in enumerate(pickers):
            if p["estado"] == "terminado":
                self._dibujar_picker(i, p, True)
        for i, p in enumerate(pickers):
            if p["estado"] != "terminado":
                self._dibujar_picker(i, p, False)

    def _dibujar_picker(self, indice, p, apagado):
        radio = self._radio_picker()
        x, y = self.grilla.centro(*self.anim.posicion_visual(p))
        color = self._color_picker(indice)
        fase = int(self.anim.t * 2.5) % 2          # hace titilar las luces del vehículo
        sprite = self.sprites.obtener(color, self._direccion_picker(p), radio,
                                      self._lleva_carga(p), apagado, fase)
        if not apagado:
            sombra = self.sprites.sombra(radio)
            self.pantalla.blit(sombra, sombra.get_rect(center=(x + 1, y + int(radio * 0.55))))
            brillo = self.sprites.resplandor(color, radio)
            self.pantalla.blit(brillo, brillo.get_rect(center=(x, y)))
            self._dibujar_aviso_estado(p["estado"], x, y, radio)
        self.pantalla.blit(sprite, sprite.get_rect(center=(x, y)))

    def _dibujar_aviso_estado(self, estado, x, y, radio):
        """Anillo por detrás del picker: amarillo pulsante si espera, rojo si está bloqueado."""
        if estado == "esperando":
            pulso = 2 + 2 * math.sin(self.anim.t * 8)
            self.pincel.anillo(x, y, int(radio + 4 + pulso), cfg.AMARILLO, 2)
        elif estado == "bloqueado":
            self.pincel.anillo(x, y, radio + 6, cfg.ROJO, 3)

    # ---------- leyenda y tooltip ----------

    def _dibujar_leyenda(self):
        f = self.fuentes.chico
        p = self.pincel
        y = 732
        x = 44
        pygame.draw.rect(self.pantalla, mapa.PASILLO_A, (x, y + 1, 24, 14), border_radius=3)
        trazo = [(x + 9, y + 4), (x + 15, y + 8), (x + 9, y + 12)]
        pygame.draw.lines(self.pantalla, mapa.CHEVRON, False, trazo, 2)
        x += 24 + 6 + p.texto("Pasillo (flecha = sentido)", f, cfg.APAGADO, x + 30, y) + 20
        pygame.draw.rect(self.pantalla, mapa.RACK_FONDO, (x, y + 1, 22, 14), border_radius=3)
        pygame.draw.line(self.pantalla, mapa.RACK_VIGA, (x + 11, y + 3), (x + 11, y + 13), 2)
        pygame.draw.rect(self.pantalla, mapa.RACK_MARCO, (x, y + 1, 22, 14), 1, border_radius=3)
        x += 22 + 6 + p.texto("Rack", f, cfg.APAGADO, x + 28, y) + 20
        self.pantalla.blit(self.cartones.obtener(16, "pendiente"), (x, y))
        x += 16 + 6 + p.texto("A recoger", f, cfg.APAGADO, x + 22, y) + 20
        self.pantalla.blit(self.cartones.obtener(16, "recogido"), (x, y))
        x += 16 + 6 + p.texto("Recogido", f, cfg.APAGADO, x + 22, y) + 20
        pygame.draw.rect(self.pantalla, mapa.DESPACHO_ABAJO, (x, y + 1, 22, 14))
        pygame.draw.rect(self.pantalla, mapa.DESPACHO_BORDE, (x, y + 1, 22, 14), 1)
        for ex, ey, sx, sy in ((x, y + 1, 1, 1), (x + 21, y + 1, -1, 1), (x, y + 14, 1, -1), (x + 21, y + 14, -1, -1)):
            pygame.draw.line(self.pantalla, mapa.ESQUINERO, (ex, ey), (ex + sx * 5, ey), 2)
            pygame.draw.line(self.pantalla, mapa.ESQUINERO, (ex, ey), (ex, ey + sy * 5), 2)
        x += 22 + 6 + p.texto("Despacho", f, cfg.APAGADO, x + 28, y) + 20
        pygame.draw.rect(self.pantalla, mapa.PUERTA_MARCO, (x - 1, y + 3, 22, 11), border_radius=3)
        pygame.draw.rect(self.pantalla, mapa.PUERTA_ARRIBA, (x + 3, y + 5, 14, 7), border_radius=2)
        pygame.draw.rect(self.pantalla, mapa.ESQUINERO, (x, y + 4, 4, 9), border_radius=1)
        pygame.draw.rect(self.pantalla, mapa.ESQUINERO, (x + 16, y + 4, 4, 9), border_radius=1)
        x += 20 + 6 + p.texto("Puerta", f, cfg.APAGADO, x + 26, y) + 20
        p.circulo_alfa(x + 7, y + 8, 5, (255, 255, 255), 170)
        p.texto("Interseccion (I)", f, cfg.APAGADO, x + 20, y)

    def dibujar_tooltip(self):
        mx, my = pygame.mouse.get_pos()
        celda = self.grilla.celda_en(mx, my)
        if celda is None:
            return
        pila = self.sesion.pilas.get(celda)
        if not pila:
            return
        lineas = [f"Pila ({celda[0]}, {celda[1]})"]
        for producto in sorted(pila, key=_z_de_producto):
            marca = "  (a recoger)" if producto.id in self.sesion.pendientes_ids else ""
            lineas.append(
                f"z{producto.ubicacion[2]}  {producto.id}  stock {producto.stock}  "
                f"{producto.peso_kg:g} kg{marca}"
            )
        ancho = 250
        alto = 12 + len(lineas) * 20
        x = min(mx + 16, cfg.ANCHO - ancho - 10)
        y = min(my + 12, cfg.ALTO - alto - 10)
        pygame.draw.rect(self.pantalla, (10, 14, 24), (x, y, ancho, alto), border_radius=8)
        pygame.draw.rect(self.pantalla, cfg.ACENTO, (x, y, ancho, alto), 1, border_radius=8)
        for i, linea in enumerate(lineas):
            fuente = self.fuentes.negrita if i == 0 else self.fuentes.chico
            color = cfg.TEXTO if i == 0 else cfg.APAGADO
            self.pincel.texto(linea, fuente, color, x + 10, y + 8 + i * 20)