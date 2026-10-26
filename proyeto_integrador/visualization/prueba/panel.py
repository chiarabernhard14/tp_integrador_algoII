"""Panel lateral: botones, tarjetas de pickers, pedidos y registro."""

import pygame

from . import config as cfg
from .widgets import Boton, dibujar_boton


class PanelLateral:

    def __init__(self, pincel, fuentes, sesion, animacion):
        self.pincel = pincel
        self.pantalla = pincel.pantalla
        self.fuentes = fuentes
        self.sesion = sesion
        self.anim = animacion
        self.botones = []
        self._crear_botones()

    def _crear_botones(self):
        b = self.botones
        # Simulación
        b.append(Boton("iniciar", "Iniciar", 900, 72, 62, 34, (22, 163, 74)))
        b.append(Boton("pausar", "Pausar", 968, 72, 62, 34))
        b.append(Boton("continuar", "Continuar", 1036, 72, 76, 34))
        b.append(Boton("reiniciar", "Reiniciar", 1118, 72, 70, 34))
        b.append(Boton("paso", "Paso", 1194, 72, 52, 34))
        # Velocidad
        b.append(Boton("vel_menos", "-", 1160, 118, 36, 26))
        b.append(Boton("vel_mas", "+", 1204, 118, 36, 26))
        # Escenarios, partidas y editor
        b.append(Boton("generar", "Generar escenario", 900, 156, 166, 30))
        b.append(Boton("cargar_escenario", "Cargar escenario", 1074, 156, 166, 30))
        b.append(Boton("guardar_escenario", "Guardar escenario", 900, 194, 166, 30))
        b.append(Boton("cargar_partida", "Cargar partida", 1074, 194, 166, 30))
        b.append(Boton("guardar_partida", "Guardar partida", 900, 232, 340, 30))

    def boton_en(self, pos):
        """Nombre del botón bajo el mouse, o None."""
        for boton in self.botones:
            if boton.rect.collidepoint(pos):
                return boton.nombre
        return None

    # ---------- dibujo ----------

    def dibujar(self):
        pygame.draw.rect(self.pantalla, cfg.PANEL, (880, 20, 380, 740), border_radius=18)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUELO, (880, 20, 380, 740), 2, border_radius=18)
        self.pincel.texto("WAVE PICKING", self.fuentes.sub, cfg.ACENTO, 900, 32)
        self.pincel.texto("Algoritmos II", self.fuentes.chico, cfg.APAGADO, 1240, 38, "der")
        for boton in self.botones:
            self._dibujar_boton(boton)
        self.pincel.texto(f"Velocidad  x{self.anim.velocidad():g}", self.fuentes.chico,
                          cfg.TEXTO, 900, 124)
        self._dibujar_tarjetas_pickers()
        self._dibujar_pedidos()
        self._dibujar_log()

    def _dibujar_boton(self, boton):
        dibujar_boton(self.pantalla, self.fuentes.normal, boton.rect, boton.texto, boton.color)

    def _dibujar_tarjetas_pickers(self):
        sesion = self.sesion
        p_ = self.pincel
        f = self.fuentes
        p_.texto("PICKERS", f.mini, cfg.APAGADO, 900, 276)
        lista = sesion.estado["pickers"]
        for i, p in enumerate(lista[:cfg.MAX_TARJETAS]):
            y = 294 + i * 48
            color = cfg.COLORES_PICKER[i % len(cfg.COLORES_PICKER)]
            pygame.draw.rect(self.pantalla, cfg.TARJETA, (900, y, 340, 44), border_radius=8)
            pygame.draw.rect(self.pantalla, cfg.BORDE, (900, y, 340, 44), 1, border_radius=8)
            pygame.draw.rect(self.pantalla, color, (900, y + 6, 5, 32), border_radius=2)
            p_.texto(p["id"], f.negrita, cfg.TEXTO, 914, y + 3)
            nombre = cfg.NOMBRE_ESTADO_PICKER.get(p["estado"], p["estado"])
            color_estado = cfg.COLOR_ESTADO_PICKER.get(p["estado"], cfg.TEXTO)
            p_.texto(nombre, f.chico, color_estado, 1232, y + 5, "der")
            objetivo = p["objetivo"] if p["objetivo"] is not None else "-"
            capacidad = sesion.capacidades.get(p["id"], 0)
            linea = (f"Objetivo {objetivo}   Pend. {len(p['pendientes'])}   "
                     f"Recog. {len(p['recogidos'])}   Cap. {capacidad:g} kg")
            p_.texto(p_.recortar(linea, f.mini, 320), f.mini, cfg.APAGADO, 914, y + 26)
        if len(lista) > cfg.MAX_TARJETAS:
            extra = len(lista) - cfg.MAX_TARJETAS
            p_.texto(f"+{extra} pickers mas", f.chico, cfg.APAGADO, 900,
                     294 + cfg.MAX_TARJETAS * 48 - 2)

    def _dibujar_pedidos(self):
        p_ = self.pincel
        f = self.fuentes
        p_.texto("PEDIDOS DE LA WAVE", f.mini, cfg.APAGADO, 900, 556)
        pedidos = self.sesion.sim.pedidos_wave
        for i, pedido in enumerate(pedidos[:cfg.MAX_PEDIDOS]):
            y = 574 + i * 24
            pygame.draw.rect(self.pantalla, cfg.TARJETA, (900, y, 340, 20), border_radius=6)
            p_.texto(pedido.id, f.chico, cfg.TEXTO, 910, y + 3)
            for k in range(5):
                relleno = cfg.AMARILLO if k < pedido.prioridad else (96, 102, 116)
                p_.circulo(986 + k * 10, y + 10, 3, relleno)
            p_.texto(f"{len(pedido.items)} items", f.mini, cfg.APAGADO, 1050, y + 5)
            color = cfg.COLOR_ESTADO_PEDIDO.get(pedido.estado, cfg.APAGADO)
            p_.texto(pedido.estado, f.mini, color, 1230, y + 5, "der")
        if len(pedidos) > cfg.MAX_PEDIDOS:
            extra = len(pedidos) - cfg.MAX_PEDIDOS
            p_.texto(f"+{extra} pedidos mas", f.mini, cfg.APAGADO, 1240, 556, "der")

    def _dibujar_log(self):
        p_ = self.pincel
        f = self.fuentes
        p_.texto("REGISTRO", f.mini, cfg.APAGADO, 900, 676)
        lineas = self.sesion.estado["log"][-cfg.LINEAS_LOG:]
        for i, linea in enumerate(lineas):
            p_.texto(p_.recortar(linea, f.mini, 340), f.mini, cfg.TEXTO, 900, 692 + i * 14)