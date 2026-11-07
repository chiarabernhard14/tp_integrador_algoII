"""Aplicación visual: bucle principal y reparto de eventos.

La lógica de la simulación vive en simulation.simulationV.SesionV; acá solo hay
interfaz (ventana, mouse, teclado, animación y alertas).
"""

import ctypes

import pygame

from simulation.simulationV.Sesion import Sesion
from . import config as cfg
from . import dialogos
from .animacion import Animacion
from .panel import PanelLateral, PanelWaves
from .generador_pantalla import PantallaGenerador
from .pincel import Fuentes, Pincel
from .vista_mapa import VistaMapa
from . import widgets
from .widgets import Alerta


class App:

   
    def __init__(self, datos, waves=None, generador_waves=None, partida_guardada=None):
        pygame.init()
        titulo = "Wave Picking - Simulacion"
        pygame.display.set_caption(titulo)
        self.ventana = pygame.display.set_mode(
            (cfg.ANCHO, cfg.ALTO), pygame.RESIZABLE
        )
        # Se dibuja en un lienzo de referencia y se escala a la ventana
        # maximizada; así todos los botones conservan sus posiciones relativas.
        self.pantalla = pygame.Surface((cfg.ANCHO, cfg.ALTO))
        self.reloj = pygame.time.Clock()

        self._maximizar_ventana(titulo)

        self.fuentes = Fuentes()
        self.pincel = Pincel(self.pantalla)
        self.alerta = Alerta(self.fuentes.alerta_titulo, self.fuentes.alerta_texto)

        self.sesion = Sesion(datos, waves=waves, generador_waves=generador_waves)
        self._autoguardado_alerta_mostrada = False
        if partida_guardada is not None:
            self.sesion.usar_partida(datos, partida_guardada)
        self.anim = Animacion()
        self.vista = VistaMapa(self.pincel, self.fuentes, self.sesion, self.anim)
        self.vista.mouse_pos = (0, 0)
        self.panel = PanelLateral(self.pincel, self.fuentes, self.sesion, self.anim)
        self.panel_waves = PanelWaves(self.pincel, self.fuentes, self.sesion)
        self.generador = None
        if partida_guardada is not None:
            self.alerta.mostrar("Listo", "Se restauró la última partida guardada.")

    def _refrescar_vista(self):
        """Tras cambiar la simulación: nuevo tamaño de mapa y animación en cero."""
        self.vista.recalcular()
        self.anim.reiniciar()

    # ---------- acciones ----------

    def _click(self, nombre):
        """Punto único donde se atrapan los errores y se muestran como alerta."""
        try:
            self._ejecutar(nombre)
        except Exception as error:
            self._mostrar_error(error)

    def _mostrar_error(self, error):
        """Informa errores de una acción sin terminar el proceso visual."""
        try:
            self._pausar_simulacion()
        except Exception:
            pass
        print(f"Error al ejecutar la acción: {type(error).__name__}: {error}")
        self.alerta.mostrar(type(error).__name__, str(error))

    def _pausar_simulacion(self):
        """Guarda el estado y pausa la simulación si el guardado pudo hacerse."""
        if not self._guardar_autopartida():
            return False
        self.sesion.pausar()
        self.anim.pausar()
        return True

    def _ejecutar(self, nombre):
        if nombre == "algoritmo_a_estrella":
            self._seleccionar_algoritmo_camino("a_estrella")
        elif nombre == "algoritmo_dijkstra":
            self._seleccionar_algoritmo_camino("dijkstra")
        elif nombre == "estrategia_orden":
            self._seleccionar_estrategia_recorrido("orden")
        elif nombre == "estrategia_cercania":
            self._seleccionar_estrategia_recorrido("cercania")
        elif nombre == "estrategia_zonas":
            self._seleccionar_estrategia_recorrido("zonas")
        elif nombre == "generar":
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
            self._guardar_autopartida()
        elif nombre == "pausar":
            self._pausar_simulacion()
        elif nombre == "continuar":
            self.sesion.continuar()
            self.anim.continuar()
        elif nombre == "reiniciar":
            self.sesion.reiniciar()
            self._refrescar_vista()
            self._guardar_autopartida()
        elif nombre == "paso":
            # Si había una transición congelada, se termina de mostrar antes
            # de ejecutar el único tick solicitado.
            self.anim.continuar()
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
        self._pausar_simulacion()
        ruta = dialogos.abrir("Cargar escenario")
        if not ruta:
            return
        self.sesion.cargar_escenario(ruta)
        self._refrescar_vista()
        self._guardar_autopartida()

    def _guardar_escenario(self):
        self._pausar_simulacion()
        ruta = dialogos.guardar("Guardar escenario", "escenario.json")
        if not ruta:
            return
        self.sesion.guardar_escenario(ruta)
        self.alerta.mostrar("Listo", f"Escenario guardado en {ruta}")

    def _cargar_partida(self):
        self._pausar_simulacion()
        ruta = dialogos.abrir("Cargar partida")
        if not ruta:
            return
        self.sesion.cargar_partida(ruta)
        self._refrescar_vista()
        self._guardar_autopartida()

    def _guardar_partida(self):
        self._pausar_simulacion()
        ruta = dialogos.guardar("Guardar partida", "partida.json")
        if not ruta:
            return
        self.sesion.guardar_partida(ruta)
        self.alerta.mostrar("Listo", f"Partida guardada en {ruta}")

    # ---------- generar escenario (pestañas Automático y Manual) ----------

    def _abrir_generador(self):
        self._pausar_simulacion()
        almacen = self.sesion.sim.warehouse
        self.generador = PantallaGenerador(self.pincel, self.fuentes, almacen.ancho_x, almacen.largo_y)

    def _aplicar_generacion(self):
        self.sesion.generar(self.generador.valores_generador())
        self.generador = None
        self._refrescar_vista()
        self._guardar_autopartida()
        self.alerta.mostrar("Listo", "Escenario generado.")

    def _validar_editor(self):
        modelo = self.generador.editor.modelo
        errores = modelo.validar()
        if errores:
            self.alerta.mostrar("Aviso", " | ".join(errores))
            return
        self.alerta.mostrar("Listo", "El escenario es válido")

    def _usar_editor(self):
        datos = self.generador.editor.modelo.a_diccionario()
        cantidad = self.sesion.usar_escenario_editado(datos)
        self.generador = None
        self._refrescar_vista()
        self._guardar_autopartida()
        self.alerta.mostrar("Listo", f"Escenario cargado. Se generaron {cantidad} pedidos "
                                     f"al azar con los productos del mapa.")

    def _seleccionar_algoritmo_camino(self, algoritmo):
        cambio = self.sesion.seleccionar_algoritmo_camino(algoritmo)
        if cambio:
            self._refrescar_vista()
            self._guardar_autopartida()
            nombre = "A*" if algoritmo == "a_estrella" else "Dijkstra"
            self.alerta.mostrar(
                "Listo", f"La simulación usará {nombre} para calcular los caminos."
            )

    def _seleccionar_estrategia_recorrido(self, estrategia):
        cambio = self.sesion.seleccionar_estrategia_recorrido(estrategia)
        if cambio:
            self._refrescar_vista()
            self._guardar_autopartida()
            nombres = {"orden": "Orden", "cercania": "Cercanía", "zonas": "Zonas"}
            self.alerta.mostrar(
                "Listo", f"La simulación usará la estrategia {nombres[estrategia]}."
            )

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
            if self.sesion.sim.tick % 25 == 0:
                self._guardar_autopartida()
            if self.sesion.sim.terminada:
                self._avisar_fin()

    def _guardar_autopartida(self):
        try:
            self.sesion.guardar_autopartida()
        except Exception as error:
            print(f"No se pudo guardar la última partida: {error}")
            if not self._autoguardado_alerta_mostrada:
                self._autoguardado_alerta_mostrada = True
                self.alerta.mostrar(
                    "No se pudo guardar", str(error)
                )
            return False
        return True

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
        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            pos = self._posicion_logica(ev.pos)
            self.vista.mouse_pos = pos
            widgets.actualizar_pos_mouse(pos)
            ev = pygame.event.Event(ev.type, {**ev.dict, "pos": pos})
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
            self.panel_waves.dibujar()
            self.vista.dibujar_tooltip()
        self.alerta.dibujar(self.pantalla)
        ventana = pygame.display.get_surface()
        ancho, alto = ventana.get_size()
        escala = min(ancho / cfg.ANCHO, alto / cfg.ALTO)
        tam = (max(1, int(cfg.ANCHO * escala)), max(1, int(cfg.ALTO * escala)))
        imagen = pygame.transform.smoothscale(self.pantalla, tam)
        ventana.fill(cfg.BG)
        ventana.blit(imagen, ((ancho - tam[0]) // 2, (alto - tam[1]) // 2))
        pygame.display.flip()

    def _posicion_logica(self, pos):
        ventana = pygame.display.get_surface()
        ancho, alto = ventana.get_size()
        escala = min(ancho / cfg.ANCHO, alto / cfg.ALTO)
        margen_x = (ancho - cfg.ANCHO * escala) / 2
        margen_y = (alto - cfg.ALTO * escala) / 2
        x = int((pos[0] - margen_x) / escala)
        y = int((pos[1] - margen_y) / escala)
        return x, y

    @staticmethod
    def _maximizar_ventana(titulo):
        """Maximiza la ventana conservando la barra nativa de Windows."""
        try:
            user32 = ctypes.windll.user32
            user32.ShowWindow.argtypes = (ctypes.c_void_p, ctypes.c_int)
            ventana = pygame.display.get_wm_info().get("window")
            if not ventana:
                user32.FindWindowW.restype = ctypes.c_void_p
                user32.FindWindowW.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p)
                ventana = user32.FindWindowW(None, titulo)
            if ventana:
                if not isinstance(ventana, ctypes.c_void_p):
                    ventana = ctypes.c_void_p(int(ventana))
                user32.ShowWindow(ventana, 3)  # SW_MAXIMIZE
        except (AttributeError, OSError):
            # En otros sistemas queda una ventana redimensionable normal.
            pass

    def correr(self):
        activo = True
        while activo:
            dt = self.reloj.tick(cfg.FPS) / 1000.0
            self.anim.tic(dt)
            self.alerta.actualizar(dt)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    if self._guardar_autopartida():
                        self.sesion.pausar()
                        self.anim.pausar()
                        activo = False
                else:
                    try:
                        self._evento(ev)
                    except Exception as error:
                        self._mostrar_error(error)
            try:
                if self.generador is None:
                    self._actualizar(dt)
            except Exception as error:
                self._mostrar_error(error)
            self._dibujar()
        pygame.quit()
