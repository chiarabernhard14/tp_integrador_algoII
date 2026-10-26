"""VISTA PREVIA PROVISORIA de la interfaz: python vista_previa.py [--escenario ruta.json]

Corre la aplicación visual nueva (app.py + SesionV.py + ModeloEscenarioV.py) con una
simulación FALSA que vive en este mismo archivo. No usa tu Simulacion, ni Navegacion,
ni el Warehouse reales: sirve solo para ver cómo se ven y se comportan la interfaz,
el editor de mapa y los pickers mientras la generación de waves sigue cambiando.

- Los pickers se mueven con una búsqueda simple (BFS), no con A* ni con tus recorridos.
- El generador de escenarios y el armado de waves son copias de ScenarioV y WavesV.
- Para correr con el proyecto real se usa main.py.

Requiere pegados: SesionV.py y ModeloEscenarioV.py en simulation/simulationV/, y
todos los archivos de visualization/real/.
"""

import argparse
import ctypes
import importlib
import json
import os
import random
import sys
import types
from types import SimpleNamespace

try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass

CARPETA = os.path.dirname(os.path.abspath(__file__))
VISUALIZACION = os.path.abspath(os.path.join(CARPETA, ".."))
RAIZ = os.path.dirname(VISUALIZACION)
for _ruta in (VISUALIZACION, RAIZ):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

VECINOS = ((1, 0), (-1, 0), (0, 1), (0, -1))
LIMITE_BLOQUEO = 20


# =====================================================================
# Armado de waves (copia de WavesV, solo para esta vista previa)
# =====================================================================

def _clave_pedido(pedido):
    return (-pedido.prioridad, pedido.id)


def peso_pedido(pedido):
    peso = 0.0
    for item in pedido.items:
        if item.producto is not None:
            peso += item.cantidad * item.producto.peso_kg
    return peso


def armar_waves(pedidos, max_pedidos, max_productos, max_peso=0):
    waves = []
    items_por_wave = []
    peso_por_wave = []
    excluidos = []

    for pedido in sorted(pedidos, key=_clave_pedido):
        cantidad_items = len(pedido.items)
        peso = peso_pedido(pedido) if max_peso > 0 else 0.0

        if max_productos > 0 and cantidad_items > max_productos:
            excluidos.append(pedido)
            continue
        if max_peso > 0 and peso > max_peso:
            excluidos.append(pedido)
            continue

        destino = None
        for i, wave in enumerate(waves):
            if max_pedidos > 0 and len(wave) >= max_pedidos:
                continue
            if max_productos > 0 and items_por_wave[i] + cantidad_items > max_productos:
                continue
            if max_peso > 0 and peso_por_wave[i] + peso > max_peso:
                continue
            destino = i
            break

        if destino is None:
            waves.append([pedido])
            items_por_wave.append(cantidad_items)
            peso_por_wave.append(peso)
        else:
            waves[destino].append(pedido)
            items_por_wave[destino] += cantidad_items
            peso_por_wave[destino] += peso

    return waves, excluidos


# =====================================================================
# Generador de escenarios (copia de ScenarioV, solo para esta vista previa)
# =====================================================================

ANCHO_PASILLO = 2
NIVELES = 3
MODOS_UBICACION = ("aleatoria", "agrupada", "cerca_despacho")


def generar_escenario(
    estantes=6,
    pasillos_horizontales=2,
    productos=20,
    pedidos=8,
    max_productos_pedido=4,
    max_orders_capacity=3,
    max_products_capacity=15,
    pickers=2,
    modo_ubicacion="aleatoria",
    alto_rack=6,
):
    _validar_parametros(estantes, pasillos_horizontales, productos, pedidos,
                        max_productos_pedido, pickers, modo_ubicacion, alto_rack,
                        max_orders_capacity, max_products_capacity)
    azar = random.Random()

    filas = max(1, min(pasillos_horizontales - 1, estantes))
    columnas = -(-estantes // filas)
    filas = -(-estantes // columnas)
    paso_x = 2 + ANCHO_PASILLO
    ancho_x = max(columnas * paso_x + ANCHO_PASILLO, 8)
    largo_y = 5 + filas * (alto_rack + 2)

    racks = _crear_racks(estantes, columnas, alto_rack)
    datos = {
        "warehouse": {
            "dimensiones": {"ancho_x": ancho_x, "largo_y": largo_y},
            "puertas": [],
            "zonas_despacho": [],
            "racks": racks,
            "pasillos": _crear_pasillos(racks, filas, ancho_x, alto_rack),
        },
        "pickers": [],
        "productos": [],
        "pedidos": [],
        "configuracion": {
            "wave_max_pedidos": max_orders_capacity,
            "wave_max_productos": max_products_capacity,
        },
    }
    _crear_despacho(datos["warehouse"], ancho_x)
    datos["pickers"] = _crear_pickers(pickers, ancho_x, azar)
    datos["productos"] = _crear_productos(racks, productos, modo_ubicacion, azar)
    datos["pedidos"] = _crear_pedidos(datos["productos"], pedidos, max_productos_pedido, azar)
    validar_escenario(datos)
    return datos


def generar_pedidos(productos, cantidad=8, max_productos_pedido=4):
    return _crear_pedidos(productos, cantidad, max_productos_pedido, random.Random())


def _validar_parametros(estantes, pasillos_h, productos, pedidos, max_prod, pickers, modo, alto,
                        max_orders, max_products):
    if estantes < 1:
        raise ValueError("Debe haber al menos 1 estante.")
    if pasillos_h < 2:
        raise ValueError("Hacen falta al menos 2 pasillos horizontales.")
    if productos < 1 or pedidos < 1 or max_prod < 1 or pickers < 1:
        raise ValueError("Productos, pedidos, items por pedido y pickers deben ser >= 1.")
    if alto < 2:
        raise ValueError("El alto del rack debe ser >= 2.")
    if max_orders < 0 or max_products < 0:
        raise ValueError("La capacidad de las waves no puede ser negativa (0 = sin limite).")
    if modo not in MODOS_UBICACION:
        raise ValueError(f"Modo de ubicacion invalido: {modo}.")
    capacidad = estantes * 2 * alto * NIVELES
    if productos > capacidad:
        raise ValueError(f"Con {estantes} estantes solo entran {capacidad} productos.")


def _crear_racks(estantes, columnas, alto_rack):
    paso_x = 2 + ANCHO_PASILLO
    racks = []
    for i in range(estantes):
        fila = i // columnas
        columna = i % columnas
        racks.append({
            "id": f"R{i + 1}",
            "ubicacion": {"x": ANCHO_PASILLO + columna * paso_x,
                          "y": 5 + fila * (alto_rack + 2)},
            "ancho": 2,
            "alto": alto_rack,
        })
    return racks


def _crear_pasillos(racks, filas, ancho_x, alto_rack):
    paso_x = 2 + ANCHO_PASILLO
    pasillos = []
    for k in range(filas + 1):
        pasillos.append({
            "id": f"PAS_H{k}",
            "ubicacion": {"x": 0, "y": 3 + k * (alto_rack + 2)},
            "ancho": ancho_x,
            "alto": 2,
            "sentido": "AMBOS",
        })
    for fila in range(filas):
        y = 5 + fila * (alto_rack + 2)
        en_fila = 0
        for rack in racks:
            if rack["ubicacion"]["y"] == y:
                en_fila += 1
        for j in range(en_fila + 1):
            pasillos.append({
                "id": f"PAS_V{fila}_{j}",
                "ubicacion": {"x": j * paso_x, "y": y},
                "ancho": ANCHO_PASILLO,
                "alto": alto_rack,
                "sentido": "N" if j % 2 == 0 else "S",
            })
    return pasillos


def _crear_despacho(warehouse, ancho_x):
    ancho_zona = min(5, ancho_x - 2)
    posiciones = [("OUT", "OUTBOUND", 1)]
    if ancho_x >= 16:
        posiciones.append(("IN", "INBOUND", ancho_x - 1 - ancho_zona))
    for nombre, tipo, x_zona in posiciones:
        id_puerta = f"PUERTA_{nombre}_1"
        warehouse["puertas"].append({
            "id": id_puerta,
            "tipo": tipo,
            "ubicacion": {"x": x_zona + ancho_zona // 2, "y": 0},
        })
        warehouse["zonas_despacho"].append({
            "id": f"ZONA_{nombre}",
            "puerta_id": id_puerta,
            "ubicacion": {"x": x_zona, "y": 0},
            "ancho": ancho_zona,
            "alto": 3,
            "peso_max_kg": 500.0,
        })


def _crear_pickers(cantidad, ancho_x, azar):
    columnas = ancho_x - 2
    if cantidad > 2 * columnas:
        raise ValueError(
            f"El almacén solo tiene lugar para {2 * columnas} pickers en el pasillo inicial."
        )
    en_fila_3 = min(cantidad, columnas)
    lista = []
    for i in range(cantidad):
        if i < en_fila_3:
            y = 3
            indice = i
            total = en_fila_3
        else:
            y = 4
            indice = i - en_fila_3
            total = cantidad - en_fila_3
        x = 1 + indice * (columnas // total)
        lista.append({
            "id": f"PK_{i + 1:02d}",
            "posicion_inicial": {"x": x, "y": y},
            "capacidad_carga_kg": float(azar.choice((100, 150, 200))),
        })
    return lista


def _crear_productos(racks, cantidad, modo, azar):
    posiciones = []
    for rack in racks:
        x0 = rack["ubicacion"]["x"]
        y0 = rack["ubicacion"]["y"]
        del_rack = []
        for x in range(x0, x0 + rack["ancho"]):
            for y in range(y0, y0 + rack["alto"]):
                for z in range(1, NIVELES + 1):
                    del_rack.append((rack["id"], x, y, z))
        azar.shuffle(del_rack)
        posiciones.append(del_rack)

    elegidas = []
    for del_rack in posiciones:
        elegidas.extend(del_rack)
    if modo != "agrupada":
        azar.shuffle(elegidas)
        if modo == "cerca_despacho":
            elegidas.sort(key=_fila_de_posicion)
    elegidas = elegidas[:cantidad]

    apilados = {}
    ordenadas = []
    for id_rack, x, y, _nivel in elegidas:
        apilados[(x, y)] = apilados.get((x, y), 0) + 1
        ordenadas.append((id_rack, x, y, apilados[(x, y)]))

    lista = []
    for i, (id_rack, x, y, z) in enumerate(ordenadas):
        lista.append({
            "id": f"P{i + 1:03d}",
            "nombre": f"Producto {i + 1:03d}",
            "rack_id": id_rack,
            "ubicacion": {"x": x, "y": y, "z": z},
            "cantidad_disponible": azar.randint(5, 50),
            "peso_kg": round(azar.uniform(0.2, 10.0), 1),
        })
    return lista


def _fila_de_posicion(posicion):
    return posicion[2]


def _crear_pedidos(productos, cantidad, max_items, azar):
    restante = {}
    for producto in productos:
        restante[producto["id"]] = producto["cantidad_disponible"]

    pedidos = []
    for i in range(cantidad):
        con_stock = []
        for producto in productos:
            if restante[producto["id"]] > 0:
                con_stock.append(producto)
        if not con_stock:
            raise ValueError(
                f"El stock total no alcanza para generar {cantidad} pedidos; "
                "aumentá la cantidad de productos o bajá la de pedidos."
            )

        n_items = azar.randint(1, min(max_items, len(con_stock)))
        elegidos = azar.sample(con_stock, n_items)
        items = []
        for producto in elegidos:
            tope = min(3, restante[producto["id"]])
            unidades = azar.randint(1, tope)
            restante[producto["id"]] -= unidades
            items.append({"producto_id": producto["id"], "cantidad": unidades})
        pedidos.append({
            "id": f"PED_{i + 1:02d}",
            "prioridad": azar.randint(1, 5),
            "estado": "PENDIENTE",
            "items": items,
        })
    return pedidos


# =====================================================================
# Mapa simple: celdas libres, sentidos, accesos y búsqueda BFS
# =====================================================================

class _Rectangulo:

    def __init__(self, id_, x, y, ancho, alto, sentido="AMBOS"):
        self.id = id_
        self.ubicacion = (x, y)
        self.ancho = ancho
        self.alto = alto
        self.sentido = sentido

    def cells(self):
        celdas = []
        for x in range(self.ubicacion[0], self.ubicacion[0] + self.ancho):
            for y in range(self.ubicacion[1], self.ubicacion[1] + self.alto):
                celdas.append((x, y))
        return celdas


def _rectangulos(lista):
    resultado = {}
    for d in lista:
        u = d["ubicacion"]
        resultado[d["id"]] = _Rectangulo(
            d["id"], u["x"], u["y"], d.get("ancho", 1), d.get("alto", 1), d.get("sentido", "AMBOS"))
    return resultado


def _permitido(sentido, dx, dy):
    if sentido == "N":
        return dy != -1
    if sentido == "S":
        return dy != 1
    if sentido == "E":
        return dx != -1
    if sentido == "O":
        return dx != 1
    return True


def _eje(pasillo):
    if pasillo.sentido in ("N", "S"):
        return "V"
    if pasillo.sentido in ("E", "O"):
        return "H"
    if pasillo.alto > pasillo.ancho:
        return "V"
    if pasillo.ancho > pasillo.alto:
        return "H"
    return "X"


class _Mapa:

    def __init__(self, datos):
        wh = datos["warehouse"]
        self.ancho_x = wh["dimensiones"]["ancho_x"]
        self.largo_y = wh["dimensiones"]["largo_y"]
        self.racks = _rectangulos(wh["racks"])
        self.pasillos = _rectangulos(wh["pasillos"])
        self.zonas = _rectangulos(wh["zonas_despacho"])
        self.puertas = _rectangulos(wh["puertas"])

        ocupadas = set()
        for grupo in (self.racks, self.zonas, self.puertas):
            for e in grupo.values():
                ocupadas.update(e.cells())
        self.libres = set()
        for x in range(self.ancho_x):
            for y in range(self.largo_y):
                if (x, y) not in ocupadas:
                    self.libres.add((x, y))

        self.sentido = {}
        for celda in self.libres:
            self.sentido[celda] = ("AMBOS", "")
        self.eje = {}
        for p in self.pasillos.values():
            for celda in p.cells():
                if celda in self.libres:
                    self.sentido[celda] = (p.sentido, p.id)
                    self.eje[celda] = _eje(p)

        self.despacho = set()
        for z in self.zonas.values():
            for x, y in z.cells():
                for dx, dy in VECINOS:
                    if (x + dx, y + dy) in self.libres:
                        self.despacho.add((x + dx, y + dy))

        self.intersecciones = self._calcular_intersecciones()

    def mueve(self, a, b):
        if a not in self.libres or b not in self.libres:
            return False
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        return _permitido(self.sentido[a][0], dx, dy) and _permitido(self.sentido[b][0], dx, dy)

    def _calcular_intersecciones(self):
        resultado = set()
        for celda in self.eje:
            for dx, dy in VECINOS:
                otra = (celda[0] + dx, celda[1] + dy)
                if otra not in self.eje or not self.mueve(celda, otra):
                    continue
                if self.sentido[celda][1] == self.sentido[otra][1]:
                    continue
                if self.eje[celda] != self.eje[otra] or self.eje[celda] == "X":
                    resultado.add(celda)
                    resultado.add(otra)
        return resultado

    def accesos(self, x, y):
        """Celdas de pasillo desde las que se alcanza la celda (x, y) de un rack."""
        for rack in self.racks.values():
            if (x, y) not in rack.cells():
                continue
            x0, y0 = rack.ubicacion
            candidatas = []
            if rack.ancho == 2:
                candidatas.append((x - 1, y) if x == x0 else (x + 1, y))
            if rack.alto == 2:
                candidatas.append((x, y - 1) if y == y0 else (x, y + 1))
            accesos = set()
            for c in candidatas:
                if c in self.libres:
                    accesos.add(c)
            return accesos
        return set()

    def camino(self, origen, destinos, ocupadas=()):
        """Ruta más corta (sin incluir el origen) al destino más cercano, o None."""
        if origen not in self.libres:
            return None
        if origen in destinos:
            return []
        objetivos = set(destinos) - set(ocupadas)
        if not objetivos:
            return None
        padre = {origen: None}
        cola = [origen]
        i = 0
        while i < len(cola):
            actual = cola[i]
            i += 1
            if actual in objetivos:
                ruta = []
                while actual != origen:
                    ruta.append(actual)
                    actual = padre[actual]
                ruta.reverse()
                return ruta
            for dx, dy in VECINOS:
                vecino = (actual[0] + dx, actual[1] + dy)
                if vecino in padre or vecino in ocupadas or not self.mueve(actual, vecino):
                    continue
                padre[vecino] = actual
                cola.append(vecino)
        return None

    def alcanzables(self, semillas, invertido):
        visto = set(semillas)
        cola = list(semillas)
        i = 0
        while i < len(cola):
            actual = cola[i]
            i += 1
            for dx, dy in VECINOS:
                vecino = (actual[0] + dx, actual[1] + dy)
                if vecino in visto:
                    continue
                ok = self.mueve(vecino, actual) if invertido else self.mueve(actual, vecino)
                if ok:
                    visto.add(vecino)
                    cola.append(vecino)
        return visto


def validar_escenario(datos):
    try:
        mapa = _Mapa(datos)
    except (KeyError, TypeError) as error:
        raise ValueError(f"Escenario inválido: {type(error).__name__}: {error}") from error
    if not mapa.despacho:
        raise ValueError("Ninguna celda de pasillo es adyacente a una zona de despacho.")
    ida = mapa.alcanzables(mapa.despacho, False)
    vuelta = mapa.alcanzables(mapa.despacho, True)
    for d in datos["productos"]:
        accesos = mapa.accesos(d["ubicacion"]["x"], d["ubicacion"]["y"])
        if not any(a in ida for a in accesos):
            raise ValueError(f"{d['id']} no es alcanzable desde el despacho.")
        if not any(a in vuelta for a in accesos):
            raise ValueError(f"No hay camino de regreso desde {d['id']} al despacho.")
    for d in datos["pickers"]:
        pos = (d["posicion_inicial"]["x"], d["posicion_inicial"]["y"])
        if pos not in mapa.libres:
            raise ValueError(f"{d['id']} no esta sobre una celda de pasillo.")


# =====================================================================
# Simulación provisoria (mismo contrato que Simulacion para la interfaz)
# =====================================================================

def _clave_tarea(tarea):
    return (-tarea["prioridad"], tarea["producto_id"])


def _clave_cola(wave):
    return (-len(wave["tareas"]), -wave["peso"], wave["id"])


def _id_picker(picker):
    return picker.id


class _PickerSim:

    def __init__(self, datos):
        u = datos["posicion_inicial"]
        self.id = datos["id"]
        self.capacidad = datos["capacidad_carga_kg"]
        self.pos = (u["x"], u["y"])
        self.anterior = None
        self.ruta = []
        self.pendientes = []
        self.recogidos = []
        self.objetivo = None
        self.destinos = set()
        self.estado = "disponible"
        self.trail = [self.pos]
        self.wave = None
        self.waves_hechas = []


class Simulacion:

    def __init__(self, datos, waves=None):
        self.datos = datos
        self.waves_entrada = waves
        self.mapa = _Mapa(datos)
        self.nav = SimpleNamespace(intersecciones=self.mapa.intersecciones)
        self.reiniciar()

    # ---------- armado ----------

    def reiniciar(self):
        self.tick = 0
        self.terminada = False
        self.log = []
        self.hubo_avance = False
        self.ticks_sin_avance = 0
        m = self.mapa
        self.warehouse = SimpleNamespace(
            ancho_x=m.ancho_x, largo_y=m.largo_y, racks=m.racks, pasillos=m.pasillos,
            zonas_despacho=m.zonas, puertas=m.puertas)

        self.productos = {}
        for d in self.datos["productos"]:
            u = d["ubicacion"]
            self.productos[d["id"]] = SimpleNamespace(
                id=d["id"], ubicacion=(u["x"], u["y"], u["z"]),
                stock=d["cantidad_disponible"], peso_kg=d["peso_kg"])

        self.pedidos = {}
        for d in self.datos["pedidos"]:
            items = []
            for it in d["items"]:
                items.append(SimpleNamespace(
                    producto_id=it["producto_id"], cantidad=it["cantidad"],
                    producto=self.productos.get(it["producto_id"]), picked=False))
            self.pedidos[d["id"]] = SimpleNamespace(
                id=d["id"], prioridad=d["prioridad"], estado=d["estado"], items=items)

        self.pickers = []
        for d in self.datos["pickers"]:
            self.pickers.append(_PickerSim(d))

        self.waves = []
        self.cola_waves = []
        self.pedidos_wave = []
        self._armar_waves()
        self._validar_pickers()
        self.cola_waves.sort(key=_clave_cola)
        for picker in sorted(self.pickers, key=_id_picker):
            wave = self._buscar_wave(picker)
            if wave is not None:
                self._tomar_wave(picker, wave)
        self._registrar("Simulación inicializada (PROVISORIA).")

    def _armar_waves(self):
        grupos = []
        if self.waves_entrada is None:
            config = self.datos.get("configuracion", {})
            capacidad_maxima = 0.0
            for picker in self.pickers:
                capacidad_maxima = max(capacidad_maxima, picker.capacidad)
            pendientes = []
            for pedido in self.pedidos.values():
                if pedido.estado == "PENDIENTE":
                    pendientes.append(pedido)
            armadas, excluidos = armar_waves(
                pendientes, config.get("wave_max_pedidos", 0),
                config.get("wave_max_productos", 0), capacidad_maxima)
            for pedido in excluidos:
                self._registrar(f"Pedido {pedido.id}: no entra en ninguna wave y se excluye.")
            for numero, pedidos in enumerate(armadas, start=1):
                grupos.append((f"W{numero}", pedidos))
        else:
            for wave in self.waves_entrada:
                pedidos = []
                for orden in wave["orders"]:
                    pedidos.append(self.pedidos[orden["id"]])
                grupos.append((str(wave["id"]), pedidos))
        for id_wave, pedidos in grupos:
            self._crear_wave(id_wave, pedidos)

    def _crear_wave(self, id_wave, pedidos):
        peso = 0.0
        tareas = {}
        for pedido in pedidos:
            peso += peso_pedido(pedido)
            for indice, item in enumerate(pedido.items):
                if item.producto is None:
                    continue
                if item.producto_id not in tareas:
                    tareas[item.producto_id] = {
                        "id": f"{id_wave}:{item.producto_id}",
                        "producto_id": item.producto_id,
                        "cantidad": 0,
                        "prioridad": pedido.prioridad,
                        "lineas": [],
                    }
                tarea = tareas[item.producto_id]
                tarea["cantidad"] += item.cantidad
                tarea["prioridad"] = max(tarea["prioridad"], pedido.prioridad)
                tarea["lineas"].append({"pedido_id": pedido.id, "indice_item": indice,
                                        "cantidad": item.cantidad, "item": item})
            self.pedidos_wave.append(pedido)
        for producto_id, tarea in tareas.items():
            producto = self.productos[producto_id]
            producto.stock = max(0, producto.stock - tarea["cantidad"])
        wave = {"id": id_wave, "pedidos": list(pedidos), "tareas": tareas,
                "peso": peso, "picker": None, "estado": "CREADA"}
        self.waves.append(wave)
        self.cola_waves.append(wave)

    def _validar_pickers(self):
        if not self.waves:
            raise ValueError("No hay waves para ejecutar.")
        if len(self.pickers) > len(self.waves):
            raise ValueError(
                f"Hay {len(self.pickers)} pickers pero solo {len(self.waves)} wave(s). "
                f"Cada wave la ejecuta un solo picker, así que el máximo es {len(self.waves)}.")
        capacidad_maxima = 0.0
        for picker in self.pickers:
            capacidad_maxima = max(capacidad_maxima, picker.capacidad)
        for wave in self.waves:
            if wave["peso"] > capacidad_maxima:
                raise ValueError(
                    f"La wave {wave['id']} pesa {wave['peso']:g} kg y ningún picker "
                    f"carga tanto (máximo {capacidad_maxima:g} kg).")

    def _buscar_wave(self, picker):
        for wave in self.cola_waves:
            if wave["peso"] <= picker.capacidad:
                return wave
        return None

    def _tomar_wave(self, picker, wave):
        for i, candidata in enumerate(self.cola_waves):
            if candidata is wave:
                del self.cola_waves[i]
                break
        wave["picker"] = picker.id
        wave["estado"] = "EN_PROCESO"
        picker.wave = wave
        picker.objetivo = None
        picker.destinos = set()
        picker.estado = "disponible"
        picker.pendientes = sorted(wave["tareas"].values(), key=_clave_tarea)
        self.hubo_avance = True
        self._registrar(f"{picker.id}: toma la wave {wave['id']} "
                        f"({len(wave['pedidos'])} pedidos, {len(picker.pendientes)} productos).")
        self._actualizar_pedidos()

    # ---------- avance ----------

    def paso(self):
        if self.terminada:
            return self.estado()
        self.tick += 1
        self.hubo_avance = False
        for picker in sorted(self.pickers, key=_id_picker):
            if picker.estado not in ("terminado", "bloqueado"):
                self._avanzar(picker)
        self._actualizar_pedidos()
        self._detectar_bloqueo()
        if all(p.estado in ("terminado", "bloqueado") for p in self.pickers):
            self.terminada = True
            self._registrar("Simulación finalizada.")
        return self.estado()

    def _detectar_bloqueo(self):
        if self.hubo_avance:
            self.ticks_sin_avance = 0
            return
        self.ticks_sin_avance += 1
        if self.ticks_sin_avance < LIMITE_BLOQUEO:
            return
        for picker in self.pickers:
            if picker.estado != "terminado":
                picker.estado = "bloqueado"
                self._registrar(f"{picker.id}: bloqueado, sin avance durante {LIMITE_BLOQUEO} ticks.")

    def _ocupadas(self, picker):
        ocupadas = set()
        for otro in self.pickers:
            if otro is not picker and otro.estado != "terminado":
                ocupadas.add(otro.pos)
        return ocupadas

    def _quien_ocupa(self, picker, celda):
        for otro in self.pickers:
            if otro is not picker and otro.estado != "terminado" and otro.pos == celda:
                return otro
        return None

    def _avanzar(self, picker):
        if picker.estado == "esperando":
            picker.estado = "disponible"
        if not picker.ruta:
            if picker.pendientes:
                self._elegir_objetivo(picker)
                if not picker.ruta and picker.objetivo is not None:
                    self._recoger(picker)
            else:
                self._planificar_regreso(picker)
        if picker.ruta:
            self._mover(picker)

    def _elegir_objetivo(self, picker):
        ocupadas = self._ocupadas(picker)
        mejor_tarea = None
        mejor_ruta = None
        for tarea in sorted(picker.pendientes, key=_clave_tarea):
            x, y = self.productos[tarea["producto_id"]].ubicacion[:2]
            accesos = self.mapa.accesos(x, y)
            ruta = self.mapa.camino(picker.pos, accesos, ocupadas)
            if ruta is None:
                continue
            if (mejor_ruta is None or len(ruta) < len(mejor_ruta)
                    or (len(ruta) == len(mejor_ruta)
                        and tarea["producto_id"] < mejor_tarea["producto_id"])):
                mejor_tarea = tarea
                mejor_ruta = ruta
        if mejor_tarea is None:
            picker.estado = "esperando"
            return
        picker.objetivo = mejor_tarea
        picker.ruta = list(mejor_ruta)
        picker.destinos = {mejor_ruta[-1] if mejor_ruta else picker.pos}
        picker.estado = "yendo_a_producto"
        self._registrar(f"{picker.id}: se dirige a {mejor_tarea['producto_id']}.")

    def _recoger(self, picker):
        tarea = picker.objetivo
        if tarea is None:
            return
        for linea in tarea["lineas"]:
            linea["item"].picked = True
            picker.recogidos.append({"producto_id": tarea["producto_id"],
                                     "pedido_id": linea["pedido_id"],
                                     "cantidad": linea["cantidad"]})
        picker.pendientes.remove(tarea)
        picker.objetivo = None
        picker.destinos = set()
        picker.estado = "disponible"
        self.hubo_avance = True
        self._registrar(f"{picker.id}: recogió {tarea['cantidad']} unidades de {tarea['producto_id']}.")
        self._actualizar_pedidos()

    def _planificar_regreso(self, picker):
        if picker.pos in self.mapa.despacho:
            self._llegar_a_despacho(picker)
            return
        ruta = self.mapa.camino(picker.pos, self.mapa.despacho, self._ocupadas(picker))
        if ruta is None:
            picker.estado = "esperando"
            return
        picker.ruta = list(ruta)
        picker.destinos = set(self.mapa.despacho)
        picker.estado = "regresando"

    def _llegar_a_despacho(self, picker):
        self.hubo_avance = True
        if picker.wave is not None:
            picker.wave["estado"] = "COMPLETADA"
            picker.waves_hechas.append(picker.wave["id"])
            self._registrar(f"{picker.id}: completó la wave {picker.wave['id']}.")
            picker.wave = None
        siguiente = self._buscar_wave(picker)
        if siguiente is not None:
            self._tomar_wave(picker, siguiente)
        else:
            picker.estado = "terminado"
            self._registrar(f"{picker.id}: llegó a despacho.")

    def _mover(self, picker):
        siguiente = picker.ruta[0]
        quien = self._quien_ocupa(picker, siguiente)
        if quien is not None:
            # Desempate: el de id menor espera y el otro busca un camino alternativo
            # (si los dos replanificaran a la vez se quedarían dando vueltas).
            picker.estado = "esperando"
            if picker.id > quien.id:
                self._replanificar(picker)
            return
        anterior = picker.pos
        picker.anterior = anterior
        picker.pos = siguiente
        picker.trail.append(siguiente)
        picker.ruta.pop(0)
        self.hubo_avance = True
        if picker.estado == "regresando" and picker.pos in self.mapa.despacho:
            picker.ruta = []
            self._llegar_a_despacho(picker)

    def _replanificar(self, picker):
        if picker.objetivo is not None:
            x, y = self.productos[picker.objetivo["producto_id"]].ubicacion[:2]
            destinos = self.mapa.accesos(x, y)
        else:
            destinos = self.mapa.despacho
        ruta = self.mapa.camino(picker.pos, destinos, self._ocupadas(picker))
        picker.ruta = list(ruta) if ruta is not None else []

    def _actualizar_pedidos(self):
        for wave in self.waves:
            en_cola = wave["picker"] is None
            for pedido in wave["pedidos"]:
                if en_cola:
                    pedido.estado = "PENDIENTE"
                    continue
                todos = True
                for item in pedido.items:
                    if not item.picked:
                        todos = False
                pedido.estado = "PREPARADO" if todos else "EN_PREPARACION"

    def _registrar(self, mensaje):
        self.log.append(f"[Tick {self.tick}] {mensaje}")
        if len(self.log) > 200:
            self.log.pop(0)

    # ---------- estado para la interfaz y partidas ----------

    def estado(self):
        pickers = []
        for p in self.pickers:
            pickers.append({
                "id": p.id,
                "posicion": p.pos,
                "anterior": p.anterior,
                "ruta": list(p.ruta),
                "estado": p.estado,
                "objetivo": p.objetivo["producto_id"] if p.objetivo else None,
                "pendientes": [t["producto_id"] for t in p.pendientes],
                "destinos": list(p.destinos),
                "recogidos": list(p.recogidos),
                "trail": list(p.trail),
                "wave_id": p.wave["id"] if p.wave else None,
                "waves_hechas": list(p.waves_hechas),
            })
        waves = []
        for w in self.waves:
            waves.append({"id": w["id"], "estado": w["estado"], "picker": w["picker"],
                          "pedidos": [pedido.id for pedido in w["pedidos"]]})
        pedidos = []
        for pedido in self.pedidos_wave:
            pedidos.append({"id": pedido.id, "estado": pedido.estado,
                            "items_picked": [item.picked for item in pedido.items]})
        return {"tick": self.tick, "terminada": self.terminada, "pickers": pickers,
                "waves": waves, "pedidos": pedidos, "log": list(self.log)}

    def restaurar(self, estado):
        self.reiniciar()
        self.tick = estado["tick"]
        self.terminada = estado["terminada"]
        self.log = list(estado.get("log", []))
        por_id = {}
        for wave in self.waves:
            wave["picker"] = None
            wave["estado"] = "CREADA"
            por_id[wave["id"]] = wave
        self.cola_waves = sorted(self.waves, key=_clave_cola)
        for picker in self.pickers:
            picker.wave = None
            picker.pendientes = []
            picker.objetivo = None
            picker.waves_hechas = []
        for guardada in estado["waves"]:
            wave = por_id.get(guardada["id"])
            if wave is None:
                continue
            wave["picker"] = guardada["picker"]
            wave["estado"] = guardada["estado"]
            if guardada["picker"] is not None:
                self.cola_waves = [w for w in self.cola_waves if w is not wave]
        for guardado in estado["pedidos"]:
            pedido = self.pedidos.get(guardado["id"])
            if pedido is None:
                continue
            for indice, picked in enumerate(guardado.get("items_picked", [])):
                if indice < len(pedido.items):
                    pedido.items[indice].picked = picked
            pedido.estado = guardado["estado"]
        guardados = {}
        for p in estado["pickers"]:
            guardados[p["id"]] = p
        for picker in self.pickers:
            g = guardados.get(picker.id)
            if g is None:
                continue
            picker.pos = tuple(g["posicion"])
            picker.anterior = tuple(g["anterior"]) if g.get("anterior") is not None else None
            picker.ruta = [tuple(c) for c in g["ruta"]]
            picker.estado = g["estado"]
            picker.trail = [tuple(c) for c in g["trail"]]
            picker.recogidos = list(g["recogidos"])
            picker.destinos = {tuple(d) for d in g.get("destinos", [])}
            picker.waves_hechas = list(g.get("waves_hechas", []))
            picker.wave = por_id.get(g["wave_id"])
            if picker.wave is not None:
                for producto_id in g["pendientes"]:
                    if producto_id in picker.wave["tareas"]:
                        picker.pendientes.append(picker.wave["tareas"][producto_id])
                picker.objetivo = picker.wave["tareas"].get(g["objetivo"])


# =====================================================================
# Persistencia provisoria (JSON simple)
# =====================================================================

def guardar_escenario(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)


def cargar_escenario(ruta):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"No se pudo leer {ruta}: {error}") from error


def guardar_partida(ruta, sim):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump({"datos": sim.datos, "estado": sim.estado()}, archivo, ensure_ascii=False)


def cargar_partida(ruta):
    contenido = cargar_escenario(ruta)
    return contenido["datos"], contenido["estado"]


# =====================================================================
# Arranque
# =====================================================================

def _instalar_modulos():
    """Registra las versiones provisorias con los nombres que importa SesionV."""
    paquete = "simulation.simulationV"
    definiciones = {
        "SimutionV": {"Simulacion": Simulacion},
        "ScenarioV": {"generar_escenario": generar_escenario,
                      "generar_pedidos": generar_pedidos,
                      "validar_escenario": validar_escenario},
        "PersistenceV": {"guardar_escenario": guardar_escenario,
                         "cargar_escenario": cargar_escenario,
                         "guardar_partida": guardar_partida,
                         "cargar_partida": cargar_partida},
    }
    for nombre, atributos in definiciones.items():
        modulo = types.ModuleType(f"{paquete}.{nombre}")
        for clave, valor in atributos.items():
            setattr(modulo, clave, valor)
        sys.modules[f"{paquete}.{nombre}"] = modulo


def main():
    parser = argparse.ArgumentParser(description="Vista previa provisoria de la interfaz")
    parser.add_argument("--escenario", type=str, default=None, help="Ruta a un escenario JSON")
    args = parser.parse_args()

    _instalar_modulos()
    import pygame
    # El paquete se deduce de la carpeta donde estén estos archivos (real, prueba, etc.).
    paquete = f"visualization.{os.path.basename(CARPETA)}"
    App = importlib.import_module(f"{paquete}.app").App

    datos = None
    if args.escenario:
        try:
            datos = cargar_escenario(args.escenario)
            validar_escenario(datos)
        except ValueError as error:
            print(f"No se pudo cargar el escenario: {error}")
            datos = None
    if datos is None:
        datos = generar_escenario()

    app = App(datos)
    pygame.display.set_caption("Wave Picking - VISTA PREVIA (simulación provisoria)")
    app.correr()
    sys.exit(0)


if __name__ == "__main__":
    main()