VISITAR_NODO = "visitar_nodo"            # datos: nodo
RECORRER_ARISTA = "recorrer_arista"      # datos: origen, destino, peso
ELEGIR_SIGUIENTE = "elegir_siguiente"    # datos: candidato, distancia
RECOGER_PRODUCTO = "recoger_producto"    # datos: nodo, producto


class Evento:
    def __init__(self, tipo, **datos):
        self.tipo = tipo
        self.datos = datos

    def describir(self):
        if self.tipo == VISITAR_NODO:
            return f"Visita el nodo {self.datos['nodo']}"
        if self.tipo == RECORRER_ARISTA:
            return (f"Recorre {self.datos['origen']} -> {self.datos['destino']} "
                    f"(peso {self.datos['peso']})")
        if self.tipo == ELEGIR_SIGUIENTE:
            return (f"Elige como siguiente el nodo {self.datos['candidato']} "
                    f"(distancia {self.datos['distancia']})")
        if self.tipo == RECOGER_PRODUCTO:
            return f"Recoge {self.datos['producto']} en el nodo {self.datos['nodo']}"
        return self.tipo