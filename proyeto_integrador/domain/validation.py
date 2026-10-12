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
    if not all(isinstance(coord, int) for coord in value):
        raise TypeError("Las coordenadas deben ser enteros.")
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
