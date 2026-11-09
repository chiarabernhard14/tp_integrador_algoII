"""Pantalla "Generar escenario" con dos pestañas.

- Automático: los parámetros de generar_escenario (estantes, pasillos, productos, pedidos...).
- Manual: el editor de mapa con mouse, con su paleta de herramientas.

Solo maneja la interfaz: devuelve acciones y App se las pasa a la Sesion.
"""

import math

import pygame

from . import Config as cfg
from .EditorEsc import EditorEscenario
from .VistaPrevia import VistaPreviaEscenario
from .Widgets import (
    Button, Stepper, ToolButton, StatusBar,
    ListaPickersScroll, dibujar_boton, pos_mouse,
)

NIVELES_POR_RACK = 3     # niveles de producto por celda de rack que usa el generador (ScenarioV)

# (clave, etiqueta, mínimo, máximo, valor inicial, columna, fila)
PARAMETROS = (
    ("estantes", "Estantes", 1, 60, 6, 0, 0),
    ("pasillos_horizontales", "Pasillos horizontales", 2, 8, 2, 0, 1),
    ("alto_rack", "Alto de cada estante", 2, 14, 6, 0, 2),
    ("pickers", "Pickers", 1, 12, 2, 0, 3),
    ("peso_max_zona_kg", "Peso máx. despacho (kg)", 1, 100000, 500, 0, 4),
    ("productos", "Productos", 1, 400, 20, 1, 0),
    ("pedidos", "Pedidos", 1, 120, 8, 1, 1),
    ("max_productos_pedido", "Máx. productos por pedido", 1, 12, 4, 1, 2),
    ("max_orders_capacity", "Pedidos por wave", 0, 30, 3, 1, 3),
    ("max_products_capacity", "Productos por wave", 0, 80, 15, 1, 4),
)
LIMITES = {clave: (minimo, maximo) for clave, _e, minimo, maximo, _i, _c, _f in PARAMETROS}
MODOS = (("aleatoria", "Aleatoria"), ("agrupada", "Agrupada"), ("cerca_despacho", "Cerca del despacho"))
DESCRIPCION_MODO = {
    "aleatoria": ("Distribuidos al azar", "por todos los estantes."),
    "agrupada": ("Concentrados en un", "mismo sector del depósito."),
    "cerca_despacho": ("Priorizan los estantes", "cercanos al despacho."),
}
# (posición horizontal 0..1, fila de estante 0..2) para el dibujito de cada modo
PUNTOS_MODO = {
    "aleatoria": ((0.05, 0), (0.55, 0), (0.30, 1), (0.85, 1), (0.15, 2), (0.65, 2)),
    "agrupada": ((0.30, 0), (0.42, 0), (0.54, 0), (0.30, 1), (0.42, 1), (0.54, 1)),
    "cerca_despacho": ((0.70, 0), (0.85, 0), (0.70, 1), (0.85, 1), (0.70, 2), (0.85, 2)),
}

# Herramientas de dibujo (sin números en el botón)
HERRAMIENTAS_DIBUJO = (
    ("rack", "Rack"),
    ("despacho", "Despacho"),
    ("puerta", "Puerta"),
    ("pasillo", "Pasillo"),
    ("picker", "Picker"),
    ("producto", "Producto"),
)
# Acciones: (clave, nombre, atajo)
ACCIONES = (
    ("deshacer", "Deshacer", "Ctrl+Z"),
    ("borrar", "Borrar", "7"),
)
SENTIDOS = (
    ("N", "↑", "Norte"),
    ("S", "↓", "Sur"),
    ("E", "→", "Este"),
    ("O", "←", "Oeste"),
    ("AMBOS", "↔", "Libre"),
)

MAPA_MIN_X, MAPA_MAX_X = 8, 36
MAPA_MIN_Y, MAPA_MAX_Y = 8, 30

# Pestañas (zona izquierda)
TAB_AUTO = pygame.Rect(44, 34, 190, 42)
TAB_MANUAL = pygame.Rect(242, 34, 270, 42)
CONTENEDOR_TABS = pygame.Rect(40, 30, 476, 50)

# Panel derecho (se calcula dinámicamente en dibujar)
PANEL_DERECHO_X = cfg.PANEL_DERECHO_X
PANEL_DERECHO_Y = cfg.PANEL_DERECHO_Y
PANEL_DERECHO_W = cfg.PANEL_DERECHO_W
PANEL_DERECHO_H = cfg.PANEL_DERECHO_H

# Mapa del editor (zona izquierda)
MAPA_EDITOR_X = cfg.AREA_X
MAPA_EDITOR_Y = cfg.AREA_Y
MAPA_EDITOR_W = cfg.AREA_W
MAPA_EDITOR_H = cfg.AREA_H

# Formulario Automático (zona izquierda)
PASO_FILA = 76
TARJETA_WAREHOUSE = pygame.Rect(40, 96, 400, 464)
TARJETA_PRODUCTOS = pygame.Rect(452, 96, 408, 464)
TARJETA_MODO = pygame.Rect(40, 576, 820, 272)
ANCHO_STEPPER = 150

# Tiles y miniatura (panel derecho, Automático)
TILE_W = 402
TILE_H = 96
TARJETA_MINIATURA = pygame.Rect(PANEL_DERECHO_X + cfg.PANEL_PADDING, 358,
                                PANEL_DERECHO_W - 2 * cfg.PANEL_PADDING, 444)

# Paso del stepper
PASO_NORMAL = 1
PASO_SHIFT = 5

# Ayuda contextual por herramienta (una sola línea)
AYUDA_POR_HERRAMIENTA = {
    "rack": "Dibujá estantes.",
    "despacho": "Dibujá zonas de despacho en el borde.",
    "puerta": "Colocá una puerta de 1×1 en el borde.",
    "pasillo": "Dibujá pasillos con sentido de circulación.",
    "picker": "Hacé clic para colocar un picker.",
    "producto": "Hacé clic sobre un rack para agregar producto.",
    "borrar": "Modo borrador: hacé clic para eliminar.",
    "deshacer": "Deshacé la última acción (Ctrl+Z).",
}

AYUDA_GENERICA = "Arrastrá para dibujar; clic derecho cancela."

VERDE_BOTON = (22, 163, 74)

# Bloque de validación del editor (pestaña Manual): letra grande y alto contraste
ALTO_FILA_ESTADO = 36
ALTO_LINEA_ERROR = 22
PAD_ERRORES = 12
COLOR_ERROR_FONDO = (62, 26, 34)
COLOR_ERROR_TEXTO = (255, 222, 222)
COLOR_VALIDO_FONDO = (22, 56, 46)
COLOR_AYUDA = (236, 240, 250)


class PantallaGenerador:

    def __init__(self, pincel, fuentes, ancho_actual, alto_actual):
        self.pincel = pincel
        self.pantalla = pincel.pantalla
        self.fuentes = fuentes
        self.pestana = "auto"
        self.valores = {}
        for clave, _etiqueta, _minimo, _maximo, inicial, _col, _fila in PARAMETROS:
            self.valores[clave] = inicial
        self.modo = "aleatoria"
        self.ancho_mapa = max(MAPA_MIN_X, min(MAPA_MAX_X, ancho_actual))
        self.alto_mapa = max(MAPA_MIN_Y, min(MAPA_MAX_Y, alto_actual))
        self.editor = EditorEscenario(self.ancho_mapa, self.alto_mapa, pincel, fuentes)
        self.version_vista = -1
        self.sincronizados = set()
        self.confirmar_nuevo_mapa = False
        self._rect_nuevo_mapa_manual = pygame.Rect(0, 0, 0, 0)
        self._rect_confirmar_si = pygame.Rect(0, 0, 0, 0)
        self._rect_confirmar_no = pygame.Rect(0, 0, 0, 0)

        # Rect del panel derecho
        self.panel_derecho = pygame.Rect(
            PANEL_DERECHO_X, PANEL_DERECHO_Y, PANEL_DERECHO_W, PANEL_DERECHO_H
        )

        # Steppers de tamaño de mapa
        self.stepper_ancho = Stepper(
            pygame.Rect(0, 0, 38, 34),
            pygame.Rect(0, 0, 120, 34),
            pygame.Rect(0, 0, 38, 34),
            self.ancho_mapa, MAPA_MIN_X, MAPA_MAX_X, fuentes.negrita,
        )
        self.stepper_alto = Stepper(
            pygame.Rect(0, 0, 38, 34),
            pygame.Rect(0, 0, 120, 34),
            pygame.Rect(0, 0, 38, 34),
            self.alto_mapa, MAPA_MIN_Y, MAPA_MAX_Y, fuentes.negrita,
        )

        # Toolbar de herramientas
        self.toolbuttons = []
        self._construir_toolbuttons()

        # Botones de acción (cuadrados chicos con ícono)
        self.action_buttons = []
        self._construir_action_buttons()

        # Lista de pickers con scroll
        self.lista_pickers = ListaPickersScroll(
            pygame.Rect(0, 0, cfg.PANEL_CONTENIDO_W - 10, cfg.LISTA_PICKERS_ALTO_MAX),
            fuentes.picker,
            self.editor.modelo.pickers,
            cfg.COLORES_PICKER,
        )

        # Scroll del área de contenido
        self.scroll_offset = 0
        self.scroll_max = 0
        self.area_contenido_rect = None

        # Barra de acciones al pie
        self.btn_cancelar_rect = pygame.Rect(0, 0, 130, cfg.BARRA_ACCIONES_ALTO)
        self.btn_usar_rect = pygame.Rect(0, 0, 210, cfg.BARRA_ACCIONES_ALTO)
        self.btn_generar_rect = pygame.Rect(0, 0, 200, cfg.BARRA_ACCIONES_ALTO)
        self._posicionar_barra()

        # Botones de sentido del pasillo (se llenan al dibujar, solo con la herramienta Pasillo)
        self.sentido_rects = {}

        # Vista previa automática según los parámetros del escenario.
        self.previa = VistaPreviaEscenario(pincel, fuentes)

        # Líneas de error ya cortadas al ancho del panel (se recalculan si cambian los errores)
        self._errores_cacheados = None
        self._lineas_cacheadas = []

    # ---------- construcción de UI estática ----------

    def _construir_toolbuttons(self):
        self.toolbuttons = []
        bw = (cfg.PANEL_CONTENIDO_W - 5 * cfg.ESPACIO_S) // 6
        bh = 44
        for indice, (clave, nombre) in enumerate(HERRAMIENTAS_DIBUJO):
            rect = pygame.Rect(0, 0, bw, bh)
            activo = clave == self.editor.herramienta
            self.toolbuttons.append(ToolButton(clave, nombre, "", rect, activo=activo))

    def _construir_action_buttons(self):
        for clave, nombre, atajo in ACCIONES:
            self.action_buttons.append({
                "clave": clave,
                "nombre": nombre,
                "atajo": atajo,
                "rect": pygame.Rect(0, 0, 126, 36),
                "activo": clave == self.editor.herramienta,
            })

    def _actualizar_toolbuttons(self):
        for tb in self.toolbuttons:
            tb.activo = tb.clave == self.editor.herramienta
        for ab in self.action_buttons:
            ab["activo"] = ab["clave"] == self.editor.herramienta

    # ---------- geometría ----------

    def _tarjeta_de(self, columna):
        return TARJETA_WAREHOUSE if columna == 0 else TARJETA_PRODUCTOS

    def _pos(self, columna, fila):
        t = self._tarjeta_de(columna)
        return t.x + 20, t.y + 60 + fila * PASO_FILA

    def _rects_stepper_parametro(self, columna, fila):
        t = self._tarjeta_de(columna)
        x = t.right - 20 - ANCHO_STEPPER
        y = t.y + 60 + fila * PASO_FILA
        return self._rects_stepper(x, y)

    @staticmethod
    def _rects_stepper(x, y):
        return (pygame.Rect(x, y, 40, 40), pygame.Rect(x + 40, y, 70, 40),
                pygame.Rect(x + 110, y, 40, 40))

    def _rect_modo(self, indice):
        t = TARJETA_MODO
        ancho = (t.w - 40 - 2 * 16) // 3
        return pygame.Rect(t.x + 20 + indice * (ancho + 16), t.y + 60, ancho, t.h - 60 - 20)

    def _paso(self):
        return PASO_SHIFT if pygame.key.get_mods() & pygame.KMOD_SHIFT else PASO_NORMAL

    @staticmethod
    def _alto_lista_pickers(cantidad):
        return ListaPickersScroll.alto_para(cantidad)

    # ---------- cálculo del área de contenido (layout vertical) ----------

    def _calcular_area_contenido(self):
        panel = self.panel_derecho
        y_inicio = panel.y + cfg.CONTENIDO_PADDING_TOP
        y_fin = panel.bottom - cfg.BARRA_ACCIONES_ALTO - cfg.CONTENIDO_PADDING_BOTTOM - cfg.LINEA_ESTADO_ALTO - cfg.ESPACIO_ENTRE_SECCIONES
        ancho = panel.w - 2 * cfg.PANEL_PADDING
        x = panel.x + cfg.PANEL_PADDING
        return pygame.Rect(x, y_inicio, ancho, max(1, y_fin - y_inicio))

    def _calcular_alto_contenido(self):
        f = self.fuentes
        ancho = cfg.PANEL_CONTENIDO_W
        alto_total = 0

        # Título del panel (ya se dibuja en _dibujar_panel_base, pero contamos espacio)
        alto_total += f.sub.get_height() + cfg.ESPACIO_ENTRE_SECCIONES

        # Tamaño del mapa: título + 1 fila compacta
        alto_total += f.negrita.get_height() + cfg.ESPACIO_TITULO_CONTENIDO
        alto_total += 34 + cfg.ESPACIO_ENTRE_SECCIONES

        # Botón Nuevo mapa en blanco
        alto_total += 34 + cfg.ESPACIO_ENTRE_SECCIONES

        # Herramientas
        alto_total += f.negrita.get_height() + cfg.ESPACIO_TITULO_CONTENIDO
        alto_total += 44 + cfg.ESPACIO_ENTRE_SECCIONES

        # Acciones (botones cuadrados chicos)
        alto_total += 34 + cfg.ESPACIO_ENTRE_SECCIONES

        # Ayuda (una línea)
        alto_total += f.normal.get_height() + cfg.ESPACIO_ENTRE_SECCIONES

        # Bloque de validación (crece con la cantidad de errores)
        alto_total += self._alto_bloque_validacion() + cfg.ESPACIO_ENTRE_SECCIONES

        # Pickers colocados
        cantidad = len(self.editor.modelo.pickers)
        alto_total += f.negrita.get_height() + cfg.ESPACIO_TITULO_CONTENIDO
        lista_alto = self._alto_lista_pickers(cantidad)
        alto_total += lista_alto + cfg.ESPACIO_ENTRE_SECCIONES

        # Barra de estado
        alto_total += 44

        return alto_total

    # ---------- sincronización ----------

    def _sincronizar(self):
        cambio = self.editor.actualizar_validacion()
        if self.editor.modelo.version != self.version_vista:
            self._sincronizar_con_modelo()
            cambio = True
        if cambio:
            self._recalcular_scroll()

    def _sincronizar_con_modelo(self):
        modelo = self.editor.modelo
        self.version_vista = modelo.version
        cantidades = {"estantes": len(modelo.racks), "pickers": len(modelo.pickers),
                      "productos": len(modelo.productos)}
        for clave, cantidad in cantidades.items():
            if cantidad > 0:
                minimo, maximo = LIMITES[clave]
                self.valores[clave] = max(minimo, min(maximo, cantidad))
                self.sincronizados.add(clave)
            else:
                self.sincronizados.discard(clave)
        self.lista_pickers.actualizar(modelo.pickers)

    def _recalcular_scroll(self):
        """El alto del contenido cambia con el modelo y con los errores de validación."""
        area = self._calcular_area_contenido()
        alto_contenido = self._calcular_alto_contenido()
        self.scroll_max = max(0, alto_contenido - area.h)
        self.scroll_offset = max(0, min(self.scroll_offset, self.scroll_max))

    # ---------- estado derivado ----------

    def _capacidad(self):
        return self.valores["estantes"] * 2 * self.valores["alto_rack"] * NIVELES_POR_RACK

    def _waves_minimas(self):
        por_wave = self.valores["max_orders_capacity"]
        if por_wave == 0:
            return 1
        return math.ceil(self.valores["pedidos"] / por_wave)

    def _puede_generar(self):
        return self.valores["productos"] <= self._capacidad()

    def valores_generador(self):
        """Parámetros actuales listos para pasar a generar_escenario."""
        valores = dict(self.valores)
        valores["modo_ubicacion"] = self.modo
        return valores

    # ---------- eventos ----------

    def evento(self, ev):
        if self.confirmar_nuevo_mapa:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                    return self._nuevo_mapa_en_blanco()
                if ev.key in (pygame.K_n, pygame.K_ESCAPE):
                    self.confirmar_nuevo_mapa = False
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._rect_confirmar_si.collidepoint(ev.pos):
                    return self._nuevo_mapa_en_blanco()
                if self._rect_confirmar_no.collidepoint(ev.pos):
                    self.confirmar_nuevo_mapa = False
                return None
            return None

        # Scroll con rueda sobre el área de contenido
        if ev.type == pygame.MOUSEWHEEL and self.pestana == "manual":
            mx, my = pos_mouse()
            if (self.lista_pickers.scroll_max > 0
                    and self.lista_pickers.rect.collidepoint((mx, my))):
                self.lista_pickers.scroll(-ev.y * cfg.SCROLL_PASO)
                return None
            if self.area_contenido_rect and self.area_contenido_rect.collidepoint((mx, my)):
                self.scroll_offset = max(0, min(self.scroll_max,
                                                self.scroll_offset - ev.y * cfg.SCROLL_PASO))
                return None

        accion = self._procesar(ev)
        self._sincronizar()
        return accion

    def _procesar(self, ev):
    # Con el cuadro de producto abierto, el clic izquierdo va directo al cuadro
    # (excepto el botón Cancelar de arriba, que cierra todo el generador).
        if (self.pestana == "manual" and self.editor.cuadro is not None
                and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and not self.btn_cancelar_rect.collidepoint(ev.pos)):
            self.editor.evento(ev)
            return None

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            accion = self._clic(ev.pos)
            if accion == "nada":
                return None
            if accion is not None:
                return accion
            if self.pestana == "manual":
                idx_eliminar = self.lista_pickers.clic_eliminar(ev.pos)
                if idx_eliminar >= 0:
                    self.editor.modelo.pickers.pop(idx_eliminar)
                    self.editor.modelo.version += 1
                    self.editor._marcar_cambio()
                    return "nada"
                return self._traducir(self.editor.evento(ev))
            return None
        if self.pestana == "manual":
            if ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP,
                           pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                return self._traducir(self.editor.evento(ev))
            return None
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                return "cerrar"
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self._puede_generar():
                return "generar"
        return None
    
    def _traducir(self, accion_editor):
        if accion_editor == "terminar":
            return "usar" if self.editor.valido else "validar"
        return {"validar": "validar", "salir": "cerrar"}.get(accion_editor)

    def _clic(self, pos):
        if self.btn_cancelar_rect.collidepoint(pos):
            return "cerrar"
        if self.pestana == "manual" and self.editor.cuadro is not None:
            return "nada"
        if TAB_AUTO.collidepoint(pos):
            self.pestana = "auto"
            return "nada"
        if TAB_MANUAL.collidepoint(pos):
            self.pestana = "manual"
            return "nada"
        if self.pestana == "auto":
            return self._clic_auto(pos)
        return self._clic_manual(pos)

    def _click_boton(self, nombre):
        if nombre == "cancelar":
            return "cerrar"
        if nombre == "usar":
            return "usar"
        if nombre == "generar":
            return "generar" if self._puede_generar() else "nada"
        if nombre == "nuevo_mapa":
            self.confirmar_nuevo_mapa = True
            return "nada"
        return None

    def _clic_auto(self, pos):
        paso = self._paso()
        for clave, _etiqueta, minimo, maximo, _inicial, columna, fila in PARAMETROS:
            x, y = self._pos(columna, fila)
            menos, _valor, mas = self._rects_stepper_parametro(columna, fila)
            if menos.collidepoint(pos):
                self.valores[clave] = max(minimo, self.valores[clave] - paso)
                self.sincronizados.discard(clave)
                return "nada"
            if mas.collidepoint(pos):
                self.valores[clave] = min(maximo, self.valores[clave] + paso)
                self.sincronizados.discard(clave)
                return "nada"
        for indice, (modo, _texto) in enumerate(MODOS):
            if self._rect_modo(indice).collidepoint(pos):
                self.modo = modo
                return "nada"
        if self.btn_generar_rect.collidepoint(pos):
            return "generar" if self._puede_generar() else "nada"
        if self.btn_usar_rect.collidepoint(pos):
            return "usar" if self.editor.valido else "nada"
        if pygame.Rect(PANEL_DERECHO_X, PANEL_DERECHO_Y,
                       PANEL_DERECHO_W, PANEL_DERECHO_H).collidepoint(pos):
            return "nada"
        return None

    def _clic_manual(self, pos):
        paso = self._paso()

        # Botón Nuevo mapa en blanco
        if self._rect_nuevo_mapa_manual.collidepoint(pos):
            self.confirmar_nuevo_mapa = True
            return "nada"

        # Steppers de tamaño: el cambio se aplica al mapa en el momento
        if self.stepper_ancho.clic_menos(pos):
            return self._cambiar_tamano(self.stepper_ancho, self.stepper_ancho.decrementar)
        if self.stepper_ancho.clic_mas(pos):
            return self._cambiar_tamano(self.stepper_ancho, self.stepper_ancho.incrementar)
        if self.stepper_alto.clic_menos(pos):
            return self._cambiar_tamano(self.stepper_alto, self.stepper_alto.decrementar)
        if self.stepper_alto.clic_mas(pos):
            return self._cambiar_tamano(self.stepper_alto, self.stepper_alto.incrementar)

        # Toolbar de herramientas
        for tb in self.toolbuttons:
            if tb.clic(pos):
                self.editor.seleccionar(tb.clave)
                self._actualizar_toolbuttons()
                return "nada"

        # Botones de acción
        for ab in self.action_buttons:
            if ab["rect"].collidepoint(pos):
                if ab["clave"] == "deshacer":
                    self.editor.deshacer()
                elif ab["clave"] == "borrar":
                    self.editor.seleccionar("borrar")
                self._actualizar_toolbuttons()
                return "nada"

        # Sentido del pasillo
        if self.editor.herramienta == "pasillo":
            for sentido, rect in self.sentido_rects.items():
                if rect.collidepoint(pos):
                    self.editor.elegir_sentido(sentido)
                    return "nada"

        # Barra de acciones
        if self.btn_usar_rect.collidepoint(pos):
            return "usar" if self.editor.valido else "nada"

        if self.panel_derecho.collidepoint(pos):
            return "nada"
        return None

    def _cambiar_tamano(self, stepper, cambiar):
        """Mueve el stepper y redimensiona el mapa; si no se puede, lo deja como estaba."""
        anterior = stepper.valor
        cambiar()
        motivo = self.editor.redimensionar(self.stepper_ancho.valor, self.stepper_alto.valor)
        if motivo:
            stepper.valor = anterior
            self.editor.mensaje = motivo
        else:
            self.ancho_mapa = self.stepper_ancho.valor
            self.alto_mapa = self.stepper_alto.valor
            self.editor.mensaje = ""
        return "nada"

    def _nuevo_mapa_en_blanco(self):
        """Reemplaza el editor por un mapa vacío con el tamaño elegido."""
        self.confirmar_nuevo_mapa = False
        self.editor = EditorEscenario(
            self.ancho_mapa, self.alto_mapa, self.pincel, self.fuentes
        )
        self.version_vista = -1
        self.sincronizados.clear()
        self.scroll_offset = 0
        self.lista_pickers.actualizar(self.editor.modelo.pickers)
        self._actualizar_toolbuttons()
        self.stepper_ancho.valor = self.ancho_mapa
        self.stepper_alto.valor = self.alto_mapa
        return "nada"

    # ---------- dibujo ----------

    def dibujar(self):
        self._sincronizar()
        self._dibujar_cabecera()
        if self.pestana == "auto":
            self._dibujar_formulario()
            self._dibujar_panel_auto()
        else:
            self.editor.dibujar()
            self._dibujar_panel_manual()
            self._dibujar_cuadro_producto()

    def _dibujar_cuadro_producto(self):
        """El cuadro de producto va al final: encima del mapa y del panel, con el fondo atenuado."""
        if self.editor.cuadro is None:
            return
        velo = pygame.Surface((cfg.ANCHO, cfg.ALTO), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 140))
        self.pantalla.blit(velo, (0, 0))
        self.editor.dibujar_cuadro()

    def _dibujar_cabecera(self):
        pygame.draw.rect(self.pantalla, cfg.STEPPER_FONDO, CONTENEDOR_TABS,
                         border_radius=cfg.RADIO_M)
        for rect, texto, clave in ((TAB_AUTO, "Automático", "auto"),
                                   (TAB_MANUAL, "Manual (editor de mapa)", "manual")):
            activa = self.pestana == clave
            if activa:
                pygame.draw.rect(self.pantalla, (58, 112, 190), rect, border_radius=cfg.RADIO_S)
            fuente = self.fuentes.negrita if activa else self.fuentes.normal
            color = cfg.TEXTO_PRINCIPAL if activa else cfg.TEXTO_SECUNDARIO
            self.pincel.texto(texto, fuente, color, rect.centerx, rect.centery, "cc")

    def _dibujar_panel_base(self, titulo):
        panel = self.panel_derecho
        pygame.draw.rect(self.pantalla, cfg.PANEL_FONDO, panel, border_radius=cfg.RADIO_L)
        pygame.draw.rect(self.pantalla, cfg.PANEL_BORDE, panel, 2,
                         border_radius=cfg.RADIO_L)
        self.pincel.texto(titulo, self.fuentes.sub, cfg.TEXTO_PRINCIPAL,
                          panel.x + cfg.PANEL_PADDING, panel.y + 12)

    def _dibujar_tarjeta(self, rect, titulo):
        pygame.draw.rect(self.pantalla, cfg.CARD_FONDO, rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, cfg.CARD_BORDE, rect, 1, border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, cfg.ACENTO, (rect.x + 20, rect.y + 16, 4, 18),
                         border_radius=2)
        self.pincel.texto(titulo, self.fuentes.negrita, cfg.TEXTO_PRINCIPAL,
                          rect.x + 32, rect.y + 16)
        pygame.draw.line(self.pantalla, cfg.CARD_DIVISOR,
                         (rect.x + 16, rect.y + 46), (rect.right - 16, rect.y + 46))

    def _dibujar_stepper(self, rect_menos, rect_valor, rect_mas, texto, puede_menos, puede_mas):
        f = self.fuentes
        mouse = pos_mouse()
        unido = rect_menos.union(rect_valor).union(rect_mas)
        pygame.draw.rect(self.pantalla, cfg.CONTROL_FONDO, unido, border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, cfg.CONTROL_BORDE, unido, 1, border_radius=cfg.RADIO_M)
        for rect, simbolo, habilitado in ((rect_menos, "−", puede_menos),
                                          (rect_mas, "+", puede_mas)):
            boton = rect.inflate(-8, -8)
            if not habilitado:
                fondo, color = cfg.CARD_FONDO, (110, 118, 134)
            elif rect.collidepoint(mouse):
                fondo, color = cfg.CONTROL_BOTON_SOBRE, (255, 255, 255)
            else:
                fondo, color = cfg.CONTROL_BOTON, (255, 255, 255)
            pygame.draw.rect(self.pantalla, fondo, boton, border_radius=cfg.RADIO_S)
            img = f.negrita.render(simbolo, True, color)
            self.pantalla.blit(img, img.get_rect(center=boton.center))
        self.pincel.texto(texto, f.negrita, (255, 255, 255),
                          rect_valor.centerx, rect_valor.centery, "cc")

    def _posicionar_barra(self):
        panel = self.panel_derecho
        y = panel.bottom - cfg.BARRA_ACCIONES_ALTO - cfg.BARRA_ACCIONES_PADDING
        derecha = panel.right - cfg.PANEL_PADDING
        self.btn_cancelar_rect.topleft = (panel.x + cfg.PANEL_PADDING, y)
        if self.pestana == "auto":
            self.btn_generar_rect.topright = (derecha, y)
            self.btn_usar_rect.topright = (self.btn_generar_rect.left - 12, y)
        else:
            self.btn_usar_rect.topright = (derecha, y)

    def _dibujar_barra_acciones(self):
        """Barra fija al pie. Automático: Cancelar / Usar mapa de Manual / Generar. Manual: Cancelar / Usar."""
        self._posicionar_barra()
        panel = self.panel_derecho
        f = self.fuentes
        y = self.btn_cancelar_rect.y
        pygame.draw.line(self.pantalla, cfg.PANEL_BORDE,
                         (panel.x + 3, y - 10), (panel.right - 4, y - 10), 1)
        Button("cancelar", "Cancelar", self.btn_cancelar_rect,
               variante="outline").dibujar(self.pantalla, f.negrita)
        if self.pestana == "auto":
            Button("usar", "Usar mapa de Manual", self.btn_usar_rect, variante="secondary",
                   habilitado=self.editor.valido).dibujar(self.pantalla, f.negrita)
            Button("generar", "Generar", self.btn_generar_rect, variante="primary",
                   habilitado=self._puede_generar()).dibujar(self.pantalla, f.negrita)
        else:
            Button("usar", "Usar escenario", self.btn_usar_rect, variante="primary",
                   habilitado=self.editor.valido).dibujar(self.pantalla, f.negrita)

    # --- pestaña automática ---

    def _dibujar_fila_parametro(self, clave, etiqueta, minimo, maximo, columna, fila):
        f = self.fuentes
        x, y = self._pos(columna, fila)
        menos, valor_rect, mas = self._rects_stepper_parametro(columna, fila)
        valor = self.valores[clave]
        y_texto = y + 10
        ancho = self.pincel.texto(etiqueta, f.negrita, cfg.TEXTO_PRINCIPAL, x, y_texto)
        if clave in self.sincronizados and x + ancho + 80 < menos.left:
            self.pincel.texto("● manual", f.mini, cfg.VERDE, x + ancho + 8, y_texto + 4)
        self._dibujar_stepper(menos, valor_rect, mas, str(valor),
                              valor > minimo, valor < maximo)
        tarjeta = self._tarjeta_de(columna)
        pygame.draw.line(self.pantalla, cfg.CARD_DIVISOR,
                         (tarjeta.x + 16, y + 58), (tarjeta.right - 16, y + 58))

    def _dibujar_pictograma(self, modo, area):
        pygame.draw.rect(self.pantalla, (26, 30, 38), area, border_radius=cfg.RADIO_S)
        cerca = modo == "cerca_despacho"
        for k in range(3):
            y = area.y + 12 + k * 26
            pygame.draw.rect(self.pantalla, (24, 52, 102),
                             (area.x + 10, y, area.w - 20, 10), border_radius=3)
        if cerca:
            barra = pygame.Rect(area.right - 22, area.y + 4, 16, area.h - 8)
            pygame.draw.rect(self.pantalla, (38, 98, 90), barra, border_radius=3)
            pygame.draw.rect(self.pantalla, (118, 232, 196), barra, 1, border_radius=3)
        util = area.w - 20 - (26 if cerca else 0)
        for fx, fila in PUNTOS_MODO[modo]:
            px = area.x + 10 + int(fx * (util - 10))
            py = area.y + 12 + fila * 26
            pygame.draw.rect(self.pantalla, (214, 168, 102), (px, py, 10, 10),
                             border_radius=2)

    def _dibujar_opcion_modo(self, indice, modo, titulo):
        f = self.fuentes
        rect = self._rect_modo(indice)
        activo = self.modo == modo
        sobre = rect.collidepoint(pos_mouse())
        if activo:
            fondo, borde, ancho_borde = (40, 72, 122), cfg.ACENTO, 2
        elif sobre:
            fondo, borde, ancho_borde = (52, 58, 74), cfg.CONTROL_BORDE, 1
        else:
            fondo, borde, ancho_borde = (44, 50, 62), cfg.CARD_BORDE, 1
        pygame.draw.rect(self.pantalla, fondo, rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, borde, rect, ancho_borde, border_radius=cfg.RADIO_M)
        self._dibujar_pictograma(modo, pygame.Rect(rect.x + 14, rect.y + 14, rect.w - 28, 86))
        centro = (rect.right - 26, rect.y + 118)
        pygame.draw.circle(self.pantalla, borde if activo else cfg.CONTROL_BORDE, centro, 9, 2)
        if activo:
            pygame.draw.circle(self.pantalla, cfg.ACENTO, centro, 5)
        self.pincel.texto(titulo, f.negrita, (255, 255, 255), rect.x + 16, rect.y + 110)
        linea_1, linea_2 = DESCRIPCION_MODO[modo]
        self.pincel.texto(linea_1, f.chico, cfg.TEXTO_SECUNDARIO, rect.x + 16, rect.y + 136)
        self.pincel.texto(linea_2, f.chico, cfg.TEXTO_SECUNDARIO, rect.x + 16, rect.y + 154)

    def _dibujar_formulario(self):
        f = self.fuentes
        self._dibujar_tarjeta(TARJETA_WAREHOUSE, "WAREHOUSE")
        self._dibujar_tarjeta(TARJETA_PRODUCTOS, "PRODUCTOS Y PEDIDOS")
        self._dibujar_tarjeta(TARJETA_MODO, "UBICACIÓN DE LOS PRODUCTOS")
        self.pincel.texto("Shift + clic: de a 5", f.chico, cfg.TEXTO_SECUNDARIO,
                          TARJETA_PRODUCTOS.right - 20, TARJETA_PRODUCTOS.y + 18, "der")
        for clave, etiqueta, minimo, maximo, _inicial, columna, fila in PARAMETROS:
            self._dibujar_fila_parametro(clave, etiqueta, minimo, maximo, columna, fila)
        for indice, (modo, titulo) in enumerate(MODOS):
            self._dibujar_opcion_modo(indice, modo, titulo)

    def _dibujar_tile(self, indice, etiqueta, valor, color, detalle):
        f = self.fuentes
        x = PANEL_DERECHO_X + cfg.PANEL_PADDING + (indice % 2) * (TILE_W + 8)
        y = 96 + (indice // 2) * (TILE_H + 8)
        rect = pygame.Rect(x, y, TILE_W, TILE_H)
        pygame.draw.rect(self.pantalla, cfg.CARD_FONDO, rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, cfg.CARD_BORDE, rect, 1, border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, color, (x + 1, y + 12, 4, TILE_H - 24), border_radius=2)
        self.pincel.texto(etiqueta, f.negrita, cfg.TEXTO_SECUNDARIO, x + 18, y + 10)
        self.pincel.texto(valor, f.titulo, color, x + 18, y + 28)
        color_detalle = (255, 150, 150) if color == cfg.ROJO else cfg.TEXTO_PRINCIPAL
        self.pincel.texto(detalle, f.normal, color_detalle, x + 18, y + 64)

    def _dibujar_panel_auto(self):
        f = self.fuentes
        self._dibujar_panel_base("GENERAR ESCENARIO")
        x0 = PANEL_DERECHO_X + cfg.PANEL_PADDING
        ancho = PANEL_DERECHO_W - 2 * cfg.PANEL_PADDING
        capacidad = self._capacidad()
        productos = self.valores["productos"]
        waves = self._waves_minimas()
        pickers = self.valores["pickers"]
        pedidos = self.valores["pedidos"]
        por_wave = self.valores["max_orders_capacity"]
        entran = productos <= capacidad
        uso = round(100 * productos / capacidad) if capacidad else 100

        self._dibujar_tile(0, "UBICACIONES", str(capacidad), cfg.ACENTO,
                           f"{self.valores['estantes']} estantes · alto {self.valores['alto_rack']}")
        self._dibujar_tile(1, "PRODUCTOS A UBICAR", str(productos),
                           cfg.VERDE if entran else cfg.ROJO,
                           f"{uso} % de ocupación" if entran else "No entran en esos estantes")
        self._dibujar_tile(2, "WAVES COMO MÍNIMO", str(waves), cfg.AMARILLO,
                           f"{pedidos} pedidos · "
                           + ("sin límite por wave" if por_wave == 0 else f"{por_wave} por wave"))
        self._dibujar_tile(3, "PICKERS", str(pickers), cfg.NARANJA,
                           "Pueden colaborar en una misma wave" if pickers > waves
                           else f"{waves} waves para repartir")

        estado = pygame.Rect(x0, 306, ancho, 40)
        color = cfg.VERDE if entran else cfg.ROJO
        texto = ("Todo listo: podés generar el escenario." if entran
                 else "No se puede generar: subí estantes o alto, o bajá los productos.")
        self.pincel.rect_alfa(estado.x, estado.y, estado.w, estado.h, (*color, 40), cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, color, estado, 1, border_radius=cfg.RADIO_M)
        self.pincel.texto(texto, f.negrita, (255, 255, 255), estado.x + 20,
                          estado.centery - f.negrita.get_height() // 2)

        self._dibujar_vista_previa()
        self._dibujar_barra_acciones()

    def _dibujar_vista_previa(self):
        self._dibujar_tarjeta(TARJETA_MINIATURA, "VISTA PREVIA")
        marco = pygame.Rect(
            TARJETA_MINIATURA.x + 16, TARJETA_MINIATURA.y + 58,
            TARJETA_MINIATURA.w - 32, TARJETA_MINIATURA.h - 58 - 40,
        )
        pygame.draw.rect(self.pantalla, cfg.MAPA_FONDO, marco, border_radius=cfg.RADIO_S)
        self._dibujar_borde_punteado(marco, (100, 108, 122))
        self._dibujar_previa_automatica(marco)

    def _dibujar_previa_automatica(self, marco):
        """Warehouse que se generaría con los parámetros actuales (se redibuja al cambiarlos)."""
        v = self.valores
        self.previa.actualizar(v["estantes"], v["pasillos_horizontales"], v["alto_rack"],
                               v["productos"], v["pickers"], self.modo,
                               v["peso_max_zona_kg"])
        self.previa.dibujar(marco.inflate(-16, -16))
        resumen = self.previa.resumen()
        if resumen:
            self.pincel.texto(resumen, self.fuentes.normal, cfg.TEXTO_SECUNDARIO,
                              marco.centerx, marco.bottom + 8, "centro")

    def _dibujar_borde_punteado(self, rect, color, paso=12):
        for x in range(rect.left + 8, rect.right - 8, paso):
            pygame.draw.line(self.pantalla, color, (x, rect.top),
                             (min(x + 6, rect.right - 8), rect.top), 1)
            pygame.draw.line(self.pantalla, color, (x, rect.bottom - 1),
                             (min(x + 6, rect.right - 8), rect.bottom - 1), 1)
        for y in range(rect.top + 8, rect.bottom - 8, paso):
            pygame.draw.line(self.pantalla, color, (rect.left, y),
                             (rect.left, min(y + 6, rect.bottom - 8)), 1)
            pygame.draw.line(self.pantalla, color, (rect.right - 1, y),
                             (rect.right - 1, min(y + 6, rect.bottom - 8)), 1)

    # --- pestaña manual ---

    def _dibujar_panel_manual(self):
        f = self.fuentes
        panel = self.panel_derecho
        x0 = panel.x + cfg.PANEL_PADDING
        ancho = panel.w - 2 * cfg.PANEL_PADDING

        self._dibujar_panel_base("EDITOR DE MAPA")

        # Área de contenido scrollable
        self.area_contenido_rect = self._calcular_area_contenido()
        alto_contenido = self._calcular_alto_contenido()
        hay_scroll = alto_contenido > self.area_contenido_rect.h

        self.pantalla.set_clip(self.area_contenido_rect)

        cursor = self.area_contenido_rect.top - self.scroll_offset

        # b) Tamaño del mapa: título + fila compacta
        cursor += cfg.ESPACIO_ENTRE_SECCIONES
        self.pincel.texto("TAMAÑO DEL MAPA (celdas)", f.negrita, cfg.TEXTO_SECUNDARIO,
                          x0, cursor)
        cursor += f.negrita.get_height() + cfg.ESPACIO_TITULO_CONTENIDO

        # Fila: Ancho [stepper]   Alto [stepper]   [Nuevo mapa en blanco]
        y_etiqueta = cursor + (34 - f.normal.get_height()) // 2
        self.pincel.texto("Ancho", f.negrita, cfg.TEXTO_PRINCIPAL, x0, y_etiqueta)
        x_ancho = x0 + 56
        self.stepper_ancho.rect_menos.topleft = (x_ancho, cursor)
        self.stepper_ancho.rect_valor.topleft = (x_ancho + 40, cursor)
        self.stepper_ancho.rect_mas.topleft = (x_ancho + 162, cursor)
        self.stepper_ancho.dibujar(self.pantalla)

        x_alto_label = x0 + 280
        self.pincel.texto("Alto", f.negrita, cfg.TEXTO_PRINCIPAL, x_alto_label, y_etiqueta)
        x_alto = x_alto_label + 46
        self.stepper_alto.rect_menos.topleft = (x_alto, cursor)
        self.stepper_alto.rect_valor.topleft = (x_alto + 40, cursor)
        self.stepper_alto.rect_mas.topleft = (x_alto + 162, cursor)
        self.stepper_alto.dibujar(self.pantalla)

        # Botón Nuevo mapa en blanco a la derecha
        btn_nuevo_w = 200
        btn_nuevo_rect = pygame.Rect(
            panel.right - cfg.PANEL_PADDING - btn_nuevo_w, cursor,
            btn_nuevo_w, 34,
        )
        btn_nuevo = Button("nuevo_mapa", "Nuevo mapa en blanco", btn_nuevo_rect,
                           variante="danger")
        btn_nuevo.dibujar(self.pantalla, f.negrita)
        self._rect_nuevo_mapa_manual = btn_nuevo_rect

        cursor += 34 + cfg.ESPACIO_ENTRE_SECCIONES

        # d) Herramientas
        self.pincel.texto("HERRAMIENTAS", f.negrita, cfg.TEXTO_SECUNDARIO, x0, cursor)
        cursor += f.negrita.get_height() + cfg.ESPACIO_TITULO_CONTENIDO

        bw = (ancho - 5 * cfg.ESPACIO_S) // 6
        bh = 44
        for indice, (clave, nombre) in enumerate(HERRAMIENTAS_DIBUJO):
            tb = self.toolbuttons[indice]
            tb.rect.x = x0 + indice * (bw + cfg.ESPACIO_S)
            tb.rect.y = cursor
            tb.dibujar(self.pantalla, f.negrita)
        cursor += bh + cfg.ESPACIO_ENTRE_SECCIONES

        # e) Acciones: Deshacer y Borrar con ícono + texto
        x_accion = x0
        for ab in self.action_buttons:
            ab["rect"].x = x_accion
            ab["rect"].y = cursor
            self._dibujar_boton_accion(ab)
            x_accion += ab["rect"].w + cfg.ESPACIO_S
        if self.editor.herramienta == "pasillo":
            self._dibujar_sentidos(x_accion + cfg.ESPACIO_L, cursor)
        else:
            self.sentido_rects = {}
        cursor += 36 + cfg.ESPACIO_ENTRE_SECCIONES

        # f) Ayuda (una sola línea)
        ayuda = AYUDA_POR_HERRAMIENTA.get(self.editor.herramienta, AYUDA_GENERICA)
        self.pincel.texto(ayuda, f.negrita, COLOR_AYUDA, x0, cursor)
        cursor += f.negrita.get_height() + cfg.ESPACIO_ENTRE_SECCIONES

        # g) Estado de validación con la lista de errores
        self._dibujar_bloque_validacion(x0, cursor, ancho)
        cursor += self._alto_bloque_validacion() + cfg.ESPACIO_ENTRE_SECCIONES

        # h) PICKERS COLOCADOS
        cantidad = len(self.editor.modelo.pickers)
        self.pincel.texto(f"PICKERS COLOCADOS ({cantidad})",
                          f.negrita, cfg.TEXTO_SECUNDARIO, x0, cursor)
        cursor += f.negrita.get_height() + cfg.ESPACIO_TITULO_CONTENIDO

        lista_alto = self._alto_lista_pickers(cantidad)
        self.lista_pickers.rect.x = x0
        self.lista_pickers.rect.y = cursor
        self.lista_pickers.rect.w = ancho - 10
        self.lista_pickers.rect.h = lista_alto
        self.lista_pickers.dibujar(self.pantalla)
        cursor += lista_alto + cfg.ESPACIO_ENTRE_SECCIONES

        # Barra de estado del editor
        g = self.editor.grilla
        celda = self.editor.hover
        coord = f"({celda[0]}, {celda[1]})" if celda else "(0, 0)"
        tamano = f"{self.editor.modelo.ancho_x} × {self.editor.modelo.largo_y}"
        self.status_bar = StatusBar(
            pygame.Rect(x0, cursor, ancho, 44), f.normal, f.negrita,
        )
        self.status_bar.actualizar(self.editor.herramienta, coord, tamano)
        self.status_bar.dibujar(self.pantalla)
        cursor += 44

        self.pantalla.set_clip(None)
        self._dibujar_barra_acciones()

        # Barra de scroll
        if hay_scroll:
            x_scroll = self.area_contenido_rect.right - 6
            alto_barra = max(20, int(self.area_contenido_rect.h *
                                     self.area_contenido_rect.h / alto_contenido))
            y_scroll = self.area_contenido_rect.top + int(
                self.scroll_offset / self.scroll_max *
                (self.area_contenido_rect.h - alto_barra)) if self.scroll_max > 0 else 0
            pygame.draw.rect(self.pantalla, (80, 88, 104),
                             (x_scroll, y_scroll, 6, alto_barra), border_radius=3)

        # El modal se dibuja al final, fuera del clip del área scrollable.
        if self.confirmar_nuevo_mapa:
            self._dibujar_confirmacion_nuevo_mapa()

    def _dibujar_sentidos(self, x, y):
        """Botones de sentido del pasillo con el nombre del punto cardinal (el activo va resaltado)."""
        f = self.fuentes
        mouse = pos_mouse()
        ancho_etiqueta = self.pincel.texto("Sentido", f.negrita, cfg.TEXTO_PRINCIPAL, x,
                                           y + (36 - f.negrita.get_height()) // 2)
        x += ancho_etiqueta + 14
        self.sentido_rects = {}
        for sentido, _flecha, nombre in SENTIDOS:
            rect = pygame.Rect(x, y, 70, 36)
            self.sentido_rects[sentido] = rect
            activo = self.editor.sentido == sentido
            if activo:
                fondo, borde = cfg.TOOL_BUTTON_FONDO_ACTIVO, cfg.TOOL_BUTTON_BORDE_ACTIVO
            elif rect.collidepoint(mouse):
                fondo, borde = cfg.SENTIDO_FONDO_SOBRE, cfg.BOTON_BORDE_SOBRE
            else:
                fondo, borde = cfg.SENTIDO_FONDO, cfg.TOOL_BUTTON_BORDE
            pygame.draw.rect(self.pantalla, fondo, rect, border_radius=cfg.RADIO_M)
            pygame.draw.rect(self.pantalla, borde, rect, 2 if activo else 1,
                             border_radius=cfg.RADIO_M)
            self.pincel.texto(nombre, f.negrita, (255, 255, 255),
                              rect.centerx, rect.centery, "cc")
            x += rect.w + 6

    def _dibujar_boton_accion(self, ab):
        rect = ab["rect"]
        sobre = rect.collidepoint(pos_mouse())
        if ab["activo"]:
            fondo = cfg.TOOL_BUTTON_FONDO_ACTIVO
            borde = cfg.TOOL_BUTTON_BORDE_ACTIVO
        elif sobre:
            fondo = cfg.TOOL_BUTTON_FONDO_SOBRE
            borde = cfg.BOTON_BORDE_SOBRE
        else:
            fondo = cfg.TOOL_BUTTON_FONDO
            borde = cfg.TOOL_BUTTON_BORDE
        pygame.draw.rect(self.pantalla, fondo, rect, border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, borde, rect, 1, border_radius=cfg.RADIO_M)

        color = (255, 255, 255)
        cx, cy = rect.x + 22, rect.centery
        if ab["clave"] == "deshacer":
            self._icono_deshacer(cx, cy, color)
        else:
            self._icono_borrar(cx, cy, color)
        img = self.fuentes.negrita.render(ab["nombre"], True, color)
        self.pantalla.blit(img, img.get_rect(midleft=(rect.x + 42, rect.centery)))

    def _icono_deshacer(self, cx, cy, color):
        """Flecha curva: sale hacia la izquierda arriba, rodea a la derecha y vuelve abajo."""
        r = 6
        puntos = [(cx - 3, cy - r)]
        for k in range(0, 13):
            ang = -math.pi / 2 + math.pi * k / 12
            puntos.append((cx + 1 + r * math.cos(ang), cy + r * math.sin(ang)))
        puntos.append((cx - 5, cy + r))
        pygame.draw.lines(self.pantalla, color, False, puntos, 2)
        pygame.draw.polygon(self.pantalla, color,
                            [(cx - 9, cy - r), (cx - 3, cy - r - 5), (cx - 3, cy - r + 5)])

    def _icono_borrar(self, cx, cy, color):
        """Tacho: tapa con manija, cuerpo y dos rayitas."""
        pygame.draw.line(self.pantalla, color, (cx - 8, cy - 5), (cx + 8, cy - 5), 2)
        pygame.draw.rect(self.pantalla, color, (cx - 3, cy - 9, 6, 4), 2, border_radius=1)
        pygame.draw.rect(self.pantalla, color, (cx - 6, cy - 3, 12, 12), 2, border_radius=2)
        pygame.draw.line(self.pantalla, color, (cx - 2, cy), (cx - 2, cy + 6), 1)
        pygame.draw.line(self.pantalla, color, (cx + 2, cy), (cx + 2, cy + 6), 1)

    def _envolver(self, texto, fuente, ancho, sangria="  "):
        """Parte el texto en líneas que entren en `ancho` píxeles."""
        lineas = []
        actual = ""
        for palabra in texto.split():
            prueba = palabra if not actual else actual + " " + palabra
            if not actual or fuente.size(prueba)[0] <= ancho:
                actual = prueba
            else:
                lineas.append(actual)
                actual = sangria + palabra
        if actual:
            lineas.append(actual)
        return lineas

    def _lineas_validacion(self):
        errores = tuple(self.editor.errores_validacion)
        if errores != self._errores_cacheados:
            self._errores_cacheados = errores
            ancho = cfg.PANEL_CONTENIDO_W - 32
            lineas = []
            for error in errores:
                lineas.extend(self._envolver("• " + error, self.fuentes.negrita, ancho))
            self._lineas_cacheadas = lineas
        return self._lineas_cacheadas

    def _estado_validacion(self):
        if self.editor.esta_vacio():
            return "vacio"
        if self.editor.errores_validacion:
            return "error"
        if self.editor.valido:
            return "valido"
        return "validando"

    def _alto_bloque_validacion(self):
        if self._estado_validacion() != "error":
            return ALTO_FILA_ESTADO
        return (ALTO_FILA_ESTADO + len(self._lineas_validacion()) * ALTO_LINEA_ERROR
                + PAD_ERRORES)

    def _dibujar_bloque_validacion(self, x, y, ancho):
        """Estado del mapa y, si hay errores, cada uno en letra grande y con contraste."""
        f = self.fuentes
        estado = self._estado_validacion()
        if estado == "error":
            cantidad = len(self.editor.errores_validacion)
            titulo = (f"{cantidad} error por corregir" if cantidad == 1
                      else f"{cantidad} errores por corregir")
            fondo, borde, color_icono, glifo = COLOR_ERROR_FONDO, cfg.ROJO, cfg.ROJO, "!"
        elif estado == "valido":
            titulo = "Warehouse válido"
            fondo, borde = COLOR_VALIDO_FONDO, cfg.VALIDACION_VALIDO
            color_icono, glifo = cfg.VALIDACION_VALIDO, "✓"
        elif estado == "vacio":
            titulo = "Mapa vacío"
            fondo, borde = cfg.TARJETA_FONDO_OSCURO, cfg.TARJETA_BORDE
            color_icono, glifo = cfg.VALIDACION_VACIO, "–"
        else:
            titulo = "Validando…"
            fondo, borde = cfg.TARJETA_FONDO_OSCURO, cfg.TARJETA_BORDE
            color_icono, glifo = cfg.VALIDACION_VACIO, "…"

        rect = pygame.Rect(x, y, ancho, self._alto_bloque_validacion())
        pygame.draw.rect(self.pantalla, fondo, rect, border_radius=cfg.RADIO_S)
        pygame.draw.rect(self.pantalla, borde, rect, 2 if estado == "error" else 1,
                         border_radius=cfg.RADIO_S)

        cy = y + ALTO_FILA_ESTADO // 2
        mostrar_icono = estado == "error"
        if mostrar_icono:
            pygame.draw.circle(self.pantalla, color_icono, (x + 24, cy), 11)
            img_glifo = f.negrita.render(glifo, True, (20, 24, 32))
            self.pantalla.blit(img_glifo, img_glifo.get_rect(center=(x + 24, cy)))
        margen_titulo = 46 if mostrar_icono else 16
        img_titulo = f.sub.render(titulo, True, (255, 255, 255))
        self.pantalla.blit(img_titulo, img_titulo.get_rect(midleft=(x + margen_titulo, cy)))

        if estado == "error":
            for i, linea in enumerate(self._lineas_validacion()):
                img = f.negrita.render(linea, True, COLOR_ERROR_TEXTO)
                self.pantalla.blit(img, (x + 16, y + ALTO_FILA_ESTADO + i * ALTO_LINEA_ERROR))

    def _dibujar_confirmacion_nuevo_mapa(self):
        ancho, alto = 440, 190
        x = (cfg.ANCHO - ancho) // 2
        y = (cfg.ALTO - alto) // 2

        velo = pygame.Surface((cfg.ANCHO, cfg.ALTO), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 150))
        self.pantalla.blit(velo, (0, 0))

        sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        pygame.draw.rect(sup, (20, 24, 32, 245), sup.get_rect(), border_radius=cfg.RADIO_L)
        pygame.draw.rect(sup, cfg.ROJO, sup.get_rect(), 2, border_radius=cfg.RADIO_L)
        self.pantalla.blit(sup, (x, y))

        self.pincel.texto("¿Borrar el mapa actual?", self.fuentes.sub,
                          cfg.TEXTO_PRINCIPAL, x + 24, y + 22)
        self.pincel.texto("Se descarta todo lo dibujado y queda un mapa vacío.",
                          self.fuentes.chico, cfg.TEXTO_SECUNDARIO, x + 24, y + 60)
        self.pincel.texto("También podés usar Y (sí) o N (no).",
                          self.fuentes.chico, cfg.TEXTO_SECUNDARIO, x + 24, y + 82)

        bw, bh = 150, 40
        self._rect_confirmar_no = pygame.Rect(x + 24, y + alto - 24 - bh, bw, bh)
        self._rect_confirmar_si = pygame.Rect(
            x + ancho - 24 - bw, y + alto - 24 - bh, bw, bh
        )
        Button("confirmar_no", "Cancelar", self._rect_confirmar_no,
               variante="secondary").dibujar(self.pantalla, self.fuentes.negrita)
        Button("confirmar_si", "Sí, borrar", self._rect_confirmar_si,
               variante="danger").dibujar(self.pantalla, self.fuentes.negrita)
