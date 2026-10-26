"""Aplicación visual: bucle principal y reparto de eventos.

La lógica de la simulación vive en simulation.simulationV.SesionV; acá solo hay
interfaz (ventana, mouse, teclado, animación y alertas).
"""

import pygame

from simulation.simulationV.Sesion import Sesion
from . import config as cfg
from . import dialogos
from .animacion import Animacion
from .panel import PanelLateral
from .generador_pantalla import PantallaGenerador
from .pincel import Fuentes, Pincel
from .vista_mapa import VistaMapa
from .widgets import Alerta


class App:

    def __init__(self, datos):
        pygame.init()
        pygame.display.set_caption("Wave Picking - Simulacion")
        self.pantalla = pygame.display.set_mode((cfg.ANCHO, cfg.ALTO))
        self.reloj = pygame.time.Clock()

        self.fuentes = Fuentes()
        self.pincel = Pincel(self.pantalla)
        self.alerta = Alerta(self.fuentes.alerta_titulo, self.fuentes.alerta_texto)

        self.sesion = Sesion(datos)
        self.anim = Animacion()
        self.vista = VistaMapa(self.pincel, self.fuentes, self.sesion, self.anim)
        self.panel = PanelLateral(self.pincel, self.fuentes, self.sesion, self.anim)
        self.generador = None

    def _refrescar_vista(self):
        """Tras cambiar la simulación: nuevo tamaño de mapa y animación en cero."""
        self.vista.recalcular()
        self.anim.reiniciar()

    # ---------- acciones ----------

    def _click(self, nombre):
        """Punto único donde se atrapan los errores y se muestran como alerta."""
        try:
            self._ejecutar(nombre)
        except (TypeError, ValueError) as error:
            self.sesion.pausar()
            self.alerta.mostrar(type(error).__name__, str(error))

    def _ejecutar(self, nombre):
        if nombre == "generar":
            self._abrir_generador()
        elif nombre == "cargar_escenario":
            self._cargar_escenario()
        elif nombre == "guardar_escenario":
            self._guardar_escenario()
        elif nombre == "cargar_partida":
            self._cargar_partida()
        elif nombre == "guardar_partida":
            self._guardar_partida()
        elif nombre == "iniciar":
            self.sesion.iniciar()
            self._refrescar_vista()
        elif nombre == "pausar":
            self.sesion.pausar()
        elif nombre == "continuar":
            self.sesion.continuar()
        elif nombre == "reiniciar":
            self.sesion.reiniciar()
            self._refrescar_vista()
        elif nombre == "paso":
            self.sesion.pedir_paso()
        elif nombre == "vel_menos":
            self.anim.frenar()
        elif nombre == "vel_mas":
            self.anim.acelerar()
        elif nombre == "aplicar_generacion":
            self._aplicar_generacion()
        elif nombre == "validar_editor":
            self._validar_editor()
        elif nombre == "usar_editor":
            self._usar_editor()


    def _cargar_escenario(self):
        self.sesion.pausar()
        ruta = dialogos.abrir("Cargar escenario")
        if not ruta:
            return
        self.sesion.cargar_escenario(ruta)
        self._refrescar_vista()

    def _guardar_escenario(self):
        self.sesion.pausar()
        ruta = dialogos.guardar("Guardar escenario", "escenario.json")
        if not ruta:
            return
        self.sesion.guardar_escenario(ruta)
        self.alerta.mostrar("Listo", f"Escenario guardado en {ruta}")

    def _cargar_partida(self):
        self.sesion.pausar()
        ruta = dialogos.abrir("Cargar partida")
        if not ruta:
            return
        self.sesion.cargar_partida(ruta)
        self._refrescar_vista()

    def _guardar_partida(self):
        self.sesion.pausar()
        ruta = dialogos.guardar("Guardar partida", "partida.json")
        if not ruta:
            return
        self.sesion.guardar_partida(ruta)
        self.alerta.mostrar("Listo", f"Partida guardada en {ruta}")

    # ---------- generar escenario (pestañas Automático y Manual) ----------

    def _abrir_generador(self):
        self.sesion.pausar()
        almacen = self.sesion.sim.warehouse
        self.generador = PantallaGenerador(self.pincel, self.fuentes, almacen.ancho_x, almacen.largo_y)

    def _aplicar_generacion(self):
        self.sesion.generar(self.generador.valores_generador())
        self.generador = None
        self._refrescar_vista()
        self.alerta.mostrar("Listo", "Escenario generado.")

    def _validar_editor(self):
        modelo = self.generador.editor.modelo
        errores = modelo.validar()
        if errores:
            self.alerta.mostrar("Aviso", " | ".join(errores))
            return
        self.sesion.validar_datos(modelo.a_diccionario())
        self.alerta.mostrar("Listo", "El escenario es válido")

    def _usar_editor(self):
        datos = self.generador.editor.modelo.a_diccionario()
        cantidad = self.sesion.usar_escenario_editado(datos)
        self.generador = None
        self._refrescar_vista()
        self.alerta.mostrar("Listo", f"Escenario cargado. Se generaron {cantidad} pedidos "
                                     f"al azar con los productos del mapa.")

    def _evento_generador(self, ev):
        accion = self.generador.evento(ev)
        if accion == "generar":
            self._click("aplicar_generacion")
        elif accion == "validar":
            self._click("validar_editor")
        elif accion == "usar":
            self._click("usar_editor")
        elif accion == "cerrar":
            self.generador = None

    # ---------- avance y fin ----------

    def _actualizar(self, dt):
        if self.anim.en_curso():
            self.anim.avanzar(dt)
            return
        if self.sesion.debe_avanzar():
            self.anim.arrancar(self.sesion.posiciones())
            self.sesion.dar_paso()
            if self.sesion.sim.terminada:
                self._avisar_fin()

    def _avisar_fin(self):
        bloqueados = []
        for p in self.sesion.estado["pickers"]:
            if p["estado"] == "bloqueado":
                bloqueados.append(p["id"])
        if bloqueados:
            self.alerta.mostrar(
                "Aviso",
                "La simulación terminó con pickers bloqueados: " + ", ".join(bloqueados) + ".",
            )

    # ---------- entrada ----------

    def _teclado(self, tecla):
        if tecla == pygame.K_ESCAPE:
            self.alerta.cerrar()
        elif tecla == pygame.K_SPACE:
            if self.sesion.corriendo:
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
        elif tecla == pygame.K_i:
            self.vista.alternar_intersecciones()

    def _clic_mouse(self, pos):
        nombre = self.panel.boton_en(pos)
        if nombre is not None:
            self._click(nombre)

    def _evento(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.alerta.visible():
            if self.alerta.rect.collidepoint(ev.pos):
                self.alerta.clic(ev.pos)
                return
        if self.generador is not None:
            self._evento_generador(ev)
        elif ev.type == pygame.KEYDOWN:
            self._teclado(ev.key)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self._clic_mouse(ev.pos)

    # ---------- dibujo y bucle ----------

    def _dibujar(self):
        self.vista.dibujar_fondo()
        if self.generador is not None:
            self.generador.dibujar()
        else:
            self.vista.dibujar()
            self.panel.dibujar()
            self.vista.dibujar_tooltip()
        self.alerta.dibujar(self.pantalla)
        pygame.display.flip()

    def correr(self):
        activo = True
        while activo:
            dt = self.reloj.tick(cfg.FPS) / 1000.0
            self.anim.tic(dt)
            self.alerta.actualizar(dt)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    activo = False
                else:
                    self._evento(ev)
            try:
                if self.generador is None:
                    self._actualizar(dt)
            except (TypeError, ValueError) as error:
                self.sesion.pausar()
                self.alerta.mostrar(type(error).__name__, str(error))
            self._dibujar()
        pygame.quit()