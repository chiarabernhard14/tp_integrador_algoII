"""Diálogos nativos de archivo (único lugar donde se usa Tkinter)."""

def abrir(titulo):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    ruta = filedialog.askopenfilename(
        title=titulo, filetypes=[("Archivos JSON", "*.json")], parent=root)
    root.destroy()
    return ruta


def guardar(titulo, nombre):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    ruta = filedialog.asksaveasfilename(
        title=titulo, defaultextension=".json", initialfile=nombre,
        filetypes=[("Archivos JSON", "*.json")], parent=root)
    root.destroy()
    return ruta