"""Formulario (tkinter) para generar un escenario, con el mismo estilo que la
interfaz de pygame: paleta oscura, tarjetas, azul de acento y todo redondeado.

tkinter no trae widgets redondeados, así que cada uno se dibuja sobre un
Canvas (rectángulo con esquinas curvas) y se le coloca encima lo necesario.

Uso:
    valores = pedir_parametros_generacion()
    if valores is not None:
        datos = generar_escenario(**valores)

Devuelve un dict con las claves de generar_escenario, o None si se cancela.
"""

import tkinter as tk
from tkinter import font as tkfont

FONDO = "#2c3038"
TARJETA = "#3c414c"
BORDE = "#5a606e"
TEXTO = "#e2e8f5"
APAGADO = "#8b96b0"
ACENTO = "#58a6ff"
OSCURO = "#0b1220"
ROJO = "#ef4444"
VERDE = "#16a34a"
VERDE_HOVER = "#34c168"
GRIS = "#4b5263"
GRIS_HOVER = "#646e82"
FLECHA = "#4b5263"
FLECHA_HOVER = "#6b7690"

FUENTE = "Segoe UI"
MARGEN_TARJETA = 16

MODOS = {
    "Aleatoria": "aleatoria",
    "Agrupada": "agrupada",
    "Cerca despacho": "cerca_despacho",
}

# (titulo, columna, fila, con_modo, campos)
# campo = (clave de generar_escenario, etiqueta, valor inicial, minimo, maximo)
SECCIONES = (
    ("ALMACEN", 0, 0, False, (
        ("estantes", "Estantes", 6, 1, 60),
        ("pasillos_horizontales", "Pasillos horizontales", 2, 2, 10),
        ("alto_rack", "Alto de cada rack", 6, 2, 12),
    )),
    ("PICKERS", 0, 1, False, (
        ("pickers", "Cantidad de pickers", 2, 1, 12),
    )),
    ("PRODUCTOS Y PEDIDOS", 1, 0, True, (
        ("productos", "Productos", 20, 1, 500),
        ("pedidos", "Pedidos", 8, 1, 200),
        ("max_productos_pedido", "Items maximos por pedido", 4, 1, 10),
    )),
    ("WAVE ", 1, 1, False, (
        ("max_orders_capacity", "Pedidos maximos por wave", 3, 0, 50),
        ("max_products_capacity", "Productos maximos por wave", 15, 0, 200),
    )),
)


def _rect_redondeado(lienzo, x1, y1, x2, y2, radio, **opciones):
    """Dibuja un rectángulo de esquinas redondeadas en un Canvas."""
    puntos = [
        x1 + radio, y1, x1 + radio, y1,
        x2 - radio, y1, x2 - radio, y1,
        x2, y1, x2, y1 + radio,
        x2, y1 + radio, x2, y2 - radio,
        x2, y2 - radio, x2, y2,
        x2 - radio, y2, x2 - radio, y2,
        x1 + radio, y2, x1 + radio, y2,
        x1, y2, x1, y2 - radio,
        x1, y2 - radio, x1, y1 + radio,
        x1, y1 + radio, x1, y1,
    ]
    return lienzo.create_polygon(puntos, smooth=True, **opciones)


class Tarjeta(tk.Canvas):
    """Panel redondeado. Los campos van dentro de self.interior (con grid)."""

    def __init__(self, padre, titulo):
        super().__init__(padre, bg=FONDO, highlightthickness=0, bd=0)
        self.interior = tk.Frame(self, bg=TARJETA)
        self.create_window(MARGEN_TARJETA, MARGEN_TARJETA, window=self.interior, anchor="nw")
        tk.Label(self.interior, text=titulo, font=(FUENTE, 9, "bold"), fg=APAGADO,
                 bg=TARJETA).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

    def finalizar(self):
        """Se llama cuando ya se agregaron todos los campos: ajusta el tamaño y dibuja el fondo."""
        self.update_idletasks()
        ancho = self.interior.winfo_reqwidth() + 2 * MARGEN_TARJETA
        alto = self.interior.winfo_reqheight() + 2 * MARGEN_TARJETA
        self.config(width=ancho, height=alto)
        forma = _rect_redondeado(self, 1, 1, ancho - 1, alto - 1, 18,
                                 fill=TARJETA, outline=BORDE, width=1)
        self.tag_lower(forma)


class CampoNumero(tk.Canvas):
    """Campo de texto redondeado con dos flechas (subir/bajar) amplias y separadas del borde."""

    ANCHO = 128
    ALTO = 38

    def __init__(self, padre, variable, minimo, maximo, fondo=TARJETA):
        super().__init__(padre, width=self.ANCHO, height=self.ALTO, bg=fondo,
                         highlightthickness=0, bd=0)
        self.variable = variable
        self.minimo = minimo
        self.maximo = maximo
        self.direccion = 1
        self.repeticion = None

        self.borde = _rect_redondeado(self, 1, 1, self.ANCHO - 1, self.ALTO - 1, 12,
                                      fill=FONDO, outline=BORDE, width=1)

        self.entrada = tk.Entry(
            self, textvariable=variable, bd=0, relief="flat", highlightthickness=0,
            bg=FONDO, fg=TEXTO, insertbackground=TEXTO,
            selectbackground=ACENTO, selectforeground=OSCURO,
            justify="center", font=(FUENTE, 11))
        self.create_window(14, self.ALTO // 2, window=self.entrada, anchor="w",
                           width=self.ANCHO - 14 - 46, height=24)

        # Flechas: 28x12 px, a 10 px del borde derecho y 6 px del superior/inferior.
        x1 = self.ANCHO - 38
        x2 = self.ANCHO - 10
        self.fondo_subir = _rect_redondeado(self, x1, 6, x2, 18, 5, fill=FLECHA,
                                            outline="", tags=("subir",))
        self.fondo_bajar = _rect_redondeado(self, x1, 20, x2, 32, 5, fill=FLECHA,
                                            outline="", tags=("bajar",))
        cx = self.ANCHO - 24
        self.create_polygon(cx, 9, cx - 4, 15, cx + 4, 15, fill=TEXTO, outline="",
                            tags=("subir",))
        self.create_polygon(cx, 29, cx - 4, 23, cx + 4, 23, fill=TEXTO, outline="",
                            tags=("bajar",))

        for etiqueta in ("subir", "bajar"):
            self.tag_bind(etiqueta, "<Enter>", self._entrar_flecha)
            self.tag_bind(etiqueta, "<Leave>", self._salir_flecha)
            self.tag_bind(etiqueta, "<ButtonPress-1>", self._presionar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<MouseWheel>", self._rueda)

        self.entrada.bind("<FocusIn>", self._foco_entrada)
        self.entrada.bind("<FocusOut>", self._foco_salida)
        self.entrada.bind("<Up>", self._tecla_arriba)
        self.entrada.bind("<Down>", self._tecla_abajo)
        self.entrada.bind("<MouseWheel>", self._rueda)

    # ---------- flechas ----------

    def _etiqueta_actual(self):
        ids = self.find_withtag("current")
        if not ids:
            return None
        etiquetas = self.gettags(ids[0])
        if "subir" in etiquetas:
            return "subir"
        if "bajar" in etiquetas:
            return "bajar"
        return None

    def _entrar_flecha(self, evento):
        etiqueta = self._etiqueta_actual()
        if etiqueta == "subir":
            self.itemconfigure(self.fondo_subir, fill=FLECHA_HOVER)
        elif etiqueta == "bajar":
            self.itemconfigure(self.fondo_bajar, fill=FLECHA_HOVER)
        self.config(cursor="hand2")

    def _salir_flecha(self, evento):
        self.itemconfigure(self.fondo_subir, fill=FLECHA)
        self.itemconfigure(self.fondo_bajar, fill=FLECHA)
        self.config(cursor="")

    def _presionar(self, evento):
        etiqueta = self._etiqueta_actual()
        if etiqueta is None:
            return
        self.direccion = 1 if etiqueta == "subir" else -1
        self._paso()
        self._cancelar_repeticion()
        self.repeticion = self.after(400, self._repetir)

    def _repetir(self):
        self._paso()
        self.repeticion = self.after(70, self._repetir)

    def _soltar(self, evento):
        self._cancelar_repeticion()

    def _cancelar_repeticion(self):
        if self.repeticion is not None:
            self.after_cancel(self.repeticion)
            self.repeticion = None

    def _paso(self):
        try:
            valor = int(self.variable.get().strip())
        except ValueError:
            self.variable.set(str(self.minimo))
            return
        valor = max(self.minimo, min(self.maximo, valor + self.direccion))
        self.variable.set(str(valor))

    # ---------- rueda y teclado ----------

    def _rueda(self, evento):
        self.direccion = 1 if evento.delta > 0 else -1
        self._paso()

    def _tecla_arriba(self, evento):
        self.direccion = 1
        self._paso()

    def _tecla_abajo(self, evento):
        self.direccion = -1
        self._paso()

    # ---------- foco ----------

    def _foco_entrada(self, evento):
        self.itemconfigure(self.borde, outline=ACENTO, width=2)

    def _foco_salida(self, evento):
        self.itemconfigure(self.borde, outline=BORDE, width=1)


class SelectorSegmentado(tk.Canvas):
    """Grupo de opciones en forma de píldoras redondeadas (una sola seleccionada).
    Cada píldora se ensancha lo necesario para que le entre su texto."""

    RELLENO = 28   # espacio extra (px) que se suma al ancho del texto
    SEPARACION = 6

    def __init__(self, padre, opciones, inicial, ancho=320, alto=34, fondo=TARJETA):
        self.opciones = list(opciones)
        self.seleccion = inicial

        fuente = tkfont.Font(root=padre, family=FUENTE, size=9, weight="bold")
        anchos = []
        for nombre in self.opciones:
            anchos.append(fuente.measure(nombre) + self.RELLENO)

        total = sum(anchos) + self.SEPARACION * (len(anchos) - 1)
        if total < ancho:
            # Sobra lugar: se reparte en partes iguales entre las píldoras.
            extra = (ancho - total) / len(anchos)
            for i in range(len(anchos)):
                anchos[i] += extra
            total = ancho

        super().__init__(padre, width=int(total), height=alto, bg=fondo,
                         highlightthickness=0, bd=0, cursor="hand2")

        self.limites = []
        self.formas = []
        self.textos = []
        x1 = 0
        for i, nombre in enumerate(self.opciones):
            x2 = x1 + anchos[i]
            forma = _rect_redondeado(self, x1 + 1, 1, x2 - 1, alto - 1, 12,
                                     fill=FONDO, outline=BORDE, width=1)
            texto = self.create_text((x1 + x2) / 2, alto / 2, text=nombre,
                                     font=(FUENTE, 9, "bold"), fill=TEXTO)
            self.limites.append((x1, x2))
            self.formas.append(forma)
            self.textos.append(texto)
            x1 = x2 + self.SEPARACION

        self.bind("<Button-1>", self._clic)
        self._pintar()

    def _clic(self, evento):
        for i, (x1, x2) in enumerate(self.limites):
            if x1 <= evento.x <= x2:
                self.seleccion = self.opciones[i]
                self._pintar()
                return

    def _pintar(self):
        for i, nombre in enumerate(self.opciones):
            if nombre == self.seleccion:
                self.itemconfigure(self.formas[i], fill=ACENTO, outline=ACENTO)
                self.itemconfigure(self.textos[i], fill=OSCURO)
            else:
                self.itemconfigure(self.formas[i], fill=FONDO, outline=BORDE)
                self.itemconfigure(self.textos[i], fill=TEXTO)


class BotonRedondeado(tk.Canvas):

    def __init__(self, padre, texto, comando, color, color_hover, ancho=120, alto=38,
                 fondo=FONDO):
        super().__init__(padre, width=ancho, height=alto, bg=fondo,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.comando = comando
        self.color = color
        self.color_hover = color_hover
        self.ancho = ancho
        self.alto = alto
        self.forma = _rect_redondeado(self, 1, 1, ancho - 1, alto - 1, 14,
                                      fill=color, outline=color)
        self.create_text(ancho // 2, alto // 2, text=texto, fill="#ffffff",
                         font=(FUENTE, 10, "bold"))
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._salir)
        self.bind("<ButtonRelease-1>", self._soltar)

    def _entrar(self, evento):
        self.itemconfigure(self.forma, fill=self.color_hover, outline=self.color_hover)

    def _salir(self, evento):
        self.itemconfigure(self.forma, fill=self.color, outline=self.color)

    def _soltar(self, evento):
        if 0 <= evento.x <= self.ancho and 0 <= evento.y <= self.alto:
            self.comando()


class FormularioGenerador:

    def __init__(self, inicial=None):
        self.inicial = inicial if inicial is not None else {}
        self.resultado = None
        self.vars = {}
        self.etiquetas = {}
        self.selector_modo = None
        self.primer_campo = None

        self.root = tk.Tk()
        self._configurar_ventana()
        self._construir()
        self._centrar()

    def mostrar(self):
        if self.primer_campo is not None:
            self.primer_campo.focus_set()
        self.root.mainloop()
        return self.resultado

    # ---------- configuración ----------

    def _configurar_ventana(self):
        self.root.title("Generar escenario")
        self.root.configure(bg=FONDO)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._cancelar)
        self.root.bind("<Return>", self._tecla_generar)
        self.root.bind("<Escape>", self._tecla_cancelar)

    def _centrar(self):
        self.root.update_idletasks()
        ancho = self.root.winfo_reqwidth()
        alto = self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - ancho) // 2
        y = (self.root.winfo_screenheight() - alto) // 2
        self.root.geometry(f"+{x}+{y}")

    # ---------- construcción ----------

    def _construir(self):
        cabecera = tk.Frame(self.root, bg=FONDO)
        cabecera.pack(fill="x", padx=22, pady=(18, 4))
        tk.Label(cabecera, text="GENERAR ESCENARIO", font=(FUENTE, 15, "bold"),
                 fg=ACENTO, bg=FONDO).pack(anchor="w")
        tk.Label(cabecera, text="Configura el almacen, los pedidos y los pickers.",
                 font=(FUENTE, 10), fg=APAGADO, bg=FONDO).pack(anchor="w")

        cuerpo = tk.Frame(self.root, bg=FONDO)
        cuerpo.pack(padx=16, pady=6)
        for seccion in SECCIONES:
            self._construir_seccion(cuerpo, seccion)

        self.etiqueta_error = tk.Label(
            self.root, text="", font=(FUENTE, 10), fg=ROJO, bg=FONDO,
            wraplength=560, justify="left")
        self.etiqueta_error.pack(anchor="w", padx=22)

        botones = tk.Frame(self.root, bg=FONDO)
        botones.pack(fill="x", padx=22, pady=(8, 18))
        boton_generar = BotonRedondeado(botones, "Generar", self._generar, VERDE, VERDE_HOVER)
        boton_generar.pack(side="right")
        boton_cancelar = BotonRedondeado(botones, "Cancelar", self._cancelar, GRIS, GRIS_HOVER)
        boton_cancelar.pack(side="right", padx=(0, 10))

    def _construir_seccion(self, padre, seccion):
        titulo, columna, fila, con_modo, campos = seccion

        tarjeta = Tarjeta(padre, titulo)
        tarjeta.grid(row=fila, column=columna, padx=6, pady=6, sticky="n")

        for i, campo in enumerate(campos):
            clave, etiqueta, inicial, minimo, maximo = campo
            self._campo_numero(tarjeta, i + 1, clave, etiqueta, inicial, minimo, maximo)

        if con_modo:
            self._campo_modo(tarjeta, len(campos) + 1)

        tarjeta.finalizar()

    def _campo_numero(self, tarjeta, fila, clave, etiqueta, inicial, minimo, maximo):
        variable = tk.StringVar(value=str(self.inicial.get(clave, inicial)))
        self.vars[clave] = variable
        self.etiquetas[clave] = etiqueta

        tk.Label(tarjeta.interior, text=etiqueta, font=(FUENTE, 10), fg=TEXTO,
                 bg=TARJETA).grid(row=fila, column=0, sticky="w", padx=(0, 16), pady=5)
        campo = CampoNumero(tarjeta.interior, variable, minimo, maximo)
        campo.grid(row=fila, column=1, pady=5)

        if self.primer_campo is None:
            self.primer_campo = campo.entrada

    def _campo_modo(self, tarjeta, fila):
        modo_inicial = self.inicial.get("modo_ubicacion", "aleatoria")
        nombre_inicial = "Aleatoria"
        for nombre, valor in MODOS.items():
            if valor == modo_inicial:
                nombre_inicial = nombre

        tk.Label(tarjeta.interior, text="Ubicacion de productos", font=(FUENTE, 10),
                 fg=TEXTO, bg=TARJETA).grid(row=fila, column=0, columnspan=2,
                                            sticky="w", pady=(8, 4))
        self.selector_modo = SelectorSegmentado(tarjeta.interior, list(MODOS), nombre_inicial)
        self.selector_modo.grid(row=fila + 1, column=0, columnspan=2, sticky="w", pady=(0, 4))

    # ---------- acciones ----------

    def _tecla_generar(self, evento):
        self._generar()

    def _tecla_cancelar(self, evento):
        self._cancelar()

    def _generar(self):
        valores = {}
        for clave, variable in self.vars.items():
            texto = variable.get().strip()
            try:
                valores[clave] = int(texto)
            except ValueError:
                self.etiqueta_error.config(
                    text=f"'{self.etiquetas[clave]}' tiene que ser un numero entero.")
                return
        valores["modo_ubicacion"] = MODOS[self.selector_modo.seleccion]
        self.resultado = valores
        self.root.destroy()

    def _cancelar(self):
        self.resultado = None
        self.root.destroy()


def pedir_parametros_generacion(inicial=None):
    """Muestra el formulario y devuelve los parámetros (dict) o None si se cancela."""
    formulario = FormularioGenerador(inicial)
    return formulario.mostrar()


if __name__ == "__main__":
    print(pedir_parametros_generacion())