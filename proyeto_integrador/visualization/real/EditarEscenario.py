import pygame

HERRAMIENTAS = {
    pygame.K_1: "rack", pygame.K_2: "despacho", pygame.K_3: "puerta",
    pygame.K_4: "pasillo", pygame.K_5: "picker", pygame.K_6: "borrar",
}
SENTIDOS = {pygame.K_n: "N", pygame.K_s: "S", pygame.K_e: "E",
            pygame.K_o: "O", pygame.K_a: "AMBOS"}
LISTAS = ("racks", "zonas", "puertas", "pasillos", "pickers")

COLOR_RACK = (24, 52, 102)
COLOR_ZONA = (52, 211, 153)
COLOR_PUERTA = (251, 146, 60)
COLOR_PASILLO = (108, 114, 126)
COLOR_OK = (52, 211, 153, 120)
COLOR_MAL = (239, 68, 68, 120)


class EditorEscenario:

    def __init__(self, ancho_x, largo_y, area):
        self.ancho_x = ancho_x
        self.largo_y = largo_y
        self.celda = max(6, min(area.w // ancho_x, area.h // largo_y))
        self.origen_x = area.x + (area.w - self.celda * ancho_x) // 2
        self.origen_y = area.y + (area.h - self.celda * largo_y) // 2

        self.herramienta = "rack"
        self.sentido = "AMBOS"
        self.inicio = None
        self.actual = None
        self.error = ""

        self.racks = []
        self.zonas = []
        self.puertas = []
        self.pasillos = []
        self.pickers = []
        self.historial = []
        self.contadores = {"R": 0, "Z": 0, "PUERTA_": 0, "PAS_": 0, "PK_": 0}

    # ---------- coordenadas ----------

    def _celda_en(self, mx, my):
        gx = (mx - self.origen_x) // self.celda
        gy = (my - self.origen_y) // self.celda
        if 0 <= gx < self.ancho_x and 0 <= gy < self.largo_y:
            return int(gx), int(self.largo_y - 1 - gy)
        return None

    def _rect_px(self, x, y, w, h):
        return pygame.Rect(self.origen_x + x * self.celda,
                           self.origen_y + (self.largo_y - (y + h)) * self.celda,
                           w * self.celda, h * self.celda)

    # ---------- geometría del arrastre ----------

    def _rect_arrastre(self):
        x0, y0 = self.inicio
        x1, y1 = self.actual
        dx = abs(x1 - x0) + 1
        dy = abs(y1 - y0) + 1
        if self.herramienta == "rack":
            if dx >= dy:                       # rack horizontal: alto fijo en 2
                return min(x0, x1), y0, max(dx, 2), 2
            return x0, min(y0, y1), 2, dy      # rack vertical: ancho fijo en 2
        if self.herramienta in ("despacho", "pasillo"):
            return min(x0, x1), min(y0, y1), dx, dy
        return x0, y0, 1, 1                    # puerta y picker: una celda

    def _bloqueantes(self):
        if self.herramienta == "picker":
            return self.racks + self.zonas + self.puertas + self.pickers
        return self.racks + self.zonas + self.puertas + self.pasillos

    def _solapa(self, x, y, w, h):
        for e in self._bloqueantes():
            ex = e["ubicacion"]["x"]
            ey = e["ubicacion"]["y"]
            ew = e.get("ancho", 1)
            eh = e.get("alto", 1)
            if x < ex + ew and ex < x + w and y < ey + eh and ey < y + h:
                return True
        return False

    def _error(self, x, y, w, h):
        if x < 0 or y < 0 or x + w > self.ancho_x or y + h > self.largo_y:
            return "Se sale del warehouse"
        if self.herramienta == "puerta":
            en_borde = (x == 0 or x == self.ancho_x - 1
                        or y == 0 or y == self.largo_y - 1)
            if not en_borde:
                return "La puerta tiene que ir sobre el borde"
        if self._solapa(x, y, w, h):
            return "Se solapa con otro elemento"
        return ""

    # ---------- alta / baja ----------

    def _nuevo_id(self, prefijo):
        self.contadores[prefijo] += 1
        return f"{prefijo}{self.contadores[prefijo]}"

    def _agregar(self, x, y, w, h):
        elem = {"ubicacion": {"x": x, "y": y}, "ancho": w, "alto": h}
        if self.herramienta == "rack":
            elem["id"] = self._nuevo_id("R")
            self.racks.append(elem)
            self.historial.append("racks")
        elif self.herramienta == "despacho":
            elem["id"] = self._nuevo_id("Z")
            self.zonas.append(elem)
            self.historial.append("zonas")
        elif self.herramienta == "puerta":
            elem["id"] = self._nuevo_id("PUERTA_")
            self.puertas.append(elem)
            self.historial.append("puertas")
        elif self.herramienta == "pasillo":
            elem["id"] = self._nuevo_id("PAS_")
            elem["sentido"] = self.sentido
            self.pasillos.append(elem)
            self.historial.append("pasillos")
        elif self.herramienta == "picker":
            elem["id"] = self._nuevo_id("PK_")
            self.pickers.append(elem)
            self.historial.append("pickers")

    def _contiene(self, e, x, y):
        ex = e["ubicacion"]["x"]
        ey = e["ubicacion"]["y"]
        return ex <= x < ex + e.get("ancho", 1) and ey <= y < ey + e.get("alto", 1)

    def _borrar(self, celda):
        for nombre in LISTAS:
            lista = getattr(self, nombre)
            for e in reversed(lista):
                if self._contiene(e, celda[0], celda[1]):
                    lista.remove(e)
                    return

    def _deshacer(self):
        if self.historial:
            getattr(self, self.historial.pop()).pop()

    # ---------- eventos ----------

    def evento(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            celda = self._celda_en(*ev.pos)
            if celda is None:
                return
            if self.herramienta == "borrar":
                self._borrar(celda)
                return
            self.inicio = celda
            self.actual = celda
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self.inicio = None
        elif ev.type == pygame.MOUSEMOTION and self.inicio is not None:
            celda = self._celda_en(*ev.pos)
            if celda is not None:
                self.actual = celda
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.inicio is not None:
            x, y, w, h = self._rect_arrastre()
            self.error = self._error(x, y, w, h)
            if not self.error:
                self._agregar(x, y, w, h)
            self.inicio = None
        elif ev.type == pygame.KEYDOWN:
            if ev.key in HERRAMIENTAS:
                self.herramienta = HERRAMIENTAS[ev.key]
            elif ev.key in SENTIDOS and self.herramienta == "pasillo":
                self.sentido = SENTIDOS[ev.key]
            elif ev.key == pygame.K_z and ev.mod & pygame.KMOD_CTRL:
                self._deshacer()

    # ---------- dibujo ----------

    def _dibujar_lista(self, pantalla, lista, color):
        for e in lista:
            r = self._rect_px(e["ubicacion"]["x"], e["ubicacion"]["y"],
                              e.get("ancho", 1), e.get("alto", 1))
            pygame.draw.rect(pantalla, color, r.inflate(-2, -2), border_radius=4)

    def dibujar(self, pantalla, fuente):
        fondo = self._rect_px(0, 0, self.ancho_x, self.largo_y)
        pygame.draw.rect(pantalla, (66, 72, 84), fondo)
        for i in range(self.ancho_x + 1):               # grilla
            px = self.origen_x + i * self.celda
            pygame.draw.line(pantalla, (78, 84, 96), (px, fondo.top), (px, fondo.bottom))
        for j in range(self.largo_y + 1):
            py = self.origen_y + j * self.celda
            pygame.draw.line(pantalla, (78, 84, 96), (fondo.left, py), (fondo.right, py))

        self._dibujar_lista(pantalla, self.pasillos, COLOR_PASILLO)
        for p in self.pasillos:                         # letra del sentido
            r = self._rect_px(p["ubicacion"]["x"], p["ubicacion"]["y"], p["ancho"], p["alto"])
            img = fuente.render(p["sentido"], True, (255, 255, 255))
            pantalla.blit(img, img.get_rect(center=r.center))
        self._dibujar_lista(pantalla, self.zonas, COLOR_ZONA)
        self._dibujar_lista(pantalla, self.racks, COLOR_RACK)
        self._dibujar_lista(pantalla, self.puertas, COLOR_PUERTA)
        self._dibujar_lista(pantalla, self.pickers, (59, 130, 246))

        if self.inicio is not None:                     # vista previa
            x, y, w, h = self._rect_arrastre()
            ok = self._error(x, y, w, h) == ""
            prev = pygame.Surface((w * self.celda, h * self.celda), pygame.SRCALPHA)
            prev.fill(COLOR_OK if ok else COLOR_MAL)
            pantalla.blit(prev, self._rect_px(x, y, w, h).topleft)

        texto = f"Herramienta: {self.herramienta}"
        if self.herramienta == "pasillo":
            texto += f"  (sentido {self.sentido})"
        if self.error:
            texto += f"   |   {self.error}"
        pantalla.blit(fuente.render(texto, True, (30, 30, 30)), (self.origen_x, self.origen_y - 28))

    # ---------- exportar ----------

    def _puerta_de_zona(self, z):
        x = z["ubicacion"]["x"]
        y = z["ubicacion"]["y"]
        w = z["ancho"]
        h = z["alto"]
        for p in self.puertas:
            px = p["ubicacion"]["x"]
            py = p["ubicacion"]["y"]
            arriba_abajo = x <= px < x + w and py in (y - 1, y + h)
            costados = y <= py < y + h and px in (x - 1, x + w)
            if arriba_abajo or costados:
                return p["id"]
        raise ValueError(f"La zona {z['id']} no tiene una puerta adyacente")

    def a_diccionario(self):
        zonas = []
        for z in self.zonas:
            zonas.append({**z, "puerta_id": self._puerta_de_zona(z), "peso_max_kg": 500.0})
        puertas = [{"id": p["id"], "tipo": "AMBOS", "ubicacion": p["ubicacion"]}
                   for p in self.puertas]
        pickers = [{"id": k["id"], "posicion_inicial": k["ubicacion"],
                    "capacidad_carga_kg": 100.0} for k in self.pickers]
        return {
            "warehouse": {
                "dimensiones": {"ancho_x": self.ancho_x, "largo_y": self.largo_y},
                "puertas": puertas, "zonas_despacho": zonas,
                "racks": self.racks, "pasillos": self.pasillos,
            },
            "pickers": pickers, "productos": [], "pedidos": [],
            "configuracion": {"wave_max_pedidos": 3, "wave_max_productos": 15},
        }