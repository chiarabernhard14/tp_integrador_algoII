"""Coordina ocupación de celdas y conflictos al mover pickers."""


class GestorColisionesV:
    """Resuelve bloqueos entre pickers y aplica los movimientos permitidos.

    La simulación le proporciona callbacks para replanificar, registrar eventos,
    marcar avance del trabajo y completar una entrega al llegar a despacho.
    """

    def __init__(
        self,
        pickers,
        registrar,
        replanificar,
        llegar_a_despacho,
        marcar_avance,
    ):
        self.pickers = pickers
        self._registrar = registrar
        self._replanificar = replanificar
        self._llegar_a_despacho = llegar_a_despacho
        self._marcar_avance = marcar_avance
        # Celdas reservadas para el movimiento de este tick (celda -> id picker).
        self.reservas = {}

    def limpiar_reservas(self):
        """Limpia las reservas al inicio de cada tick."""
        self.reservas = {}

    def orden_movimiento(self):
        """Prioriza pickers con trabajo; desempata por ID para ser repetible."""
        return sorted(
            self.pickers,
            key=lambda picker: (picker.estado == "deambulando", picker.id),
        )

    def ocupadas(self, picker):
        """Devuelve las celdas ocupadas o reservadas por los demás pickers."""
        ocupadas = {otro.pos for otro in self.pickers if otro is not picker}
        ocupadas.update(self.reservas.values())
        return ocupadas

    def mover(self, picker):
        """Avanza una celda o resuelve el conflicto que impide avanzar."""
        if not picker.ruta:
            return

        siguiente = picker.ruta[0]
        if siguiente in self.ocupadas(picker):
            if picker.estado == "deambulando":
                # Un picker sin trabajo cede el paso y busca destino en otro tick.
                picker.ruta = []
                return
            # Esperar sin replanificar de inmediato: esto evita el deadlock
            # de dos pickers que se replanifican mutuamente sin avanzar nunca.
            # Un picker ya bloqueado se mantiene bloqueado (no pierde la cuenta
            # de ticks esperando ni su prioridad en la resolución de deadlocks).
            if picker.estado != "bloqueado":
                picker.estado = "esperando"
            return

        distancia = (
            abs(siguiente[0] - picker.pos[0])
            + abs(siguiente[1] - picker.pos[1])
        )
        if distancia != 1:
            picker.ruta = []
            if picker.estado != "deambulando":
                picker.estado = "esperando"
            return

        # Reservar la celda destino para que otro picker no la tome este tick.
        self.reservas[siguiente] = picker.id

        anterior = picker.pos
        picker.anterior = anterior
        picker.pos = siguiente
        picker.ruta.pop(0)

        if picker.estado != "deambulando":
            picker.trail.append(siguiente)
            picker.pasos_trabajo += 1
            self._marcar_avance()
            self._registrar(f"{picker.id}: {anterior} -> {siguiente}.")

        if picker.estado == "regresando" and picker.pos in picker.destinos:
            picker.ruta = []
            self._llegar_a_despacho(picker)
