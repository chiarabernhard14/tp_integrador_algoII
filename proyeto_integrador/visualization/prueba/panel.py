"""Paneles laterales para los controles y el seguimiento de waves."""

import pygame

from . import config as cfg
from .widgets import Boton, dibujar_boton


class PanelLateral:
    """Contenedor continuo de controles de simulación y estado de pickers."""

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
        b.append(Boton("algoritmo_a_estrella", "A*", 976, 104, 100, 30))
        b.append(Boton("algoritmo_dijkstra", "Dijkstra", 1084, 104, 236, 30))
        b.append(Boton("estrategia_orden", "Orden", 976, 148, 100, 28))
        b.append(Boton("estrategia_cercania", "Cercanía", 1084, 148, 128, 28))
        b.append(Boton("estrategia_zonas", "Zonas", 1220, 148, 100, 28))
        b.append(Boton("iniciar", "Iniciar", 900, 198, 76, 38, (22, 163, 74)))
        b.append(Boton("pausar", "Pausar", 982, 198, 76, 38))
        b.append(Boton("continuar", "Continuar", 1064, 198, 84, 38))
        b.append(Boton("reiniciar", "Reiniciar", 1154, 198, 84, 38))
        b.append(Boton("paso", "Paso", 1244, 198, 76, 38))
        b.append(Boton("vel_menos", "-", 1236, 248, 36, 30))
        b.append(Boton("vel_mas", "+", 1284, 248, 36, 30))
        b.append(Boton("generar", "Generar escenario", 900, 300, 204, 38))
        b.append(Boton("cargar_escenario", "Cargar escenario", 1112, 300, 208, 38))
        b.append(Boton("guardar_escenario", "Guardar escenario", 900, 348, 204, 38))
        b.append(Boton("cargar_partida", "Cargar partida", 1112, 348, 208, 38))
        b.append(Boton("guardar_partida", "Guardar partida", 900, 396, 420, 38))

    def boton_en(self, pos):
        for boton in self.botones:
            if boton.rect.collidepoint(pos):
                return boton.nombre
        return None

    def dibujar(self):
        pygame.draw.rect(self.pantalla, cfg.PANEL, (880, 20, 460, 860), border_radius=18)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUELO, (880, 20, 460, 860), 2, border_radius=18)
        p = self.pincel
        f = self.fuentes
        p.texto("SIMULACIÓN", f.sub, cfg.ACENTO, 900, 76)
        p.texto("Camino", f.mini, cfg.APAGADO, 900, 112)
        p.texto("Recorrido", f.mini, cfg.APAGADO, 900, 156)
        for boton in self.botones:
            self._dibujar_boton(boton)
        p.texto(f"Velocidad  x{self.anim.velocidad():g}", f.chico, cfg.TEXTO, 900, 258)
        self._dibujar_pickers()

    def _dibujar_boton(self, boton):
        algoritmos = {
            "algoritmo_a_estrella": "a_estrella",
            "algoritmo_dijkstra": "dijkstra",
        }
        estrategias = {
            "estrategia_orden": "orden",
            "estrategia_cercania": "cercania",
            "estrategia_zonas": "zonas",
        }
        activo = (
            (boton.nombre in algoritmos
             and self.sesion.algoritmo_camino == algoritmos[boton.nombre])
            or (boton.nombre in estrategias
                and self.sesion.estrategia_recorrido == estrategias[boton.nombre])
        )
        selector = boton.nombre in algoritmos or boton.nombre in estrategias
        dibujar_boton(
            self.pantalla,
            self.fuentes.chico if selector else self.fuentes.normal,
            boton.rect,
            boton.texto,
            boton.color,
            activo=activo,
        )

    def _dibujar_pickers(self):
        p = self.pincel
        f = self.fuentes
        pickers = self.sesion.estado["pickers"]
        visibles = pickers[:cfg.MAX_TARJETAS]
        p.texto(f"PICKERS ({len(pickers)})", f.mini, cfg.APAGADO, 900, 480)
        y_inicio = 510 if len(visibles) != 1 else 640
        y_final = 790
        alto_tarjeta = 62
        if len(visibles) > 1:
            paso = min(220, max(alto_tarjeta + 12, (y_final - y_inicio) // (len(visibles) - 1)))
        else:
            paso = 0
        for i, picker in enumerate(visibles):
            y = y_inicio + i * paso
            color = cfg.COLORES_PICKER[i % len(cfg.COLORES_PICKER)]
            pygame.draw.rect(self.pantalla, cfg.TARJETA, (900, y, 420, alto_tarjeta), border_radius=8)
            pygame.draw.rect(self.pantalla, cfg.BORDE, (900, y, 420, alto_tarjeta), 1, border_radius=8)
            pygame.draw.rect(self.pantalla, color, (900, y + 9, 5, 44), border_radius=2)
            p.texto(picker["id"], f.negrita, cfg.TEXTO, 914, y + 7)
            nombre = cfg.NOMBRE_ESTADO_PICKER.get(picker["estado"], picker["estado"])
            color_estado = cfg.COLOR_ESTADO_PICKER.get(picker["estado"], cfg.TEXTO)
            p.texto(nombre, f.chico, color_estado, 1310, y + 10, "der")
            objetivo = picker["objetivo"] if picker["objetivo"] is not None else "-"
            capacidad = self.sesion.capacidades.get(picker["id"], 0)
            detalle = (f"Objetivo {objetivo}   Pend. {len(picker['pendientes'])}   "
                       f"A bordo {len(picker['recogidos'])}   Cap. {capacidad:g} kg")
            p.texto(p.recortar(detalle, f.chico, 400), f.chico, cfg.APAGADO, 914, y + 39)
        if len(pickers) > cfg.MAX_TARJETAS:
            p.texto(f"+{len(pickers) - cfg.MAX_TARJETAS} pickers más",
                    f.chico, cfg.APAGADO, 1310, 480, "der")


class PanelWaves:
    """Columna de ticks, estado de cada wave y registro de eventos."""

    X = 1360
    ANCHO = 380
    MAX_WAVES = 8
    MAX_LOG = 8
    ALTO_TARJETA = 52
    PASO_TARJETA = 64

    COLORES_WAVE = {
        "CREADA": cfg.APAGADO,
        "PENDIENTE": cfg.APAGADO,
        "ASIGNADA": cfg.ACENTO,
        "EN_PROCESO": cfg.ACENTO,
        "COMPLETADA": cfg.VERDE,
        "INCOMPLETA": cfg.NARANJA,
    }

    NOMBRES_WAVE = {
        "CREADA": "En cola",
        "PENDIENTE": "En cola",
        "ASIGNADA": "Asignada",
        "EN_PROCESO": "En curso",
        "COMPLETADA": "Completada",
        "INCOMPLETA": "Incompleta",
    }

    def __init__(self, pincel, fuentes, sesion):
        self.pincel = pincel
        self.pantalla = pincel.pantalla
        self.fuentes = fuentes
        self.sesion = sesion

    def dibujar(self):
        x = self.X
        ancho = self.ANCHO
        pygame.draw.rect(self.pantalla, cfg.PANEL, (x, 20, ancho, 860), border_radius=18)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUELO, (x, 20, ancho, 860), 2, border_radius=18)

        p = self.pincel
        f = self.fuentes
        estado = self.sesion.estado
        p.texto("TICKS Y WAVES", f.sub, cfg.ACENTO, x + 20, 76)
        estado_sim = "Finalizada" if estado.get("terminada") else (
            "En curso" if self.sesion.corriendo else "En pausa"
        )
        p.texto(f"Tick {estado['tick']}  ·  {estado_sim}", f.chico, cfg.TEXTO, x + 20, 128)
        p.texto("ESTADO DE WAVES", f.mini, cfg.APAGADO, x + 20, 164)

        waves = estado.get("waves", [])
        visibles = waves[:self.MAX_WAVES]
        y_inicio = 200 if len(visibles) != 1 else 390
        y_final = 600
        if len(visibles) > 1:
            paso = min(220, max(self.ALTO_TARJETA + 10,
                                (y_final - y_inicio) // (len(visibles) - 1)))
        else:
            paso = 0
        for indice, wave in enumerate(visibles):
            self._dibujar_wave(wave, y_inicio + indice * paso)
        if len(waves) > self.MAX_WAVES:
            y_mas = y_inicio + (len(visibles) - 1) * paso + self.ALTO_TARJETA + 8
            p.texto(f"+{len(waves) - self.MAX_WAVES} waves más", f.mini,
                    cfg.APAGADO, x + 20, min(830, y_mas))
        else:
            y_mas = None

        y_ultima = y_inicio + (len(visibles) - 1) * paso if visibles else 164
        y_log = max(650, y_ultima + self.ALTO_TARJETA + 30)
        if y_mas is not None:
            y_log = max(y_log, y_mas + 26)
        y_log = min(y_log, 730)
        lineas_visibles = max(1, min(self.MAX_LOG, (875 - y_log - 18) // 22 + 1))
        self._dibujar_log(y_log, lineas_visibles)

    def _dibujar_wave(self, wave, y):
        x = self.X + 20
        ancho = self.ANCHO - 40
        pygame.draw.rect(self.pantalla, cfg.TARJETA, (x, y, ancho, self.ALTO_TARJETA), border_radius=8)
        pygame.draw.rect(self.pantalla, cfg.BORDE, (x, y, ancho, self.ALTO_TARJETA), 1, border_radius=8)

        estado = str(wave.get("estado", "CREADA")).upper()
        nombre_estado = self.NOMBRES_WAVE.get(estado, estado.replace("_", " ").title())
        color = self.COLORES_WAVE.get(estado, cfg.APAGADO)
        p = self.pincel
        f = self.fuentes
        p.texto(str(wave.get("id", "Wave")), f.negrita, cfg.TEXTO, x + 10, y + 4)
        p.texto(nombre_estado, f.mini, color, x + ancho - 10, y + 6, "der")
        pickers = self._pickers_asignados(wave)
        detalle = self._detalle_progreso(wave)
        p.texto(f"Pickers: {pickers}   ·   {detalle}", f.chico, cfg.APAGADO, x + 10, y + 29)

    def _pickers_asignados(self, wave):
        wave_id = str(wave.get("id", ""))
        asignados = [
            str(picker["id"])
            for picker in self.sesion.estado.get("pickers", [])
            if str(picker.get("wave_id")) == wave_id
        ]
        return ", ".join(asignados) if asignados else "—"

    def _detalle_progreso(self, wave):
        productos = wave.get("productos")
        pendientes = wave.get("pendiente")
        if isinstance(productos, list) and isinstance(pendientes, dict):
            total = sum(linea.get("cantidad", 0) for linea in productos)
            quedan = sum(pendientes.values())
            return f"Recogidas {max(0, total - quedan)}/{total} u."

        ids_pedidos = wave.get("pedidos")
        if ids_pedidos:
            return f"{len(ids_pedidos)} pedidos"
        return "Progreso no disponible"

    def _dibujar_log(self, y_titulo, cantidad_lineas):
        p = self.pincel
        f = self.fuentes
        x = self.X + 20
        p.texto("REGISTRO POR TICK", f.mini, cfg.APAGADO, x, y_titulo)
        lineas = self.sesion.estado.get("log", [])[-cantidad_lineas:]
        for i, linea in enumerate(lineas):
            p.texto(p.recortar(linea, f.mini, self.ANCHO - 40), f.mini,
                    cfg.TEXTO, x, y_titulo + 18 + i * 22)
