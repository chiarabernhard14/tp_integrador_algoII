from simulation.simulationV.SimutionV import Simulacion, waves_de_estado
from simulation.simulationV.AsignadorPickersV import (
    ALGORITMOS_CAMINO,
    ESTRATEGIAS,
)
from simulation.simulationV.ScenarioV import (
    generar_escenario,
    generar_pedidos,
    validar_escenario,
)
from simulation.simulationV.PersistenceV import (
    guardar_escenario,
    cargar_escenario,
    guardar_partida,
    cargar_partida,
    ruta_autoguardado,
)


class Sesion:

    def __init__(
        self, datos, waves=None, generador_waves=None,
        algoritmo_camino="a_estrella", estrategia_recorrido="cercania",
        datos_validados=False,
    ):
        """
        - waves: lista de waves ya generadas por el módulo de tu compañera.
        - generador_waves: adaptador opcional fn(datos) -> list[wave]. Si no se
          proporciona, Simulacion llama al GeneradorWaves del proyecto con los
          pedidos del Warehouse.
        """
        self.generador_waves = generador_waves
        self.algoritmo_camino = algoritmo_camino
        self.estrategia_recorrido = estrategia_recorrido
        if datos_validados:
            self._usar_datos_validados(datos, waves)
        else:
            self.usar_datos(datos, waves)

    # ---------- estado ----------

    def usar_simulacion(self, sim):
        self.sim = sim
        self.algoritmo_camino = sim.algoritmo_camino
        self.estrategia_recorrido = sim.estrategia
        self.capacidades = {}
        for picker in self.sim.pickers:
            # Lee capacidad desde EstadoPicker o directamente desde la entidad Picker
            self.capacidades[picker.id] = getattr(
                picker, "capacidad", getattr(picker.entidad, "capacidad_carga_kg", 0)
            )
        self._reiniciar_estado()

    def _reiniciar_estado(self):
        self.corriendo = False
        self.paso_pendiente = False
        self._armar_pilas()
        self._refrescar_estado()

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

    # ---------- comandos de simulación ----------

    def iniciar(self):
        # Si la simulación todavía no avanzó, se conserva la posición a la que
        # llegaron los pickers deambulando en la vista previa.
        if self.sim.tick > 0 or self.sim.terminada:
            self.reiniciar()
        self.paso_pendiente = False
        self.corriendo = True

    def pausar(self):
        self.corriendo = False
        self.paso_pendiente = False

    def continuar(self):
        if not self.sim.terminada:
            self.corriendo = True

    def reiniciar(self):
        self.sim.reiniciar()
        self._reiniciar_estado()

    def pedir_paso(self):
        self.corriendo = False
        if not self.sim.terminada:
            self.paso_pendiente = True

    def debe_avanzar(self):
        return (self.corriendo or self.paso_pendiente) and not self.sim.terminada

    def debe_deambular(self):
        """Vista previa: los pickers pasean antes del primer tick."""
        return (
            not self.corriendo
            and not self.paso_pendiente
            and not self.sim.terminada
            and self.sim.en_espera
            and self.sim.tick == 0
        )

    def deambular_vista(self):
        """Mueve un paso a los pickers en espera, sin avanzar el reloj."""
        self.sim.deambular_vista()
        self._refrescar_estado()

    def posiciones(self):
        posiciones = {}
        for p in self.estado["pickers"]:
            posiciones[p["id"]] = p["posicion"]
        return posiciones

    def dar_paso(self):
        self.sim.paso()
        self._refrescar_estado()
        self.paso_pendiente = False
        if self.sim.terminada:
            self.corriendo = False

    # ---------- escenarios, waves y partidas ----------

    # CÓDIGO MUERTO — REVISAR (no se llama desde ningún archivo vivo)
    # def validar_datos(self, datos):
    #     validar_escenario(datos)

    def _obtener_waves(self, datos, waves=None):
        """Usa waves explícitas o un generador externo si la sesión lo recibió.

        Si devuelve None, Simulacion invoca el generador del proyecto usando
        los pedidos del Warehouse que ya cargó.
        """
        if waves is not None:
            return waves
        if self.generador_waves is not None:
            return self.generador_waves(datos)
        return None

    def usar_datos(self, datos, waves=None):
        validar_escenario(datos)
        self._usar_datos_validados(datos, waves)

    def _usar_datos_validados(self, datos, waves=None):
        """Inicializa la simulación con datos ya validados por su origen."""
        waves_listas = self._obtener_waves(datos, waves)
        self.usar_simulacion(
            Simulacion(
                datos,
                waves_listas,
                algoritmo_camino=self.algoritmo_camino,
                estrategia=self.estrategia_recorrido,
            )
        )

    def _seleccionar_configuracion_recorrido(self, algoritmo=None, estrategia=None):
        algoritmo = self.algoritmo_camino if algoritmo is None else algoritmo
        estrategia = self.estrategia_recorrido if estrategia is None else estrategia
        if algoritmo not in ALGORITMOS_CAMINO:
            raise ValueError(
                f"Algoritmo de camino desconocido: {algoritmo}. "
                f"Opciones: {', '.join(ALGORITMOS_CAMINO)}."
            )
        if estrategia not in ESTRATEGIAS:
            raise ValueError(
                f"Estrategia de recorrido desconocida: {estrategia}. "
                f"Opciones: {', '.join(ESTRATEGIAS)}."
            )
        if (algoritmo, estrategia) == (
            self.algoritmo_camino, self.estrategia_recorrido
        ):
            return False
        if self.sim.tick > 0:
            raise ValueError(
                "Para cambiar el recorrido, reiniciá la simulación y elegí las "
                "opciones antes de avanzar."
            )
        waves = self.sim.waves_entrada
        self.algoritmo_camino = algoritmo
        self.estrategia_recorrido = estrategia
        self._usar_datos_validados(self.sim.datos, waves)
        return True

    def seleccionar_algoritmo_camino(self, algoritmo):
        return self._seleccionar_configuracion_recorrido(algoritmo=algoritmo)

    def seleccionar_estrategia_recorrido(self, estrategia):
        return self._seleccionar_configuracion_recorrido(estrategia=estrategia)

    # CÓDIGO MUERTO — REVISAR (no se llama desde ningún archivo vivo)
    # def seleccionar_algoritmo_asignacion(self, algoritmo):
    #     """Compatibilidad con llamadas antiguas: ahora se elige el buscador de caminos."""
    #     return self.seleccionar_algoritmo_camino(algoritmo)

    def usar_escenario_editado(self, datos, cantidad_pedidos=8, max_items=4):
        completo = dict(datos)
        completo["pedidos"] = generar_pedidos(
            completo["productos"], cantidad_pedidos, max_items
        )
        self.usar_datos(completo)
        return len(completo["pedidos"])

    def generar(self, valores):
        # generar_escenario ya valida el resultado antes de devolverlo.
        self._usar_datos_validados(generar_escenario(**valores))

    def cargar_escenario(self, ruta):
        # cargar_escenario ya valida el contenido leído.
        self._usar_datos_validados(cargar_escenario(ruta))

    def guardar_escenario(self, ruta):
        guardar_escenario(ruta, self.sim.datos)

    def cargar_partida(self, ruta):
        datos, estado = cargar_partida(ruta)
        self.usar_partida(datos, estado)

    def usar_partida(self, datos, estado):
        """Restaura una instantánea ya leída, incluida la configuración guardada."""
        sim = Simulacion(datos, waves_de_estado(estado))
        try:
            sim.restaurar(estado)
        except (KeyError, IndexError) as error:
            raise ValueError(f"La partida está dañada y no se pudo restaurar: {error}") from error
        self.usar_simulacion(sim)

    def guardar_partida(self, ruta):
        guardar_partida(ruta, self.sim)

    def guardar_autopartida(self):
        guardar_partida(ruta_autoguardado(), self.sim)
