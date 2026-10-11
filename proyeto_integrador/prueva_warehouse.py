from domain.warehouse.Aisle2 import Aisle
from domain.warehouse.Rack2 import Rack
from domain.warehouse.LinearElement import LinearElement


def probar(nombre, funcion, *args):
    try:
        funcion(*args)
        print(nombre, "-> ACEPTADO")
    except (ValueError, TypeError, AttributeError) as e:
        print(nombre, "-> rechazado:", type(e).__name__, "-", e)


a = Aisle((0, 5), (10, 5))
print("1.", a, "| largo:", a.length, "|", a.direction, "| celdas:", len(a.cells()))

b = Aisle((5, 10), (5, 0))
print("2.", b, "| largo:", b.length, "|", b.direction)

probar("3. diagonal", Aisle, (0, 0), (2, 3))
probar("4. largo cero", Aisle, (4, 4), (4, 4))
probar("5. nodos None", Aisle, None, None)
probar("6. coordenadas no enteras", Aisle, (0, 0), (0, 2.5))
probar("7. cambiar un nodo", setattr, a, "start_node", (1, 1))
probar("8. cambiar la dirección", setattr, a, "direction", "VERTICAL")

r = Rack((2, 6), (2, 9))
print("9.", r, "| es LinearElement:", isinstance(r, LinearElement), "| capacity:", r.capacity)
print("10. celdas:", r.cells())