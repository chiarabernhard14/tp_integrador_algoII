"""Modelo del escenario que arma el editor de mapa (sin pygame).

Guarda los elementos como diccionarios con el mismo formato del JSON del
anexo A. Acá solo hay reglas de colocación y de exportación; la validación de
estructura la hacen las clases del Warehouse y la de alcanzabilidad es
ScenarioV.validar_escenario.
"""

import copy

# Valores por defecto del escenario exportado (el generador usa hasta 200 kg).
PESO_MAX_ZONA_KG = 500.0
CAPACIDAD_PICKER_KG = 200.0

# Contra qué listas choca cada herramienta al colocarse.
# La puerta puede ir sobre una zona (la puerta va DENTRO de la zona de despacho).
BLOQUEAN = {
    "rack": ("racks", "zonas", "puertas", "pasillos", "pickers"),
    "despacho": ("racks", "zonas", "pasillos", "pickers"),
    "puerta": ("racks", "puertas", "pasillos", "pickers"),
    "pasillo": ("racks", "zonas", "puertas", "pasillos"),
    "picker": ("racks", "zonas", "puertas", "pickers"),
}
LISTA_DE = {"rack": "racks", "despacho": "zonas", "puerta": "puertas",
            "pasillo": "pasillos", "picker": "pickers"}
PREFIJO = {"rack": "R", "despacho": "Z", "puerta": "PUERTA_",
           "pasillo": "PAS_", "picker": "PK_"}
NOMBRE_LISTA = {"racks": "un rack", "zonas": "una zona de despacho",
                "puertas": "una puerta", "pasillos": "un pasillo",
                "pickers": "un picker"}


class ModeloEscenario:

    def __init__(self, ancho_x, largo_y):
        self.ancho_x = ancho_x
        self.largo_y = largo_y
        self.racks = []
        self.zonas = []
        self.puertas = []
        self.pasillos = []
        self.pickers = []
        self.productos = []
        self.historial = []
        self.version = 0          # sube con cada cambio: la vista lo usa para saber cuándo redibujar
        self.contadores = {"R": 0, "Z": 0, "PUERTA_": 0, "PAS_": 0, "PK_": 0, "P": 0}

    # ---------- geometría ----------

    def _contiene(self, elem, x, y):
        ex = elem["ubicacion"]["x"]
        ey = elem["ubicacion"]["y"]
        return ex <= x < ex + elem["ancho"] and ey <= y < ey + elem["alto"]

    def _solapa(self, nombre, x, y, w, h):
        for e in getattr(self, nombre):
            ex = e["ubicacion"]["x"]
            ey = e["ubicacion"]["y"]
            if x < ex + e["ancho"] and ex < x + w and y < ey + e["alto"] and ey < y + h:
                return True
        return False

    # ---------- alta y baja ----------

    def error(self, herramienta, x, y, w, h):
        """Texto del problema, o "" si se puede colocar."""
        if herramienta not in BLOQUEAN:
            return ""
        if x < 0 or y < 0 or x + w > self.ancho_x or y + h > self.largo_y:
            return "Se sale del warehouse"
        if herramienta == "rack" and w != 2 and h != 2:
            return "Un lado del rack tiene que valer 2"
        if herramienta == "puerta":
            en_borde = x == 0 or x == self.ancho_x - 1 or y == 0 or y == self.largo_y - 1
            if not en_borde:
                return "La puerta tiene que ir sobre el borde"
        for nombre in BLOQUEAN[herramienta]:
            if self._solapa(nombre, x, y, w, h):
                return "Se solapa con " + NOMBRE_LISTA[nombre]
        return ""

    def agregar(self, herramienta, x, y, w, h, sentido="AMBOS"):
        """Agrega el elemento; devuelve "" si salió bien o el texto del error."""
        problema = self.error(herramienta, x, y, w, h)
        if problema:
            return problema
        prefijo = PREFIJO[herramienta]
        self.contadores[prefijo] += 1
        elem = {"id": f"{prefijo}{self.contadores[prefijo]}",
                "ubicacion": {"x": x, "y": y}, "ancho": w, "alto": h}
        if herramienta == "pasillo":
            elem["sentido"] = sentido
        getattr(self, LISTA_DE[herramienta]).append(elem)
        self.historial.append(LISTA_DE[herramienta])
        self.version += 1
        return ""

    def rack_en(self, x, y):
        for r in self.racks:
            if self._contiene(r, x, y):
                return r["id"]
        return ""

    def siguiente_z(self, x, y):
        mayor = 0
        for p in self.productos:
            u = p["ubicacion"]
            if u["x"] == x and u["y"] == y and u["z"] > mayor:
                mayor = u["z"]
        return mayor + 1

    def agregar_producto(self, x, y, z, stock, peso_kg, nombre=""):
        rack_id = self.rack_en(x, y)
        if not rack_id:
            return "El producto tiene que ir dentro de un rack"
        if z < 1:
            return "La altura z tiene que ser 1 o más"
        if stock < 1:
            return "El stock tiene que ser al menos 1"
        if peso_kg <= 0:
            return "El peso tiene que ser mayor que 0"
        for p in self.productos:
            u = p["ubicacion"]
            if u["x"] == x and u["y"] == y and u["z"] == z:
                return f"Ya hay un producto en ({x}, {y}, {z})"
        self.contadores["P"] += 1
        id_producto = f"P{self.contadores['P']:03d}"
        self.productos.append({
            "id": id_producto,
            "nombre": nombre or f"Producto {id_producto}",
            "rack_id": rack_id,
            "ubicacion": {"x": x, "y": y, "z": z},
            "cantidad_disponible": stock,
            "peso_kg": peso_kg,
        })
        self.historial.append("productos")
        self.version += 1
        return ""

    def borrar(self, x, y):
        """Con productos en la celda saca el de mayor z; si no, el elemento."""
        self.historial.clear()
        self.version += 1
        mayor = None
        for p in self.productos:
            u = p["ubicacion"]
            if u["x"] == x and u["y"] == y:
                if mayor is None or u["z"] > mayor["ubicacion"]["z"]:
                    mayor = p
        if mayor is not None:
            self.productos.remove(mayor)
            return
        for nombre in ("pickers", "puertas", "pasillos", "zonas", "racks"):
            lista = getattr(self, nombre)
            for e in reversed(lista):
                if self._contiene(e, x, y):
                    lista.remove(e)
                    if nombre == "racks":
                        self.productos = [p for p in self.productos if p["rack_id"] != e["id"]]
                    return

    def deshacer(self):
        if not self.historial:
            return
        lista = getattr(self, self.historial.pop())
        if lista:
            lista.pop()
        self.version += 1

    # ---------- pickers: ubicar y mover ----------

    def picker_en(self, x, y):
        """Índice del picker que está en la celda (x, y), o -1."""
        for indice, picker in enumerate(self.pickers):
            if picker["ubicacion"]["x"] == x and picker["ubicacion"]["y"] == y:
                return indice
        return -1

    def error_mover_picker(self, indice, x, y):
        """Texto del problema de poner el picker `indice` en (x, y), o "" si se puede."""
        if x < 0 or y < 0 or x >= self.ancho_x or y >= self.largo_y:
            return "Se sale del warehouse"
        for nombre in ("racks", "zonas", "puertas"):
            if self._solapa(nombre, x, y, 1, 1):
                return "Se solapa con " + NOMBRE_LISTA[nombre]
        otro = self.picker_en(x, y)
        if otro != -1 and otro != indice:
            return "Se solapa con " + NOMBRE_LISTA["pickers"]
        return ""

    def mover_picker(self, indice, x, y):
        problema = self.error_mover_picker(indice, x, y)
        if problema:
            return problema
        self.pickers[indice]["ubicacion"] = {"x": x, "y": y}
        self.version += 1
        return ""

    # ---------- puerta y zona ----------

    def puerta_de_zona(self, zona):
        """La puerta va DENTRO de la zona de despacho."""
        for p in self.puertas:
            if self._contiene(zona, p["ubicacion"]["x"], p["ubicacion"]["y"]):
                return p["id"]
        return ""

    def _zona_de_puerta(self, puerta):
        for z in self.zonas:
            if self._contiene(z, puerta["ubicacion"]["x"], puerta["ubicacion"]["y"]):
                return z["id"]
        return ""

    # ---------- exportar ----------

    def validar(self):
        """Lo mínimo para poder armar el diccionario."""
        errores = []
        if not self.zonas:
            errores.append("Falta al menos una zona de despacho")
        for z in self.zonas:
            if not self.puerta_de_zona(z):
                errores.append(f"La zona {z['id']} no tiene ninguna puerta adentro")
        for p in self.puertas:
            if not self._zona_de_puerta(p):
                errores.append(f"La puerta {p['id']} no está dentro de ninguna zona")
        if not self.pickers:
            errores.append("Falta al menos un picker")
        return errores

    def a_diccionario(self):
        errores = self.validar()
        if errores:
            raise ValueError("Escenario inválido: " + " | ".join(errores))
        zonas = []
        for z in self.zonas:
            zonas.append({**copy.deepcopy(z),
                          "puerta_id": self.puerta_de_zona(z), "peso_max_kg": PESO_MAX_ZONA_KG})
        puertas = []
        for p in self.puertas:
            puertas.append({"id": p["id"], "tipo": "AMBOS",
                            "ubicacion": dict(p["ubicacion"])})
        pickers = []
        for k in self.pickers:
            pickers.append({"id": k["id"], "posicion_inicial": dict(k["ubicacion"]),
                            "capacidad_carga_kg": CAPACIDAD_PICKER_KG})
        return {
            "warehouse": {
                "dimensiones": {"ancho_x": self.ancho_x, "largo_y": self.largo_y},
                "puertas": puertas,
                "zonas_despacho": zonas,
                "racks": copy.deepcopy(self.racks),
                "pasillos": copy.deepcopy(self.pasillos),
            },
            "pickers": pickers,
            "productos": copy.deepcopy(self.productos),
            "pedidos": [],
            "configuracion": {"wave_max_pedidos": 3, "wave_max_productos": 15},
        }