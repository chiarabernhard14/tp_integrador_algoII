import math
import random
import re

from domain.ProductoInaccesible import ProductoInaccesible

from .NavegationV import Navegacion
from .CargadorV import cargar_warehouse

ANCHO_PASILLO = 2
NIVELES = 3 #Esto se puede cambiar 
MODOS_UBICACION = ("aleatoria", "agrupada", "cerca_despacho")


def _ids_de_excepcion_inaccesible(mensaje):
    """Extrae los IDs de producto (p. ej. P001) del mensaje de ProductoInaccesible."""
    return sorted(set(re.findall(r"\b(P\d+)\b", mensaje)))


def generar_escenario(
    # Crea un escenario por defecto si no se lean pasado parametros para crearlo 
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
    peso_max_zona_kg=500.0,
):
    _validar_parametros(estantes, pasillos_horizontales, productos, pedidos,
                        max_productos_pedido, pickers, modo_ubicacion, alto_rack,
                        max_orders_capacity, max_products_capacity,
                        peso_max_zona_kg)
    azar = random.Random()

    warehouse = _armar_warehouse(
        estantes, pasillos_horizontales, alto_rack, peso_max_zona_kg
    )
    racks = warehouse["racks"]
    datos = {
        "warehouse": warehouse,
        "pickers": [],
        "productos": [],
        "pedidos": [],
        "configuracion": {
            "wave_max_pedidos": max_orders_capacity,
            "wave_max_productos": max_products_capacity,
        },
    }
    datos["productos"] = _crear_productos(racks, productos, modo_ubicacion, azar)
    datos["pedidos"] = _crear_pedidos(datos["productos"], pedidos, max_productos_pedido, azar)
    datos["pickers"] = _crear_pickers(pickers, datos, azar)
    validar_escenario(datos)
    return datos


def _armar_warehouse(estantes, pasillos_horizontales, alto_rack,
                     peso_max_zona_kg=500.0):
    """Layout del warehouse: racks, pasillos, puertas y zonas de despacho."""
    filas = max(1, min(pasillos_horizontales - 1, estantes))
    columnas = -(-estantes // filas)
    filas = -(-estantes // columnas)
    paso_x = 2 + ANCHO_PASILLO
    ancho_x = max(columnas * paso_x + ANCHO_PASILLO, 8)
    largo_y = 5 + filas * (alto_rack + 2)

    racks = _crear_racks(estantes, columnas, alto_rack)
    warehouse = {
        "dimensiones": {"ancho_x": ancho_x, "largo_y": largo_y},
        "puertas": [],
        "zonas_despacho": [],
        "racks": racks,
        "pasillos": _crear_pasillos(racks, filas, ancho_x, alto_rack),
    }
    _crear_despacho(warehouse, ancho_x, peso_max_zona_kg)
    return warehouse


def generar_vista_previa(estantes, pasillos_horizontales, alto_rack, productos,
                         pickers, modo_ubicacion, semilla=7,
                         peso_max_zona_kg=500.0):
    """Layout y ubicaciones de ejemplo para la pantalla de generar escenario.

    Es determinista (misma semilla), no arma el grafo ni valida alcanzabilidad,
    así que se puede recalcular cada vez que cambia un parámetro. Si hay más
    productos que ubicaciones, se muestran solo los que entran.
    """
    if estantes < 1 or pasillos_horizontales < 2 or alto_rack < 2:
        raise ValueError("Parámetros del warehouse inválidos.")
    if modo_ubicacion not in MODOS_UBICACION:
        raise ValueError(f"Modo de ubicacion invalido: {modo_ubicacion}.")
    _validar_peso_zona(peso_max_zona_kg)

    azar = random.Random(semilla)
    warehouse = _armar_warehouse(
        estantes, pasillos_horizontales, alto_rack, peso_max_zona_kg
    )
    capacidad = estantes * 2 * alto_rack * NIVELES
    cantidad = max(0, min(productos, capacidad))
    lista_productos = _crear_productos(
        warehouse["racks"], cantidad, modo_ubicacion, azar
    )

    celdas = set()
    for pasillo in warehouse["pasillos"]:
        x0 = pasillo["ubicacion"]["x"]
        y0 = pasillo["ubicacion"]["y"]
        for x in range(x0, x0 + pasillo["ancho"]):
            for y in range(y0, y0 + pasillo["alto"]):
                celdas.add((x, y))
    elegidas = azar.sample(sorted(celdas), min(pickers, len(celdas)))
    lista_pickers = [
        {"id": f"PK_{i + 1:02d}", "posicion_inicial": {"x": x, "y": y}}
        for i, (x, y) in enumerate(elegidas)
    ]
    return {
        "warehouse": warehouse,
        "productos": lista_productos,
        "pickers": lista_pickers,
    }


def _validar_parametros(estantes, pasillos_h, productos, pedidos, max_prod, pickers, modo, alto,
                        max_orders, max_products, peso_max_zona_kg):
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
    _validar_peso_zona(peso_max_zona_kg)
    if modo not in MODOS_UBICACION:
        raise ValueError(f"Modo de ubicacion invalido: {modo}.")
    capacidad = estantes * 2 * alto * NIVELES
    if productos > capacidad:
        raise ValueError(f"Con {estantes} estantes solo entran {capacidad} productos.")


def _validar_peso_zona(peso_max_zona_kg):
    if (not isinstance(peso_max_zona_kg, (int, float))
            or isinstance(peso_max_zona_kg, bool)
            or not math.isfinite(peso_max_zona_kg)
            or peso_max_zona_kg <= 0):
        raise ValueError("El peso máximo por zona debe ser un número mayor a 0 kg.")


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


def _crear_despacho(warehouse, ancho_x, peso_max_zona_kg=500.0):
    ancho_zona = min(5, ancho_x - 2)

    posiciones = [("1", 1)]

    if ancho_x >= 16:
        posiciones.append(("2", ancho_x - 1 - ancho_zona))

    for numero, x_zona in posiciones:
        id_puerta = f"PUERTA_{numero}"

        # La puerta queda en el borde superior del almacén.
        warehouse["puertas"].append({
            "id": id_puerta,
            "tipo": "AMBOS",
            "ubicacion": {
                "x": x_zona + ancho_zona // 2,
                "y": 0,
            },
        })

        # La zona comienza en y=1.
        # La puerta queda fuera de la zona, justo arriba.
        warehouse["zonas_despacho"].append({
            "id": f"ZONA_{numero}",
            "puerta_id": id_puerta,
            "ubicacion": {
                "x": x_zona,
                "y": 1,
            },
            "ancho": ancho_zona,
            "alto": 2,
            "peso_max_kg": peso_max_zona_kg,
        })


def _crear_pickers(cantidad, datos, azar):
    """Ubica a cada picker en una celda transitable distinta del warehouse.

    Se usa el grafo real de circulación para que la posición inicial sea
    siempre una celda de pasillo alcanzable, sin importar el layout.
    """
    datos["pickers"] = []
    warehouse = cargar_warehouse(datos)
    if not warehouse.graph:
        warehouse.build_reduced_graph_v2()
    celdas = sorted(warehouse.graph)
    if cantidad > len(celdas):
        raise ValueError(
            f"El almacén solo tiene {len(celdas)} celdas transitables "
            f"para {cantidad} pickers."
        )
    elegidas = azar.sample(celdas, cantidad)
    return [
        {
            "id": f"PK_{i + 1:02d}",
            "posicion_inicial": {"x": x, "y": y},
            "capacidad_carga_kg": float(azar.choice((100, 150, 200))),
        }
        for i, (x, y) in enumerate(elegidas)
    ]


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

    if modo == "agrupada":
        elegidas = []
        for del_rack in posiciones:
            elegidas.extend(del_rack)
    else:
        elegidas = []
        for del_rack in posiciones:
            elegidas.extend(del_rack)
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
            items.append({
                "producto_id": producto["id"],
                "cantidad": unidades,
            })
        pedidos.append({
            "id": f"PED_{i + 1:02d}",
            "prioridad": azar.randint(1, 5),
            "estado": "PENDIENTE",
            "items": items,
        })
    return pedidos

def generar_pedidos(productos, cantidad=8, max_productos_pedido=4):
    """Pedidos al azar sobre una lista de productos (la usa el editor de mapa)."""
    return _crear_pedidos(productos, cantidad, max_productos_pedido, random.Random())

def _verificar_alcanzables(warehouse):
    nav = Navegacion(warehouse)
    if not nav.despacho:
        raise ValueError("Ninguna celda de pasillo es adyacente a una zona de despacho.")
    origen = next(iter(nav.despacho))
    for producto in warehouse.productos.values():
        accesos = nav.accesos(producto.ubicacion[0], producto.ubicacion[1])
        if nav.camino(origen, accesos) is None:
            raise ValueError(f"{producto.id} no es alcanzable desde el despacho.")
        vuelta = None
        for acceso in accesos:
            vuelta = nav.camino(acceso, nav.despacho)
            if vuelta is not None:
                break
        if vuelta is None:
            raise ValueError(f"No hay camino de regreso desde {producto.id} al despacho.")
    for picker in warehouse.pickers.values():
        pos = (picker.posicion[0], picker.posicion[1])
        if pos not in nav.vecinos:
            raise ValueError(f"{picker.id} no esta sobre una celda de pasillo.")

def validar_escenario(datos):
    """Valida un escenario generado, cargado o editado: estructura (Warehouse) y alcanzabilidad.

    Los productos inaccesibles no detienen el escenario: se registran en
    datos["productos_inaccesibles"] para que la capa superior muestre el
    cartel y los excluya de los viajes, pero el escenario sigue ejecutándose.
    """
    try:
        warehouse = cargar_warehouse(datos)
    except (KeyError, TypeError) as error:
        raise ValueError(f"Escenario inválido: {type(error).__name__}: {error}") from error

    # Construir el grafo (ejecuta bloquear_pasillos_sin_salida y valida
    # accesos). build_graph sigue tirando ProductoInaccesible cuando hay
    # productos sin camino al despacho: la capturamos acá, mostramos el
    # mensaje y guardamos los IDs para que el escenario siga ejecutándose
    # en vez de cortarse.
    inaccesibles = []
    mensaje_inaccesibles = ""
    try:
        warehouse.build_graph()
    except ProductoInaccesible as error:
        mensaje_inaccesibles = str(error)
        inaccesibles = _ids_de_excepcion_inaccesible(str(error))
    else:
        try:
            inaccesibles = _verificar_alcanzables(warehouse)
        except ProductoInaccesible as error:
            mensaje_inaccesibles = str(error)
            inaccesibles = _ids_de_excepcion_inaccesible(str(error))

    if inaccesibles:
        datos["productos_inaccesibles"] = sorted(inaccesibles)
        datos["mensaje_inaccesibles"] = mensaje_inaccesibles
    else:
        datos.pop("productos_inaccesibles", None)
        datos.pop("mensaje_inaccesibles", None)
