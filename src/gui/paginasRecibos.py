'''
Pantalla «Recibos» del bloque de control económico (Sprint 2). Tiene una pestaña por historia:
HU13 Emitir la remesa mensual de recibos.
'''
import tkinter as tk
from tkinter import ttk

from src.gui import estilos as e
from src.gui.componentes import Aviso, cabecera, campo, tabla, tarjeta
from src.gui.paginas import Pagina
from src.recibos.comun import ReciboError, describirActividad, describirImporte, nombreMes
from src.recibos.remesaModel import RemesaModel

#Texto de cada estado en pantalla
TEXTO_ESTADO = {"EMITIDO": "Emitido", "COBRADO": "Cobrado", "DEVUELTO": "Devuelto"}


def configurarPestanas(widget):
    estilo = ttk.Style(widget)
    estilo.configure("TNotebook", background=e.FONDO, borderwidth=0)
    estilo.configure("TNotebook.Tab", padding=(e.px(16), e.px(8)), font=e.fuente(10))
    estilo.map("TNotebook.Tab", background=[("selected", e.TARJETA)],
               font=[("selected", e.fuente(10, "bold"))])


def colorearEstados(tv):
    tv.tag_configure("COBRADO", foreground=e.OK_TEXTO)
    tv.tag_configure("DEVUELTO", foreground=e.ERROR_TEXTO)
    tv.tag_configure("EMITIDO", foreground=e.AVISO_TEXTO)


class PaginaRecibos(Pagina):
    '''Remesas, resultado del banco y consulta de recibos, cada una en su pestaña.'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Recibos",
                 "Emite la remesa mensual de recibos de las inscripciones para cobrarla en el banco")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))
        configurarPestanas(self)
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True)
        self.remesa = PestanaRemesa(self.pestanas, self)
        self.pestanas.add(self.remesa, text="Emitir remesa")
        self.pestanas.bind("<<NotebookTabChanged>>", lambda ev: self.refrescar())

    def refrescar(self):
        self.aviso.ocultar()
        self.pestanas.nametowidget(self.pestanas.select()).refrescar()


#--------------------------------------------------------------------------------------------
class PestanaRemesa(ttk.Frame):
    '''HU13: emitir la remesa mensual y ver las remesas emitidas con sus recibos.'''

    def __init__(self, master, pagina):
        super().__init__(master, padding=(0, e.px(14), 0, 0))
        self.pagina = pagina
        self.app = pagina.app
        self.aviso = pagina.aviso

        #Arriba el formulario y las remesas emitidas; debajo, los recibos de la remesa elegida
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(1, weight=1)

        form = tarjeta(self)
        form.contenedor.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))
        ttk.Label(form, text="Nueva remesa", style="Seccion.TLabel").pack(anchor="w")
        tk.Label(form, text="Un recibo por cada inscripción activa del mes, con la cuota mensual de "
                            "la actividad. Se pasa al cobro a principio de mes.",
                 bg=e.TARJETA, fg=e.TEXTO_SUAVE, font=e.fuente(9), justify="left",
                 wraplength=e.px(240)).pack(anchor="w")
        self.mes = campo(form, "Mes (AAAA-MM)", ancho=14)
        self.mes.bind("<Return>", lambda ev: self.emitir())
        ttk.Button(form, text="Emitir remesa", style="Primario.TButton",
                   command=self.emitir).pack(anchor="w", pady=(12, 0))

        izq = tarjeta(self)
        izq.contenedor.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        ttk.Label(izq, text="Remesas emitidas", style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))
        marco, self.tablaRemesas = tabla(izq, [
            ("mes", "Mes", 150, True), ("emision", "Emisión", 95, False),
            ("recibos", "Recibos", 70, False), ("total", "Importe", 100, False),
            ("pendientes", "Pendientes del banco", 150, False)], altura=4)
        marco.pack(fill="both", expand=True)
        self.tablaRemesas.bind("<<TreeviewSelect>>", lambda ev: self._cargarRecibos())

        der = tarjeta(self)
        der.contenedor.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.tituloRecibos = ttk.Label(der, text="Elige una remesa", style="Seccion.TLabel")
        self.tituloRecibos.pack(anchor="w", pady=(0, 10))
        marco, self.tablaRecibos = tabla(der, [
            ("id", "Recibo", 70, False), ("socio", "Socio", 260, True),
            ("actividad", "Actividad", 200, True), ("importe", "Importe", 100, False),
            ("estado", "Estado", 100, False)], altura=7)
        marco.pack(fill="both", expand=True)
        colorearEstados(self.tablaRecibos)

    @property
    def modelo(self):
        return self.app.remesas

    def refrescar(self):
        if not self.mes.get().strip():
            self.mes.insert(0, self.modelo.mesPorDefecto())
        seleccion = self.tablaRemesas.selection()
        self.tablaRemesas.delete(*self.tablaRemesas.get_children())
        for r in self.modelo.getRemesas():
            self.tablaRemesas.insert("", "end", iid=r["mes"], values=(
                nombreMes(r["mes"]).capitalize(), r["fechaEmision"], r["recibos"],
                describirImporte(r["total"]), r["pendientes"]))
        if seleccion and self.tablaRemesas.exists(seleccion[0]):
            self.tablaRemesas.selection_set(seleccion[0])
        else:
            self._cargarRecibos()

    def _cargarRecibos(self):
        self.tablaRecibos.delete(*self.tablaRecibos.get_children())
        sel = self.tablaRemesas.selection()
        if not sel:
            self.tituloRecibos.configure(text="Elige una remesa")
            return
        recibos = self.modelo.getRecibos(sel[0])
        self.tituloRecibos.configure(text=f"Recibos de {nombreMes(sel[0])} ({len(recibos)})")
        for r in recibos:
            self.tablaRecibos.insert("", "end", iid=str(r["id"]), tags=(r["estado"],), values=(
                r["id"], f"{r['nombre']} {r['apellidos']} ({r['dni']})",
                describirActividad(r["modalidad"], r["nivel"]), describirImporte(r["importe"]),
                TEXTO_ESTADO[r["estado"]]))

    def emitir(self):
        self.aviso.ocultar()
        mes = self.mes.get().strip() or None
        try:
            previa = self.modelo.prepararRemesa(mes)
        except ReciboError as error:
            self.aviso.mostrar(str(error), "error")
            return
        if not self.app.confirmar("Emitir remesa", self.modelo.describirPrevia(previa) + "\n\n¿Emitir la remesa?"):
            self.aviso.mostrar("No se ha emitido la remesa", "info")
            return
        try:
            resultado = self.modelo.emitirRemesa(mes)
        except ReciboError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.refrescar()
        self.tablaRemesas.selection_set(resultado["mes"])
        self._cargarRecibos()
        self.aviso.mostrar(resultado["mensaje"], "ok")
