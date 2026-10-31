class Wave:

    def __init__(self, id="", orders=None, max_orders_capacity=0, max_products_capacity=0, locations_to_visit=None, route=None, status="CREADA",products=None):
        self.id = id
        self.orders = list(orders) if orders is not None else []
        self.max_orders_capacity = max_orders_capacity
        self.max_products_capacity = max_products_capacity
        self.locations_to_visit = list(locations_to_visit) if locations_to_visit is not None else []
        self.route = list(route) if route is not None else []
        self.status = status
        self.products = list(products) if products is not None else []
        
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
    def products(self):
        return self._products

    @products.setter
    def products(self, value):
        if not isinstance(value, list):
            raise TypeError("products debe ser una lista.")
        for item in value:
            self._validar_registro_producto(item)
        self._products = value

    @staticmethod
    def _validar_registro_producto(item):
        if not isinstance(item, dict):
            raise TypeError("Cada registro de products debe ser un diccionario.")
        if not {"order", "product", "quantity"}.issubset(item):
            raise ValueError("Cada registro requiere order, product y quantity.")
        cantidad = item["quantity"]
        if not isinstance(cantidad, int) or isinstance(cantidad, bool):
            raise TypeError("quantity debe ser un entero.")
        if cantidad <= 0:
            raise ValueError("quantity debe ser mayor a cero.")
        if item["order"] is None or item["product"] is None:
            raise ValueError("order y product no pueden ser nulos.")

    @property
    def max_orders_capacity(self):
        return self._max_orders_capacity

    @max_orders_capacity.setter
    def max_orders_capacity(self, value):
        self._validar_capacidad(value, "max_orders_capacity")
        self._max_orders_capacity = value

    @property
    def max_products_capacity(self):
        return self._max_products_capacity

    @max_products_capacity.setter
    def max_products_capacity(self, value):
        self._validar_capacidad(value, "max_products_capacity")
        self._max_products_capacity = value

    @staticmethod
    def _validar_capacidad(value, nombre):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{nombre} debe ser un entero.")
        if value < 0:
            raise ValueError(f"{nombre} no puede ser negativo.")

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
        estados = {"CREADA", "EN_PROCESO", "COMPLETADA", "CANCELADA"}
        if not isinstance(value, str):
            raise TypeError("El estado debe ser una cadena.")
        normalizado = value.strip().upper()
        if normalizado not in estados:
            raise ValueError(f"Estado no válido: {value}.")
        self._status = normalizado

    def add_order(self, order):
        if order is None:
            raise ValueError("No se puede agregar un pedido nulo.")
        if any(o.id == order.id for o in self.orders):
            return
        if self.max_orders_capacity > 0 and len(self.orders) >= self.max_orders_capacity:
            raise ValueError("Capacidad máxima de pedidos alcanzada.")
        self.orders.append(order)

    def add_product(self, order, product, quantity):
        registro = {"order": order, "product": product, "quantity": quantity}
        self._validar_registro_producto(registro)

        ya_incluido = any(o.id == order.id for o in self.orders)
        if (
            not ya_incluido
            and self.max_orders_capacity > 0
            and len(self.orders) >= self.max_orders_capacity
        ):
            raise ValueError("Capacidad máxima de pedidos alcanzada.")

        unidades_actuales = sum(item["quantity"] for item in self.products)
        if (
            self.max_products_capacity > 0
            and unidades_actuales + quantity > self.max_products_capacity
        ):
            raise ValueError("Capacidad máxima de unidades alcanzada.")

        # Validar todo antes de modificar el objeto.
        if not ya_incluido:
            self.orders.append(order)
        self.products.append(registro)

    def __repr__(self):
        unidades = sum(item["quantity"] for item in self.products)
        return (
            f"Wave(id='{self.id}', orders={len(self.orders)}, "
            f"products={len(self.products)}, units={unidades}, "
            f"status='{self.status}')")
