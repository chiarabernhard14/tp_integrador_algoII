class Wave:
    """
    Representa el conjunto agrupado de pedidos pendientes que se procesarán y prepararán en un mismo recorrido.
    """

    def __init__(self, id="", orders=None, max_orders_capacity=0, max_products_capacity=0,
                 locations_to_visit=None, route=None, status="CREADA"):
        self.id = id
        self.orders = orders if orders is not None else []
        self.max_orders_capacity = max_orders_capacity
        self.max_products_capacity = max_products_capacity
        self.locations_to_visit = locations_to_visit if locations_to_visit is not None else []
        self.route = route if route is not None else []
        self.status = status

    # --- Properties and Setters ---

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if not isinstance(value, (int, str)):
            raise TypeError("El ID de la ola (Wave) debe ser un entero o una cadena de texto.")
        self._id = str(value)

    @property
    def orders(self):
        return self._orders

    @orders.setter
    def orders(self, value):
        if not isinstance(value, list):
            raise TypeError("orders debe ser una lista.")
        self._orders = value

    @property
    def max_orders_capacity(self):
        return self._max_orders_capacity

    @max_orders_capacity.setter
    def max_orders_capacity(self, value):
        if not isinstance(value, int):
            raise TypeError("max_orders_capacity debe ser un número entero.")
        if value < 0:
            raise ValueError("max_orders_capacity no puede ser negativo.")
        self._max_orders_capacity = value

    @property
    def max_products_capacity(self):
        return self._max_products_capacity

    @max_products_capacity.setter
    def max_products_capacity(self, value):
        if not isinstance(value, int):
            raise TypeError("max_products_capacity debe ser un número entero.")
        if value < 0:
            raise ValueError("max_products_capacity no puede ser negativo.")
        self._max_products_capacity = value

    @property
    def locations_to_visit(self):
        return self._locations_to_visit

    @locations_to_visit.setter
    def locations_to_visit(self, value):
        if not isinstance(value, list):
            raise TypeError("locations_to_visit debe ser una lista.")
        self._locations_to_visit = value

    @property
    def route(self):
        return self._route

    @route.setter
    def route(self, value):
        if not isinstance(value, list):
            raise TypeError("route debe ser una lista.")
        self._route = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        valid_statuses = {"CREADA", "EN_PROCESO", "COMPLETADA", "CANCELADA"}
        if not isinstance(value, str):
            raise TypeError("El estado debe ser una cadena de texto.")
        normalized = value.strip().upper()
        if normalized not in valid_statuses:
            raise ValueError(f"Estado '{value}' no válido. Opciones permitidas: {', '.join(sorted(valid_statuses))}.")
        self._status = normalized

    def add_order(self, order):
        if order is None:
            raise ValueError("No se puede agregar un pedido nulo.")
        if self._max_orders_capacity > 0 and len(self._orders) >= self._max_orders_capacity:
            raise ValueError(f"Capacidad máxima de pedidos alcanzada ({self._max_orders_capacity}).")
        self._orders.append(order)

    def __repr__(self):
        return (f"Wave(id='{self.id}', orders={len(self.orders)}, "
                f"max_orders={self.max_orders_capacity}, max_products={self.max_products_capacity}, "
                f"status='{self.status}')")
