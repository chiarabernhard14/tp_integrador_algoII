class Warehouse:
    """
    Modela la estructura física global del almacén e integra todos sus componentes.
    """

    def __init__(self, graph=None, aisles=None, racks=None, products=None,
                 dispatch_zones=None, doors=None, docks=None):
        self.graph = graph if graph is not None else {}
        self.aisles = aisles if aisles is not None else {}
        self.racks = racks if racks is not None else {}
        self.products = products if products is not None else {}
        self.dispatch_zones = dispatch_zones if dispatch_zones is not None else {}
        
        if docks is not None:
            self.doors = docks
        elif doors is not None:
            self.doors = doors
        else:
            self.doors = {}

    # --- Properties and Setters ---

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("El grafo debe ser un diccionario o lista de adyacencia.")
        self._graph = value

    @property
    def aisles(self):
        return self._aisles

    @aisles.setter
    def aisles(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("aisles debe ser un diccionario o lista de pasillos.")
        self._aisles = value

    @property
    def racks(self):
        return self._racks

    @racks.setter
    def racks(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("racks debe ser un diccionario o lista de estanterías.")
        self._racks = value

    @property
    def products(self):
        return self._products

    @products.setter
    def products(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("products debe ser un diccionario o lista de productos.")
        self._products = value

    @property
    def dispatch_zones(self):
        return self._dispatch_zones

    @dispatch_zones.setter
    def dispatch_zones(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("dispatch_zones debe ser un diccionario o lista de zonas de despacho.")
        self._dispatch_zones = value

    @property
    def doors(self):
        return self._doors

    @doors.setter
    def doors(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError("doors debe ser un diccionario o lista.")
        self._doors = value

    @property
    def docks(self):
        return self._doors

    @docks.setter
    def docks(self, value):
        self.doors = value

    def __repr__(self):
        return (f"Warehouse(aisles={len(self.aisles)}, racks={len(self.racks)}, "
                f"products={len(self.products)}, dispatch_zones={len(self.dispatch_zones)})")
