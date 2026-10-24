"""Generador sencillo: agrupa pedidos por cercanía y luego asigna pickers.

La distancia es la mínima entre accesos de los productos, calculada con
Dijkstra sobre el grafo del almacén. No ejecuta movimientos ni cambia stock.
"""
from collections import defaultdict
from domain.Entradas.OrderE import Order
from domain.validation import validate_non_negative_int, validate_positive_int
from .CargadorV import cargar_warehouse
from .NavegationV import Navegacion
from .ServiciosNavegacionGenerador import _crear_servicios_navegacion
from .ConstruccionWaves import _construir_waves_intermedias
from .AsignacionPickers import _asignar_pickers_a_waves


def _validar_limite(config, clave, cero_sin_limite=False):
    """Valida un límite configurable y devuelve infinito si se desactiva con 0."""
    valor = config.get(clave)
    if valor is None:
        return float("inf")
    if cero_sin_limite:
        validate_non_negative_int(valor, clave)
        return float("inf") if valor == 0 else valor
    validate_positive_int(valor, clave)
    return valor


def _validar_numero_positivo(valor, nombre):
    """Valida pesos/capacidades, para los que no hay un validador genérico existente."""
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        raise TypeError(f"{nombre} debe ser un valor numérico.")
    if valor <= 0:
        raise ValueError(f"{nombre} debe ser mayor a 0.")


def _validar_pedidos(pedidos):
    """Comprueba el contrato de pedidos y devuelve el índice por identificador."""
    por_id = {}
    for pedido in pedidos:
        if not isinstance(pedido, Order):
            raise TypeError("Cada pedido debe ser una instancia de Order")
        clave_id = pedido.id.upper()
        if clave_id in por_id:
            raise ValueError("IDs de pedidos duplicados")
        por_id[clave_id] = pedido
        for item in pedido.items:
            validate_positive_int(item.cantidad, "La cantidad de unidades")
    return por_id


def _validar_productos(productos_datos):
    """Valida el catálogo de productos y devuelve un índice por ID."""
    productos = {producto["id"]: producto for producto in productos_datos}
    if len(productos) != len(productos_datos):
        raise ValueError("IDs de productos duplicados")
    for producto in productos.values():
        _validar_numero_positivo(producto.get("peso_kg", 0), "Peso")
        validate_non_negative_int(producto.get("cantidad_disponible", 0), "Stock")
    return productos


def _validar_pickers(pickers_datos):
    """Valida y ordena los pickers para que las decisiones sean deterministas."""
    pickers = sorted(pickers_datos, key=lambda picker: str(picker["id"]))
    if not pickers:
        raise ValueError("No hay pickers")
    for picker in pickers:
        _validar_numero_positivo(
            picker.get("capacidad_carga_kg", 0), "Capacidad de carga"
        )
    return pickers


def _preparar_tareas(pedidos, productos):
    """Reserva stock lógicamente por prioridad y prepara cantidades planificables."""
    stock_restante = {
        producto_id: producto["cantidad_disponible"]
        for producto_id, producto in productos.items()
    }
    tareas = []
    for pedido in sorted(pedidos, key=lambda p: (-p.prioridad, p.id)):
        for item in pedido.items:
            producto_id = item.producto_id
            if producto_id not in productos:
                continue
            cantidad = min(item.cantidad, stock_restante[producto_id])
            if cantidad > 0:
                tareas.append({
                    "pedido_id": pedido.id,
                    "prioridad": pedido.prioridad,
                    "producto_id": producto_id,
                    "restante": cantidad,
                })
                stock_restante[producto_id] -= cantidad
    return tareas


def generar_waves(datos):
    """Genera waves deterministas mediante vecino más cercano global.

    Valida y prepara los datos, construye las waves por prioridad y asigna
    los productos a los pickers. No modifica los pedidos ni el stock original.
    """
    config = datos.get("configuracion", {})
    pedidos = list(datos["pedidos"])
    objetos_pedido_por_id = _validar_pedidos(pedidos)
    max_pedidos = _validar_limite(config, "wave_max_pedidos", cero_sin_limite=True)
    max_unidades = _validar_limite(config, "wave_max_productos", cero_sin_limite=True)
    productos = _validar_productos(datos["productos"])
    pickers = _validar_pickers(datos["pickers"])
    tareas = _preparar_tareas(pedidos, productos)
    if not tareas:
        return []

    datos_warehouse = {**datos, "pedidos": []}
    almacen = cargar_warehouse(datos_warehouse)
    navegacion = Navegacion(almacen)
    despacho = sorted(navegacion.despacho)
    if not despacho:
        raise ValueError("Navegación no proporcionó acceso al despacho")

    servicios = _crear_servicios_navegacion(
        navegacion, productos, tareas, pickers, despacho
    )
    waves_intermedias = _construir_waves_intermedias(
        tareas=tareas,
        productos=productos,
        pickers=pickers,
        max_pedidos=max_pedidos,
        max_unidades=max_unidades,
        accesos=servicios["accesos"],
        despacho=despacho,
        posiciones_iniciales=servicios["posiciones_iniciales"],
        distancia=servicios["distancia"],
        distancia_productos=servicios["distancia_productos"],
        accesible_desde_un_origen=servicios["accesible_desde_un_origen"],
        existe_secuencia_factible=servicios["existe_secuencia_factible"],
    )
    return _asignar_pickers_a_waves(
        waves_intermedias=waves_intermedias,
        productos=productos,
        pickers=pickers,
        max_pedidos=max_pedidos,
        max_unidades=max_unidades,
        objetos_pedido_por_id=objetos_pedido_por_id,
        distancia=servicios["distancia"],
        accesos=servicios["accesos"],
        despacho=despacho,
        calcular_recorrido=servicios["calcular_recorrido"],
    )


def generar_plan_waves(datos):
    """Devuelve las waves, cantidades pendientes y un resumen de planificación.

    ``datos["pedidos"]`` debe contener objetos ``Order``. Los pedidos originales
    se consultan directamente y no se modifican durante la planificación.
    """
    pedidos = list(datos["pedidos"])
    if any(not isinstance(pedido, Order) for pedido in pedidos):
        raise TypeError("Cada pedido debe ser una instancia de Order")

    waves = generar_waves(datos)
    solicitadas, planificadas = defaultdict(int), defaultdict(int)
    productos = {p["id"]: p for p in datos["productos"]}
    for pedido in pedidos:
        for item in pedido.items:
            solicitadas[(pedido.id, item.producto_id)] += item.cantidad
    for wave in waves:
        for asignacion in wave["picker_assignments"]:
            for pedido_id, pid, q in asignacion["items"]:
                planificadas[(pedido_id, pid)] += q
    pendientes = []
    for (pedido_id, pid), q in sorted(solicitadas.items()):
        falta = q - planificadas[(pedido_id, pid)]
        if falta > 0:
            motivo = ("producto_inexistente" if pid not in productos else
                      ("sin_stock" if productos[pid]["cantidad_disponible"] == 0 else "stock_insuficiente"))
            pendientes.append({"pedido_id": pedido_id, "producto_id": pid,
                               "cantidad": falta, "motivo": motivo})
    return {"waves": waves, "pendientes": pendientes,
            "resumen": {"waves_generadas": len(waves),
                        "unidades_solicitadas": sum(solicitadas.values()),
                        "unidades_planificadas": sum(planificadas.values()),
                        "unidades_pendientes": sum(p["cantidad"] for p in pendientes)}}
