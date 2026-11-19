"""Pantalla de inscripciones de temporadas anteriores."""
from pathlib import Path
from tkinter import filedialog, ttk

from src.gui.componentes import Aviso, cabecera, tabla
from src.gui.paginas import Pagina
from src.inscripciones.historicoModel import HistoricoError


class PaginaHistorico(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.validacion = None
        cabecera(self, "Histórico de inscripciones", "Valida un fichero CSV de temporadas anteriores.")

        acciones = ttk.Frame(self)
        acciones.pack(fill="x", pady=(0, 10))
        ttk.Button(acciones, text="Seleccionar y validar CSV", command=self.validar).pack(side="left")
        self.fichero = ttk.Label(acciones)
        self.fichero.pack(side="left", padx=10)
        self.botonImportar = ttk.Button(
            acciones, text="Importar filas válidas", command=self.importar, state="disabled"
        )
        self.botonImportar.pack(side="right")

        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 10))
        marco, self.incidencias = tabla(self, [
            ("linea", "Línea", 70, False),
            ("motivo", "Incidencia", 530, True),
        ], altura=6)
        marco.pack(fill="x")

    def validar(self):
        ruta = filedialog.askopenfilename(
            parent=self, title="Selecciona el histórico", filetypes=[("Ficheros CSV", "*.csv")]
        )
        if not ruta:
            return
        self.validacion = None
        self.botonImportar.configure(state="disabled")
        self.incidencias.delete(*self.incidencias.get_children())
        self.fichero.configure(text=Path(ruta).name)
        try:
            self.validacion = self.app.historico.validar(ruta)
        except HistoricoError as error:
            self.aviso.mostrar(str(error), "error")
            return

        resultado = self.validacion
        for incidencia in resultado.incidencias:
            self.incidencias.insert("", "end", values=(incidencia.linea, incidencia.motivo))
        self.aviso.mostrar(
            f"Filas válidas: {len(resultado.solicitudes)}. Filas descartadas: {resultado.descartadas}.",
            "error" if resultado.incidencias else "ok",
        )
        if resultado.solicitudes:
            self.botonImportar.configure(state="normal")

    def importar(self):
        resultado = self.validacion
        if resultado is None or not resultado.solicitudes:
            return
        mensaje = (f"Se importarán {len(resultado.solicitudes)} filas válidas. "
                   f"Se omitirán {resultado.descartadas} filas. ¿Continuar?")
        if not self.app.confirmar("Importar histórico", mensaje):
            return
        try:
            importadas, descartadas = self.app.historico.importar(resultado)
        except HistoricoError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.validacion = None
        self.botonImportar.configure(state="disabled")
        self.aviso.mostrar(
            f"Filas importadas: {importadas}. Filas descartadas: {descartadas}.", "ok"
        )
