'''
Pantallas del bloque "Ocupación de instalaciones y asistencia" (Sprint 2):
HU16 Añadir a la oferta actual una actividad de la oferta anterior y HU19 Modalidades por instalación.
'''
import tkinter as tk
from tkinter import ttk

from src.gui import estilos as e
from src.gui.componentes import Aviso, cabecera, campo, tabla, tarjeta
from src.gui.paginas import Pagina
from src.instalaciones.instalacionModel import DIAS_SEMANA
from src.ofertas.ofertaAnteriorModel import OfertaAnteriorError, describirPeriodicidad
from src.util.validation import ValidationError, validate_positive_int
from src.instalaciones.modalidadInstalacionModel import (
    ConfirmacionRequerida,
    ModalidadInstalacionError,
)


#--------------------------------------------------------------------------------------------
class PaginaModalidades(Pagina):
    '''HU19: indicar qué modalidades admite cada instalación e informe de incoherencias.'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Modalidades por instalación",
                 "Indica qué modalidades admite cada instalación para evitar asignaciones incoherentes")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2)
        cuerpo.rowconfigure(0, weight=1)
        cuerpo.rowconfigure(1, weight=1)

        izq = tarjeta(cuerpo)
        izq.contenedor.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))
        ttk.Label(izq, text="Instalaciones", style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))
        marco, self.tablaConfig = tabla(izq, [
            ("nombre", "Instalación", 170, False), ("modalidades", "Modalidades que admite", 320, True)],
            altura=7)
        marco.pack(fill="both", expand=True)
        self.tablaConfig.bind("<<TreeviewSelect>>", lambda ev: self._cargarSeleccion())

        der = tarjeta(cuerpo)
        der.contenedor.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        self.tituloEdicion = ttk.Label(der, text="Elige una instalación", style="Seccion.TLabel")
        self.tituloEdicion.pack(anchor="w", pady=(0, 10))
        self.marcas = tk.Frame(der, bg=e.TARJETA)
        self.marcas.pack(fill="x")
        self.variables = {}
        self.botonGuardar = ttk.Button(der, text="Guardar modalidades", style="Primario.TButton",
                                       command=self.guardar, state="disabled")
        self.botonGuardar.pack(anchor="e", pady=(14, 0))

        inf = tarjeta(cuerpo)
        inf.contenedor.grid(row=1, column=0, columnspan=2, sticky="nsew")
        ttk.Label(inf, text="Asignaciones incoherentes (solo consulta)",
                  style="Seccion.TLabel").pack(anchor="w")
        self.resumenInforme = tk.Label(inf, bg=e.TARJETA, fg=e.TEXTO_SUAVE, anchor="w")
        self.resumenInforme.pack(fill="x", pady=(2, 8))
        marco, self.tablaIncoherencias = tabla(inf, [
            ("actividad", "Actividad", 260, True), ("instalacion", "Instalación", 200, True),
            ("motivo", "Motivo", 300, True)], altura=4)
        marco.pack(fill="both", expand=True)

    def refrescar(self):
        self.aviso.ocultar()
        modelo = self.app.modalidadesInstalacion
        seleccion = self.tablaConfig.selection()
        self.tablaConfig.delete(*self.tablaConfig.get_children())
        for inst in modelo.getConfiguracion():
            self.tablaConfig.insert("", "end", iid=str(inst["id"]), values=(
                inst["nombre"], ", ".join(inst["modalidades"]) or "Ninguna"))
        if not self.variables:
            for m in modelo.getModalidades():
                var = tk.BooleanVar(value=False)
                ttk.Checkbutton(self.marcas, text=m["nombre"], variable=var).pack(anchor="w", pady=2)
                self.variables[m["id"]] = var
        if seleccion and self.tablaConfig.exists(seleccion[0]):
            self.tablaConfig.selection_set(seleccion[0])
        self._actualizarInforme()

    def _actualizarInforme(self):
        self.tablaIncoherencias.delete(*self.tablaIncoherencias.get_children())
        incoherencias = self.app.modalidadesInstalacion.getIncoherencias()
        for a in incoherencias:
            self.tablaIncoherencias.insert("", "end", values=(
                f"{a['modalidad']} {a['nivel'].lower()} (actividad {a['id']})", a["instalacion"],
                f"{a['instalacion']} no admite {a['modalidad']}"))
        self.resumenInforme.configure(
            text="No hay asignaciones incoherentes" if not incoherencias
            else f"{len(incoherencias)} asignación(es) no cumplen la configuración")

    def _cargarSeleccion(self):
        sel = self.tablaConfig.selection()
        if not sel:
            return
        idInstalacion = int(sel[0])
        admitidas = set(self.app.modalidadesInstalacion.getModalidadesAdmitidas(idInstalacion))
        for idModalidad, var in self.variables.items():
            var.set(idModalidad in admitidas)
        self.tituloEdicion.configure(text=f"Modalidades de {self.tablaConfig.item(sel[0], 'values')[0]}")
        self.botonGuardar.configure(state="normal")

    def guardar(self):
        sel = self.tablaConfig.selection()
        if not sel:
            self.aviso.mostrar("Selecciona una instalación", "info")
            return
        ids = [idModalidad for idModalidad, var in self.variables.items() if var.get()]
        modelo = self.app.modalidadesInstalacion
        try:
            try:
                mensaje = modelo.guardarModalidades(int(sel[0]), ids)
            except ConfirmacionRequerida as aviso:
                if not self.app.confirmar("Actividades afectadas", str(aviso)):
                    self.aviso.mostrar("No se ha guardado ningún cambio", "info")
                    return
                mensaje = modelo.guardarModalidades(int(sel[0]), ids, confirmar=True)
        except ModalidadInstalacionError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.refrescar()
        self.aviso.mostrar(mensaje, "ok")


#--------------------------------------------------------------------------------------------
class PaginaOfertaAnterior(Pagina):
    '''HU16: añadir a la oferta actual una actividad de la oferta de la temporada anterior.'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Actividades de la temporada anterior",
                 "Elige una actividad de la oferta anterior, revisa su demanda y añádela a la oferta actual")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))

        lista = tarjeta(self, fill="both", expand=True)
        self.titulo = ttk.Label(lista, text="Oferta anterior", style="Seccion.TLabel")
        self.titulo.pack(anchor="w", pady=(0, 10))
        marco, self.tablaAnterior = tabla(lista, [
            ("actividad", "Actividad", 190, True), ("horario", "Horario", 210, True),
            ("plazas", "Plazas", 60, False), ("inscritos", "Inscritos", 70, False),
            ("espera", "En espera", 80, False), ("ocupacion", "Ocupación", 80, False),
            ("instalacion", "Instalación anterior", 150, True)], altura=7)
        marco.pack(fill="both", expand=True)
        self.tablaAnterior.tag_configure("llena", foreground=e.OK_TEXTO)
        self.tablaAnterior.tag_configure("sinDatos", foreground=e.NO_CABE_TEXTO)
        self.tablaAnterior.bind("<<TreeviewSelect>>", lambda ev: self._precargar())

        form = tarjeta(self, fill="x", pady=(14, 0))
        self.tituloForm = ttk.Label(form, text="Elige una actividad para precargar sus datos",
                                    style="Seccion.TLabel")
        self.tituloForm.pack(anchor="w")
        fila = tk.Frame(form, bg=e.TARJETA)
        fila.pack(fill="x", pady=(8, 0))
        diasMarco = tk.Frame(fila, bg=e.TARJETA)
        diasMarco.pack(side="left", padx=(0, 18))
        ttk.Label(diasMarco, text="Días", style="Campo.TLabel").pack(anchor="w")
        filaDias = tk.Frame(diasMarco, bg=e.TARJETA)
        filaDias.pack(anchor="w")
        self.dias = {}
        for dia, nombre in DIAS_SEMANA.items():
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(filaDias, text=nombre[:3].capitalize(), variable=var).pack(side="left", padx=(0, 6))
            self.dias[dia] = var
        campos = {}
        for clave, texto in (("inicio", "Hora inicio (HH:MM)"), ("fin", "Hora fin (HH:MM)"), ("plazas", "Plazas")):
            marcoCampo = tk.Frame(fila, bg=e.TARJETA)
            marcoCampo.pack(side="left", padx=(0, 12))
            campos[clave] = campo(marcoCampo, texto, ancho=12)
        self.horaInicio, self.horaFin, self.plazas = campos["inicio"], campos["fin"], campos["plazas"]
        self.boton = ttk.Button(fila, text="Añadir a la oferta actual", style="Primario.TButton",
                                command=self.anadir, state="disabled")
        self.boton.pack(side="right", anchor="s")

    def refrescar(self):
        self.aviso.ocultar()
        self.tablaAnterior.delete(*self.tablaAnterior.get_children())
        self.boton.configure(state="disabled")
        modelo = self.app.ofertaAnterior
        try:
            actual, anterior = modelo.comprobarDisponible()
        except OfertaAnteriorError as error:
            self.titulo.configure(text="Oferta anterior")
            self.aviso.mostrar(str(error), "info")
            return
        self.titulo.configure(text=f"Oferta {anterior['curso']} → se añadirá a la oferta {actual['curso']}")
        actividades = modelo.getActividadesConDemanda(anterior["id"])
        if not actividades:
            self.aviso.mostrar("La oferta anterior no tiene actividades", "info")
        self.origen = {}
        for a in actividades:
            horario = (describirPeriodicidad(a["dias"], a["horaInicio"], a["horaFin"])
                       if a["dias"] else "sin horario")
            demanda = (("Sin datos", "Sin datos", "Sin datos") if a["sinDatos"]
                       else (a["inscritos"], a["espera"], f"{a['ocupacion']} %"))
            tag = "sinDatos" if a["sinDatos"] else "llena" if a["espera"] > 0 else ""
            self.tablaAnterior.insert("", "end", iid=str(a["id"]), tags=(tag,), values=(
                f"{a['modalidad']} {a['nivel'].lower()}", horario, a["plazas"], *demanda,
                a["instalacion"] or "Sin instalación"))
            self.origen[str(a["id"])] = a

    #Rellena el formulario con los datos de la actividad elegida
    def _precargar(self):
        sel = self.tablaAnterior.selection()
        if not sel:
            return
        a = self.origen[sel[0]]
        for dia, var in self.dias.items():
            var.set(dia in a["dias"])
        for entrada, valor in ((self.horaInicio, a["horaInicio"]), (self.horaFin, a["horaFin"]),
                               (self.plazas, a["plazas"])):
            entrada.delete(0, "end")
            entrada.insert(0, "" if valor is None else str(valor))
        self.tituloForm.configure(text=f"{a['modalidad']} {a['nivel'].lower()}: ajusta los datos si hace falta")
        self.boton.configure(state="normal")

    def anadir(self):
        sel = self.tablaAnterior.selection()
        if not sel:
            self.aviso.mostrar("Elige una actividad de la oferta anterior", "info")
            return
        try:
            plazas = validate_positive_int(self.plazas.get())
        except ValidationError as error:
            self.aviso.mostrar(f"Plazas no válidas. {error}", "error")
            return
        dias = [dia for dia, var in self.dias.items() if var.get()]
        try:
            resultado = self.app.ofertaAnterior.anadirDesdeAnterior(
                int(sel[0]), plazas, dias, self.horaInicio.get().strip(), self.horaFin.get().strip())
        except OfertaAnteriorError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.aviso.mostrar(resultado["mensaje"] + ". Asígnale una instalación en «Asignar instalación».", "ok")
