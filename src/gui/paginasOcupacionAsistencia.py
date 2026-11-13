'''
Pantallas del bloque "Ocupación de instalaciones y asistencia" (Sprint 2):
HU16 Añadir a la oferta actual una actividad de la oferta anterior, HU17 Asistencia a cada sesión,
HU18 Ocupación planificada frente a real y HU19 Modalidades por instalación.
'''
import tkinter as tk
from tkinter import ttk

from src.gui import estilos as e
from src.gui.componentes import Aviso, cabecera, campo, tabla, tarjeta
from src.gui.paginas import Pagina
from src.inscripciones.asistenciaModel import (
    CANCELADA,
    FUTURA,
    REGISTRADA,
    SIN_REGISTRAR,
    AsistenciaError,
    describirFecha,
)
from src.inscripciones.ocupacionRealModel import UMBRAL_DIFERENCIA, OcupacionRealError
from src.instalaciones.instalacionModel import DIAS_SEMANA, describirActividad
from src.ofertas.ofertaAnteriorModel import OfertaAnteriorError, describirPeriodicidad
from src.util.validation import ValidationError, validate_date, validate_positive_int
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


#--------------------------------------------------------------------------------------------
class PaginaAsistencia(Pagina):
    '''HU17: registrar y consultar la asistencia a cada sesión.'''

    COLOR_ESTADO = {REGISTRADA: "registrada", SIN_REGISTRAR: "sinRegistrar", CANCELADA: "cancelada"}

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Asistencia",
                 "Registra quién asiste a cada sesión (de hoy o pasadas) y consulta el uso real de la actividad")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))

        fila = tk.Frame(self, bg=e.FONDO)
        fila.pack(fill="x", pady=(0, 12))
        ttk.Label(fila, text="Actividad").pack(side="left", padx=(0, 8))
        self.combo = ttk.Combobox(fila, state="readonly", width=40)
        self.combo.pack(side="left")
        self.combo.bind("<<ComboboxSelected>>", lambda ev: self._cargarSesiones())
        self.resumen = ttk.Label(fila, text="", style="Subtitulo.TLabel")
        self.resumen.pack(side="left", padx=(16, 0))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2)
        cuerpo.rowconfigure(0, weight=1)

        izq = tarjeta(cuerpo)
        izq.contenedor.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(izq, text="Sesiones hasta hoy", style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))
        marco, self.tablaSesiones = tabla(izq, [
            ("fecha", "Sesión", 200, True), ("horario", "Horario", 110, False),
            ("estado", "Estado", 110, False), ("asistentes", "Asistentes", 90, False),
            ("porcentaje", "%", 60, False)], altura=12)
        marco.pack(fill="both", expand=True)
        self.tablaSesiones.tag_configure("registrada", foreground=e.OK_TEXTO)
        self.tablaSesiones.tag_configure("sinRegistrar", foreground=e.AVISO_TEXTO)
        self.tablaSesiones.tag_configure("cancelada", foreground=e.NO_CABE_TEXTO)
        self.tablaSesiones.bind("<<TreeviewSelect>>", lambda ev: self._cargarHoja())

        der = tarjeta(cuerpo)
        der.contenedor.grid(row=0, column=1, sticky="nsew")
        self.tituloHoja = ttk.Label(der, text="Elige una sesión", style="Seccion.TLabel")
        self.tituloHoja.pack(anchor="w")
        tk.Label(der, text="Haz clic en una persona para cambiar si asistió", bg=e.TARJETA,
                 fg=e.TEXTO_SUAVE, font=e.fuente(9)).pack(anchor="w", pady=(0, 8))
        marco, self.tablaHoja = tabla(der, [("persona", "Inscrito", 200, True), ("asistio", "Asistió", 70, False)],
                                      altura=8)
        marco.pack(fill="both", expand=True)
        self.tablaHoja.tag_configure("si", foreground=e.OK_TEXTO)
        self.tablaHoja.tag_configure("no", foreground=e.ERROR_TEXTO)
        self.tablaHoja.bind("<ButtonRelease-1>", self._clicHoja)
        botones = tk.Frame(der, bg=e.TARJETA)
        botones.pack(fill="x", pady=(12, 0))
        self.botonCancelar = ttk.Button(botones, text="Cancelar sesión", style="Secundario.TButton",
                                        command=self.cancelarSesion, state="disabled")
        self.botonCancelar.pack(side="left")
        self.botonGuardar = ttk.Button(botones, text="Guardar asistencia", style="Primario.TButton",
                                       command=self.guardar, state="disabled")
        self.botonGuardar.pack(side="right")
        self.marcas = {}

    def refrescar(self):
        self.aviso.ocultar()
        self.actividades = self.app.asistencia.getActividadesOfertaActiva()
        self.combo["values"] = [f"{describirActividad(a)} (actividad {a['id']})" for a in self.actividades]
        if not self.actividades:
            self.aviso.mostrar("No hay actividades en la oferta activa", "info")
        elif self.combo.current() >= 0:
            self._cargarSesiones()

    def _idActividad(self):
        indice = self.combo.current()
        return self.actividades[indice]["id"] if indice >= 0 else None

    def _limpiarHoja(self):
        self.tablaHoja.delete(*self.tablaHoja.get_children())
        self.marcas = {}
        self.tituloHoja.configure(text="Elige una sesión")
        self.botonGuardar.configure(state="disabled")
        self.botonCancelar.configure(state="disabled")

    def _cargarSesiones(self):
        self.tablaSesiones.delete(*self.tablaSesiones.get_children())
        self._limpiarHoja()
        idActividad = self._idActividad()
        if idActividad is None:
            return
        try:
            self.app.asistencia.getSesionesHastaHoy(idActividad)
        except AsistenciaError as error:
            self.resumen.configure(text="")
            self.aviso.mostrar(str(error), "info")
            return
        r = self.app.asistencia.getResumen(idActividad)
        for s in r["sesiones"]:
            asistentes = f"{s['asistentes']} de {s['inscritos']}" if s["estado"] == REGISTRADA else "—"
            pct = f"{s['porcentaje']} %" if s["porcentaje"] is not None else "—"
            self.tablaSesiones.insert("", "end", iid=f"{s['fecha']}|{s['horaInicio']}",
                                      tags=(self.COLOR_ESTADO.get(s["estado"], ""),), values=(
                describirFecha(s["fecha"]), f"{s['horaInicio']}–{s['horaFin']}", s["estado"], asistentes, pct))
        media = ("sin sesiones registradas" if r["mediaAsistentes"] is None
                 else f"media de {r['mediaAsistentes']:.1f} asistentes ({r['mediaPorcentaje']} %)")
        self.resumen.configure(text=f"{r['registradas']} de {r['totales']} sesiones registradas · {media}")

    def _sesionElegida(self):
        sel = self.tablaSesiones.selection()
        return sel[0].split("|") if sel else (None, None)

    def _cargarHoja(self):
        self._limpiarHoja()
        fecha, hora = self._sesionElegida()
        if fecha is None:
            return
        idActividad = self._idActividad()
        estado = self.tablaSesiones.item(f"{fecha}|{hora}", "values")[2]
        self.tituloHoja.configure(text=f"{describirFecha(fecha)} {hora}")
        if estado == CANCELADA:
            self.aviso.mostrar("La sesión está cancelada: no se registra asistencia", "info")
            return
        self.botonCancelar.configure(state="normal" if estado == SIN_REGISTRAR else "disabled")
        try:
            hoja = self.app.asistencia.getHojaAsistencia(idActividad, fecha, hora)
        except AsistenciaError as error:
            self.aviso.mostrar(str(error), "info")
            return
        self.aviso.ocultar()
        for p in hoja:
            iid = str(p["idInscripcion"])
            #Sin registrar se propone "Sí" para todos; se marca a quien no vino
            self.marcas[iid] = True if p["asistio"] is None else p["asistio"]
            self.tablaHoja.insert("", "end", iid=iid, values=(f"{p['nombre']} {p['apellidos']}", ""))
            self._pintar(iid)
        self.botonGuardar.configure(state="normal",
                                    text="Corregir asistencia" if estado == REGISTRADA else "Guardar asistencia")

    def _pintar(self, iid):
        si = self.marcas[iid]
        self.tablaHoja.set(iid, "asistio", "Sí" if si else "No")
        self.tablaHoja.item(iid, tags=("si" if si else "no",))

    def alternar(self, iid):
        if iid in self.marcas:
            self.marcas[iid] = not self.marcas[iid]
            self._pintar(iid)

    def _clicHoja(self, evento):
        iid = self.tablaHoja.identify_row(evento.y)
        if iid:
            self.alternar(iid)

    def guardar(self):
        fecha, hora = self._sesionElegida()
        if fecha is None:
            self.aviso.mostrar("Elige una sesión", "info")
            return
        try:
            mensaje = self.app.asistencia.registrarAsistencia(
                self._idActividad(), fecha, hora, {int(i): v for i, v in self.marcas.items()})
        except AsistenciaError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self._cargarSesiones()
        self.tablaSesiones.selection_set(f"{fecha}|{hora}")
        self._cargarHoja()
        self.aviso.mostrar(mensaje, "ok")

    def cancelarSesion(self):
        fecha, hora = self._sesionElegida()
        if fecha is None:
            return
        if not self.app.confirmar("Cancelar sesión",
                                  f"¿Cancelar la sesión del {describirFecha(fecha)} {hora} por causa de fuerza "
                                  "mayor? La cancelación es definitiva y no se registrará asistencia."):
            return
        try:
            mensaje = self.app.asistencia.cancelarSesion(self._idActividad(), fecha, hora)
        except AsistenciaError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self._cargarSesiones()
        self.aviso.mostrar(mensaje, "ok")


#--------------------------------------------------------------------------------------------
def _pct(valor):
    return "—" if valor is None else f"{valor} %"


class PaginaOcupacionReal(Pagina):
    '''HU18: comparar la ocupación planificada (inscritos) con la real (asistencia media).'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Ocupación planificada y real",
                 "Compara los inscritos con la asistencia media para detectar plazas que no se aprovechan. "
                 "Deja las fechas vacías para el curso completo.")
        filtros = tarjeta(self, fill="x")
        fila = tk.Frame(filtros, bg=e.TARJETA)
        fila.pack(fill="x")
        for i, (texto, peso) in enumerate((("Desde (AAAA-MM-DD)", 2), ("Hasta (AAAA-MM-DD)", 2),
                                           ("Instalación", 3), ("Actividad", 3), ("", 0))):
            fila.columnconfigure(i, weight=peso)
            ttk.Label(fila, text=texto, style="Campo.TLabel").grid(row=0, column=i, sticky="w", padx=(0, 12))
        self.desde = ttk.Entry(fila)
        self.desde.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.hasta = ttk.Entry(fila)
        self.hasta.grid(row=1, column=1, sticky="ew", padx=(0, 12))
        self.comboInstalacion = ttk.Combobox(fila, state="readonly")
        self.comboInstalacion.grid(row=1, column=2, sticky="ew", padx=(0, 12))
        self.comboActividad = ttk.Combobox(fila, state="readonly")
        self.comboActividad.grid(row=1, column=3, sticky="ew", padx=(0, 12))
        ttk.Button(fila, text="Consultar", style="Primario.TButton",
                   command=self.consultar).grid(row=1, column=4, sticky="e")

        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(14, 0))

        informe = tarjeta(self, fill="both", expand=True, pady=(14, 0))
        self.titulo = ttk.Label(informe, text="Pulsa Consultar", style="Seccion.TLabel")
        self.titulo.pack(anchor="w", pady=(0, 8))
        marco, self.tablaInforme = tabla(informe, [
            ("actividad", "Actividad", 170, True), ("instalacion", "Instalación", 130, True),
            ("plazas", "Plazas", 55, False), ("inscritos", "Inscritos", 95, False),
            ("realPlazas", "Real s/plazas", 95, False), ("realInscritos", "Real s/inscritos", 105, False),
            ("diferencia", "Diferencia", 80, False), ("sesiones", "Sesiones", 95, False)], altura=8)
        marco.pack(fill="both", expand=True)
        self.tablaInforme.tag_configure("destacada", background=e.AVISO_FONDO, foreground=e.AVISO_TEXTO)
        self.tablaInforme.tag_configure("sinDatos", foreground=e.NO_CABE_TEXTO)
        tk.Label(informe, text=f"En naranja: diferencia igual o superior al {UMBRAL_DIFERENCIA} % "
                               "(umbral provisional). Diferencia = (inscritos − asistencia media) / inscritos.",
                 bg=e.TARJETA, fg=e.TEXTO_SUAVE, font=e.fuente(9)).pack(anchor="w", pady=(6, 10))
        ttk.Label(informe, text="Totales por instalación", style="Seccion.TLabel").pack(anchor="w", pady=(0, 6))
        marco, self.tablaTotales = tabla(informe, [
            ("instalacion", "Instalación", 200, True), ("plazas", "Plazas", 70, False),
            ("inscritos", "Inscritos", 110, False), ("real", "Asistencia media", 150, False),
            ("diferencia", "Diferencia", 90, False)], altura=3)
        marco.pack(fill="x")

    def refrescar(self):
        modelo = self.app.ocupacionReal
        self.instalaciones = modelo.getInstalaciones()
        self.actividades = modelo.getActividades()
        self.comboInstalacion["values"] = ["Todas"] + [i["nombre"] for i in self.instalaciones]
        self.comboActividad["values"] = ["Todas"] + [describirActividad(a) + f" ({a['id']})" for a in self.actividades]
        if self.comboInstalacion.current() < 0:
            self.comboInstalacion.current(0)
        if self.comboActividad.current() < 0:
            self.comboActividad.current(0)

    def consultar(self):
        self.aviso.ocultar()
        try:
            desde = validate_date(self.desde.get(), allow_empty=True)
            hasta = validate_date(self.hasta.get(), allow_empty=True)
        except ValidationError as error:
            self.aviso.mostrar(str(error), "error")
            return
        if (desde is None) != (hasta is None):
            self.aviso.mostrar("Indica las dos fechas o ninguna (curso completo)", "info")
            return
        iInst, iAct = self.comboInstalacion.current(), self.comboActividad.current()
        idInstalacion = self.instalaciones[iInst - 1]["id"] if iInst > 0 else None
        idActividad = self.actividades[iAct - 1]["id"] if iAct > 0 else None
        self.tablaInforme.delete(*self.tablaInforme.get_children())
        self.tablaTotales.delete(*self.tablaTotales.get_children())
        try:
            res = self.app.ocupacionReal.getInforme(desde, hasta, idInstalacion, idActividad)
        except OcupacionRealError as error:
            self.titulo.configure(text="Sin resultados")
            self.aviso.mostrar(str(error), "info")
            return
        self.titulo.configure(text=f"Del {res['desde']} al {res['hasta']}")
        for f in res["actividades"]:
            if f["sinDatos"]:
                real = ("Sin datos", "—", "—")
                tag = "sinDatos"
            else:
                real = (f"{_pct(f['realSobrePlazas'])} ({f['mediaAsistentes']:.1f})",
                        _pct(f["realSobreInscritos"]), _pct(f["diferencia"]))
                tag = "destacada" if f["destacada"] else ""
            self.tablaInforme.insert("", "end", iid=str(f["id"]), tags=(tag,), values=(
                describirActividad(f), f["instalacion"], f["plazas"],
                f"{f['inscritos']} ({_pct(f['planificada'])})", *real,
                f"{f['sesionesRegistradas']} de {f['sesionesTotales']}"))
        for t in res["totales"]:
            self.tablaTotales.insert("", "end", values=(
                t["instalacion"], t["plazas"], f"{t['inscritos']} ({_pct(t['planificada'])})",
                f"{t['mediaAsistentes']:.1f} ({_pct(t['realSobrePlazas'])})", _pct(t["diferencia"])))
        if not res["totales"]:
            self.aviso.mostrar("Ninguna actividad tiene sesiones con asistencia registrada en el periodo", "info")
