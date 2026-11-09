"""Paneles laterales para los controles y el seguimiento de waves."""

import pygame

from . import Config as cfg
from .Widgets import Boton, dibujar_boton, pos_mouse


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
        x = cfg.PANEL_SIM_X + 20
        # Los selectores comparten el ancho completo del panel.
        b.append(Boton("algoritmo_a_estrella", "A*", x, 94, 180, 36))
        b.append(Boton("algoritmo_dijkstra", "Dijkstra", x + 180, 94, 180, 36))
        
        # Grupo 2: Estrategias de recorrido (mismo ancho entre las tres)
        b.append(Boton("estrategia_orden", "Orden", x, 168, 120, 34))
        b.append(Boton("estrategia_cercania", "Cercanía", x + 120, 168, 120, 34))
        b.append(Boton("estrategia_zonas", "Zonas", x + 240, 168, 120, 34))
        
        # Grupo 3: Controles de reproducción
        ancho_accion = 114
        b.append(Boton("iniciar", "Iniciar", x, 220, ancho_accion, 40, (22, 163, 74)))
        b.append(Boton("pausar", "Pausar", x + 123, 220, ancho_accion, 40))
        b.append(Boton("continuar", "Continuar", x + 246, 220, ancho_accion, 40))
        b.append(Boton("reiniciar", "Reiniciar", x, 272, 176, 40))
        b.append(Boton("paso", "Paso", x + 184, 272, 176, 40))
        
        # Controles de velocidad
        b.append(Boton("vel_menos", "−", x + 216, 328, 28, 28))
        b.append(Boton("vel_mas", "+", x + 320, 328, 28, 28))
        
        # Grupo 4: Gestión de escenarios y partidas
        b.append(Boton("generar", "Generar escenario", x, 370, 176, 40))
        b.append(Boton("cargar_escenario", "Cargar escenario", x + 184, 370, 176, 40))
        b.append(Boton("guardar_escenario", "Guardar escenario", x, 420, 176, 40))
        b.append(Boton("cargar_partida", "Cargar partida", x + 184, 420, 176, 40))
        
        # Botón inferior de guardado
        b.append(Boton("guardar_partida", "Guardar partida", x, 470, 360, 40))

    def boton_en(self, pos):
        for boton in self.botones:
            if boton.rect.collidepoint(pos):
                return boton.nombre
        return None

    def dibujar(self):
        pygame.draw.rect(self.pantalla, cfg.TARJETA_PANEL,
                         (cfg.PANEL_SIM_X, 20, cfg.PANEL_SIM_W, 860), border_radius=12)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUTIL,
                         (cfg.PANEL_SIM_X, 20, cfg.PANEL_SIM_W, 860), 1, border_radius=12)
        p = self.pincel
        f = self.fuentes
        
        # Títulos y etiquetas con fuente normal y tono más claro.
        x = cfg.PANEL_SIM_X + 20
        p.texto("SIMULACIÓN", f.negrita, cfg.ACENTO, x, 40)
        p.texto("Camino", f.normal, cfg.TEXTO_SUAVE, x, 66)
        p.texto("Recorrido", f.normal, cfg.TEXTO_SUAVE, x, 140)
        
        self._dibujar_selector_segmentado(
            ("algoritmo_a_estrella", "algoritmo_dijkstra"), self.sesion.algoritmo_camino,
            {"algoritmo_a_estrella": "a_estrella", "algoritmo_dijkstra": "dijkstra"},
        )
        self._dibujar_selector_segmentado(
            ("estrategia_orden", "estrategia_cercania", "estrategia_zonas"),
            self.sesion.estrategia_recorrido,
            {"estrategia_orden": "orden", "estrategia_cercania": "cercania",
             "estrategia_zonas": "zonas"},
        )
        selectores = {"algoritmo_a_estrella", "algoritmo_dijkstra",
                      "estrategia_orden", "estrategia_cercania", "estrategia_zonas",
                      "vel_menos", "vel_mas"}
        for boton in self.botones:
            if boton.nombre not in selectores:
                self._dibujar_boton(boton)
            
        self._dibujar_velocidad()
        self._dibujar_pickers()

    def _dibujar_velocidad(self):
        """Tarjeta de velocidad: etiqueta, barras de nivel, − [xN] +."""
        p = self.pincel
        f = self.fuentes
        x = cfg.PANEL_SIM_X + 20
        nivel = self.anim.vel_idx
        total = len(cfg.VELOCIDADES)

        tarjeta = pygame.Rect(x, 324, 360, 36)
        # Mismo relleno, borde y tipografía que los botones de alrededor.
        pygame.draw.rect(self.pantalla, (75, 82, 99), tarjeta, border_radius=10)
        pygame.draw.rect(self.pantalla, (110, 120, 140), tarjeta, 2, border_radius=10)
        p.texto("Velocidad", f.negrita, (255, 255, 255), tarjeta.x + 16,
                tarjeta.centery - f.negrita.get_height() // 2)

        # Barras ascendentes, como un indicador de señal: las activas van en azul.
        base = tarjeta.centery + 9
        for i in range(total):
            alto = 6 + 3 * i
            barra = pygame.Rect(x + 110 + i * 16, base - alto, 10, alto)
            color = cfg.ACENTO if i <= nivel else cfg.PISTA_PROGRESO
            pygame.draw.rect(self.pantalla, color, barra, border_radius=2)

        pastilla = pygame.Rect(x + 252, 328, 60, 28)
        pygame.draw.rect(self.pantalla, cfg.PISTA_PROGRESO, pastilla, border_radius=14)
        pygame.draw.rect(self.pantalla, (110, 120, 140), pastilla, 1, border_radius=14)
        p.texto(f"x{self.anim.velocidad():g}", f.negrita, (255, 255, 255),
                pastilla.centerx, pastilla.centery, "cc")

        mouse = pos_mouse()
        for boton in self.botones:
            if boton.nombre not in ("vel_menos", "vel_mas"):
                continue
            es_mas = boton.nombre == "vel_mas"
            habilitado = nivel < total - 1 if es_mas else nivel > 0
            sobre = habilitado and boton.rect.collidepoint(mouse)
            if not habilitado:
                fondo, borde, trazo = (58, 62, 72), (88, 94, 106), (130, 136, 150)
            elif sobre:
                fondo, borde, trazo = (58, 112, 190), (140, 188, 255), (255, 255, 255)
            else:
                fondo, borde, trazo = (58, 64, 78), (160, 170, 190), (255, 255, 255)
            cx, cy = boton.rect.center
            pygame.draw.circle(self.pantalla, fondo, (cx, cy), 14)
            pygame.draw.circle(self.pantalla, borde, (cx, cy), 14, 2)
            pygame.draw.line(self.pantalla, trazo, (cx - 6, cy), (cx + 6, cy), 2)
            if es_mas:
                pygame.draw.line(self.pantalla, trazo, (cx, cy - 6), (cx, cy + 6), 2)

    def _dibujar_selector_segmentado(self, nombres, valor_actual, valores):
        botones = [next(b for b in self.botones if b.nombre == nombre) for nombre in nombres]
        contenedor = botones[0].rect.unionall([b.rect for b in botones[1:]])
        pygame.draw.rect(self.pantalla, cfg.PISTA_PROGRESO, contenedor, border_radius=10)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUTIL, contenedor, 1, border_radius=10)
        for boton in botones:
            if valores[boton.nombre] == valor_actual:
                pygame.draw.rect(self.pantalla, (58, 112, 190),
                                 boton.rect.inflate(-4, -4), border_radius=8)
                color = (255, 255, 255)
            else:
                color = cfg.TEXTO_SUAVE
            self.pincel.texto(boton.texto, self.fuentes.negrita, color,
                              boton.rect.centerx, boton.rect.centery, "cc")

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
        
        # Forzamos f.negrita en todos los botones para que el texto sea más grueso
        dibujar_boton(
            self.pantalla,
            self.fuentes.negrita,
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

        x = cfg.PANEL_SIM_X + 20
        ancho = cfg.PANEL_SIM_W - 40
        p.texto(f"PICKERS ({len(pickers)})", f.negrita, cfg.TEXTO, x, 520)
        if len(pickers) > cfg.MAX_TARJETAS:
            p.texto(f"+{len(pickers) - cfg.MAX_TARJETAS} más", f.normal,
                    cfg.TEXTO_SUAVE, x + ancho, 521, "der")

        for i, picker in enumerate(visibles):
            self._dibujar_tarjeta_picker(i, picker, 546 + i * 80)

    def _carga_picker(self, picker):
        """Kilos que lleva encima: lo recogido en el viaje actual."""
        trabajo_id = picker.get("trabajo_id")
        if trabajo_id is None:
            return 0.0
        productos = self.sesion.sim.productos
        total = 0.0
        for recogido in picker["recogidos"]:
            if recogido.get("trabajo_id") != trabajo_id:
                continue
            producto = productos.get(recogido["producto_id"])
            if producto is not None:
                total += producto.peso_kg * recogido["cantidad"]
        return total

    def _dibujar_pildora_estado(self, x_derecha, y, texto, color):
        f = self.fuentes
        ancho = f.chico.size(texto)[0] + 32
        x = x_derecha - ancho
        self.pincel.rect_alfa(x, y, ancho, 22, (color[0], color[1], color[2], 55), 11)
        pygame.draw.rect(self.pantalla, color, (x, y, ancho, 22), 1, border_radius=11)
        pygame.draw.circle(self.pantalla, color, (x + 13, y + 11), 4)
        self.pincel.texto(texto, f.chico, (255, 255, 255), x + 22,
                          y + 11 - f.chico.get_height() // 2)

    def _dibujar_tarjeta_picker(self, indice, picker, y):
        p = self.pincel
        f = self.fuentes
        x = cfg.PANEL_SIM_X + 20
        ancho = cfg.PANEL_SIM_W - 40
        alto = 76
        color = cfg.COLORES_PICKER[indice % len(cfg.COLORES_PICKER)]
        estado = picker["estado"]
        color_estado = cfg.COLOR_ESTADO_PICKER.get(estado, cfg.TEXTO)
        alerta = estado in ("esperando", "bloqueado")

        # Fondo; si el picker espera o está bloqueado, el borde toma el color del estado.
        pygame.draw.rect(self.pantalla, cfg.TARJETA, (x, y, ancho, alto), border_radius=10)
        pygame.draw.rect(self.pantalla, color_estado if alerta else cfg.BORDE_SUTIL,
                         (x, y, ancho, alto), 2 if alerta else 1, border_radius=10)
        pygame.draw.rect(self.pantalla, color, (x + 1, y + 10, 6, alto - 20), border_radius=3)

        # Fila 1: identificador, producto objetivo y estado.
        ancho_id = p.texto(picker["id"], f.negrita, cfg.BLANCO_SUAVE, x + 18, y + 8)
        if picker["objetivo"] is not None:
            p.texto(f"→ {picker['objetivo']}", f.chico, cfg.TEXTO_SUAVE,
                    x + 18 + ancho_id + 8, y + 11)
        nombre = cfg.NOMBRE_ESTADO_PICKER.get(estado, estado)
        self._dibujar_pildora_estado(x + ancho - 12, y + 7, nombre, color_estado)

        # Fila 2: barra de carga (sólido = recogido, tenue = reservado para el viaje).
        capacidad = self.sesion.capacidades.get(picker["id"], 0)
        carga = self._carga_picker(picker)
        trabajo = picker.get("trabajo")
        reservado = trabajo["peso"] if trabajo else 0.0
        etiqueta = f"Carga {carga:.1f} / {capacidad:g} kg"
        ancho_etiqueta = p.texto(etiqueta, f.normal, (255, 255, 255),
                                 x + ancho - 14, y + 32, "der")
        barra = pygame.Rect(x + 18, y + 36, ancho - 18 - 14 - ancho_etiqueta - 12, 12)
        pygame.draw.rect(self.pantalla, cfg.PISTA_PROGRESO, barra, border_radius=6)
        if capacidad > 0:
            px_reservado = int(barra.w * min(1.0, reservado / capacidad))
            px_carga = int(barra.w * min(1.0, carga / capacidad))
            if px_reservado >= 3:
                p.rect_alfa(barra.x, barra.y, px_reservado, barra.h,
                            (color[0], color[1], color[2], 120), 6)
            if px_carga >= 3:
                pygame.draw.rect(self.pantalla, color,
                                 (barra.x, barra.y, px_carga, barra.h), border_radius=6)
        pygame.draw.rect(self.pantalla, (120, 130, 150), barra, 1, border_radius=6)

        # Fila 3: contadores, con el número apenas resaltado.
        contadores = (
            ("pend.", len(picker["pendientes"])),
            ("recogidos", len(picker["recogidos"])),
            ("entregas", len(picker.get("waves_hechas", []))),
            ("pasos", picker.get("pasos_trabajo", 0)),
        )
        cx = x + 18
        for etiqueta_contador, valor in contadores:
            ancho_valor = p.texto(str(valor), f.normal, cfg.BLANCO_SUAVE, cx, y + 54)
            ancho_texto = p.texto(etiqueta_contador, f.chico, cfg.TEXTO_SUAVE,
                                  cx + ancho_valor + 4, y + 57)
            cx += ancho_valor + ancho_texto + 16


class PanelWaves:
    """Panel derecho: métricas de ejecución, progreso de waves y registro."""

    X = cfg.PANEL_WAVES_X
    ANCHO = cfg.PANEL_WAVES_W
    PADDING = 24
    MAX_WAVES = 5
    MAX_LOG = 4

    ALTO_METRICA = 48
    PASO_METRICA = 52
    ALTO_WAVE = 68
    PASO_WAVE = 72

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

    # Las waves activas o incompletas se muestran antes que las resueltas.
    PRIORIDAD_WAVE = {
        "EN_PROCESO": 0,
        "ASIGNADA": 1,
        "INCOMPLETA": 2,
        "PENDIENTE": 3,
        "CREADA": 3,
        "COMPLETADA": 4,
    }

    def __init__(self, pincel, fuentes, sesion):
        self.pincel = pincel
        self.pantalla = pincel.pantalla
        self.fuentes = fuentes
        self.sesion = sesion
        self.desplazamiento = 0

    def desplazar(self, pasos):
        """Mueve la lista de waves visible (rueda del mouse)."""
        total = len(self.sesion.estado.get("waves", []))
        maximo = max(0, total - self.MAX_WAVES)
        self.desplazamiento = max(0, min(maximo, self.desplazamiento + pasos))

    def dibujar(self):
        x = self.X
        ancho = self.ANCHO
        pygame.draw.rect(self.pantalla, cfg.TARJETA_PANEL,
                         (x, 20, ancho, 860), border_radius=12)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUTIL,
                         (x, 20, ancho, 860), 1, border_radius=12)

        estado = self.sesion.estado
        self._dibujar_encabezado(estado)
        self._dibujar_metricas(estado)
        self._dibujar_resumen(estado)
        self._dibujar_waves(estado)
        self._dibujar_log()

    # ---------- encabezado ----------

    def _dibujar_encabezado(self, estado):
        p = self.pincel
        f = self.fuentes
        x = self.X + self.PADDING
        ancho = self.ANCHO - 2 * self.PADDING

        p.texto("MÉTRICAS", f.negrita, cfg.TEXTO, x, 44)

        if estado.get("terminada"):
            texto, color = "FINALIZADA", cfg.VERDE
        elif self.sesion.corriendo:
            texto, color = "EN CURSO", cfg.ACENTO
        else:
            texto, color = "EN PAUSA", cfg.AMARILLO
        self._dibujar_pildora(x + ancho, 45, texto, color)

        algoritmo = ("A*" if self.sesion.algoritmo_camino == "a_estrella"
                     else self.sesion.algoritmo_camino.title())
        estrategia = self.sesion.estrategia_recorrido.title()
        p.texto(f"{algoritmo}  ·  {estrategia}", f.chico, cfg.TEXTO_SUAVE, x, 70)

    def _dibujar_pildora(self, x_derecha, y, texto, color):
        p = self.pincel
        f = self.fuentes
        ancho = f.mini.size(texto)[0] + 20
        x = x_derecha - ancho
        p.rect_alfa(x, y, ancho, 18, (color[0], color[1], color[2], 46), 9)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUTIL, (x, y, ancho, 18), 1, border_radius=9)
        p.texto(texto, f.mini, color, x + ancho // 2, y + 3, "centro")

    # ---------- métricas ----------

    def _dibujar_metricas(self, estado):
        pickers = estado.get("pickers", [])
        waves = estado.get("waves", [])

        pasos = sum(p.get("pasos_trabajo", 0) for p in pickers)
        entregas = sum(len(p.get("waves_hechas", [])) for p in pickers)
        completadas = sum(
            1 for wave in waves
            if str(wave.get("estado", "")).upper() == "COMPLETADA"
        )

        unidades_total = 0
        unidades_hechas = 0
        for wave in waves:
            total, hechas = self._progreso_wave(wave, pickers)
            unidades_total += total
            unidades_hechas += hechas

        nodos, _, _ = self._metricas_planificador()
        tick_final = estado.get("tick_trabajo")

        tarjetas = (
            ("TICK ACTUAL", str(estado.get("tick", 0)), cfg.TEXTO),
            ("TICK FINAL", "—" if tick_final is None else str(tick_final),
             cfg.AMARILLO),
            ("WAVES", f"{completadas}/{len(waves)}", cfg.VERDE),
            ("UNIDADES", f"{unidades_hechas}/{unidades_total}", cfg.VERDE),
            ("DISTANCIA (PASOS)", self._formato_entero(pasos), cfg.ACENTO),
            ("NODOS EXP.", self._formato_entero(nodos), cfg.NARANJA),
            ("TIEMPO ASIGN.",
             self._formato_tiempo(estado.get("tiempo_asignacion_ms", 0.0)),
             cfg.AMARILLO),
            ("ASIGN. MÁX.",
             self._formato_tiempo(estado.get("max_asignacion_ms", 0.0)),
             cfg.NARANJA),
        )

        x = self.X + self.PADDING
        ancho_total = self.ANCHO - 2 * self.PADDING
        ancho = (ancho_total - 8) // 2
        for indice, (etiqueta, valor, color) in enumerate(tarjetas):
            columna = indice % 2
            fila = indice // 2
            x_tarjeta = x + columna * (ancho + 8)
            y_tarjeta = 94 + fila * self.PASO_METRICA
            self._dibujar_tarjeta_metrica(
                x_tarjeta, y_tarjeta, ancho, etiqueta, valor, color
            )

    def _dibujar_tarjeta_metrica(self, x, y, ancho, etiqueta, valor, color):
        p = self.pincel
        f = self.fuentes
        pygame.draw.rect(self.pantalla, cfg.TARJETA_METRICA,
                         (x, y, ancho, self.ALTO_METRICA), border_radius=9)
        p.texto(p.recortar(etiqueta, f.mini, ancho - 24), f.mini, cfg.APAGADO,
                x + 12, y + 5)
        p.texto(p.recortar(valor, f.sub, ancho - 24), f.sub, cfg.BLANCO_SUAVE,
                x + 12, y + 20)

    def _metricas_planificador(self):
        sim = getattr(self.sesion, "sim", None)
        planificador = getattr(sim, "planificador", None)
        nav = getattr(sim, "nav", None)
        nodos = getattr(planificador, "nodos_expandidos", 0)
        busquedas_plan = getattr(planificador, "busquedas", 0)
        busquedas_nav = getattr(nav, "busquedas", 0)
        return nodos, busquedas_plan, busquedas_nav

    def _dibujar_resumen(self, estado):
        p = self.pincel
        f = self.fuentes
        x = self.X + self.PADDING
        ancho = self.ANCHO - 2 * self.PADDING

        llamadas = estado.get("llamadas_asignacion", 0)
        total_ms = estado.get("tiempo_asignacion_ms", 0.0)
        promedio = total_ms / llamadas if llamadas else 0.0
        _, busquedas_plan, busquedas_nav = self._metricas_planificador()

        entregas = sum(len(p.get("waves_hechas", []))
                       for p in estado.get("pickers", []))
        linea_1 = (f"Prom. {self._formato_tiempo(promedio)}"
                   f"   ·   {llamadas} llamadas   ·   {entregas} entregas")
        linea_2 = (f"Saltos {estado.get('saltos', 0)}"
                   f"   ·   {self._formato_entero(busquedas_nav)} búsq. camino"
                   f"   ·   {self._formato_entero(busquedas_plan)} búsq. viajes")
        pygame.draw.rect(self.pantalla, cfg.TARJETA_METRICA,
                         (x, 308, ancho, 48), border_radius=9)
        p.texto(p.recortar(linea_1, f.mini, ancho - 24), f.mini,
                cfg.TEXTO_SUAVE, x + 12, 314)
        p.texto(p.recortar(linea_2, f.mini, ancho - 24), f.mini,
                cfg.TEXTO_SUAVE, x + 12, 332)

    # ---------- waves ----------

    def _dibujar_waves(self, estado):
        p = self.pincel
        f = self.fuentes
        x = self.X + self.PADDING
        ancho = self.ANCHO - 2 * self.PADDING

        waves = estado.get("waves", [])
        p.texto("WAVES", f.mini, cfg.TEXTO_SUAVE, x, 370)

        ordenadas = sorted(waves, key=self._clave_wave)
        total = len(ordenadas)
        maximo = max(0, total - self.MAX_WAVES)
        self.desplazamiento = min(self.desplazamiento, maximo)
        inicio = self.desplazamiento
        visibles = ordenadas[inicio:inicio + self.MAX_WAVES]

        if total > self.MAX_WAVES:
            rango = f"{inicio + 1}–{inicio + len(visibles)} de {total}"
        else:
            rango = f"{total} en total"
        p.texto(rango, f.mini, cfg.TEXTO_SUAVE, x + ancho, 370, "der")

        y_inicio = 390
        for indice, wave in enumerate(visibles):
            self._dibujar_wave(wave, y_inicio + indice * self.PASO_WAVE)

        if maximo:
            self._dibujar_barra_waves(x, ancho, y_inicio, total, maximo)

    def _dibujar_barra_waves(self, x, ancho, y_inicio, total, maximo):
        """Barra fina a la derecha: indica que hay más waves para recorrer."""
        alto = self.MAX_WAVES * self.PASO_WAVE - (self.PASO_WAVE - self.ALTO_WAVE)
        x_barra = x + ancho + 4
        pygame.draw.rect(self.pantalla, cfg.PISTA_PROGRESO,
                         (x_barra, y_inicio, 4, alto), border_radius=2)
        alto_thumb = max(18, int(alto * self.MAX_WAVES / total))
        recorrido = alto - alto_thumb
        y_thumb = y_inicio + int(recorrido * self.desplazamiento / maximo)
        pygame.draw.rect(self.pantalla, cfg.ACENTO,
                         (x_barra, y_thumb, 4, alto_thumb), border_radius=2)

    def _clave_wave(self, wave):
        estado = str(wave.get("estado", "CREADA")).upper()
        return (self.PRIORIDAD_WAVE.get(estado, 3),
                wave.get("numero", 0), str(wave.get("id", "")))

    def _dibujar_wave(self, wave, y):
        x = self.X + self.PADDING
        ancho = self.ANCHO - 2 * self.PADDING
        pygame.draw.rect(self.pantalla, cfg.TARJETA,
                         (x, y, ancho, self.ALTO_WAVE), border_radius=8)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUTIL,
                         (x, y, ancho, self.ALTO_WAVE), 1, border_radius=8)

        estado = str(wave.get("estado", "CREADA")).upper()
        nombre_estado = self.NOMBRES_WAVE.get(estado, estado.replace("_", " ").title())
        color = self.COLORES_WAVE.get(estado, cfg.APAGADO)
        pygame.draw.rect(self.pantalla, color,
                         (x, y + 12, 4, self.ALTO_WAVE - 24), border_radius=2)

        p = self.pincel
        f = self.fuentes
        p.texto(str(wave.get("id", "Wave")), f.negrita, cfg.TEXTO, x + 12, y + 10)
        p.texto(nombre_estado, f.mini, color, x + ancho - 12, y + 10, "der")

        pickers = self._pickers_asignados(wave)
        p.texto(p.recortar(f"Pickers: {pickers}", f.mini, ancho - 24),
                f.mini, cfg.TEXTO_SUAVE, x + 12, y + 31)

        total, hechas = self._progreso_wave(wave)
        ratio = hechas / total if total else (1.0 if estado == "COMPLETADA" else 0.0)
        ratio = max(0.0, min(1.0, ratio))

        y_barra = y + 53
        ancho_barra = ancho - 92
        pygame.draw.rect(self.pantalla, cfg.PISTA_PROGRESO,
                         (x + 12, y_barra, ancho_barra, 6), border_radius=3)
        if ratio > 0:
            pygame.draw.rect(self.pantalla, color,
                             (x + 12, y_barra, int(ancho_barra * ratio), 6),
                             border_radius=3)

        detalle = f"{self._formato_entero(total)} u." if not total else f"{hechas}/{total} u."
        p.texto(detalle, f.mini, cfg.TEXTO_SUAVE, x + ancho - 12, y + 49, "der")

    def _pickers_asignados(self, wave):
        wave_id = str(wave.get("id", ""))
        asignados = [
            str(picker["id"])
            for picker in self.sesion.estado.get("pickers", [])
            if str(picker.get("wave_id")) == wave_id
        ]
        return ", ".join(asignados) if asignados else "—"

    def _progreso_wave(self, wave, pickers=None):
        """Unidades recogidas de la wave según los pickers, no lo reservado."""
        productos = wave.get("productos")
        if not isinstance(productos, list):
            return 0, 0

        total = sum(linea.get("cantidad", 0) for linea in productos)
        if pickers is None:
            pickers = self.sesion.estado.get("pickers", [])
        wave_id = str(wave.get("id", ""))
        hechas = sum(
            recogido.get("cantidad", 0)
            for picker in pickers
            for recogido in picker.get("recogidos", [])
            if str(recogido.get("wave_id")) == wave_id
        )
        if str(wave.get("estado", "")).upper() == "COMPLETADA":
            hechas = total
        if total:
            hechas = min(hechas, total)
        return total, hechas

    # ---------- registro ----------

    def _dibujar_log(self):
        p = self.pincel
        f = self.fuentes
        x = self.X + self.PADDING
        ancho = self.ANCHO - 2 * self.PADDING
        y_titulo = 754

        p.texto("REGISTRO", f.mini, cfg.TEXTO_SUAVE, x, y_titulo)
        lineas = self.sesion.estado.get("log", [])[-self.MAX_LOG:]
        caja = pygame.Rect(x, y_titulo + 20, ancho, 86)
        pygame.draw.rect(self.pantalla, cfg.TARJETA_METRICA, caja, border_radius=9)
        for indice, linea in enumerate(lineas):
            p.texto(p.recortar(linea, f.mini, ancho - 24), f.mini, cfg.TEXTO,
                    x + 12, caja.y + 12 + indice * 15)

    # ---------- formato ----------

    @staticmethod
    def _formato_entero(valor):
        valor = int(valor)
        if valor >= 1_000_000:
            return f"{valor / 1_000_000:.1f}M"
        if valor >= 10_000:
            return f"{valor / 1_000:.1f}k"
        return str(valor)

    @staticmethod
    def _formato_tiempo(milisegundos):
        milisegundos = float(milisegundos)
        if milisegundos <= 0:
            return "0 ms"
        if milisegundos >= 1000:
            return f"{milisegundos / 1000:.2f} s"
        return f"{milisegundos:.1f} ms"