"""Pantalla "Generar escenario" con dos pestañas.

- Automático: los parámetros de generar_escenario (estantes, pasillos, productos, pedidos...).
- Manual: el editor de mapa con mouse, con su paleta de herramientas.

Solo maneja la interfaz: devuelve acciones y App se las pasa a la Sesion.
"""

import math

import pygame

from . import config as cfg
from .editor_esc import EditorEscenario
from .widgets import (
    Button, Stepper, ToolButton, StatusBar,
    ListaPickersScroll, dibujar_boton,
)

NIVELES_POR_RACK = 3     # niveles de producto por celda de rack que usa el generador (ScenarioV)

# (clave, etiqueta, mínimo, máximo, valor inicial, columna, fila)
PARAMETROS = (
    ("estantes", "Estantes", 1, 60, 6, 0, 0),
    ("pasillos_horizontales", "Pasillos horizontales", 2, 8, 2, 0, 1),
    ("alto_rack", "Alto de cada estante", 2, 14, 6, 0, 2),
    ("pickers", "Pickers", 1, 12, 2, 0, 3),
    ("productos", "Productos", 1, 400, 20, 1, 0),
    ("pedidos", "Pedidos", 1, 120, 8, 1, 1),
    ("max_productos_pedido", "Máx. productos por pedido", 1, 12, 4, 1, 2),
    ("max_orders_capacity", "Pedidos por wave (0 = sin límite)", 0, 30, 3, 1, 3),
    ("max_products_capacity", "Productos por wave (0 = sin límite)", 0, 80, 15, 1, 4),
)
LIMITES = {clave: (minimo, maximo) for clave, _e, minimo, maximo, _i, _c, _f in PARAMETROS}
MODOS = (("aleatoria", "Aleatoria"), ("agrupada", "Agrupada"), ("cerca_despacho", "Cerca del despacho"))

# Herramientas de dibujo (sin números en el botón)
HERRAMIENTAS_DIBUJO = (
    ("rack", "Rack"),
    ("despacho", "Despacho"),
    ("puerta", "Puerta"),
    ("pasillo", "Pasillo"),
    ("picker", "Picker"),
    ("producto", "Producto"),
)
# Acciones: (clave, ícono, nombre, atajo)
ACCIONES = (
    ("deshacer", "↶", "Desacre", "Z"),
    ("borrar", "🧹", "Borrar", "7"),
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
TARJETA_WAREHOUSE = pygame.Rect(40, 88, 380, 376)
TARJETA_PRODUCTOS = pygame.Rect(432, 88, 416, 512)

# Resumen y miniatura (panel derecho, Automático)
TARJETA_RESUMEN = pygame.Rect(PANEL_DERECHO_X + cfg.PANEL_PADDING, 150,
                              PANEL_DERECHO_W - 2 * cfg.PANEL_PADDING, 180)
TARJETA_MINIATURA = pygame.Rect(PANEL_DERECHO_X + cfg.PANEL_PADDING, 350,
                                PANEL_DERECHO_W - 2 * cfg.PANEL_PADDING, 270)

# Paso del stepper
PASO_NORMAL = 1
PASO_SHIFT = 5

# Ayuda contextual por herramienta (una sola línea)
AYUDA_POR_HERRAMIENTA = {
    "rack": "Dibujá estantes (un lado de 2 celdas).",
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

        # Rect del panel derecho
        self.panel_derecho = pygame.Rect(
            PANEL_DERECHO_X, PANEL_DERECHO_Y, PANEL_DERECHO_W, PANEL_DERECHO_H
        )

        # Steppers de tamaño de mapa
        self.stepper_ancho = Stepper(
            pygame.Rect(0, 0, 38, 34),
            pygame.Rect(0, 0, 120, 34),
            pygame.Rect(0, 0, 38, 34),
            self.ancho_mapa, MAPA_MIN_X, MAPA_MAX_X, fuentes.normal,
        )
        self.stepper_alto = Stepper(
            pygame.Rect(0, 0, 38, 34),
            pygame.Rect(0, 0, 120, 34),
            pygame.Rect(0, 0, 38, 34),
            self.alto_mapa, MAPA_MIN_Y, MAPA_MAX_Y, fuentes.normal,
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
            fuentes.chico,
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

        # Tooltip de acción
        self.tooltip_action = None   # (rect, texto) o None
        self.tooltip_timer = 0.0

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
        bw = 34
        bh = 34
        for clave, icono, nombre, atajo in ACCIONES:
            rect = pygame.Rect(0, 0, bw, bh)
            self.action_buttons.append({
                "clave": clave,
                "icono": icono,
                "nombre": nombre,
                "atajo": atajo,
                "rect": rect,
                "activo": clave == self.editor.herramienta,
            })

    def _actualizar_toolbuttons(self):
        for tb in self.toolbuttons:
            tb.activo = tb.clave == self.editor.herramienta
        for ab in self.action_buttons:
            ab["activo"] = ab["clave"] == self.editor.herramienta

    # ---------- geometría ----------

    def _pos(self, columna, fila):
        return (58 if columna == 0 else 450), 146 + fila * (68 if columna == 0 else 50)

    def _rects_stepper_parametro(self, columna, fila):
        x = 260 if columna == 0 else 688
        y = 138 + fila * (68 if columna == 0 else 50)
        return self._rects_stepper(x, y)

    @staticmethod
    def _rects_stepper(x, y):
        return (pygame.Rect(x, y, 38, 34), pygame.Rect(x + 38, y, 68, 34),
                pygame.Rect(x + 106, y, 38, 34))

    def _rect_modo(self, indice):
        anchos = (100, 100, 164)
        x = 450 + 4 + sum(anchos[:indice]) + 4 * indice
        return pygame.Rect(x, 418, anchos[indice], 38)

    def _paso(self):
        return PASO_SHIFT if pygame.key.get_mods() & pygame.KMOD_SHIFT else PASO_NORMAL

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
        alto_total += f.mini.get_height() + cfg.ESPACIO_TITULO_CONTENIDO
        alto_total += 34 + cfg.ESPACIO_ENTRE_SECCIONES

        # Botón Nuevo mapa en blanco
        alto_total += 34 + cfg.ESPACIO_ENTRE_SECCIONES

        # Herramientas
        alto_total += f.mini.get_height() + cfg.ESPACIO_TITULO_CONTENIDO
        alto_total += 44 + cfg.ESPACIO_ENTRE_SECCIONES

        # Acciones (botones cuadrados chicos)
        alto_total += 34 + cfg.ESPACIO_ENTRE_SECCIONES

        # Ayuda (una línea)
        alto_total += f.chico.get_height() + cfg.ESPACIO_ENTRE_SECCIONES

        # Línea de estado de validación
        alto_total += cfg.LINEA_ESTADO_ALTO + cfg.ESPACIO_ENTRE_SECCIONES

        # Pickers colocados
        cantidad = len(self.editor.modelo.pickers)
        alto_total += f.mini.get_height() + cfg.ESPACIO_TITULO_CONTENIDO
        lista_alto = min(cfg.LISTA_PICKERS_ALTO_MAX, cantidad * cfg.LISTA_PICKERS_ITEM_ALTO_CON_BOTON)
        alto_total += lista_alto + cfg.ESPACIO_ENTRE_SECCIONES

        # Barra de estado
        alto_total += 34

        return alto_total

    # ---------- sincronización ----------

    def _sincronizar(self):
        modelo = self.editor.modelo
        if modelo.version == self.version_vista:
            return
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

        # Validación automática del editor
        self.editor.actualizar_validacion()

        # Actualizar lista de pickers
        self.lista_pickers.actualizar(modelo.pickers)

        # Recalcular scroll
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

    # ---------- eventos ----------

    def evento(self, ev):
        if self.confirmar_nuevo_mapa and ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_y:
                self.confirmar_nuevo_mapa = False
                return self._click_boton("nuevo_mapa")
            if ev.key == pygame.K_n:
                self.confirmar_nuevo_mapa = False
                return None
            return None

        # Scroll con rueda sobre el área de contenido
        if ev.type == pygame.MOUSEWHEEL and self.pestana == "manual":
            mx, my = pygame.mouse.get_pos()
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
                and not BTN_CANCELAR.collidepoint(ev.pos)):
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
            return "nuevo_mapa"
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
        if self.btn_usar_rect.collidepoint(pos):
            return "usar" if self.editor.valido else "nada"
        if pygame.Rect(PANEL_DERECHO_X, PANEL_DERECHO_Y,
                       PANEL_DERECHO_W, PANEL_DERECHO_H).collidepoint(pos):
            return "nada"
        return None

    def _clic_manual(self, pos):
        paso = self._paso()

        # Steppers
        if self.stepper_ancho.clic_menos(pos):
            self.stepper_ancho.decrementar()
            self.ancho_mapa = self.stepper_ancho.valor
            return "nada"
        if self.stepper_ancho.clic_mas(pos):
            self.stepper_ancho.incrementar()
            self.ancho_mapa = self.stepper_ancho.valor
            return "nada"
        if self.stepper_alto.clic_menos(pos):
            self.stepper_alto.decrementar()
            self.alto_mapa = self.stepper_alto.valor
            return "nada"
        if self.stepper_alto.clic_mas(pos):
            self.stepper_alto.incrementar()
            self.alto_mapa = self.stepper_alto.valor
            return "nada"

        # Botón Nuevo mapa en blanco (se posiciona en dibujar, verificamos colisión)
        # Se maneja en _dibujar_panel_manual pasando el rect

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
            for indice, (sentido, _flecha, _nombre) in enumerate(SENTIDOS):
                pass  # se manejan en dibujar

        # Barra de acciones
        if self.btn_usar_rect.collidepoint(pos):
            return "usar" if self.editor.valido else "nada"

        if self.panel_derecho.collidepoint(pos):
            return "nada"
        return None

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

    def _dibujar_stepper(self, rect_menos, rect_valor, rect_mas, texto, puede_menos, puede_mas):
        unido = rect_menos.union(rect_valor).union(rect_mas)
        pygame.draw.rect(self.pantalla, cfg.STEPPER_FONDO,
                         unido, border_radius=cfg.RADIO_M)
        for rect, simbolo, habilitado in ((rect_menos, "−", puede_menos),
                                          (rect_mas, "+", puede_mas)):
            color = cfg.TEXTO_PRINCIPAL if habilitado else cfg.TEXTO_DESCATIVADO
            imagen = self.fuentes.negrita.render(simbolo, True, color)
            self.pantalla.blit(imagen, imagen.get_rect(center=rect.center))
        pygame.draw.line(self.pantalla, cfg.STEPPER_DIVISOR,
                         (rect_valor.left, rect_valor.top + 7),
                         (rect_valor.left, rect_valor.bottom - 7), 1)
        pygame.draw.line(self.pantalla, cfg.STEPPER_DIVISOR,
                         (rect_valor.right, rect_valor.top + 7),
                         (rect_valor.right, rect_valor.bottom - 7), 1)
        self.pincel.texto(texto, self.fuentes.normal, cfg.TEXTO_PRINCIPAL,
                          rect_valor.centerx, rect_valor.centery, "cc")

    def _dibujar_barra_acciones(self):
        """Barra fija al pie: [Cancelar] [Usar escenario]."""
        panel = self.panel_derecho
        y = panel.bottom - cfg.BARRA_ACCIONES_ALTO - cfg.BARRA_ACCIONES_PADDING
        alto = cfg.BARRA_ACCIONES_ALTO

        pygame.draw.rect(self.pantalla, cfg.PANEL_FONDO,
                         (panel.x, y, panel.w, alto))
        pygame.draw.line(self.pantalla, cfg.PANEL_BORDE,
                         (panel.x, y - 1), (panel.right, y - 1), 1)

        x_cancelar = panel.x + cfg.PANEL_PADDING
        x_usar = panel.right - cfg.PANEL_PADDING - self.btn_usar_rect.w

        self.btn_cancelar_rect.x = x_cancelar
        self.btn_cancelar_rect.y = y
        self.btn_usar_rect.x = x_usar
        self.btn_usar_rect.y = y

        cancelar = Button("cancelar", "Cancelar", self.btn_cancelar_rect,
                          variante="outline")
        cancelar.dibujar(self.pantalla, self.fuentes.normal)

        usar_habilitado = self.editor.valido
        usar = Button("usar", "Usar escenario", self.btn_usar_rect,
                      variante="primary", habilitado=usar_habilitado)
        usar.dibujar(self.pantalla, self.fuentes.normal)

    # --- pestaña automática ---

    def _dibujar_formulario(self):
        f = self.fuentes
        pygame.draw.rect(self.pantalla, cfg.TARJETA_FONDO_OSCURO, TARJETA_WAREHOUSE,
                         border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, cfg.TARJETA_FONDO_OSCURO, TARJETA_PRODUCTOS,
                         border_radius=cfg.RADIO_M)
        self.pincel.texto("WAREHOUSE", f.negrita, cfg.TEXTO_PRINCIPAL, 58, 104)
        self.pincel.texto("PRODUCTOS Y PEDIDOS", f.negrita, cfg.TEXTO_PRINCIPAL, 450, 104)
        for clave, etiqueta, minimo, maximo, _inicial, columna, fila in PARAMETROS:
            x, y = self._pos(columna, fila)
            valor = self.valores[clave]
            menos, valor_rect, mas = self._rects_stepper_parametro(columna, fila)
            fuente_etiqueta = f.normal
            if fuente_etiqueta.size(etiqueta)[0] > menos.left - x - 12:
                fuente_etiqueta = f.chico
            ancho_etiqueta = self.pincel.texto(etiqueta, fuente_etiqueta, cfg.TEXTO_SECUNDARIO, x, y)
            if clave in self.sincronizados and x + ancho_etiqueta + 6 < menos.left - 45:
                self.pincel.texto("● manual", f.mini, cfg.VERDE, x + ancho_etiqueta + 6, y + 3)
            self._dibujar_stepper(menos, valor_rect, mas, str(valor),
                                  valor > minimo, valor < maximo)
        self.pincel.texto("Ubicación de los productos", f.normal, cfg.TEXTO_SECUNDARIO, 450, 392)
        pygame.draw.rect(self.pantalla, cfg.STEPPER_FONDO,
                         pygame.Rect(450, 418, 380, 38), border_radius=cfg.RADIO_M)
        for indice, (modo, texto) in enumerate(MODOS):
            rect = self._rect_modo(indice)
            activo = self.modo == modo
            if activo:
                pygame.draw.rect(self.pantalla, cfg.ACENTO, rect, border_radius=cfg.RADIO_M)
            color = (255, 255, 255) if activo else cfg.TEXTO_SUAVE
            self.pincel.texto(texto, f.chico, color, rect.centerx, rect.centery, "cc")
        self.pincel.texto("Shift + clic en − o + cambia de a 5", f.chico,
                          cfg.TEXTO_DESCATIVADO, 450, 470)

    def _dibujar_panel_auto(self):
        f = self.fuentes
        self._dibujar_panel_base("GENERAR ESCENARIO")
        descripcion = ("Genera un warehouse al azar con estos parámetros.",
                       "Para usar el mapa que dibujaste en Manual,",
                       "apretá ahí «Usar escenario».")
        for i, linea in enumerate(descripcion):
            self.pincel.texto(linea, f.chico, cfg.TEXTO_SECUNDARIO,
                              PANEL_DERECHO_X + cfg.PANEL_PADDING, 76 + i * 20)

        pygame.draw.rect(self.pantalla, cfg.TARJETA_FONDO_OSCURO, TARJETA_RESUMEN,
                         border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, cfg.TARJETA_BORDE, TARJETA_RESUMEN, 1,
                         border_radius=cfg.RADIO_M)
        self.pincel.texto("RESUMEN", f.negrita, cfg.TEXTO_PRINCIPAL,
                          TARJETA_RESUMEN.x + 16, TARJETA_RESUMEN.y + 14)
        capacidad = self._capacidad()
        productos = self.valores["productos"]
        waves = self._waves_minimas()
        lineas = [(f"Ubicaciones de producto: {capacidad}", cfg.TEXTO_CUERPO)]
        if productos > capacidad:
            lineas.append((f"{productos} productos no entran en", cfg.ROJO))
            lineas.append(("esos estantes: subí estantes o alto.", cfg.ROJO))
        else:
            lineas.append((f"Productos a ubicar: {productos}", cfg.TEXTO_CUERPO))
        lineas.append((f"Waves: {waves} como mínimo", cfg.TEXTO_CUERPO))
        if self.valores["pickers"] > waves:
            lineas.append(("Hay más pickers que waves: pueden colaborar", cfg.AMARILLO))
            lineas.append(("varios pickers en una misma wave.", cfg.AMARILLO))
        for i, (texto, color) in enumerate(lineas):
            fuente = f.negrita if color == cfg.TEXTO_CUERPO else f.chico
            self.pincel.texto(texto, fuente, color,
                              TARJETA_RESUMEN.x + 16, TARJETA_RESUMEN.y + 46 + i * 20)

        self._dibujar_miniatura_manual()

    def _dibujar_miniatura_manual(self):
        f = self.fuentes
        pygame.draw.rect(self.pantalla, cfg.TARJETA_FONDO_OSCURO, TARJETA_MINIATURA,
                         border_radius=cfg.RADIO_M)
        pygame.draw.rect(self.pantalla, cfg.TARJETA_BORDE, TARJETA_MINIATURA, 1,
                         border_radius=cfg.RADIO_M)
        self.pincel.texto("MAPA DE LA PESTAÑA MANUAL", f.mini, cfg.TEXTO_SECUNDARIO,
                          TARJETA_MINIATURA.x + 16, TARJETA_MINIATURA.y + 12)
        marco = pygame.Rect(
            TARJETA_MINIATURA.x + 12, TARJETA_MINIATURA.y + 38,
            TARJETA_MINIATURA.w - 24, TARJETA_MINIATURA.h - 50,
        )
        pygame.draw.rect(self.pantalla, cfg.MAPA_FONDO, marco, border_radius=cfg.RADIO_S)
        self._dibujar_borde_punteado(marco, (100, 108, 122))
        if self.editor.esta_vacio():
            icono = pygame.Surface((112, 72), pygame.SRCALPHA)
            color_icono = (210, 220, 238, 30)
            pygame.draw.rect(icono, color_icono, (5, 5, 102, 62), 2, border_radius=6)
            for cx in (39, 73):
                pygame.draw.line(icono, color_icono, (cx, 7), (cx, 65), 2)
            for cy in (27, 48):
                pygame.draw.line(icono, color_icono, (7, cy), (105, cy), 2)
            self.pantalla.blit(icono, icono.get_rect(center=(marco.centerx, marco.centery - 24)))
            self.pincel.texto("Todavía no dibujaste nada.", f.chico, cfg.TEXTO_DESCATIVADO,
                              marco.centerx, marco.centery + 24, "centro")
            self.pincel.texto("Lo que armes en Manual aparece acá.", f.chico, cfg.TEXTO_DESCATIVADO,
                              marco.centerx, marco.centery + 43, "centro")
            return
        self.editor.miniatura(marco.inflate(-12, -12))
        m = self.editor.modelo
        resumen = (f"{len(m.racks)} racks · {len(m.zonas)} despacho · {len(m.pickers)} pickers · "
                   f"{len(m.productos)} productos")
        self.pincel.texto(resumen, f.chico, cfg.TEXTO_DESCATIVADO,
                          marco.centerx, marco.bottom + 6, "centro")

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
        self.pincel.texto("TAMAÑO DEL MAPA (celdas)", f.mini, cfg.TEXTO_SECUNDARIO,
                          x0, cursor)
        cursor += f.mini.get_height() + cfg.ESPACIO_TITULO_CONTENIDO

        # Fila: Ancho [stepper]   Alto [stepper]   [Nuevo mapa en blanco]
        self.pincel.texto("Ancho", f.normal, cfg.TEXTO_PRINCIPAL, x0, cursor)
        self.stepper_ancho.rect_menos.x = x0
        self.stepper_ancho.rect_menos.y = cursor
        self.stepper_ancho.rect_valor.x = x0 + 40
        self.stepper_ancho.rect_valor.y = cursor
        self.stepper_ancho.rect_mas.x = x0 + 162
        self.stepper_ancho.rect_mas.y = cursor
        self.stepper_ancho.dibujar(self.pantalla)

        x_alto = x0 + 260
        self.pincel.texto("Alto", f.normal, cfg.TEXTO_PRINCIPAL, x_alto, cursor)
        self.stepper_alto.rect_menos.x = x_alto
        self.stepper_alto.rect_menos.y = cursor
        self.stepper_alto.rect_valor.x = x_alto + 40
        self.stepper_alto.rect_valor.y = cursor
        self.stepper_alto.rect_mas.x = x_alto + 162
        self.stepper_alto.rect_mas.y = cursor
        self.stepper_alto.dibujar(self.pantalla)

        # Botón Nuevo mapa en blanco a la derecha
        btn_nuevo_w = 200
        btn_nuevo_rect = pygame.Rect(
            panel.right - cfg.PANEL_PADDING - btn_nuevo_w, cursor,
            btn_nuevo_w, 34,
        )
        btn_nuevo = Button("nuevo_mapa", "Nuevo mapa en blanco", btn_nuevo_rect,
                           variante="danger")
        btn_nuevo.dibujar(self.pantalla, f.normal)
        self._rect_nuevo_mapa_manual = btn_nuevo_rect

        cursor += 34 + cfg.ESPACIO_ENTRE_SECCIONES
        if self.confirmar_nuevo_mapa:
            self._dibujar_confirmacion_nuevo_mapa()
            cursor += 140 + cfg.ESPACIO_ENTRE_SECCIONES

        # d) Herramientas
        self.pincel.texto("HERRAMIENTAS", f.mini, cfg.TEXTO_SECUNDARIO, x0, cursor)
        cursor += f.mini.get_height() + cfg.ESPACIO_TITULO_CONTENIDO

        bw = (ancho - 5 * cfg.ESPACIO_S) // 6
        bh = 44
        for indice, (clave, nombre) in enumerate(HERRAMIENTAS_DIBUJO):
            tb = self.toolbuttons[indice]
            tb.rect.x = x0 + indice * (bw + cfg.ESPACIO_S)
            tb.rect.y = cursor
            tb.dibujar(self.pantalla, f.normal)
        cursor += bh + cfg.ESPACIO_ENTRE_SECCIONES

        # e) Acciones: botones cuadrados chicos con ícono
        bw_accion = 34
        bh_accion = 34
        x_accion = x0
        for ab in self.action_buttons:
            ab["rect"].x = x_accion
            ab["rect"].y = cursor
            # Dibujar botón cuadrado
            activo = ab["activo"]
            sobre = ab["rect"].collidepoint(pygame.mouse.get_pos())
            if activo:
                fondo = cfg.TOOL_BUTTON_FONDO_ACTIVO
                borde = cfg.TOOL_BUTTON_FONDO_ACTIVO
                texto_color = cfg.TEXTO_PRINCIPAL
            elif sobre:
                fondo = cfg.TOOL_BUTTON_FONDO_SOBRE
                borde = cfg.TOOL_BUTTON_BORDE
                texto_color = cfg.TEXTO_PRINCIPAL
            else:
                fondo = cfg.TOOL_BUTTON_FONDO
                borde = cfg.TOOL_BUTTON_BORDE
                texto_color = cfg.TEXTO_PRINCIPAL
            pygame.draw.rect(self.pantalla, fondo, ab["rect"],
                             border_radius=cfg.RADIO_M)
            pygame.draw.rect(self.pantalla, borde, ab["rect"], 1,
                             border_radius=cfg.RADIO_M)
            img = f.normal.render(ab["icono"], True, texto_color)
            self.pantalla.blit(img, img.get_rect(center=ab["rect"].center))
            # Tooltip
            if sobre:
                self.tooltip_action = (ab["rect"], f"{ab['nombre']} · {ab['atajo']}")
            x_accion += bw_accion + cfg.ESPACIO_S
        cursor += bh_accion + cfg.ESPACIO_ENTRE_SECCIONES

        # f) Ayuda (una sola línea)
        ayuda = AYUDA_POR_HERRAMIENTA.get(self.editor.herramienta, AYUDA_GENERICA)
        self.pincel.texto(ayuda, f.chico, cfg.TEXTO_SECUNDARIO, x0, cursor)
        cursor += f.chico.get_height() + cfg.ESPACIO_ENTRE_SECCIONES

        # g) Línea de estado de validación (arriba de barra de acciones)
        self._dibujar_linea_estado_validacion(x0, cursor, ancho)
        cursor += cfg.LINEA_ESTADO_ALTO + cfg.ESPACIO_ENTRE_SECCIONES

        # h) PICKERS COLOCADOS
        cantidad = len(self.editor.modelo.pickers)
        self.pincel.texto(f"PICKERS COLOCADOS ({cantidad})",
                          f.mini, cfg.TEXTO_SECUNDARIO, x0, cursor)
        cursor += f.mini.get_height() + cfg.ESPACIO_TITULO_CONTENIDO

        lista_alto = min(cfg.LISTA_PICKERS_ALTO_MAX,
                         cantidad * cfg.LISTA_PICKERS_ITEM_ALTO_CON_BOTON)
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
            pygame.Rect(x0, cursor, ancho, 34), f.chico,
        )
        self.status_bar.actualizar(self.editor.herramienta, coord, tamano)
        self.status_bar.dibujar(self.pantalla)
        cursor += 34

        self.pantalla.set_clip(None)

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

        # Dibujar tooltip si corresponde
        if self.tooltip_action:
            rect, texto = self.tooltip_action
            self._dibujar_tooltip(rect, texto)
            self.tooltip_action = None

    def _dibujar_linea_estado_validacion(self, x, y, ancho):
        """Línea de estado de validación: ícono + texto."""
        f = self.fuentes
        if self.editor.esta_vacio:
            icono = "○"
            color = cfg.VALIDACION_VACIO
            texto_estado = "Mapa vacío"
        elif self.editor.valido:
            icono = "✓"
            color = cfg.VALIDACION_VALIDO
            texto_estado = "Mapa válido"
        else:
            icono = "!"
            color = cfg.VALIDACION_ERROR
            errores = self.editor.errores_validacion
            texto_estado = f"{len(errores)} error(es)"

        # Fondo de la línea
        rect_linea = pygame.Rect(x, y, ancho, cfg.LINEA_ESTADO_ALTO)
        pygame.draw.rect(self.pantalla, cfg.TARJETA_FONDO_OSCURO, rect_linea,
                         border_radius=cfg.RADIO_S)
        pygame.draw.rect(self.pantalla, cfg.TARJETA_BORDE, rect_linea, 1,
                         border_radius=cfg.RADIO_S)

        # Ícono
        img_icono = f.normal.render(icono, True, color)
        self.pantalla.blit(img_icono, (x + 10, y + (cfg.LINEA_ESTADO_ALTO - img_icono.get_height()) // 2))

        # Texto
        img_texto = f.chico.render(texto_estado, True, cfg.TEXTO_PRINCIPAL)
        self.pantalla.blit(img_texto, (x + 30, y + (cfg.LINEA_ESTADO_ALTO - img_texto.get_height()) // 2))

    def _dibujar_tooltip(self, rect, texto):
        """Tooltip pequeño sobre botón de acción."""
        f = self.fuentes
        img = f.chico.render(texto, True, (255, 255, 255))
        pad = 6
        tw = img.get_width() + 2 * pad
        th = img.get_height() + 2 * pad
        tx = rect.centerx - tw // 2
        ty = rect.top - th - 6
        # Mantener dentro de pantalla
        if tx < 0:
            tx = 0
        if tx + tw > cfg.ANCHO:
            tx = cfg.ANCHO - tw
        if ty < 0:
            ty = rect.bottom + 6
        sup = pygame.Surface((tw, th), pygame.SRCALPHA)
        pygame.draw.rect(sup, (40, 44, 56, 230), sup.get_rect(), border_radius=4)
        pygame.draw.rect(sup, cfg.ACENTO, sup.get_rect(), 1, border_radius=4)
        self.pantalla.blit(sup, (tx, ty))
        self.pantalla.blit(img, (tx + pad, ty + pad))

    def _dibujar_confirmacion_nuevo_mapa(self):
        ancho, alto = 420, 140
        x = (cfg.ANCHO - ancho) // 2
        y = (cfg.ALTO - alto) // 2
        sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        pygame.draw.rect(sup, (20, 24, 32, 235), sup.get_rect(), border_radius=cfg.RADIO_L)
        pygame.draw.rect(sup, cfg.ROJO, sup.get_rect(), 2, border_radius=cfg.RADIO_L)
        self.pantalla.blit(sup, (x, y))
        self.pincel.texto("¿Borrar el mapa actual?", self.fuentes.normal,
                          cfg.TEXTO_PRINCIPAL, x + 20, y + 18)
        self.pincel.texto("Esta acción no se puede deshacer.", self.fuentes.chico,
                          cfg.TEXTO_SECUNDARIO, x + 20, y + 44)
        self.pincel.texto("Y = Sí   N = No", self.fuentes.negrita,
                          cfg.TEXTO_PRINCIPAL, x + 20, y + 74)
