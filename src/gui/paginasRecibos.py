'''
Pantalla «Recibos» del bloque de control económico (Sprint 2). Tiene una pestaña por historia:
HU13 Emitir la remesa mensual de recibos, HU14 Importar el resultado del banco y
HU15 Consultar los recibos y los ingresos por actividad.
'''
import tkinter as tk
from tkinter import ttk

from src.gui import estilos as e
from src.gui.componentes import Aviso, cabecera, campo, tabla, tarjeta
from src.gui.paginas import Pagina
from src.recibos.comun import ReciboError, describirActividad, describirImporte, nombreMes

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
                 "Emite la remesa mensual, importa el resultado del banco y consulta los ingresos por actividad")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))
        configurarPestanas(self)
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True)
        self.remesa = PestanaRemesa(self.pestanas, self)
        self.pestanas.add(self.remesa, text="Emitir remesa")
        self.resultado = PestanaResultado(self.pestanas, self)
        self.pestanas.add(self.resultado, text="Resultado del banco")
        self.consulta = PestanaConsulta(self.pestanas, self)
        self.pestanas.add(self.consulta, text="Recibos e ingresos")
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


#--------------------------------------------------------------------------------------------
class PestanaResultado(ttk.Frame):
    '''HU14: importar el resultado del banco y ver el resumen con los errores.'''

    def __init__(self, master, pagina):
        super().__init__(master, padding=(0, e.px(14), 0, 0))
        self.app = pagina.app
        self.aviso = pagina.aviso

        form = tarjeta(self, fill="x")
        ttk.Label(form, text="Importar el resultado del banco", style="Seccion.TLabel").pack(anchor="w")
        self.ayuda = tk.Label(form, bg=e.TARJETA, fg=e.TEXTO_SUAVE, font=e.fuente(9), justify="left",
                              anchor="w")
        self.ayuda.pack(fill="x")
        #La ruta de la carpeta puede ser larga: el texto se ajusta al ancho disponible
        self.ayuda.bind("<Configure>", lambda ev: self.ayuda.configure(wraplength=max(ev.width - e.px(10), e.px(200))))
        fila = tk.Frame(form, bg=e.TARJETA)
        fila.pack(fill="x")
        marcoMes = tk.Frame(fila, bg=e.TARJETA)
        marcoMes.pack(side="left")
        self.mes = campo(marcoMes, "Mes de la remesa (AAAA-MM)", ancho=14)
        self.mes.bind("<Return>", lambda ev: self.importar())
        ttk.Button(fila, text="Importar resultado", style="Primario.TButton",
                   command=self.importar).pack(side="left", anchor="s", padx=(14, 0))
        ttk.Button(fila, text="Generar fichero de prueba", style="Secundario.TButton",
                   command=self.generarPrueba).pack(side="right", anchor="s")

        resumen = tarjeta(self, fill="both", expand=True, pady=(14, 0))
        self.tituloResumen = ttk.Label(resumen, text="Resumen de la importación", style="Seccion.TLabel")
        self.tituloResumen.pack(anchor="w")
        self.cifras = tk.Label(resumen, text="Todavía no se ha importado ningún fichero", bg=e.TARJETA,
                               fg=e.TEXTO_SUAVE, anchor="w", font=e.fuente(10))
        self.cifras.pack(fill="x", pady=(2, 10))
        marco, self.tablaErrores = tabla(resumen, [("linea", "Línea", 70, False),
                                                   ("motivo", "Motivo del error", 500, True)], altura=8)
        marco.pack(fill="both", expand=True)
        self.tablaErrores.tag_configure("error", foreground=e.ERROR_TEXTO)

    @property
    def modelo(self):
        return self.app.resultadosBanco

    def refrescar(self):
        if not self.mes.get().strip():
            self.mes.insert(0, self.modelo.mesPorDefecto())
        self.ayuda.configure(text=f"Se lee el fichero resultado_AAAA-MM.txt de la carpeta {self.modelo.carpeta}, "
                                  "con una línea por recibo: id;COBRADO o id;DEVUELTO.")

    def _limpiarResumen(self):
        self.tablaErrores.delete(*self.tablaErrores.get_children())
        self.cifras.configure(text="Todavía no se ha importado ningún fichero")

    def importar(self):
        self.aviso.ocultar()
        self._limpiarResumen()
        try:
            r = self.modelo.importarResultado(self.mes.get().strip() or None)
        except ReciboError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.cifras.configure(text=f"{r['cobrados']} cobrado(s) · {r['devueltos']} devuelto(s) · "
                                   f"{r['erroneos']} erróneo(s)")
        for i, err in enumerate(r["errores"]):
            self.tablaErrores.insert("", "end", iid=str(i), tags=("error",),
                                     values=(err["linea"], err["motivo"]))
        self.aviso.mostrar(r["mensaje"], "ok" if not r["errores"] else "info")

    def generarPrueba(self):
        self.aviso.ocultar()
        try:
            ruta = self.modelo.generarFicheroPrueba(self.mes.get().strip() or None)
        except ReciboError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.aviso.mostrar(f"Fichero de prueba del banco generado: {ruta}. Ya se puede importar.", "info")


#--------------------------------------------------------------------------------------------
class PestanaConsulta(ttk.Frame):
    '''HU15: consultar los recibos y los ingresos por actividad de una temporada.'''

    ESTADOS = [("Todos", None), ("Emitido", "EMITIDO"), ("Cobrado", "COBRADO"), ("Devuelto", "DEVUELTO")]

    def __init__(self, master, pagina):
        super().__init__(master, padding=(0, e.px(14), 0, 0))
        self.app = pagina.app
        self.aviso = pagina.aviso
        self.temporadas, self.actividades = [], []

        filtros = tarjeta(self, fill="x")
        fila = tk.Frame(filtros, bg=e.TARJETA)
        fila.pack(fill="x")
        self.comboTemporada = self._combo(fila, "Temporada", 16)
        self.comboTemporada.bind("<<ComboboxSelected>>", lambda ev: self._cargarActividades())
        self.comboActividad = self._combo(fila, "Actividad", 30)
        self.comboEstado = self._combo(fila, "Estado del recibo", 12)
        self.comboEstado["values"] = [t for t, _ in self.ESTADOS]
        self.comboEstado.current(0)
        ttk.Button(fila, text="Consultar", style="Primario.TButton",
                   command=self.consultar).pack(side="left", anchor="s", padx=(6, 0))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True, pady=(14, 0))
        cuerpo.columnconfigure(0, weight=2)
        cuerpo.columnconfigure(1, weight=3)
        cuerpo.rowconfigure(0, weight=1)

        izq = tarjeta(cuerpo)
        izq.contenedor.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(izq, text="Ingresos por actividad", style="Seccion.TLabel").pack(anchor="w")
        tk.Label(izq, text="Ingresos: solo recibos cobrados. Pendiente: emitidos sin respuesta del banco.",
                 bg=e.TARJETA, fg=e.TEXTO_SUAVE, font=e.fuente(9)).pack(anchor="w", pady=(0, 8))
        marco, self.tablaResumen = tabla(izq, [
            ("actividad", "Actividad", 170, True), ("ingresos", "Ingresos", 95, False),
            ("pendiente", "Pendiente", 95, False), ("devuelto", "Devuelto", 95, False)], altura=9)
        marco.pack(fill="both", expand=True)
        self.tablaResumen.tag_configure("total", font=e.fuente(10, "bold"), background=e.DIA_FONDO)
        self.tablaResumen.tag_configure("sinRecibos", foreground=e.NO_CABE_TEXTO)

        der = tarjeta(cuerpo)
        der.contenedor.grid(row=0, column=1, sticky="nsew")
        self.tituloRecibos = ttk.Label(der, text="Recibos", style="Seccion.TLabel")
        self.tituloRecibos.pack(anchor="w", pady=(0, 10))
        marco, self.tablaRecibos = tabla(der, [
            ("id", "Recibo", 60, False), ("socio", "Socio", 190, True),
            ("actividad", "Actividad", 150, True), ("mes", "Mes", 75, False),
            ("importe", "Importe", 80, False), ("emision", "Emisión", 90, False),
            ("estado", "Estado", 80, False)], altura=9)
        marco.pack(fill="both", expand=True)
        colorearEstados(self.tablaRecibos)

    @staticmethod
    def _combo(fila, texto, ancho):
        marco = tk.Frame(fila, bg=e.TARJETA)
        marco.pack(side="left", padx=(0, 14))
        ttk.Label(marco, text=texto, style="Campo.TLabel").pack(anchor="w", pady=(0, 2))
        combo = ttk.Combobox(marco, state="readonly", width=ancho)
        combo.pack(fill="x")
        return combo

    @property
    def modelo(self):
        return self.app.consultaRecibos

    def refrescar(self):
        anterior = self._idTemporada()
        self.temporadas = self.modelo.getTemporadas()
        self.comboTemporada["values"] = [
            t["curso"] + (" (vigente)" if t["estado"] == "ACTIVA" else "") for t in self.temporadas]
        if not self.temporadas:
            self.aviso.mostrar("No hay temporadas registradas", "info")
            return
        ids = [t["id"] for t in self.temporadas]
        self.comboTemporada.current(ids.index(anterior) if anterior in ids else 0)
        self._cargarActividades(conservar=True)
        self.consultar()

    def _idTemporada(self):
        i = self.comboTemporada.current()
        return self.temporadas[i]["id"] if i >= 0 and i < len(self.temporadas) else None

    def _cargarActividades(self, conservar=False):
        anterior = self._idActividad() if conservar else None
        idTemporada = self._idTemporada()
        self.actividades = self.modelo.getActividades(idTemporada) if idTemporada else []
        self.comboActividad["values"] = ["Todas"] + [
            f"{a['nombre']} (actividad {a['id']})" for a in self.actividades]
        ids = [a["id"] for a in self.actividades]
        self.comboActividad.current(ids.index(anterior) + 1 if anterior in ids else 0)

    def _idActividad(self):
        i = self.comboActividad.current()
        return self.actividades[i - 1]["id"] if 0 < i <= len(self.actividades) else None

    def consultar(self):
        self.aviso.ocultar()
        self.tablaResumen.delete(*self.tablaResumen.get_children())
        self.tablaRecibos.delete(*self.tablaRecibos.get_children())
        estado = self.ESTADOS[max(self.comboEstado.current(), 0)][1]
        try:
            r = self.modelo.consultar(self._idTemporada(), self._idActividad(), estado)
        except ReciboError as error:
            self.aviso.mostrar(str(error), "error")
            return
        for f in r["resumen"]:
            self.tablaResumen.insert("", "end", iid=str(f["idActividad"]),
                                     tags=("sinRecibos",) if not f["recibos"] else (), values=(
                f["actividad"], describirImporte(f["ingresos"]), describirImporte(f["pendiente"]),
                describirImporte(f["devuelto"])))
        t = r["totales"]
        self.tablaResumen.insert("", "end", iid="total", tags=("total",), values=(
            "Total", describirImporte(t["ingresos"]), describirImporte(t["pendiente"]),
            describirImporte(t["devuelto"])))
        for rec in r["recibos"]:
            self.tablaRecibos.insert("", "end", iid=str(rec["id"]), tags=(rec["estado"],), values=(
                rec["id"], rec["socio"], rec["actividad"], rec["mes"], describirImporte(rec["importe"]),
                rec["fechaEmision"], TEXTO_ESTADO[rec["estado"]]))
        self.tituloRecibos.configure(text=f"Recibos de la temporada {r['temporada']['curso']} "
                                          f"({len(r['recibos'])})")
        if r["mensaje"]:
            self.aviso.mostrar(r["mensaje"], "info")
