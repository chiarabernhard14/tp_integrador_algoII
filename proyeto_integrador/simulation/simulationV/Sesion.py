from simulation.simulationV.SimutionV import Simulacion
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
)


class Sesion:

    def __init__(self, datos, waves=None, generador_waves=None):
        """
        - waves: lista de waves ya generadas por el módulo de tu compañera.
        - generador_waves: función opcional fn(datos) -> list[wave] de tu compañera
          para recalcular waves automáticamente al cargar/generar otro escenario en la UI.
        """
        self.generador_waves = generador_waves
        self.usar_datos(datos, waves)

    # ---------- estado ----------

    def usar_simulacion(self, sim):
        self.sim = sim
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
        self.reiniciar()
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

    def validar_datos(self, datos):
        validar_escenario(datos)

    def _obtener_waves(self, datos, waves=None):
        """Usa la lista recibida, llama al módulo de Wave Manager o arma waves provisorias."""
        if waves is not None:
            return waves
        if self.generador_waves is not None:
            return self.generador_waves(datos)
        return self._waves_provisorias(datos)

    def _waves_provisorias(self, datos):
        """Fallback por si se abre un escenario desde la UI sin generador_waves conectado."""
        pickers = [p["id"] for p in datos.get("pickers", [])]
        if not pickers:
            raise ValueError("El escenario no tiene pickers definidos.")

        pedidos = sorted(
            datos.get("pedidos", []),
            key=lambda ped: ped.get("prioridad", 1),
            reverse=True,
        )
        max_ped = datos.get("configuracion", {}).get("wave_max_pedidos", 3)

        waves = []
        for idx in range(0, len(pedidos), max_ped):
            grupo = pedidos[idx : idx + max_ped]
            productos = []
            for ped in grupo:
                for it in ped.get("items", []):
                    productos.append({
                        "producto_id": it["producto_id"],
                        "cantidad": it["cantidad"],
                    })
            waves.append({
                "id": f"W_{idx // max_ped + 1:02d}",
                "picker": pickers[(idx // max_ped) % len(pickers)],
                "productos": productos,
            })
        return waves

    def usar_datos(self, datos, waves=None):
        validar_escenario(datos)
        waves_listas = self._obtener_waves(datos, waves)
        self.usar_simulacion(Simulacion(datos, waves_listas))

    def usar_escenario_editado(self, datos, cantidad_pedidos=8, max_items=4):
        completo = dict(datos)
        completo["pedidos"] = generar_pedidos(
            completo["productos"], cantidad_pedidos, max_items
        )
        self.usar_datos(completo)
        return len(completo["pedidos"])

    def generar(self, valores):
        self.usar_datos(generar_escenario(**valores))

    def cargar_escenario(self, ruta):
        self.usar_datos(cargar_escenario(ruta))

    def guardar_escenario(self, ruta):
        guardar_escenario(ruta, self.sim.datos)

    def cargar_partida(self, ruta):
        datos, estado = cargar_partida(ruta)
        waves_guardadas = [
            {
                "id": w["id"],
                "picker": w["picker"],
                "productos": w["productos"],
            }
            for w in estado.get("waves", [])
        ]
        sim = Simulacion(datos, waves_guardadas)
        try:
            sim.restaurar(estado)
        except (KeyError, IndexError) as error:
            raise ValueError(f"La partida está dañada y no se pudo restaurar: {error}") from error
        self.usar_simulacion(sim)

    def guardar_partida(self, ruta):
        guardar_partida(ruta, self.sim)