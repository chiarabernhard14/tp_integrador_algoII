"""Estado de la animación entre ticks (solo visual; la lógica está en Sesion)."""

from . import config as cfg


class Animacion:

    def __init__(self):
        self.vel_idx = cfg.VEL_INICIAL
        self.t = 0.0
        self.reiniciar()

    def reiniciar(self):
        self.progreso = 1.0
        self.prev = {}

    def tic(self, dt):
        self.t += dt

    def en_curso(self):
        return self.progreso < 1.0

    def avanzar(self, dt):
        paso = dt * cfg.VELOCIDADES[self.vel_idx] / cfg.TICK_SEG
        self.progreso = min(1.0, self.progreso + paso)

    def arrancar(self, posiciones_previas):
        self.prev = posiciones_previas
        self.progreso = 0.0

    def velocidad(self):
        return cfg.VELOCIDADES[self.vel_idx]

    def acelerar(self):
        self.vel_idx = min(len(cfg.VELOCIDADES) - 1, self.vel_idx + 1)

    def frenar(self):
        self.vel_idx = max(0, self.vel_idx - 1)

    def posicion_visual(self, picker):
        actual = picker["posicion"]
        previa = self.prev.get(picker["id"])
        if previa is None or self.progreso >= 1.0:
            return actual[0], actual[1]
        t = self.progreso
        return (previa[0] + (actual[0] - previa[0]) * t,
                previa[1] + (actual[1] - previa[1]) * t)