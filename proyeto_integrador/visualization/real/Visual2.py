from tkinter import filedialog
import math
import sys
import argparse
import ctypes
import tkinter as tk

try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass

import pygame
from pygame import gfxdraw

# Ajustá estos nombres de módulo a los de tu proyecto.
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.abspath(os.path.join(current_dir, ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)


from simulation.simulationV.SimutionV import Simulacion
from simulation.simulationV.ScenarioV import generar_escenario
from simulation.simulationV.PersistenceV import (
    guardar_escenario,
    cargar_escenario,
    guardar_partida,
    cargar_partida,
)
from simulation.simulationV.RecomendadorV import recomendar_pickers
from real.Formulario import pedir_parametros_generacion
from visualization.real.Panel_recomendaciónV import PanelRecomendacion
from visualization.real.Alerta import Alerta

ANCHO = 1280
ALTO = 780
FPS = 60

# Zona donde se dibuja el mapa del almacén (dentro del tablero oscuro).
AREA_X = 40
AREA_Y = 96
AREA_W = 800
AREA_H = 620

TICK_SEG = 0.30   
VELOCIDADES = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)

MAX_TARJETAS = 5
MAX_PEDIDOS = 4
LINEAS_LOG = 4

DURACION_ALERTA = 7.0
ANCHO_ALERTA = 720

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
ROJO = (239, 68, 68)
PASILLO = (108, 114, 126)
PASILLO_FLECHA = (156, 162, 174)
RACK = (24, 52, 102)
RACK_BORDE = (59, 130, 246)
CAJA = (214, 160, 90)
CAJA_APAGADA = (92, 76, 60)

COLORES_PICKER = (
    (59, 130, 246),
    (244, 114, 182),
    (250, 204, 21),
    (52, 211, 153),
    (167, 139, 250),
    (163, 230, 53),
    (34, 211, 238),
    (232, 121, 249),
)

COLOR_ESTADO_PICKER = {
    "disponible": TEXTO,
    "yendo_a_producto": ACENTO,
    "regresando": ACENTO,
    "esperando": AMARILLO,
    "terminado": VERDE,
    "bloqueado": ROJO,
}

NOMBRE_ESTADO_PICKER = {
    "disponible": "Disponible",
    "yendo_a_producto": "Yendo a producto",
    "regresando": "Regresando",
    "esperando": "Esperando",
    "terminado": "Terminado",
    "bloqueado": "Bloqueado",
}

COLOR_ESTADO_PEDIDO = {
    "PENDIENTE": (120, 130, 150),
    "EN_PREPARACION": NARANJA,
    "PREPARADO": VERDE,
}

COLOR_ALERTA = {
    "ValueError": (185, 40, 40),
    "TypeError": (200, 100, 20),
    "Aviso": (170, 130, 10),
    "Listo": (22, 130, 90),
}


def _z_de_producto(producto):
    return producto.ubicacion[2]


class Boton:
    def __init__(self, nombre, texto, x, y, ancho, alto, color=None):
        self.nombre = nombre
        self.texto = texto
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.color = color


class Alerta:
    """Cartel rojo/naranja que aparece arriba y se cierra solo (o con un clic)."""

    def __init__(self, f_titulo, f_texto):
        self.f_titulo = f_titulo
        self.f_texto = f_texto
        self.titulo = ""
        self.lineas = []
        self.color = COLOR_ALERTA["Aviso"]
        self.restante = 0.0
        self.rect = pygame.Rect(0, 0, 0, 0)

    def mostrar(self, titulo, mensaje):
        self.titulo = titulo
        self.color = COLOR_ALERTA.get(titulo, COLOR_ALERTA["Aviso"])
        self.lineas = self._envolver(mensaje, ANCHO_ALERTA - 40)
        self.restante = DURACION_ALERTA
        alto = 16 + 24 + len(self.lineas) * 20 + 12
        self.rect = pygame.Rect((ANCHO - ANCHO_ALERTA) // 2, 24, ANCHO_ALERTA, alto)

    def cerrar(self):
        self.restante = 0.0

    def visible(self):
        return self.restante > 0.0

    def actualizar(self, dt):
        if self.restante > 0.0:
            self.restante = max(0.0, self.restante - dt)

    def _envolver(self, texto, ancho):
        lineas = []
        actual = ""
        for palabra in texto.split():
            prueba = palabra if not actual else actual + " " + palabra
            if self.f_texto.size(prueba)[0] <= ancho:
                actual = prueba
            else:
                if actual:
                    lineas.append(actual)
                actual = palabra
        if actual:
            lineas.append(actual)
        if not lineas:
            lineas.append("")
        return lineas

    def dibujar(self, pantalla):
        if not self.visible():
            return
        pygame.draw.rect(pantalla, self.color, self.rect, border_radius=12)
        pygame.draw.rect(pantalla, (255, 255, 255), self.rect, 2, border_radius=12)
        titulo = self.f_titulo.render(self.titulo, True, (255, 255, 255))
        pantalla.blit(titulo, (self.rect.x + 20, self.rect.y + 12))
        for i, linea in enumerate(self.lineas):
            img = self.f_texto.render(linea, True, (255, 255, 255))
            pantalla.blit(img, (self.rect.x + 20, self.rect.y + 40 + i * 20))


class App:

    def __init__(self, datos):
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

        self.alerta = Alerta(self.f_negrita, self.f_normal)
        self.f_alerta_titulo = pygame.font.SysFont(nombres, 24, bold=True)
        self.f_alerta_texto = pygame.font.SysFont(nombres, 19)
        self.alerta = Alerta(self.f_alerta_titulo, self.f_alerta_texto)
        
        self.panel = PanelRecomendacion(self.f_sub, self.f_normal, self.f_chico, self.f_mini)
        
        self.vel_idx = 2
        self.t_anim = 0.0

        self.botones = []
        self._crear_botones()

        self.sim = None
        self._usar_simulacion(Simulacion(datos))

    # ---------- carga de simulaciones ----------

    def _usar_simulacion(self, sim):
        self.sim = sim
        self.capacidades = {}
        for picker in self.sim.pickers:
            self.capacidades[picker.id] = picker.capacidad
        self._preparar_mapa()
        self._reiniciar_vista()

    def _preparar_mapa(self):
        almacen = self.sim.warehouse
        self.ancho_celdas = almacen.ancho_x
        self.alto_celdas = almacen.largo_y
        celda = min(AREA_W // self.ancho_celdas, AREA_H // self.alto_celdas)
        self.celda = max(6, celda)
        ancho_px = self.celda * self.ancho_celdas
        alto_px = self.celda * self.alto_celdas
        self.mapa_x = AREA_X + (AREA_W - ancho_px) // 2
        self.mapa_y = AREA_Y + (AREA_H - alto_px) // 2

    def _reiniciar_vista(self):
        """Vuelve a leer del Warehouse de la simulación (productos nuevos tras reiniciar)."""
        self.corriendo = False
        self.paso_pendiente = False
        self.progreso = 1.0
        self.prev = {}
        self._armar_pilas()
        self._refrescar_estado()

    def _reiniciar(self):
        self.sim.reiniciar()
        self._reiniciar_vista()

    def _armar_pilas(self):
        self.pilas = {}
        for producto in self.sim.productos.values():
            celda = (producto.ubicacion[0], producto.ubicacion[1])
            self.pilas.setdefault(celda, []).append(producto)

    def _refrescar_estado(self):
        self.estado = self.sim.estado()
        self.pendientes_ids = set()
        self.recogidos_ids = set()
        for p in self.estado["pickers"]:
            self.pendientes_ids.update(p["pendientes"])
            for recogido in p["recogidos"]:
                self.recogidos_ids.add(recogido["producto_id"])

    # ---------- botones ----------

    def _crear_botones(self):
        self.botones = []
        # Simulación
        self.botones.append(Boton("iniciar", "Iniciar", 900, 72, 62, 34, (22, 163, 74)))
        self.botones.append(Boton("pausar", "Pausar", 968, 72, 62, 34))
        self.botones.append(Boton("continuar", "Continuar", 1036, 72, 76, 34))
        self.botones.append(Boton("reiniciar", "Reiniciar", 1118, 72, 70, 34))
        self.botones.append(Boton("paso", "Paso", 1194, 72, 52, 34))
        self.botones.append(Boton("recomendar", "Recomendar", 1000, 116, 150, 30))
        # Velocidad
        self.botones.append(Boton("vel_menos", "-", 1160, 118, 36, 26))
        self.botones.append(Boton("vel_mas", "+", 1204, 118, 36, 26))
        # Escenarios y partidas
        self.botones.append(Boton("generar", "Generar escenario", 900, 156, 166, 30))
        self.botones.append(Boton("cargar_escenario", "Cargar escenario", 1074, 156, 166, 30))
        self.botones.append(Boton("guardar_escenario", "Guardar escenario", 900, 194, 166, 30))
        self.botones.append(Boton("cargar_partida", "Cargar partida", 1074, 194, 166, 30))
        self.botones.append(Boton("guardar_partida", "Guardar partida", 900, 232, 340, 30))

    def _click(self, nombre):
        """Punto único donde se atrapan los errores y se muestran como alerta."""
        try:
            self._ejecutar(nombre)
        except (TypeError, ValueError) as error:
            self.corriendo = False
            self.alerta.mostrar(type(error).__name__, str(error))

    def _ejecutar(self, nombre):
        if nombre == "generar":
            self._generar()
        elif nombre == "cargar_escenario":
            self._cargar_escenario()
        elif nombre == "guardar_escenario":
            self._guardar_escenario()
        elif nombre == "cargar_partida":
            self._cargar_partida()
        elif nombre == "guardar_partida":
            self._guardar_partida()
        elif nombre == "iniciar":
            self._reiniciar()
            self.corriendo = True
        elif nombre == "pausar":
            self.corriendo = False
        elif nombre == "continuar":
            if not self.sim.terminada:
                self.corriendo = True
        elif nombre == "reiniciar":
            self._reiniciar()
        elif nombre == "paso":
            self.corriendo = False
            if not self.sim.terminada:
                self.paso_pendiente = True
        elif nombre == "vel_menos":
            self.vel_idx = max(0, self.vel_idx - 1)
        elif nombre == "vel_mas":
            self.vel_idx = min(len(VELOCIDADES) - 1, self.vel_idx + 1)
        elif nombre == "recomendar":
            self._recomendar()
        elif nombre == "usar_recomendado":
            self._usar_recomendado()
            self.panel.cerrar()

    # ---------- escenarios y partidas ----------

    def _dialogo_abrir(self, titulo):
        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()
        ruta = filedialog.askopenfilename(
            title=titulo, filetypes=[("Archivos JSON", "*.json")], parent=root)
        root.destroy()
        return ruta

    def _dialogo_guardar(self, titulo, nombre):
        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()
        ruta = filedialog.asksaveasfilename(
            title=titulo, defaultextension=".json", initialfile=nombre,
            filetypes=[("Archivos JSON", "*.json")], parent=root)
        root.destroy()
        return ruta

    def _generar(self):
        self.corriendo = False
        valores = pedir_parametros_generacion()
        if valores is None:
            return
        datos = generar_escenario(**valores)
        self._usar_simulacion(Simulacion(datos))

    def _cargar_escenario(self):
        self.corriendo = False
        ruta = self._dialogo_abrir("Cargar escenario")
        if not ruta:
            return
        datos = cargar_escenario(ruta)
        self._usar_simulacion(Simulacion(datos))

    def _guardar_escenario(self):
        self.corriendo = False
        ruta = self._dialogo_guardar("Guardar escenario", "escenario.json")
        if not ruta:
            return
        guardar_escenario(ruta, self.sim.datos)
        self.alerta.mostrar("Listo", f"Escenario guardado en {ruta}")

    def _cargar_partida(self):
        self.corriendo = False
        ruta = self._dialogo_abrir("Cargar partida")
        if not ruta:
            return
        datos, estado = cargar_partida(ruta)
        sim = Simulacion(datos)
        try:
            sim.restaurar(estado)
        except (KeyError, IndexError) as error:
            raise ValueError(f"La partida está dañada y no se pudo restaurar: {error}") from error
        self._usar_simulacion(sim)

    def _guardar_partida(self):
        self.corriendo = False
        ruta = self._dialogo_guardar("Guardar partida", "partida.json")
        if not ruta:
            return
        guardar_partida(ruta, self.sim)
        self.alerta.mostrar("Listo", f"Partida guardada en {ruta}")

    def _recomendar(self):                 
        self.corriendo = False
        self._dibujar()
        self._rect_alfa(440, 340, 400, 80, (10, 14, 24, 230), 14)
        self._texto("Calculando recomendacion...", self.f_sub, TEXTO, 640, 380, "cc")
        pygame.display.flip()
        self.panel.mostrar(recomendar_pickers(self.sim.datos, self.sim.waves_entrada))

    def _usar_recomendado(self):            
        nuevos = dict(self.sim.datos)
        nuevos["pickers"] = list(self.panel.pickers_recomendados)
        self._usar_simulacion(Simulacion(nuevos, self.sim.waves_entrada))

    # ---------- avance de la simulación ----------

    def _dar_paso(self):
        self.prev = {}
        for p in self.estado["pickers"]:
            self.prev[p["id"]] = p["posicion"]
        self.sim.paso()
        self._refrescar_estado()
        self.progreso = 0.0
        self.paso_pendiente = False
        if self.sim.terminada:
            self.corriendo = False
            self._avisar_fin()

    def _avisar_fin(self):
        bloqueados = []
        for p in self.estado["pickers"]:
            if p["estado"] == "bloqueado":
                bloqueados.append(p["id"])
        if bloqueados:
            self.alerta.mostrar(
                "Aviso",
                "La simulación terminó con pickers bloqueados: " + ", ".join(bloqueados) + ".",
            )

    def _actualizar(self, dt):
        if self.progreso < 1.0:
            self.progreso = min(1.0, self.progreso + dt * VELOCIDADES[self.vel_idx] / TICK_SEG)
            return
        if self.sim.terminada:
            self.corriendo = False
            self.paso_pendiente = False
            return
        if self.corriendo or self.paso_pendiente:
            self._dar_paso()

    # ---------- utilidades de coordenadas ----------

    def _centro(self, x, y):
        px = self.mapa_x + x * self.celda + self.celda / 2
        py = self.mapa_y + (self.alto_celdas - 1 - y) * self.celda + self.celda / 2
        return int(px), int(py)

    def _rect_celdas(self, x, y, ancho, alto):
        izq = self.mapa_x + x * self.celda
        arriba = self.mapa_y + (self.alto_celdas - (y + alto)) * self.celda
        return pygame.Rect(int(izq), int(arriba), ancho * self.celda, alto * self.celda)

    def _celda_en(self, mx, my):
        gx = (mx - self.mapa_x) // self.celda
        gy = (my - self.mapa_y) // self.celda
        if 0 <= gx < self.ancho_celdas and 0 <= gy < self.alto_celdas:
            return (int(gx), int(self.alto_celdas - 1 - gy))
        return None

    def _pos_visual(self, p):
        actual = p["posicion"]
        previa = self.prev.get(p["id"])
        if previa is None or self.progreso >= 1.0:
            return actual[0], actual[1]
        t = self.progreso
        return (previa[0] + (actual[0] - previa[0]) * t,
                previa[1] + (actual[1] - previa[1]) * t)

    def _color_picker(self, indice):
        return COLORES_PICKER[indice % len(COLORES_PICKER)]

    # ---------- utilidades de dibujo ----------

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

    def _recortar(self, texto, fuente, ancho):
        if fuente.size(texto)[0] <= ancho:
            return texto
        while len(texto) > 1 and fuente.size(texto + "...")[0] > ancho:
            texto = texto[:-1]
        return texto + "..."

    def _circulo(self, x, y, radio, color):
        gfxdraw.filled_circle(self.pantalla, x, y, radio, color)
        gfxdraw.aacircle(self.pantalla, x, y, radio, color)

    def _circulo_alfa(self, x, y, radio, color, alfa):
        sup = pygame.Surface((radio * 2 + 2, radio * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(sup, (color[0], color[1], color[2], alfa), (radio + 1, radio + 1), radio)
        self.pantalla.blit(sup, (x - radio - 1, y - radio - 1))

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

    # ---------- dibujo del warehouse ----------

    def _dibujar_base(self):
        rect = self._rect_celdas(0, 0, self.ancho_celdas, self.alto_celdas)
        pygame.draw.rect(self.pantalla, (66, 72, 84), rect)

    def _dibujar_perimetro(self):
        rect = self._rect_celdas(0, 0, self.ancho_celdas, self.alto_celdas)
        pygame.draw.rect(self.pantalla, TEXTO, rect.inflate(2, 2), 2)

    def _dibujar(self):
        self.pantalla.fill(BG)
        pygame.draw.rect(self.pantalla, SUELO, (20, 20, 840, 740), border_radius=18)
        pygame.draw.rect(self.pantalla, BORDE_SUELO, (20, 20, 840, 740), 2, border_radius=18)

        self._dibujar_encabezado()
        self._dibujar_base()  
        self._dibujar_pasillos()
        self._dibujar_despacho()
        self._dibujar_racks()
        self._dibujar_perimetro() 
        self._dibujar_productos()
        self._dibujar_recorridos()
        self._dibujar_objetivos()
        self._dibujar_pickers()
        self._dibujar_leyenda()
        self._dibujar_panel()
        self._dibujar_tooltip()
        self.panel.dibujar(self.pantalla)
        self.alerta.dibujar(self.pantalla)

        pygame.display.flip()

    def _texto_estado(self):
        if self.sim.terminada:
            for p in self.estado["pickers"]:
                if p["estado"] == "bloqueado":
                    return "Terminada con pickers bloqueados"
            return "Simulacion terminada"
        if self.corriendo:
            return "En curso"
        if self.estado["tick"] == 0:
            return "Listo. Presiona Iniciar o Paso"
        return "En pausa"

    def _dibujar_encabezado(self):
        preparados = 0
        for pedido in self.sim.pedidos_wave:
            if pedido.estado == "PREPARADO":
                preparados += 1
        pasos = 0
        for p in self.estado["pickers"]:
            pasos += len(p["trail"]) - 1
        self._texto("Almacen", self.f_titulo, TEXTO, 44, 30)
        resumen = (f"Tick {self.estado['tick']}   |   Pickers {len(self.estado['pickers'])}   |   "
                   f"Pedidos listos {preparados}/{len(self.sim.pedidos_wave)}   |   Pasos {pasos}")
        self._texto(resumen, self.f_normal, APAGADO, 44, 68)
        ancho = 300
        self._rect_alfa(540, 36, ancho, 30, (88, 166, 255, 38), 15)
        self._texto(self._texto_estado(), self.f_chico, TEXTO, 540 + ancho // 2, 44, "centro")

    def _dibujar_pasillos(self):
        pasillos = self.sim.warehouse.pasillos.values()
        for pasillo in pasillos:
            x0, y0 = pasillo.ubicacion
            rect = self._rect_celdas(x0, y0, pasillo.ancho, pasillo.alto)
            pygame.draw.rect(self.pantalla, PASILLO, rect)
        s = max(2, int(self.celda * 0.16))
        for pasillo in pasillos:
            if pasillo.sentido not in ("N", "S", "E", "O"):
                continue
            for celda in pasillo.cells():
                cx, cy = self._centro(celda[0], celda[1])
                if pasillo.sentido == "N":
                    puntos = [(cx, cy - s), (cx - s, cy + s), (cx + s, cy + s)]
                elif pasillo.sentido == "S":
                    puntos = [(cx, cy + s), (cx - s, cy - s), (cx + s, cy - s)]
                elif pasillo.sentido == "E":
                    puntos = [(cx + s, cy), (cx - s, cy - s), (cx - s, cy + s)]
                else:
                    puntos = [(cx - s, cy), (cx + s, cy - s), (cx + s, cy + s)]
                pygame.draw.polygon(self.pantalla, PASILLO_FLECHA, puntos)

    def _dibujar_despacho(self):
        almacen = self.sim.warehouse
        for zona in almacen.zonas_despacho.values():
            x0, y0 = zona.ubicacion
            rect = self._rect_celdas(x0, y0, zona.ancho, zona.alto)
            self._rect_alfa(rect.x, rect.y, rect.width, rect.height, (52, 211, 153, 60), 6)
            self._rect_punteado(rect.x, rect.y, rect.width, rect.height, VERDE)
            if rect.width >= 80:
                self._texto("DESPACHO", self.f_mini, VERDE, rect.x + 6, rect.y + 4)
        for puerta in almacen.puertas.values():
            cx, cy = self._centro(puerta.ubicacion[0], puerta.ubicacion[1])
            lado = max(6, int(self.celda * 0.8))
            pygame.draw.rect(self.pantalla, NARANJA,
                             (cx - lado // 2, cy - lado // 2, lado, lado), border_radius=3)
            if self.celda >= 16:
                self._texto("P", self.f_mini, (60, 30, 5), cx, cy, "cc")

    def _dibujar_racks(self):
        for rack in self.sim.warehouse.racks.values():
            x0, y0 = rack.ubicacion
            rect = self._rect_celdas(x0, y0, rack.ancho, rack.alto).inflate(-2, -2)
            pygame.draw.rect(self.pantalla, RACK, rect, border_radius=4)
            pygame.draw.rect(self.pantalla, RACK_BORDE, rect, 2, border_radius=4)

    def _dibujar_productos(self):
        lado = max(4, int(self.celda * 0.62))
        for celda, pila in self.pilas.items():
            cx, cy = self._centro(celda[0], celda[1])
            pendiente = False
            recogido = False
            for producto in pila:
                if producto.id in self.pendientes_ids:
                    pendiente = True
                if producto.id in self.recogidos_ids:
                    recogido = True
            if pendiente:
                relleno = NARANJA
                borde = (255, 236, 200)
            elif recogido:
                relleno = (34, 110, 84)
                borde = VERDE
            else:
                relleno = CAJA_APAGADA
                borde = (70, 62, 52)
            rect = pygame.Rect(cx - lado // 2, cy - lado // 2, lado, lado)
            pygame.draw.rect(self.pantalla, relleno, rect, border_radius=3)
            pygame.draw.rect(self.pantalla, borde, rect, 1, border_radius=3)
            if len(pila) > 1 and self.celda >= 20:
                color_n = (60, 40, 20) if pendiente else TEXTO
                self._texto(str(len(pila)), self.f_mini, color_n, cx, cy, "cc")

    def _dibujar_recorridos(self):
        self.glow.fill((0, 0, 0, 0))
        ancho = max(2, self.celda // 6)
        for i, p in enumerate(self.estado["pickers"]):
            color = self._color_picker(i)
            puntos = []
            for celda in p["trail"]:
                puntos.append(self._centro(celda[0], celda[1]))
            if len(puntos) >= 2:
                pygame.draw.lines(self.glow, (color[0], color[1], color[2], 110),
                                  False, puntos, ancho)
        self.pantalla.blit(self.glow, (0, 0))
        for i, p in enumerate(self.estado["pickers"]):
            color = self._color_picker(i)
            for celda in p["ruta"]:
                cx, cy = self._centro(celda[0], celda[1])
                pygame.draw.circle(self.pantalla, color, (cx, cy), 2)

    def _dibujar_objetivos(self):
        pulso = 2 * math.sin(self.t_anim * 6)
        radio = int(self.celda * 0.55 + pulso)
        for i, p in enumerate(self.estado["pickers"]):
            if p["objetivo"] is None:
                continue
            producto = self.sim.productos.get(p["objetivo"])
            if producto is None:
                continue
            cx, cy = self._centro(producto.ubicacion[0], producto.ubicacion[1])
            self._anillo(cx, cy, radio, self._color_picker(i), 2)

    def _etiqueta_picker(self, id_picker):
        numero = id_picker[3:]
        return numero.lstrip("0") or numero

    def _dibujar_pickers(self):
        radio = max(6, min(14, int(self.celda * 0.4)))
        # Primero los que ya terminaron (apagados), así no tapan a los activos.
        for i, p in enumerate(self.estado["pickers"]):
            if p["estado"] != "terminado":
                continue
            x, y = self._centro(*self._pos_visual(p))
            self._circulo_alfa(x, y, radio, self._color_picker(i), 110)
        for i, p in enumerate(self.estado["pickers"]):
            if p["estado"] == "terminado":
                continue
            x, y = self._centro(*self._pos_visual(p))
            self._circulo(x, y, radio, self._color_picker(i))
            if radio >= 7:
                self._texto(self._etiqueta_picker(p["id"]), self.f_mini, (8, 20, 30), x, y, "cc")

    def _dibujar_leyenda(self):
        y = 732
        x = 44
        pygame.draw.rect(self.pantalla, PASILLO, (x, y + 2, 24, 12), border_radius=3)
        pygame.draw.polygon(self.pantalla, PASILLO_FLECHA,
                            [(x + 18, y + 8), (x + 8, y + 3), (x + 8, y + 13)])
        x += 24 + 6 + self._texto("Pasillo (flecha = sentido)", self.f_chico, APAGADO, x + 30, y) + 20
        pygame.draw.rect(self.pantalla, RACK, (x, y + 1, 22, 14), border_radius=3)
        pygame.draw.rect(self.pantalla, RACK_BORDE, (x, y + 1, 22, 14), 1, border_radius=3)
        x += 22 + 6 + self._texto("Rack", self.f_chico, APAGADO, x + 28, y) + 20
        pygame.draw.rect(self.pantalla, NARANJA, (x, y + 1, 14, 14), border_radius=3)
        x += 14 + 6 + self._texto("A recoger", self.f_chico, APAGADO, x + 20, y) + 20
        pygame.draw.rect(self.pantalla, (34, 110, 84), (x, y + 1, 14, 14), border_radius=3)
        pygame.draw.rect(self.pantalla, VERDE, (x, y + 1, 14, 14), 1, border_radius=3)
        x += 14 + 6 + self._texto("Recogido", self.f_chico, APAGADO, x + 20, y) + 20
        pygame.draw.rect(self.pantalla, VERDE, (x, y + 1, 22, 14), 1, border_radius=3)
        x += 22 + 6 + self._texto("Despacho", self.f_chico, APAGADO, x + 28, y) + 20
        pygame.draw.rect(self.pantalla, NARANJA, (x, y + 1, 14, 14), border_radius=3)
        self._texto("Puerta", self.f_chico, APAGADO, x + 20, y)

    # ---------- panel lateral ----------

    def _dibujar_boton(self, boton):
        mx, my = pygame.mouse.get_pos()
        sobre = boton.rect.collidepoint((mx, my))

        if boton.color is not None:
            relleno = boton.color
            if sobre:
                relleno = tuple(min(255, v + 30) for v in relleno)
        elif sobre:
            relleno = (100, 110, 130)
        else:
            relleno = (75, 82, 99)

        radio = 10
        pygame.draw.rect(self.pantalla, relleno, boton.rect, border_radius=radio)
        borde = (160, 170, 190) if sobre else (110, 120, 140)
        pygame.draw.rect(self.pantalla, borde, boton.rect, 2, border_radius=radio)
        self._texto(boton.texto, self.f_normal, (255, 255, 255),
                    boton.rect.centerx, boton.rect.centery, "cc")

    def _dibujar_panel(self):
        pygame.draw.rect(self.pantalla, PANEL, (880, 20, 380, 740), border_radius=18)
        pygame.draw.rect(self.pantalla, BORDE_SUELO, (880, 20, 380, 740), 2, border_radius=18)
        self._texto("WAVE PICKING", self.f_sub, ACENTO, 900, 32)
        self._texto("Algoritmos II", self.f_chico, APAGADO, 1240, 38, "der")
        for boton in self.botones:
            self._dibujar_boton(boton)
        self._texto(f"Velocidad  x{VELOCIDADES[self.vel_idx]:g}", self.f_chico, TEXTO, 900, 124)
        self._dibujar_tarjetas_pickers()
        self._dibujar_pedidos()
        self._dibujar_log()

    def _dibujar_tarjetas_pickers(self):
        self._texto("PICKERS", self.f_mini, APAGADO, 900, 276)
        lista = self.estado["pickers"]
        for i, p in enumerate(lista[:MAX_TARJETAS]):
            y = 294 + i * 48
            color = self._color_picker(i)
            pygame.draw.rect(self.pantalla, TARJETA, (900, y, 340, 44), border_radius=8)
            pygame.draw.rect(self.pantalla, BORDE, (900, y, 340, 44), 1, border_radius=8)
            pygame.draw.rect(self.pantalla, color, (900, y + 6, 5, 32), border_radius=2)
            self._texto(p["id"], self.f_negrita, TEXTO, 914, y + 3)
            nombre = NOMBRE_ESTADO_PICKER.get(p["estado"], p["estado"])
            color_estado = COLOR_ESTADO_PICKER.get(p["estado"], TEXTO)
            self._texto(nombre, self.f_chico, color_estado, 1232, y + 5, "der")
            objetivo = p["objetivo"] if p["objetivo"] is not None else "-"
            capacidad = self.capacidades.get(p["id"], 0)
            linea = (f"Objetivo {objetivo}   Pend. {len(p['pendientes'])}   "
                     f"Recog. {len(p['recogidos'])}   Cap. {capacidad:g} kg")
            self._texto(self._recortar(linea, self.f_mini, 320), self.f_mini, APAGADO, 914, y + 26)
        if len(lista) > MAX_TARJETAS:
            extra = len(lista) - MAX_TARJETAS
            self._texto(f"+{extra} pickers mas", self.f_chico, APAGADO, 900, 294 + MAX_TARJETAS * 48 - 2)

    def _dibujar_pedidos(self):
        self._texto("PEDIDOS DE LA WAVE", self.f_mini, APAGADO, 900, 556)
        pedidos = self.sim.pedidos_wave
        for i, pedido in enumerate(pedidos[:MAX_PEDIDOS]):
            y = 574 + i * 24
            pygame.draw.rect(self.pantalla, TARJETA, (900, y, 340, 20), border_radius=6)
            self._texto(pedido.id, self.f_chico, TEXTO, 910, y + 3)
            for k in range(5):
                relleno = AMARILLO if k < pedido.prioridad else (96, 102, 116)
                self._circulo(986 + k * 10, y + 10, 3, relleno)
            self._texto(f"{len(pedido.items)} items", self.f_mini, APAGADO, 1050, y + 5)
            color = COLOR_ESTADO_PEDIDO.get(pedido.estado, APAGADO)
            self._texto(pedido.estado, self.f_mini, color, 1230, y + 5, "der")
        if len(pedidos) > MAX_PEDIDOS:
            extra = len(pedidos) - MAX_PEDIDOS
            self._texto(f"+{extra} pedidos mas", self.f_mini, APAGADO, 900, 574 + MAX_PEDIDOS * 24)

    def _dibujar_log(self):
        self._texto("REGISTRO", self.f_mini, APAGADO, 900, 676)
        lineas = self.estado["log"][-LINEAS_LOG:]
        for i, linea in enumerate(lineas):
            self._texto(self._recortar(linea, self.f_mini, 340), self.f_mini, TEXTO, 900, 692 + i * 14)

    def _dibujar_tooltip(self):
        mx, my = pygame.mouse.get_pos()
        celda = self._celda_en(mx, my)
        if celda is None:
            return
        pila = self.pilas.get(celda)
        if not pila:
            return
        lineas = [f"Pila ({celda[0]}, {celda[1]})"]
        for producto in sorted(pila, key=_z_de_producto):
            marca = "  (a recoger)" if producto.id in self.pendientes_ids else ""
            lineas.append(
                f"z{producto.ubicacion[2]}  {producto.id}  stock {producto.stock}  "
                f"{producto.peso_kg:g} kg{marca}"
            )
        ancho = 250
        alto = 12 + len(lineas) * 20
        x = min(mx + 16, ANCHO - ancho - 10)
        y = min(my + 12, ALTO - alto - 10)
        pygame.draw.rect(self.pantalla, (10, 14, 24), (x, y, ancho, alto), border_radius=8)
        pygame.draw.rect(self.pantalla, ACENTO, (x, y, ancho, alto), 1, border_radius=8)
        for i, linea in enumerate(lineas):
            fuente = self.f_negrita if i == 0 else self.f_chico
            self._texto(linea, fuente, TEXTO if i == 0 else APAGADO, x + 10, y + 8 + i * 20)

    # ---------- bucle principal ----------

    def _teclado(self, tecla):
        if tecla == pygame.K_ESCAPE:
            if self.alerta.visible():
                self.alerta.cerrar()
            else:
                self.panel.cerrar()
            return

        if self.panel.visible():
            return
        
        if tecla == pygame.K_SPACE:
            if self.corriendo:
                self._click("pausar")
            else:
                self._click("continuar")
        elif tecla == pygame.K_n:
            self._click("paso")
        elif tecla == pygame.K_r:
            self._click("reiniciar")
        elif tecla in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self._click("vel_mas")
        elif tecla in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._click("vel_menos")
        elif tecla == pygame.K_ESCAPE:
            self.panel.cerrar()
            
    def correr(self):
        activo = True
        while activo:
            dt = self.reloj.tick(FPS) / 1000.0
            self.t_anim += dt
            self.alerta.actualizar(dt)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    activo = False
                elif ev.type == pygame.KEYDOWN:
                    self._teclado(ev.key)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.alerta.visible() and self.alerta.rect.collidepoint(ev.pos):
                        self.alerta.clic(ev.pos)
                        continue
                    if self.panel.visible():
                        if self.panel.clic(ev.pos) == "usar":
                            self._click("usar_recomendado")
                        continue
                    for boton in self.botones:
                        if boton.rect.collidepoint(ev.pos):
                            self._click(boton.nombre)
                            break
            try:
                self._actualizar(dt)
            except (TypeError, ValueError) as error:
                self.corriendo = False
                self.paso_pendiente = False
                self.alerta.mostrar(type(error).__name__, str(error))
            self._dibujar()
        pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de Wave Picking")
    parser.add_argument("--escenario", type=str, help="Ruta al archivo JSON a cargar", default=None)
    args = parser.parse_args()

    datos_iniciales = None
    if args.escenario:
        try:
            datos_iniciales = cargar_escenario(args.escenario)
        except ValueError as error:
            print(f"No se pudo cargar el escenario: {error}")

    if datos_iniciales is None:
        datos_iniciales = generar_escenario()

    app = App(datos_iniciales)
    app.correr()
    sys.exit(0)