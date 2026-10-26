"""Pantalla "Generar escenario" con dos pestañas.

- Automático: los parámetros de generar_escenario (estantes, pasillos, productos, pedidos...).
- Manual: el editor de mapa con mouse, con su paleta de herramientas.

Solo maneja la interfaz: devuelve acciones y App se las pasa a la Sesion.
"""

import math

import pygame

from . import config as cfg
from .editor_esc import EditorEscenario
from .widgets import dibujar_boton

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
ANCHOS_MODO = (100, 100, 138)

HERRAMIENTAS = (
    ("rack", "Rack"), ("despacho", "Despacho"), ("puerta", "Puerta"), ("pasillo", "Pasillo"),
    ("picker", "Picker"), ("producto", "Producto"), ("borrar", "Borrar"), ("deshacer", "Deshacer"),
)
SENTIDOS = (("N", "N"), ("S", "S"), ("E", "E"), ("O", "O"), ("AMBOS", "Libre"))

MAPA_MIN_X, MAPA_MAX_X = 8, 36
MAPA_MIN_Y, MAPA_MAX_Y = 8, 30

TAB_AUTO = pygame.Rect(44, 34, 190, 42)
TAB_MANUAL = pygame.Rect(242, 34, 270, 42)
BTN_CANCELAR = pygame.Rect(728, 38, 112, 34)
PANEL_DERECHO = pygame.Rect(880, 20, 380, 740)

BTN_GENERAR = pygame.Rect(900, 690, 340, 44)

ANCHO_MENOS = pygame.Rect(1060, 94, 38, 30)
ANCHO_VALOR = pygame.Rect(1104, 94, 76, 30)
ANCHO_MAS = pygame.Rect(1186, 94, 38, 30)
ALTO_MENOS = pygame.Rect(1060, 132, 38, 30)
ALTO_VALOR = pygame.Rect(1104, 132, 76, 30)
ALTO_MAS = pygame.Rect(1186, 132, 38, 30)
BTN_NUEVO = pygame.Rect(900, 174, 340, 32)
BTN_VALIDAR = pygame.Rect(900, 690, 168, 44)
BTN_USAR = pygame.Rect(1072, 690, 168, 44)

AYUDA_MANUAL = (
    "Arrastrá sobre el mapa para dibujar.",
    "Clic derecho: cancelar el arrastre.",
    "Producto: clic en un rack (z, stock, peso).",
    "Picker: clic para colocar; arrastralo para moverlo.",
    "Borrar: saca primero el producto.",
    "Atajos: 1-7 herramientas, Ctrl+Z, V, Enter.",
)

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
        self.version_vista = -1          # última versión del mapa manual que se copió a Automático
        self.sincronizados = set()       # parámetros que hoy vienen del mapa manual

    def valores_generador(self):
        """Argumentos para generar_escenario(**valores)."""
        valores = dict(self.valores)
        valores["modo_ubicacion"] = self.modo
        return valores

    # ---------- geometría de los controles ----------

    def _pos(self, columna, fila):
        return 60 + columna * 390, 150 + fila * 78

    def _rect_modo(self, indice):
        x, y = self._pos(0, 4)
        desplazamiento = 0
        for k in range(indice):
            desplazamiento += ANCHOS_MODO[k] + 8
        return pygame.Rect(x + desplazamiento, y + 26, ANCHOS_MODO[indice], 34)

    def _rect_herramienta(self, indice):
        return pygame.Rect(900 + (indice % 2) * 172, 238 + (indice // 2) * 40, 168, 34)

    def _rect_sentido(self, indice):
        return pygame.Rect(900 + indice * 68, 432, 64, 30)

    def _paso(self):
        return 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1

    # ---------- lo que se dibuja en Manual se refleja en Automático ----------

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

    # ---------- estado derivado (resumen y validación en vivo) ----------

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
        """Devuelve "generar", "validar", "usar", "cerrar" o None."""
        accion = self._procesar(ev)
        self._sincronizar()
        return accion

    def _procesar(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            accion = self._clic(ev.pos)
            if accion == "nada":
                return None
            if accion is not None:
                return accion
            if self.pestana == "manual":
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
        return {"validar": "validar", "terminar": "usar", "salir": "cerrar"}.get(accion_editor)

    def _clic(self, pos):
        """Acción ("generar", "validar", "usar", "cerrar"), "nada" si el clic se usó, o None."""
        if BTN_CANCELAR.collidepoint(pos):
            return "cerrar"
        if self.pestana == "manual" and self.editor.cuadro is not None:
            return "nada"                                # el cuadro de producto es modal
        if TAB_AUTO.collidepoint(pos):
            self.pestana = "auto"
            return "nada"
        if TAB_MANUAL.collidepoint(pos):
            self.pestana = "manual"
            return "nada"
        if self.pestana == "auto":
            return self._clic_auto(pos)
        return self._clic_manual(pos)

    def _clic_auto(self, pos):
        paso = self._paso()
        for clave, _etiqueta, minimo, maximo, _inicial, columna, fila in PARAMETROS:
            x, y = self._pos(columna, fila)
            if pygame.Rect(x, y + 26, 38, 34).collidepoint(pos):
                self.valores[clave] = max(minimo, self.valores[clave] - paso)
                self.sincronizados.discard(clave)
                return "nada"
            if pygame.Rect(x + 146, y + 26, 38, 34).collidepoint(pos):
                self.valores[clave] = min(maximo, self.valores[clave] + paso)
                self.sincronizados.discard(clave)
                return "nada"
        for indice, (modo, _texto) in enumerate(MODOS):
            if self._rect_modo(indice).collidepoint(pos):
                self.modo = modo
                return "nada"
        if BTN_GENERAR.collidepoint(pos):
            return "generar" if self._puede_generar() else "nada"
        if PANEL_DERECHO.collidepoint(pos):
            return "nada"
        return None

    def _clic_manual(self, pos):
        paso = self._paso()
        if ANCHO_MENOS.collidepoint(pos):
            self.ancho_mapa = max(MAPA_MIN_X, self.ancho_mapa - paso)
            return "nada"
        if ANCHO_MAS.collidepoint(pos):
            self.ancho_mapa = min(MAPA_MAX_X, self.ancho_mapa + paso)
            return "nada"
        if ALTO_MENOS.collidepoint(pos):
            self.alto_mapa = max(MAPA_MIN_Y, self.alto_mapa - paso)
            return "nada"
        if ALTO_MAS.collidepoint(pos):
            self.alto_mapa = min(MAPA_MAX_Y, self.alto_mapa + paso)
            return "nada"
        if BTN_NUEVO.collidepoint(pos):
            self.editor = EditorEscenario(self.ancho_mapa, self.alto_mapa, self.pincel, self.fuentes)
            self.version_vista = -1
            self._sincronizar()
            return "nada"
        for indice, (clave, _texto) in enumerate(HERRAMIENTAS):
            if self._rect_herramienta(indice).collidepoint(pos):
                if clave == "deshacer":
                    self.editor.deshacer()
                else:
                    self.editor.seleccionar(clave)
                return "nada"
        if self.editor.herramienta == "pasillo":
            for indice, (sentido, _texto) in enumerate(SENTIDOS):
                if self._rect_sentido(indice).collidepoint(pos):
                    self.editor.elegir_sentido(sentido)
                    return "nada"
        if BTN_VALIDAR.collidepoint(pos):
            return "validar"
        if BTN_USAR.collidepoint(pos):
            return "usar"
        if PANEL_DERECHO.collidepoint(pos):
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
        for rect, texto, clave in ((TAB_AUTO, "Automático", "auto"),
                                   (TAB_MANUAL, "Manual (editor de mapa)", "manual")):
            activa = self.pestana == clave
            color = (58, 112, 190) if activa else (60, 65, 76)
            pygame.draw.rect(self.pantalla, color, rect,
                             border_top_left_radius=12, border_top_right_radius=12)
            if not activa:
                pygame.draw.rect(self.pantalla, cfg.BORDE, rect, 1,
                                 border_top_left_radius=12, border_top_right_radius=12)
            fuente = self.fuentes.negrita if activa else self.fuentes.normal
            self.pincel.texto(texto, fuente, cfg.TEXTO if activa else cfg.APAGADO,
                              rect.centerx, rect.centery, "cc")
        pygame.draw.line(self.pantalla, (58, 112, 190), (44, 76), (836, 76), 2)
        dibujar_boton(self.pantalla, self.fuentes.normal, BTN_CANCELAR, "Cancelar")

    def _dibujar_panel_base(self, titulo):
        pygame.draw.rect(self.pantalla, cfg.PANEL, PANEL_DERECHO, border_radius=18)
        pygame.draw.rect(self.pantalla, cfg.BORDE_SUELO, PANEL_DERECHO, 2, border_radius=18)
        self.pincel.texto(titulo, self.fuentes.sub, cfg.ACENTO, 900, 32)

    def _dibujar_stepper(self, rect_menos, rect_valor, rect_mas, texto, puede_menos, puede_mas):
        dibujar_boton(self.pantalla, self.fuentes.negrita, rect_menos, "-", habilitado=puede_menos)
        dibujar_boton(self.pantalla, self.fuentes.negrita, rect_mas, "+", habilitado=puede_mas)
        pygame.draw.rect(self.pantalla, cfg.TARJETA, rect_valor, border_radius=8)
        pygame.draw.rect(self.pantalla, cfg.BORDE, rect_valor, 1, border_radius=8)
        self.pincel.texto(texto, self.fuentes.negrita, cfg.TEXTO,
                          rect_valor.centerx, rect_valor.centery, "cc")

    # --- pestaña automática ---

    def _dibujar_formulario(self):
        f = self.fuentes
        self.pincel.texto("WAREHOUSE", f.mini, cfg.ACENTO, 60, 100)
        self.pincel.texto("PRODUCTOS Y PEDIDOS", f.mini, cfg.ACENTO, 450, 100)
        for clave, etiqueta, minimo, maximo, _inicial, columna, fila in PARAMETROS:
            x, y = self._pos(columna, fila)
            valor = self.valores[clave]
            ancho_etiqueta = self.pincel.texto(etiqueta, f.normal, cfg.TEXTO, x, y)
            if clave in self.sincronizados:
                self.pincel.texto("● del mapa manual", f.mini, cfg.VERDE, x + ancho_etiqueta + 10, y + 3)
            self._dibujar_stepper(pygame.Rect(x, y + 26, 38, 34), pygame.Rect(x + 44, y + 26, 96, 34),
                                  pygame.Rect(x + 146, y + 26, 38, 34), str(valor),
                                  valor > minimo, valor < maximo)
        x, y = self._pos(0, 4)
        self.pincel.texto("Ubicación de los productos", f.normal, cfg.TEXTO, x, y)
        for indice, (modo, texto) in enumerate(MODOS):
            dibujar_boton(self.pantalla, f.chico, self._rect_modo(indice), texto,
                          activo=self.modo == modo)
        self.pincel.texto("Shift + clic en - o + cambia de a 5", f.chico, cfg.APAGADO, 60, 700)

    def _dibujar_panel_auto(self):
        f = self.fuentes
        self._dibujar_panel_base("GENERAR ESCENARIO")
        descripcion = ("Genera un warehouse al azar con estos parámetros.",
                       "Para usar el mapa que dibujaste en Manual,",
                       "apretá ahí «Usar escenario».")
        for i, linea in enumerate(descripcion):
            self.pincel.texto(linea, f.chico, cfg.APAGADO, 900, 76 + i * 20)

        self.pincel.texto("RESUMEN", f.mini, cfg.ACENTO, 900, 168)
        capacidad = self._capacidad()
        productos = self.valores["productos"]
        waves = self._waves_minimas()
        lineas = [(f"Ubicaciones de producto: {capacidad}", cfg.TEXTO)]
        if productos > capacidad:
            lineas.append((f"{productos} productos no entran en", cfg.ROJO))
            lineas.append(("esos estantes: subí estantes o alto.", cfg.ROJO))
        else:
            lineas.append((f"Productos a ubicar: {productos}", cfg.TEXTO))
        lineas.append((f"Waves: {waves} como mínimo", cfg.TEXTO))
        if self.valores["pickers"] > waves:
            lineas.append(("Hay más pickers que waves: cada wave", cfg.AMARILLO))
            lineas.append(("la ejecuta un solo picker, y puede fallar.", cfg.AMARILLO))
        for i, (texto, color) in enumerate(lineas):
            self.pincel.texto(texto, f.chico, color, 900, 194 + i * 22)
        self._dibujar_miniatura_manual()

        habilitado = self._puede_generar()
        dibujar_boton(self.pantalla, f.sub, BTN_GENERAR, "Generar escenario",
                      color=VERDE_BOTON if habilitado else None, habilitado=habilitado)
        if habilitado:
            self.pincel.texto("También con Enter", f.mini, cfg.APAGADO, BTN_GENERAR.centerx, 740, "centro")

    def _dibujar_miniatura_manual(self):
        f = self.fuentes
        self.pincel.texto("MAPA DE LA PESTAÑA MANUAL", f.mini, cfg.ACENTO, 900, 360)
        marco = pygame.Rect(900, 382, 340, 262)
        pygame.draw.rect(self.pantalla, (30, 34, 44), marco, border_radius=10)
        pygame.draw.rect(self.pantalla, cfg.BORDE, marco, 1, border_radius=10)
        if self.editor.esta_vacio():
            self.pincel.texto("Todavía no dibujaste nada.", f.chico, cfg.APAGADO, marco.centerx, marco.centery - 10, "centro")
            self.pincel.texto("Lo que armes en Manual aparece acá.", f.chico, cfg.APAGADO, marco.centerx, marco.centery + 10, "centro")
            return
        self.editor.miniatura(marco.inflate(-12, -12))
        m = self.editor.modelo
        resumen = (f"{len(m.racks)} racks · {len(m.zonas)} despacho · {len(m.pickers)} pickers · "
                   f"{len(m.productos)} productos")
        self.pincel.texto(resumen, f.chico, cfg.APAGADO, marco.centerx, marco.bottom + 6, "centro")

    # --- pestaña manual ---

    def _dibujar_panel_manual(self):
        f = self.fuentes
        self._dibujar_panel_base("EDITOR DE MAPA")
        self.pincel.texto("TAMAÑO DEL MAPA (celdas)", f.mini, cfg.ACENTO, 900, 72)
        self.pincel.texto("Ancho", f.normal, cfg.TEXTO, 900, 99)
        self._dibujar_stepper(ANCHO_MENOS, ANCHO_VALOR, ANCHO_MAS, str(self.ancho_mapa),
                              self.ancho_mapa > MAPA_MIN_X, self.ancho_mapa < MAPA_MAX_X)
        self.pincel.texto("Alto", f.normal, cfg.TEXTO, 900, 137)
        self._dibujar_stepper(ALTO_MENOS, ALTO_VALOR, ALTO_MAS, str(self.alto_mapa),
                              self.alto_mapa > MAPA_MIN_Y, self.alto_mapa < MAPA_MAX_Y)
        dibujar_boton(self.pantalla, f.normal, BTN_NUEVO, "Nuevo mapa en blanco")

        self.pincel.texto("HERRAMIENTAS", f.mini, cfg.ACENTO, 900, 218)
        for indice, (clave, texto) in enumerate(HERRAMIENTAS):
            activo = clave == self.editor.herramienta
            dibujar_boton(self.pantalla, f.normal, self._rect_herramienta(indice), texto, activo=activo)

        es_pasillo = self.editor.herramienta == "pasillo"
        self.pincel.texto("SENTIDO DEL PASILLO", f.mini, cfg.ACENTO if es_pasillo else cfg.APAGADO, 900, 412)
        for indice, (sentido, texto) in enumerate(SENTIDOS):
            dibujar_boton(self.pantalla, f.normal, self._rect_sentido(indice), texto,
                          activo=es_pasillo and sentido == self.editor.sentido, habilitado=es_pasillo)

        for i, linea in enumerate(AYUDA_MANUAL):
            self.pincel.texto(linea, f.chico, cfg.APAGADO, 900, 484 + i * 20)
        self._dibujar_pickers_colocados()

        dibujar_boton(self.pantalla, f.normal, BTN_VALIDAR, "Validar")
        dibujar_boton(self.pantalla, f.normal, BTN_USAR, "Usar escenario", color=VERDE_BOTON)

    def _dibujar_pickers_colocados(self):
        """Fichas con el color de cada picker (es el mismo que va a tener en la simulación)."""
        cantidad = len(self.editor.modelo.pickers)
        self.pincel.texto(f"PICKERS COLOCADOS ({cantidad})", self.fuentes.mini, cfg.ACENTO, 900, 618)
        if cantidad == 0:
            self.pincel.texto("Ninguno todavía", self.fuentes.chico, cfg.APAGADO, 900, 642)
            return
        for indice in range(min(cantidad, 12)):
            color = cfg.COLORES_PICKER[indice % len(cfg.COLORES_PICKER)]
            x = 912 + indice * 27
            self.pincel.circulo(x, 650, 10, (16, 22, 34))
            self.pincel.circulo(x, 650, 8, color)