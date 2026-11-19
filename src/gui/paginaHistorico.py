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
        cabecera(self, "Histórico de inscripciones", "Inscripciones de temporadas anteriores.")
        pestanas = ttk.Notebook(self)
        pestanas.pack(fill="both", expand=True)
        carga = ttk.Frame(pestanas, padding=12)
        consulta = ttk.Frame(pestanas, padding=12)
        pestanas.add(carga, text="Importar CSV")
        pestanas.add(consulta, text="Consultar histórico")
        self._crearCarga(carga)
        self._crearConsulta(consulta)

    def _crearCarga(self, contenedor):
        acciones = ttk.Frame(contenedor)
        acciones.pack(fill="x", pady=(0, 10))
        ttk.Button(acciones, text="Seleccionar y validar CSV", command=self.validar).pack(side="left")
        self.fichero = ttk.Label(acciones)
        self.fichero.pack(side="left", padx=10)
        self.botonImportar = ttk.Button(
            acciones, text="Importar filas válidas", command=self.importar, state="disabled"
        )
        self.botonImportar.pack(side="right")

        self.aviso = Aviso(contenedor)
        self.aviso.pack(fill="x", pady=(0, 10))
        marco, self.incidencias = tabla(contenedor, [
            ("linea", "Línea", 70, False),
            ("motivo", "Incidencia", 530, True),
        ], altura=6)
        marco.pack(fill="x")

    def _crearConsulta(self, contenedor):
        filtros = ttk.Frame(contenedor)
        filtros.pack(fill="x", pady=(0, 10))
        self.temporada = self._crearFiltro(filtros, "Temporada", 14, self._cambiarTemporada)
        self.categoria = self._crearFiltro(filtros, "Categoría", 23, self._mostrarResultados)
        self.nivel = self._crearFiltro(filtros, "Nivel", 16, self._mostrarResultados)
        self.estadoConsulta = ttk.Label(contenedor)
        self.estadoConsulta.pack(anchor="w", pady=(0, 8))
        marco, self.resultados = tabla(contenedor, [
            ("categoria", "Categoría", 170, True),
            ("nivel", "Nivel", 100, True),
            ("plazas", "Plazas", 65, False),
            ("solicitudes", "Solicitudes", 90, False),
            ("inscripciones", "Confirmadas", 100, False),
        ])
        marco.pack(fill="both", expand=True)

    @staticmethod
    def _crearFiltro(contenedor, etiqueta, ancho, accion):
        campo = ttk.Frame(contenedor)
        campo.pack(side="left", padx=(0, 12))
        ttk.Label(campo, text=etiqueta).pack(anchor="w")
        combo = ttk.Combobox(campo, state="readonly", width=ancho)
        combo.pack(anchor="w")
        combo.bind("<<ComboboxSelected>>", lambda evento: accion())
        return combo

    def refrescar(self):
        temporadas = self.app.historico.getTemporadas()
        self.temporada.configure(values=temporadas)
        if self.temporada.get() not in temporadas:
            self.temporada.set(temporadas[0] if temporadas else "")
        self._cambiarTemporada()

    def _cambiarTemporada(self):
        self.filasTemporada = self.app.historico.consultar(self.temporada.get())
        categorias = {f["categoria"] for f in self.filasTemporada}
        niveles = {f["nivel"] for f in self.filasTemporada}
        for combo, opciones in ((self.categoria, categorias), (self.nivel, niveles)):
            combo.configure(values=("Todos", *sorted(opciones, key=str.casefold)))
            if combo.get() not in opciones:
                combo.current(0)
        self._mostrarResultados()

    def _mostrarResultados(self):
        categoria, nivel = self.categoria.get(), self.nivel.get()
        filas = [f for f in self.filasTemporada
                 if (categoria == "Todos" or f["categoria"] == categoria)
                 and (nivel == "Todos" or f["nivel"] == nivel)]
        self.resultados.delete(*self.resultados.get_children())
        for fila in filas:
            self.resultados.insert("", "end", values=(
                fila["categoria"], fila["nivel"], fila["plazas"], fila["solicitudes"], fila["inscripciones"],
            ))
        if not self.temporada.get():
            texto = "Todavía no hay temporadas importadas."
        elif not filas:
            texto = "No hay resultados para los filtros seleccionados."
        else:
            texto = f"Resultados: {len(filas)}"
        self.estadoConsulta.configure(text=texto)

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
        self.refrescar()
