"""Modelo del escenario que arma el editor de mapa (sin pygame).

Guarda los elementos como diccionarios con el mismo formato del JSON del
anexo A. Acá quedan las reglas de colocación propias del editor y la
exportación; la geometría compartida vive en domain.Validation, la validación
de estructura la hacen las clases del Warehouse y la de alcanzabilidad es
Scenario.validar_escenario.
"""

import copy
import math

from domain.Validation import (
    adjacent_cells,
    border_cells,
    inside_bounds,
    on_border,
    point_in_rect,
    rack_clearance_error,
    rack_side_ok,
    rect_contains,
    rects_overlap,
    same_rect,
)

from .Scenario import validar_escenario

# Valores iniciales para zonas manuales; cada zona puede personalizarse.
PESO_MAX_ZONA_KG = 500.0
CAPACIDAD_PICKER_KG = 200.0

# Contra qué listas choca cada herramienta al colocarse.
# La puerta ocupa una celda del borde, contigua a su zona de despacho.
# Excepción: si la zona llega hasta el borde del warehouse, la puerta puede
# compartir esa celda del borde con la zona.
BLOQUEAN = {
    "rack": ("racks", "zonas", "puertas", "pasillos", "pickers"),
    "despacho": ("racks", "zonas", "puertas", "pasillos", "pickers"),
    "puerta": ("racks", "zonas", "puertas", "pasillos", "pickers"),
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

    @staticmethod
    def _rect_de(elem):
        """Devuelve (x, y, ancho, alto) de un elemento serializado."""
        u = elem["ubicacion"]
        return u["x"], u["y"], elem["ancho"], elem["alto"]

    def _contiene(self, elem, x, y):
        return point_in_rect(x, y, *self._rect_de(elem))

    def _solapa(self, nombre, x, y, w, h):
        return any(
            rects_overlap(x, y, w, h, *self._rect_de(e))
            for e in getattr(self, nombre)
        )

    def _en_borde_warehouse(self, x, y):
        return on_border(x, y, self.ancho_x, self.largo_y)

    def _puerta_sobre_zona(self, x, y):
        """La celda es borde del warehouse y pertenece a una zona de despacho.

        En ese caso la puerta puede compartir la celda con la zona: la zona
        llega hasta la pared y el portón se marca sobre su borde exterior.
        """
        if not self._en_borde_warehouse(x, y):
            return False
        return any(self._contiene(z, x, y) for z in self.zonas)

    def _puertas_sobre_borde_de_zona(self, x, y, w, h):
        """True si todas las puertas que caen dentro del rectángulo quedan
        sobre su perímetro y sobre el borde del warehouse.

        Permite dibujar una zona que incluya una puerta ya colocada en la
        pared, siempre que la puerta quede en el borde de esa zona.
        """
        for puerta in self.puertas:
            px = puerta["ubicacion"]["x"]
            py = puerta["ubicacion"]["y"]
            if not (x <= px < x + w and y <= py < y + h):
                continue
            en_perimetro = px in (x, x + w - 1) or py in (y, y + h - 1)
            if not (en_perimetro and self._en_borde_warehouse(px, py)):
                return False
        return True

    def _solapa_rect(self, elemento, x, y, w, h):
        return rects_overlap(x, y, w, h, *self._rect_de(elemento))

    def _contiene_rect(self, elemento, x, y, w, h):
        return rect_contains(*self._rect_de(elemento), x, y, w, h)

    def _mismo_rect(self, elemento, x, y, w, h):
        return same_rect(*self._rect_de(elemento), x, y, w, h)

    def _pasillo_solapa_permitida(self, x, y, w, h):
        """Un pasillo nuevo puede cubrir por completo a los que solapa.

        Así, al redibujar encima de un pasillo chico, se reemplaza en vez de
        rechazarse. Si el solapamiento es parcial, sigue siendo un error.
        """
        for pasillo in self.pasillos:
            if (self._solapa_rect(pasillo, x, y, w, h)
                    and not self._contiene_rect(pasillo, x, y, w, h)):
                return False
        return True

    # ---------- alta y baja ----------

    def error(self, herramienta, x, y, w, h):
        """Texto del problema, o "" si se puede colocar."""
        if herramienta not in BLOQUEAN:
            return ""
        if any(not isinstance(v, int) or isinstance(v, bool) for v in (x, y, w, h)):
            return "La ubicación y el tamaño deben expresarse en celdas enteras"
        if w < 1 or h < 1:
            return "El elemento debe ocupar al menos una celda"
        if not inside_bounds(x, y, w, h, self.ancho_x, self.largo_y):
            return "Se sale del warehouse"
        if herramienta == "rack" and not rack_side_ok(w, h):
            return "Un lado del rack tiene que valer 2"
        if herramienta == "rack":
            motivo = rack_clearance_error(
                x, y, w, h, self.ancho_x, self.largo_y
            )
            if motivo:
                return motivo
        if herramienta == "puerta":
            if (w, h) != (1, 1):
                return "La puerta ocupa una sola celda"
            if not on_border(x, y, self.ancho_x, self.largo_y):
                return "La puerta tiene que ir sobre el borde"
        for nombre in BLOQUEAN[herramienta]:
            if (herramienta == "puerta" and nombre == "zonas"
                    and self._puerta_sobre_zona(x, y)):
                continue
            if (herramienta == "despacho" and nombre == "puertas"
                    and self._puertas_sobre_borde_de_zona(x, y, w, h)):
                continue
            if (herramienta == "pasillo" and nombre == "pasillos"
                    and self._pasillo_solapa_permitida(x, y, w, h)):
                continue
            if self._solapa(nombre, x, y, w, h):
                return "Se solapa con " + NOMBRE_LISTA[nombre]
        return ""

    def agregar(self, herramienta, x, y, w, h, sentido="AMBOS"):
        """Agrega el elemento; devuelve "" si salió bien o el texto del error."""
        problema = self.error(herramienta, x, y, w, h)
        if problema:
            return problema
        if herramienta == "pasillo":
            for pasillo in self.pasillos:
                if self._mismo_rect(pasillo, x, y, w, h):
                    # Redibujar el mismo pasillo solo actualiza su sentido.
                    if pasillo.get("sentido") != sentido:
                        self._guardar_deshacer()
                        pasillo["sentido"] = sentido
                        self.version += 1
                    return ""
            self._guardar_deshacer()
            self.pasillos[:] = [
                pasillo for pasillo in self.pasillos
                if not self._contiene_rect(pasillo, x, y, w, h)
            ]
        else:
            self._guardar_deshacer()
        prefijo = PREFIJO[herramienta]
        self.contadores[prefijo] += 1
        elem = {"id": f"{prefijo}{self.contadores[prefijo]}",
                "ubicacion": {"x": x, "y": y}, "ancho": w, "alto": h}
        if herramienta == "pasillo":
            elem["sentido"] = sentido
        elif herramienta == "despacho":
            elem["peso_max_kg"] = PESO_MAX_ZONA_KG
        getattr(self, LISTA_DE[herramienta]).append(elem)
        self.version += 1
        return ""

    def establecer_peso_zona(self, zona_id, peso_max_kg):
        """Actualiza la capacidad de una zona sin cambiar las demás."""
        if (not isinstance(peso_max_kg, (int, float))
                or isinstance(peso_max_kg, bool)
                or not math.isfinite(peso_max_kg)
                or peso_max_kg <= 0):
            return "El peso máximo debe ser un número mayor a 0 kg"
        zona = next((zona for zona in self.zonas if zona["id"] == zona_id), None)
        if zona is None:
            return "No se encontró la zona de despacho"
        self._guardar_deshacer()
        zona["peso_max_kg"] = float(peso_max_kg)
        self.version += 1
        return ""

    # ---------- deshacer ----------

    CAMPOS_ESTADO = ("racks", "zonas", "puertas", "pasillos", "pickers",
                     "productos")

    def _instantanea(self):
        estado = {
            campo: copy.deepcopy(getattr(self, campo))
            for campo in self.CAMPOS_ESTADO
        }
        estado["contadores"] = dict(self.contadores)
        return estado

    def _guardar_deshacer(self):
        self.historial.append(self._instantanea())
        if len(self.historial) > 100:
            self.historial.pop(0)

    def _restaurar(self, estado):
        for campo in self.CAMPOS_ESTADO:
            setattr(self, campo, estado[campo])
        self.contadores = dict(estado["contadores"])

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
        if z != self.siguiente_z(x, y):
            return f"En esa celda, el próximo nivel disponible es z={self.siguiente_z(x, y)}"
        if stock < 1:
            return "El stock tiene que ser al menos 1"
        if peso_kg <= 0:
            return "El peso tiene que ser mayor que 0"
        for p in self.productos:
            u = p["ubicacion"]
            if u["x"] == x and u["y"] == y and u["z"] == z:
                return f"Ya hay un producto en ({x}, {y}, {z})"
        self._guardar_deshacer()
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
        self.version += 1
        return ""

    def borrar(self, x, y):
        """Con productos en la celda saca el de mayor z; si no, el elemento."""
        mayor = None
        for p in self.productos:
            u = p["ubicacion"]
            if u["x"] == x and u["y"] == y:
                if mayor is None or u["z"] > mayor["ubicacion"]["z"]:
                    mayor = p
        if mayor is not None:
            self._guardar_deshacer()
            self.productos.remove(mayor)
            self.version += 1
            return
        for nombre in ("pickers", "puertas", "pasillos", "zonas", "racks"):
            lista = getattr(self, nombre)
            for e in reversed(lista):
                if self._contiene(e, x, y):
                    self._guardar_deshacer()
                    lista.remove(e)
                    if nombre == "racks":
                        self.productos = [p for p in self.productos if p["rack_id"] != e["id"]]
                    self.version += 1
                    return

    def deshacer(self):
        if not self.historial:
            return
        self._restaurar(self.historial.pop())
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
        actual = self.pickers[indice]["ubicacion"]
        if (actual["x"], actual["y"]) == (x, y):
            return ""
        self._guardar_deshacer()
        self.pickers[indice]["ubicacion"] = {"x": x, "y": y}
        self.version += 1
        return ""

    # ---------- puerta y zona ----------

    def puerta_de_zona(self, zona):
        """Devuelve la puerta asociada a la zona (contigua o sobre su borde)."""
        for p in self.puertas:
            ubicacion = (p["ubicacion"]["x"], p["ubicacion"]["y"])
            if ubicacion in self._celdas_de_puerta(zona):
                return p["id"]
        return ""

    def _zona_de_puerta(self, puerta):
        for z in self.zonas:
            ubicacion = (puerta["ubicacion"]["x"], puerta["ubicacion"]["y"])
            if ubicacion in self._celdas_de_puerta(z):
                return z["id"]
        return ""

    def _celdas_del_borde(self, elemento):
        """Celdas del elemento que también están sobre el borde del warehouse."""
        x, y, w, h = self._rect_de(elemento)
        return border_cells(x, y, w, h, self.ancho_x, self.largo_y)

    def _celdas_de_puerta(self, zona):
        """Celdas donde puede ir la puerta de una zona.

        Incluye las celdas contiguas por fuera de la zona y, si la zona llega
        al borde del warehouse, también sus propias celdas de ese borde.
        """
        return self._celdas_adyacentes(zona) | self._celdas_del_borde(zona)

    def _celdas_adyacentes(self, elemento):
        """Celdas vecinas del rectángulo que quedan dentro del warehouse."""
        x, y, w, h = self._rect_de(elemento)
        return adjacent_cells(x, y, w, h, self.ancho_x, self.largo_y)

    # ---------- exportar ----------

    def _errores_editor(self):
        """Reglas del editor, sin recalcular la alcanzabilidad del escenario."""
        errores = []
        if not self.zonas:
            errores.append("Falta al menos una zona de despacho")
        for z in self.zonas:
            if not self.puerta_de_zona(z):
                errores.append(f"La zona {z['id']} necesita una puerta contigua en el borde del warehouse")
        for p in self.puertas:
            if not self._zona_de_puerta(p):
                errores.append(f"La puerta {p['id']} no tiene una zona de despacho enfrente")
        if not self.pickers:
            errores.append("Falta al menos un picker")
        if not self.productos:
            errores.append("Falta al menos un producto")
        elif sum(p["cantidad_disponible"] for p in self.productos) < 8:
            errores.append("El stock total debe alcanzar para generar los 8 pedidos del escenario")
        return errores

    def validar(self):
        """Valida requisitos del editor y reutiliza la validación del Warehouse."""
        errores = self._errores_editor()
        if not errores:
            try:
                validar_escenario(self._construir_diccionario())
            except (KeyError, TypeError, ValueError) as error:
                errores.append(str(error))
        return errores

    def a_diccionario(self):
        errores = self._errores_editor()
        if errores:
            raise ValueError("Escenario inválido: " + " | ".join(errores))
        return self._construir_diccionario()

    def _construir_diccionario(self):
        zonas = []
        for z in self.zonas:
            zonas.append({**copy.deepcopy(z),
                          "puerta_id": self.puerta_de_zona(z),
                          "peso_max_kg": z.get("peso_max_kg", PESO_MAX_ZONA_KG)})
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
