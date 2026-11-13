'''
Pantallas del bloque "Ocupación de instalaciones y asistencia" (Sprint 2):
HU19 Modalidades por instalación.
'''
import tkinter as tk
from tkinter import ttk

from src.gui import estilos as e
from src.gui.componentes import Aviso, cabecera, tabla, tarjeta
from src.gui.paginas import Pagina
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
