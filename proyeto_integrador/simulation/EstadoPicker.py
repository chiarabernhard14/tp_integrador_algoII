
class EstadoPicker:

    def __init__(self, picker):
        self.entidad = picker
        self.id = picker.id

        self.anterior = None
        self.pendientes = []
        self.recogidos = []
        self.objetivo = None
        self.destinos = set()
        self.estado = "disponible"
        self.trail = [picker.posicion]

        # Viaje que está ejecutando el picker.
        self.wave = None
        self.waves_hechas = []

        # Veces que se salteó la próxima tarea del orden planificado.
        self.saltos = 0

        # Patrulla sin trabajo y pasos dados trabajando.
        self.indice_punto = 0
        self.pasos_trabajo = 0

        # Ticks consecutivos esperando por un bloqueo (para evitar deadlocks).
        self.ticks_esperando = 0

    # ---------- acceso a la entidad ----------

    @property
    def pos(self):
        return self.entidad.posicion

    @pos.setter
    def pos(self, valor):
        self.entidad.posicion = valor

    @property
    def ruta(self):
        return self.entidad.current_route

    @ruta.setter
    def ruta(self, valor):
        self.entidad.current_route = valor

    @property
    def capacidad(self):
        return self.entidad.capacidad_carga_kg

    # ---------- viaje ----------

    def asignar_viaje(self, id_trabajo, wave_id, zona, peso, tareas):
        self.wave = {"id": id_trabajo, "wave_id": wave_id, "zona": zona,
                     "peso": peso, "tareas": tareas, "estado": "EN_PROCESO"}

    # ---------- serialización ----------

    def a_dict(self):
        viaje = self.wave
        return {
            "id": self.id,
            "posicion": self.pos,
            "anterior": self.anterior,
            "ruta": list(self.ruta),
            "estado": self.estado,
            "objetivo": self.objetivo["producto_id"] if self.objetivo else None,
            "pendientes": [t["producto_id"] for t in self.pendientes],
            "destinos": list(self.destinos),
            "recogidos": list(self.recogidos),
            "trail": list(self.trail),
            "wave_id": viaje["wave_id"] if viaje else None,
            "trabajo_id": viaje["id"] if viaje else None,
            "trabajo": self._trabajo_a_dict(),
            "waves_hechas": list(self.waves_hechas),
            "saltos": self.saltos,
            "pasos_trabajo": self.pasos_trabajo,
            "indice_punto": self.indice_punto,
            "ticks_esperando": self.ticks_esperando,
        }

    def _trabajo_a_dict(self):
        if self.wave is None:
            return None
        datos = {k: self.wave[k] for k in ("id", "wave_id", "zona", "peso")}
        datos["tareas"] = [dict(t) for t in self.wave["tareas"].values()]
        return datos

    def restaurar(self, g):
        self.pos = tuple(g["posicion"])
        self.anterior = tuple(g["anterior"]) if g.get("anterior") else None
        self.ruta = [tuple(c) for c in g["ruta"]]
        self.estado = g["estado"]
        self.trail = [tuple(c) for c in g["trail"]]
        self.recogidos = list(g["recogidos"])
        self.destinos = {tuple(d) for d in g.get("destinos", [])}
        self.waves_hechas = list(g.get("waves_hechas", []))
        self.saltos = g.get("saltos", 0)
        self.pasos_trabajo = g.get("pasos_trabajo", 0)
        self.indice_punto = g.get("indice_punto", self.indice_punto)
        self.ticks_esperando = g.get("ticks_esperando", 0)

        self.wave = None
        self.pendientes = []
        self.objetivo = None
        trabajo = g.get("trabajo")
        if trabajo is not None:
            tareas = {t["producto_id"]: dict(t) for t in trabajo["tareas"]}
            self.asignar_viaje(trabajo["id"], trabajo["wave_id"],
                               trabajo["zona"], trabajo["peso"], tareas)
            self.pendientes = [tareas[p] for p in g["pendientes"] if p in tareas]
            self.objetivo = tareas.get(g["objetivo"])