'''
Componentes reutilizables de la interfaz gráfica.
'''
import tkinter as tk
from tkinter import ttk

from src.gui import estilos as e


class Aviso(tk.Frame):
    '''
    Banda de mensaje coloreada para mostrar el resultado de una acción
    (tipo "ok", "error" o "info"). Ocupa su sitio en la página y, oculta, no se ve.
    '''

    COLORES = {"ok": (e.OK_FONDO, e.OK_TEXTO, "✔"),
               "error": (e.ERROR_FONDO, e.ERROR_TEXTO, "✖"),
               "info": (e.INFO_FONDO, e.INFO_TEXTO, "i")}

    def __init__(self, master):
        super().__init__(master, bg=e.FONDO, height=1)
        self.icono = tk.Label(self, font=e.fuente(12, "bold"), padx=12)
        self.texto = tk.Label(self, font=e.fuente(10), justify="left", anchor="w", pady=10, padx=4)
        self.texto.bind("<Configure>", lambda ev: self.texto.configure(wraplength=max(ev.width - 10, 200)))
        self.tipo = None

    def mostrar(self, mensaje, tipo="info"):
        fondo, color, icono = self.COLORES[tipo]
        self.configure(bg=fondo)
        self.icono.configure(text=icono, bg=fondo, fg=color)
        self.texto.configure(text=mensaje, bg=fondo, fg=color)
        self.tipo = tipo
        self.icono.pack(side="left", fill="y")
        self.texto.pack(side="left", fill="both", expand=True)

    def ocultar(self):
        self.tipo = None
        self.texto.configure(text="")
        self.icono.pack_forget()
        self.texto.pack_forget()
        self.configure(bg=e.FONDO)

    @property
    def mensaje(self):
        return self.texto.cget("text")


def tarjeta(master, **pack):
    '''Marco blanco con borde fino y margen interior.'''
    borde = tk.Frame(master, bg=e.BORDE)
    interior = tk.Frame(borde, bg=e.TARJETA, padx=18, pady=16)
    interior.pack(fill="both", expand=True, padx=1, pady=1)
    if pack:
        borde.pack(**pack)
    interior.contenedor = borde
    return interior


def cabecera(master, titulo, subtitulo):
    ttk.Label(master, text=titulo, style="Titulo.TLabel").pack(anchor="w")
    ttk.Label(master, text=subtitulo, style="Subtitulo.TLabel").pack(anchor="w", pady=(2, 18))


def tabla(master, columnas, altura=8, arbol=False):
    '''
    Treeview con barra de desplazamiento. columnas: lista de (id, título, ancho, stretch).
    '''
    marco = tk.Frame(master, bg=e.BORDE)
    tv = ttk.Treeview(marco, columns=[c[0] for c in columnas], height=altura,
                      show="tree headings" if arbol else "headings", selectmode="browse")
    if arbol:
        tv.column("#0", width=120, minwidth=100, stretch=False)
        tv.heading("#0", text="Día", anchor="w")
    for ident, titulo, ancho, stretch in columnas:
        tv.heading(ident, text=titulo, anchor="w")
        tv.column(ident, width=ancho, minwidth=50, stretch=stretch, anchor="w")
    barra = ttk.Scrollbar(marco, orient="vertical", command=tv.yview)

    #La barra solo se muestra cuando hay más filas de las que caben
    def desplazar(primero, ultimo):
        barra.set(primero, ultimo)
        if float(primero) <= 0.0 and float(ultimo) >= 1.0:
            barra.pack_forget()
        elif not barra.winfo_ismapped():
            barra.pack(side="right", fill="y", pady=1, padx=(0, 1), before=tv)

    tv.configure(yscrollcommand=desplazar)
    tv.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    return marco, tv


def campo(master, etiqueta, ancho=28):
    '''Etiqueta pequeña encima de una entrada de texto. Devuelve la entrada.'''
    ttk.Label(master, text=etiqueta, style="Campo.TLabel").pack(anchor="w", pady=(8, 2))
    entrada = ttk.Entry(master, width=ancho)
    entrada.pack(fill="x")
    return entrada
