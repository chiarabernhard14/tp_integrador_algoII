def validate_positive_int(value, property="El valor"):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{property} debe ser un entero.")
    if value <= 0:
        raise ValueError(f"{property} debe ser mayor a 0.")
    return True

def validate_non_negative_int(value, property="El valor"):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{property} debe ser un entero.")
    if value < 0:
        raise ValueError(f"{property} debe ser mayor o igual a 0.")
    return True

def validate_coordinates(value, cantidad=2):
    if not isinstance(value, tuple) or len(value) != cantidad:
        raise TypeError(f"Debe ser una tupla de {cantidad} coordenadas.")
    for coord in value:
        validate_non_negative_int(coord)
    return True

def validate_start_end(value, second_node):
    validate_coordinates(value)
    validate_coordinates(second_node)

    if second_node[0] == value[0]:
        if second_node[1]>value[1]:
            return value, second_node
        else:
            return second_node, value

    if second_node[1] == value[1]:
        if second_node[0]>value[0]:
            return value, second_node
        else:
            return second_node, value

    raise ValueError("La posición de comienzo y fin debe estar en la misma fila o columna.")

# esto lo podemos sacar 
def validate_segment(start_node, end_node):
    start, end = validate_start_end(start_node, end_node)
    if start == end:
        raise ValueError("El segmento debe tener largo mayor que cero.")
    return start, end

#comentario 


# Reglas geométricas compartidas por el dominio y el editor de mapas.
# Trabajan con rectángulos (x, y, ancho, alto) expresados en celdas.
def point_in_rect(px, py, x, y, ancho, alto):
    """True si el punto cae dentro del rectángulo (borde superior/izquierdo incluido)."""
    return x <= px < x + ancho and y <= py < y + alto


def rects_overlap(ax, ay, aw, ah, bx, by, bw, bh):
    """True si dos rectángulos se superponen en al menos una celda."""
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def rect_contains(ox, oy, ow, oh, ix, iy, iw, ih):
    """True si el rectángulo interior queda completamente dentro del exterior."""
    return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh


def same_rect(ax, ay, aw, ah, bx, by, bw, bh):
    """True si ambos rectángulos tienen la misma posición y tamaño."""
    return ax == bx and ay == by and aw == bw and ah == bh


def point_inside_bounds(px, py, ancho, largo):
    """True si el punto está dentro de los límites del warehouse."""
    return 0 <= px < ancho and 0 <= py < largo


def inside_bounds(x, y, ancho_rect, alto_rect, ancho, largo):
    """True si el rectángulo entra completo y tiene tamaño positivo."""
    return (
        ancho_rect >= 1
        and alto_rect >= 1
        and x >= 0
        and y >= 0
        and x + ancho_rect <= ancho
        and y + alto_rect <= largo
    )


def on_border(x, y, ancho, largo):
    """True si la celda está sobre el borde del warehouse."""
    return x == 0 or x == ancho - 1 or y == 0 or y == largo - 1


def rack_side_ok(ancho, alto):
    """Un rack siempre tiene uno de sus dos lados igual a 2."""
    return ancho == 2 or alto == 2


def rack_clearance_error(x, y, ancho_rect, alto_rect, ancho, largo):
    """Devuelve el motivo si el rack no tiene una celda libre en sus caras largas."""
    if ancho_rect == 2 and (x < 1 or x + ancho_rect >= ancho):
        return "El rack necesita espacio libre a ambos lados para acceder a sus productos"
    if ancho_rect != 2 and (y < 1 or y + alto_rect >= largo):
        return "El rack necesita espacio libre a ambos lados para acceder a sus productos"
    return ""


def border_cells(x, y, ancho_rect, alto_rect, ancho, largo):
    """Celdas del rectángulo que también están sobre el borde del warehouse."""
    return {
        (cx, cy)
        for cx in range(x, x + ancho_rect)
        for cy in range(y, y + alto_rect)
        if on_border(cx, cy, ancho, largo)
    }


def adjacent_cells(x, y, ancho_rect, alto_rect, ancho, largo):
    """Celdas vecinas por fuera del rectángulo, recortadas al warehouse."""
    resultado = set()
    for cx in range(x, x + ancho_rect):
        resultado.update(((cx, y - 1), (cx, y + alto_rect)))
    for cy in range(y, y + alto_rect):
        resultado.update(((x - 1, cy), (x + ancho_rect, cy)))
    return {
        (cx, cy)
        for cx, cy in resultado
        if point_inside_bounds(cx, cy, ancho, largo)
    }
