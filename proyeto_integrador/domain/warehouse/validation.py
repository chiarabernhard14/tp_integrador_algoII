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
