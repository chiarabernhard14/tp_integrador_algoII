"""Dibujo de los pickers como pequeños sprites (vistos desde arriba).

Cada sprite se dibuja una sola vez en alta resolución (con degradados y brillos), se
gira según hacia dónde mira y se reduce con suavizado, así los bordes quedan prolijos.
Después se guarda en caché: dibujarlo en cada cuadro es solo un blit.

Estilos (se elige con ESTILO_PICKER en config.py): "montacargas" o "robot".
Además de los sprites, la fábrica entrega la sombra suave y el resplandor de color
que van por debajo de cada picker.
"""

import pygame

ESCALA = 4   # el sprite se dibuja 4 veces más grande y se reduce al final

# pygame.transform.rotate gira en sentido antihorario; el sprite base mira hacia arriba (N).
GRADOS = {"N": 0, "O": 90, "S": 180, "E": 270}

CAJA = (214, 168, 102)
CAJA_CLARA = (236, 204, 146)
CAJA_BORDE = (118, 84, 44)
CAJA_CINTA = (246, 228, 182)
FARO = (255, 246, 190)
RUEDA = (26, 30, 40)
RUEDA_BRILLO = (58, 64, 78)
ACERO_CLARO = (214, 219, 228)
ACERO_OSCURO = (128, 135, 150)
JAULA = (52, 58, 72)
BALIZA_ON = (255, 176, 46)
BALIZA_OFF = (150, 96, 30)
CHASIS_ROBOT_ARRIBA = (74, 82, 100)
CHASIS_ROBOT_ABAJO = (34, 40, 52)


def _oscurecer(color, factor):
    return (int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))


def _aclarar(color, mezcla):
    return (int(color[0] + (255 - color[0]) * mezcla),
            int(color[1] + (255 - color[1]) * mezcla),
            int(color[2] + (255 - color[2]) * mezcla))


def _degradado(ancho, alto, inicio, fin, horizontal=False):
    """Superficie con un degradado lineal de `inicio` a `fin` (de arriba a abajo, o
    de izquierda a derecha si `horizontal`)."""
    sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    pasos = ancho if horizontal else alto
    for i in range(pasos):
        t = i / max(1, pasos - 1)
        color = (int(inicio[0] + (fin[0] - inicio[0]) * t),
                 int(inicio[1] + (fin[1] - inicio[1]) * t),
                 int(inicio[2] + (fin[2] - inicio[2]) * t), 255)
        if horizontal:
            pygame.draw.line(sup, color, (i, 0), (i, alto))
        else:
            pygame.draw.line(sup, color, (0, i), (ancho, i))
    return sup


def _rect_degradado(sup, rect, inicio, fin, radio, horizontal=False):
    """Rectángulo redondeado con degradado, recortado con una máscara."""
    relleno = _degradado(rect.w, rect.h, inicio, fin, horizontal)
    mascara = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=radio)
    relleno.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    sup.blit(relleno, rect.topleft)


def _brillo(sup, rect, intensidad=70):
    """Reflejo suave en la parte de arriba de una pieza."""
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(capa, (255, 255, 255, intensidad),
                        pygame.Rect(int(rect.w * 0.14), int(rect.h * 0.05),
                                    int(rect.w * 0.6), int(rect.h * 0.2)))
    sup.blit(capa, rect.topleft)


def _luz(sup, centro, radio, color, glow_alfa=70):
    """Luz puntual con halo."""
    capa = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(capa, (color[0], color[1], color[2], glow_alfa), centro, int(radio * 2.2))
    sup.blit(capa, (0, 0))
    pygame.draw.circle(sup, color, centro, radio)


class FabricaSprites:

    def __init__(self, estilo):
        self.estilo = estilo
        self.cache = {}

    # ---------- sprites ----------

    def obtener(self, color, direccion, radio, carga, apagado=False, fase=0):
        """`fase` (0 o 1) hace titilar las luces; el sprite apagado no titila."""
        if apagado:
            fase = 0
        clave = ("sprite", color, direccion, radio, carga, apagado, fase)
        sprite = self.cache.get(clave)
        if sprite is None:
            sprite = self._crear(color, direccion, radio, carga, fase)
            if apagado:
                sprite.set_alpha(110)
            self.cache[clave] = sprite
        return sprite

    def _crear(self, color, direccion, radio, carga, fase):
        lado = int(radio * 3.0)
        grande = pygame.Surface((lado * ESCALA, lado * ESCALA), pygame.SRCALPHA)
        if self.estilo == "robot":
            self._dibujar_robot(grande, color, radio * ESCALA, carga, fase)
        else:
            self._dibujar_montacargas(grande, color, radio * ESCALA, carga, fase)
        grande = pygame.transform.rotate(grande, GRADOS[direccion])
        return pygame.transform.smoothscale(grande, (lado, lado))

    # ---------- sombra y resplandor (van por debajo del sprite) ----------

    def sombra(self, radio):
        """Sombra suave, achatada: varias elipses translúcidas apiladas."""
        clave = ("sombra", radio)
        sup = self.cache.get(clave)
        if sup is None:
            ancho = int(radio * 2.8)
            alto = int(radio * 2.3)
            sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
            for i in range(8):
                f = 1.0 - i * 0.07
                capa = pygame.Surface((ancho, alto), pygame.SRCALPHA)
                rect = pygame.Rect(0, 0, int(ancho * f), int(alto * f))
                rect.center = (ancho // 2, alto // 2)
                pygame.draw.ellipse(capa, (0, 0, 0, 13), rect)
                sup.blit(capa, (0, 0))
            self.cache[clave] = sup
        return sup

    def resplandor(self, color, radio):
        """Halo del color del picker sobre el suelo: ayuda a ubicarlo de un vistazo."""
        clave = ("resplandor", color, radio)
        sup = self.cache.get(clave)
        if sup is None:
            lado = int(radio * 3.4)
            sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
            for i in range(11):
                capa = pygame.Surface((lado, lado), pygame.SRCALPHA)
                r = int(lado / 2 * (1.0 - i * 0.07))
                pygame.draw.circle(capa, (color[0], color[1], color[2], 8), (lado // 2, lado // 2), r)
                sup.blit(capa, (0, 0))
            self.cache[clave] = sup
        return sup

    # ---------- montacargas: horquillas, mástil, cabina con jaula y baliza ----------

    def _dibujar_montacargas(self, sup, color, r, carga, fase):
        cx = sup.get_width() // 2
        cy = sup.get_height() // 2
        oscuro = _oscurecer(color, 0.45)
        arriba = _aclarar(color, 0.30)
        abajo = _oscurecer(color, 0.78)

        chasis = pygame.Rect(0, 0, int(r * 1.5), int(r * 1.7))
        chasis.center = (cx, cy + int(r * 0.12))

        # horquillas (acero con degradado horizontal para dar volumen)
        for lado in (-1, 1):
            horquilla = pygame.Rect(0, 0, int(r * 0.24), int(r * 0.78))
            horquilla.midbottom = (cx + lado * int(r * 0.48), chasis.top + int(r * 0.12))
            _rect_degradado(sup, horquilla, ACERO_CLARO, ACERO_OSCURO, int(r * 0.07), horizontal=True)

        # mástil (barra transversal) y caja sobre las horquillas
        mastil = pygame.Rect(0, 0, int(r * 1.25), int(r * 0.22))
        mastil.midbottom = (cx, chasis.top + int(r * 0.12))
        _rect_degradado(sup, mastil, ACERO_OSCURO, JAULA, int(r * 0.08))
        if carga:
            self._dibujar_caja(sup, cx, chasis.top - int(r * 0.34), int(r * 1.02), int(r * 0.68))

        # ruedas
        for sx in (-1, 1):
            for sy in (-1, 1):
                rueda = pygame.Rect(0, 0, int(r * 0.3), int(r * 0.56))
                rueda.center = (cx + sx * int(r * 0.82), chasis.centery + sy * int(r * 0.5))
                pygame.draw.rect(sup, RUEDA, rueda, border_radius=int(r * 0.1))
                pygame.draw.line(sup, RUEDA_BRILLO, (rueda.centerx, rueda.top + int(r * 0.1)),
                                 (rueda.centerx, rueda.bottom - int(r * 0.1)), max(2, int(r * 0.05)))

        # chasis con degradado, contorno y reflejo
        pygame.draw.rect(sup, oscuro, chasis.inflate(int(r * 0.14), int(r * 0.14)),
                         border_radius=int(r * 0.38))
        _rect_degradado(sup, chasis, arriba, abajo, int(r * 0.3))
        _brillo(sup, chasis, 60)

        # contrapeso trasero con rayitas
        contrapeso = pygame.Rect(0, 0, int(r * 1.2), int(r * 0.4))
        contrapeso.midbottom = (cx, chasis.bottom - int(r * 0.07))
        _rect_degradado(sup, contrapeso, _oscurecer(color, 0.55), _oscurecer(color, 0.32), int(r * 0.14))
        for k in (-1, 0, 1):
            x = cx + k * int(r * 0.32)
            pygame.draw.line(sup, _oscurecer(color, 0.7), (x, contrapeso.top + int(r * 0.08)),
                             (x, contrapeso.bottom - int(r * 0.08)), max(2, int(r * 0.05)))

        # cabina con vidrio, jaula de seguridad y baliza
        techo = pygame.Rect(0, 0, int(r * 0.98), int(r * 0.82))
        techo.center = (cx, chasis.centery - int(r * 0.1))
        _rect_degradado(sup, techo, _aclarar(color, 0.7), _aclarar(color, 0.3), int(r * 0.2))
        _brillo(sup, techo, 90)
        jaula = techo.inflate(int(r * 0.2), int(r * 0.2))
        pygame.draw.rect(sup, JAULA, jaula, max(2, int(r * 0.07)), border_radius=int(r * 0.22))
        pygame.draw.line(sup, JAULA, (jaula.left, jaula.centery), (jaula.right, jaula.centery),
                         max(2, int(r * 0.05)))
        if fase:
            _luz(sup, (cx, techo.centery + int(r * 0.02)), int(r * 0.13), BALIZA_ON, 90)
        else:
            pygame.draw.circle(sup, BALIZA_OFF, (cx, techo.centery + int(r * 0.02)), int(r * 0.13))

        # faros delanteros
        for lado in (-1, 1):
            _luz(sup, (cx + lado * int(r * 0.55), chasis.top + int(r * 0.2)), int(r * 0.09), FARO, 60)

    # ---------- robot: chasis oscuro, tapa de color con anillo y faros ----------

    def _dibujar_robot(self, sup, color, r, carga, fase):
        cx = sup.get_width() // 2
        cy = sup.get_height() // 2

        for sx in (-1, 1):
            for sy in (-1, 1):
                rueda = pygame.Rect(0, 0, int(r * 0.36), int(r * 0.62))
                rueda.center = (cx + sx * int(r * 0.92), cy + sy * int(r * 0.6))
                pygame.draw.rect(sup, RUEDA, rueda, border_radius=int(r * 0.12))
                pygame.draw.line(sup, RUEDA_BRILLO, (rueda.centerx, rueda.top + int(r * 0.1)),
                                 (rueda.centerx, rueda.bottom - int(r * 0.1)), max(2, int(r * 0.05)))

        chasis = pygame.Rect(0, 0, int(r * 1.75), int(r * 2.15))
        chasis.center = (cx, cy)
        pygame.draw.rect(sup, (20, 24, 32), chasis.inflate(int(r * 0.14), int(r * 0.14)),
                         border_radius=int(r * 0.5))
        _rect_degradado(sup, chasis, CHASIS_ROBOT_ARRIBA, CHASIS_ROBOT_ABAJO, int(r * 0.42))

        # tapa del color del picker, con anillo de luz
        tapa = chasis.inflate(-int(r * 0.34), -int(r * 0.5))
        tapa.center = (cx, cy + int(r * 0.1))
        pygame.draw.rect(sup, _oscurecer(color, 0.5), tapa.inflate(int(r * 0.1), int(r * 0.1)),
                         border_radius=int(r * 0.34))
        _rect_degradado(sup, tapa, _aclarar(color, 0.38), _oscurecer(color, 0.85), int(r * 0.3))
        _brillo(sup, tapa, 80)
        anillo = tapa.inflate(-int(r * 0.2), -int(r * 0.2))
        pygame.draw.rect(sup, _aclarar(color, 0.7), anillo, max(2, int(r * 0.05)),
                         border_radius=int(r * 0.22))

        # frente: faros y sensor
        for lado in (-1, 1):
            _luz(sup, (cx + lado * int(r * 0.52), chasis.top + int(r * 0.2)), int(r * 0.12), FARO, 70)
        pygame.draw.circle(sup, (14, 18, 26), (cx, chasis.top + int(r * 0.2)), int(r * 0.13))
        pygame.draw.circle(sup, (96, 170, 255), (cx, chasis.top + int(r * 0.2)), int(r * 0.05))

        # luz de estado atrás (titila)
        if fase:
            _luz(sup, (cx, chasis.bottom - int(r * 0.2)), int(r * 0.1), BALIZA_ON, 90)
        else:
            pygame.draw.circle(sup, BALIZA_OFF, (cx, chasis.bottom - int(r * 0.2)), int(r * 0.1))

        if carga:
            self._dibujar_caja(sup, cx, tapa.centery, int(r * 0.9), int(r * 0.72))

    # ---------- caja que lleva ----------

    def _dibujar_caja(self, sup, cx, cy, ancho, alto):
        caja = pygame.Rect(0, 0, ancho, alto)
        caja.center = (cx, cy)
        radio = max(2, int(alto * 0.16))
        pygame.draw.rect(sup, CAJA_BORDE, caja.inflate(int(alto * 0.14), int(alto * 0.14)),
                         border_radius=radio + 2)
        _rect_degradado(sup, caja, CAJA_CLARA, CAJA, radio)
        pygame.draw.line(sup, CAJA_CINTA, (cx, caja.top + radio), (cx, caja.bottom - radio),
                         max(2, int(alto * 0.14)))
        _brillo(sup, caja, 70)