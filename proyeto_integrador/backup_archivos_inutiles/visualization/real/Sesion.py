from simulation.simulationV.SimutionV import Simulacion
from simulation.simulationV.ScenarioV import generar_escenario
from simulation.simulationV.PersistenceV import (
    guardar_escenario,
    cargar_escenario,
    guardar_partida,
    cargar_partida,
)
from simulation.simulationV.RecomendadorV import recomendar_pickers


class Sesion:

    def __init__(self, datos):
        self.usar_simulacion(Simulacion(datos))

    # ---------- estado ----------

    def usar_simulacion(self, sim):
        self.sim = sim
        self.capacidades = {}
        for picker in self.sim.pickers:
            self.capacidades[picker.id] = picker.capacidad
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

    # ---------- comandos ----------

    def iniciar(self):
        self.reiniciar()
        self.corriendo = True

    def pausar(self):
        self.corriendo = False

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

    # ---------- escenarios y partidas ----------

    def usar_datos(self, datos):
        self.usar_simulacion(Simulacion(datos))

    def generar(self, valores):
        self.usar_datos(generar_escenario(**valores))

    def cargar_escenario(self, ruta):
        self.usar_datos(cargar_escenario(ruta))

    def guardar_escenario(self, ruta):
        guardar_escenario(ruta, self.sim.datos)

    def cargar_partida(self, ruta):
        datos, estado = cargar_partida(ruta)
        sim = Simulacion(datos)
        try:
            sim.restaurar(estado)
        except (KeyError, IndexError) as error:
            raise ValueError(f"La partida está dañada y no se pudo restaurar: {error}") from error
        self.usar_simulacion(sim)

    def guardar_partida(self, ruta):
        guardar_partida(ruta, self.sim)

    # ---------- recomendación ----------

    def recomendar(self):
        return recomendar_pickers(self.sim.datos, self.sim.waves_entrada)

    def usar_pickers(self, pickers):
        nuevos = dict(self.sim.datos)
        nuevos["pickers"] = list(pickers)
        self.usar_simulacion(Simulacion(nuevos, self.sim.waves_entrada))