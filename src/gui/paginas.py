'''
Pantallas de la interfaz gráfica. Cada página usa los mismos modelos que la versión de consola,
de modo que las reglas de las historias de usuario están en un único sitio.
'''
import tkinter as tk
from tkinter import ttk

from src.inscripciones.inscripcionModel import InscripcionError
from src.ofertas.actividadModel import ActividadError
from src.ofertas.ofertaModel import OfertaError
from src.gui import estilos as e
from src.gui.componentes import Aviso, cabecera, campo, tabla, tarjeta
from src.instalaciones.instalacionModel import (
    DIAS_SEMANA,
    AsignacionError,
    describirActividad,
    describirFranja,
)
from src.instalaciones.ocupacionModel import APERTURA, CIERRE, OcupacionError
from src.personas.personaModel import PersonaError
from src.util.validation import ValidationError, validate_date, validate_positive_int


#"2026-10-01" -> "01/10/26"
def fechaCorta(fecha):
    anio, mes, dia = fecha.split("-")
    return f"{dia}/{mes}/{anio[2:]}"


class Pagina(ttk.Frame):
    '''Página base: se refresca cada vez que se muestra.'''

    def __init__(self, master, app):
        super().__init__(master, padding=(e.px(32), e.px(26)))
        self.app = app

    def refrescar(self):
        pass


#--------------------------------------------------------------------------------------------
class PaginaInicio(Pagina):
    '''Resumen del centro con tarjetas y accesos rápidos.'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Bienvenido", "Resumen del Centro Deportivo Inteligente")
        self.fila = ttk.Frame(self)
        self.fila.pack(fill="x")
        self.valores = {}
        datos = [("instalaciones", "Instalaciones", "registradas en el centro"),
                 ("actividades", "Actividades", "en la oferta del curso"),
                 ("sinInstalacion", "Sin instalación", "pendientes de asignar"),
                 ("socios", "Socios", "y no socios registrados")]
        for i, (clave, titulo, pie) in enumerate(datos):
            self.fila.columnconfigure(i, weight=1, uniform="tarjetas")
            caja = tk.Frame(self.fila, bg=e.COLORES_TARJETAS[i])
            caja.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            interior = tk.Frame(caja, bg=e.TARJETA, padx=18, pady=14)
            interior.pack(fill="both", expand=True, padx=(5, 0))
            tk.Label(interior, text=titulo.upper(), bg=e.TARJETA, fg=e.TEXTO_SUAVE,
                     font=e.fuente(9, "bold")).pack(anchor="w")
            valor = tk.Label(interior, text="-", bg=e.TARJETA, fg=e.TEXTO, font=e.fuente(28, "bold"))
            valor.pack(anchor="w", pady=(2, 0))
            pieLabel = tk.Label(interior, text=pie, bg=e.TARJETA, fg=e.TEXTO_SUAVE, font=e.fuente(9))
            pieLabel.pack(anchor="w")
            self.valores[clave] = (valor, pieLabel)

        accesos = tarjeta(self, fill="x", pady=(22, 0))
        ttk.Label(accesos, text="¿Qué quieres hacer?", style="Seccion.TLabel").pack(anchor="w")
        botones = tk.Frame(accesos, bg=e.TARJETA)
        botones.pack(anchor="w", pady=(12, 0))
        for texto, pagina in (("Asignar una instalación", "asignar"),
                              ("Ver la ocupación de una instalación", "ocupacion"),
                              ("Registrar o consultar personas", "personas")):
            ttk.Button(botones, text=texto, style="Secundario.TButton",
                       command=lambda p=pagina: app.mostrar(p)).pack(side="left", padx=(0, 10))

        horario = tarjeta(self, fill="x", pady=(16, 0))
        ttk.Label(horario, text="Horario del centro", style="Seccion.TLabel").pack(anchor="w")
        tk.Label(horario, text=f"Todos los días de {APERTURA} a {CIERRE} (salvo festivos). "
                               "Curso de octubre a junio.",
                 bg=e.TARJETA, fg=e.TEXTO_SUAVE).pack(anchor="w", pady=(6, 0))

    def refrescar(self):
        inst = self.app.instalaciones
        personas = self.app.personas.contarPersonas()
        self.valores["instalaciones"][0].configure(text=len(inst.getInstalaciones()))
        self.valores["actividades"][0].configure(text=inst.countActividades())
        self.valores["sinInstalacion"][0].configure(text=len(inst.getActividadesSinInstalacion()))
        self.valores["socios"][0].configure(text=personas["socios"])
        self.valores["socios"][1].configure(text=f"y {personas['noSocios']} no socios registrados")


#--------------------------------------------------------------------------------------------
class PaginaAsignar(Pagina):
    '''HU3: asignar una instalación a una actividad.'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Asignar instalación",
                 "Elige una actividad sin instalación y la instalación donde se impartirá")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.columnconfigure(1, weight=0, minsize=e.px(290))
        cuerpo.rowconfigure(0, weight=1)

        izq = tarjeta(cuerpo)
        izq.contenedor.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(izq, text="1. Actividad", style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))
        marco, self.tablaActividades = tabla(izq, [
            ("id", "ID", 36, False), ("actividad", "Actividad", 170, True),
            ("plazas", "Plazas", 56, False), ("horario", "Horario", 190, True),
            ("fechas", "Periodo", 160, False)], altura=10)
        marco.pack(fill="both", expand=True)
        self.tablaActividades.bind("<<TreeviewSelect>>", lambda ev: self._marcarCapacidad())

        der = tarjeta(cuerpo)
        der.contenedor.grid(row=0, column=1, sticky="nsew")
        ttk.Label(der, text="2. Instalación", style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))
        marco, self.tablaInstalaciones = tabla(der, [
            ("id", "ID", 36, False), ("nombre", "Nombre", 150, True),
            ("capacidad", "Capacidad", 76, False)], altura=10)
        marco.pack(fill="both", expand=True)
        self.tablaInstalaciones.tag_configure("noCabe", foreground=e.NO_CABE_TEXTO)

        pie = ttk.Frame(self)
        pie.pack(fill="x", pady=(16, 0))
        self.boton = ttk.Button(pie, text="Asignar instalación", style="Primario.TButton",
                                command=self.asignar)
        self.boton.pack(side="right")
        ttk.Label(pie, text="Las instalaciones en gris no tienen capacidad suficiente para la actividad elegida.",
                  style="Subtitulo.TLabel").pack(side="left")

    def refrescar(self):
        self.aviso.ocultar()
        inst = self.app.instalaciones
        self.tablaActividades.delete(*self.tablaActividades.get_children())
        self.tablaInstalaciones.delete(*self.tablaInstalaciones.get_children())
        self.plazas = {}
        if inst.countActividades() == 0:
            self.aviso.mostrar("No hay actividades registradas", "info")
        elif not inst.getActividadesSinInstalacion():
            self.aviso.mostrar("Todas las actividades tienen instalación asignada", "info")
        for a in inst.getActividadesSinInstalacion():
            horario = ", ".join(describirFranja(h) for h in inst.getHorarios(a["id"])) or "sin horario"
            self.tablaActividades.insert("", "end", iid=str(a["id"]), values=(
                a["id"], describirActividad(a), a["plazas"], horario,
                f"{fechaCorta(a['fechaInicio'])} – {fechaCorta(a['fechaFin'])}"))
            self.plazas[str(a["id"])] = a["plazas"]
        instalaciones = inst.getInstalaciones()
        if not instalaciones:
            self.aviso.mostrar("No hay instalaciones registradas", "info")
        self.capacidad = {}
        for i in instalaciones:
            self.tablaInstalaciones.insert("", "end", iid=str(i["id"]),
                                           values=(i["id"], i["nombre"], i["capacidad"]))
            self.capacidad[str(i["id"])] = i["capacidad"]

    #Marca en gris las instalaciones con menos capacidad que plazas tiene la actividad elegida
    def _marcarCapacidad(self):
        sel = self.tablaActividades.selection()
        plazas = self.plazas.get(sel[0]) if sel else None
        for iid in self.tablaInstalaciones.get_children():
            noCabe = plazas is not None and self.capacidad[iid] < plazas
            self.tablaInstalaciones.item(iid, tags=("noCabe",) if noCabe else ())

    def asignar(self):
        actividad = self.tablaActividades.selection()
        instalacion = self.tablaInstalaciones.selection()
        if not actividad or not instalacion:
            self.aviso.mostrar("Selecciona una actividad y una instalación", "info")
            return
        try:
            mensaje = self.app.instalaciones.asignarInstalacion(int(actividad[0]), int(instalacion[0]))
        except AsignacionError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.refrescar()
        self.aviso.mostrar(mensaje, "ok")


#--------------------------------------------------------------------------------------------
class PaginaOcupacion(Pagina):
    '''HU9: consultar la ocupación de una instalación (lista por día y hora).'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Ocupación de instalaciones",
                 f"Franjas ocupadas y huecos libres de {APERTURA} a {CIERRE}. "
                 "Deja las fechas vacías para ver el curso completo.")

        filtros = tarjeta(self, fill="x")
        fila = tk.Frame(filtros, bg=e.TARJETA)
        fila.pack(fill="x")
        for i, (texto, peso) in enumerate((("Instalación", 3), ("Desde (AAAA-MM-DD)", 2),
                                           ("Hasta (AAAA-MM-DD)", 2), ("", 0))):
            fila.columnconfigure(i, weight=peso)
            ttk.Label(fila, text=texto, style="Campo.TLabel").grid(row=0, column=i, sticky="w",
                                                                    padx=(0, 12))
        self.combo = ttk.Combobox(fila, state="readonly")
        self.combo.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.desde = ttk.Entry(fila)
        self.desde.grid(row=1, column=1, sticky="ew", padx=(0, 12))
        self.hasta = ttk.Entry(fila)
        self.hasta.grid(row=1, column=2, sticky="ew", padx=(0, 12))
        ttk.Button(fila, text="Consultar", style="Primario.TButton",
                   command=self.consultar).grid(row=1, column=3, sticky="e")

        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(14, 0))

        resultado = tarjeta(self, fill="both", expand=True, pady=(14, 0))
        self.titulo = ttk.Label(resultado, text="Elige una instalación y pulsa Consultar",
                                style="Seccion.TLabel")
        self.titulo.pack(anchor="w", pady=(0, 10))
        marco, self.lista = tabla(resultado, [
            ("franja", "Franja", 130, False), ("estado", "Estado", 90, False),
            ("actividad", "Actividad", 260, True), ("fechas", "Fechas", 200, True)],
            altura=12, arbol=True)
        marco.pack(fill="both", expand=True)
        self.lista.tag_configure("dia", background=e.DIA_FONDO, font=e.fuente(10, "bold"))
        self.lista.tag_configure("ocupada", background=e.OCUPADA_FONDO)
        self.lista.tag_configure("libre", background=e.LIBRE_FONDO)
        leyenda = tk.Frame(resultado, bg=e.TARJETA)
        leyenda.pack(anchor="w", pady=(10, 0))
        for color, texto in ((e.OCUPADA_FONDO, "Ocupada"), (e.LIBRE_FONDO, "Libre")):
            tk.Label(leyenda, bg=color, width=2, relief="flat").pack(side="left")
            tk.Label(leyenda, text=texto, bg=e.TARJETA, fg=e.TEXTO_SUAVE).pack(side="left", padx=(4, 14))

    def refrescar(self):
        self.instalaciones = self.app.instalaciones.getInstalaciones()
        self.combo["values"] = [i["nombre"] for i in self.instalaciones]
        if not self.instalaciones:
            self.aviso.mostrar("No hay instalaciones registradas", "info")

    def consultar(self):
        self.aviso.ocultar()
        indice = self.combo.current()
        if indice < 0:
            self.aviso.mostrar("Selecciona una instalación", "info")
            return
        try:
            desde = validate_date(self.desde.get(), allow_empty=True)
            hasta = validate_date(self.hasta.get(), allow_empty=True)
        except ValidationError as error:
            self.aviso.mostrar(str(error), "error")
            return
        if (desde is None) != (hasta is None):
            self.aviso.mostrar("Indica las dos fechas o ninguna (curso completo)", "info")
            return
        try:
            res = self.app.ocupacion.consultarOcupacion(self.instalaciones[indice]["id"], desde, hasta)
        except OcupacionError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.mostrarOcupacion(res)

    def mostrarOcupacion(self, res):
        self.lista.delete(*self.lista.get_children())
        self.titulo.configure(text=f"{res['instalacion']['nombre']} · del {res['fechaInicio']} "
                                   f"al {res['fechaFin']}")
        if not res["dias"]:
            self.aviso.mostrar(f"La instalación está libre en todo el periodo "
                               f"({int(APERTURA[:2])}:00–{CIERRE})", "ok")
            return
        for dia, nombre in DIAS_SEMANA.items():
            padre = self.lista.insert("", "end", text=nombre.capitalize(), open=True, tags=("dia",))
            ocupacion = res["dias"].get(dia, {"ocupadas": [], "libres": [(APERTURA, CIERRE)]})
            filas = [(f["horaInicio"], (f"{f['horaInicio']}–{f['horaFin']}", "Ocupada",
                                         describirActividad(f), f"{f['fechaInicio']} a {f['fechaFin']}"),
                      "ocupada") for f in ocupacion["ocupadas"]]
            filas += [(ini, (f"{ini}–{fin}", "Libre", "", ""), "libre") for ini, fin in ocupacion["libres"]]
            for _, valores, tag in sorted(filas, key=lambda x: x[0]):
                self.lista.insert(padre, "end", values=valores, tags=(tag,))


#--------------------------------------------------------------------------------------------
class PaginaPersonas(Pagina):
    '''HU8: registrar no socios y consultar personas por DNI o número de socio.'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Personas", "Registra a los no socios y consulta los datos de cualquier persona")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=1, uniform="col")
        cuerpo.columnconfigure(1, weight=1, uniform="col")
        cuerpo.rowconfigure(0, weight=1)

        #Registro
        reg = tarjeta(cuerpo)
        reg.contenedor.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(reg, text="Registrar persona no socia", style="Seccion.TLabel").pack(anchor="w")
        tk.Label(reg, text="Obligatorios: DNI, nombre, apellidos y un teléfono o correo",
                 bg=e.TARJETA, fg=e.TEXTO_SUAVE, font=e.fuente(9)).pack(anchor="w")
        self.campos = {}
        for clave, texto in (("dni", "DNI"), ("nombre", "Nombre"), ("apellidos", "Apellidos"),
                             ("fecha", "Fecha de nacimiento (AAAA-MM-DD, opcional)"),
                             ("telefono", "Teléfono"), ("correo", "Correo")):
            self.campos[clave] = campo(reg, texto)
        ttk.Button(reg, text="Registrar", style="Primario.TButton",
                   command=self.registrar).pack(anchor="e", pady=(16, 0))

        #Consulta
        con = tarjeta(cuerpo)
        con.contenedor.grid(row=0, column=1, sticky="nsew")
        ttk.Label(con, text="Consultar persona", style="Seccion.TLabel").pack(anchor="w")
        self.tipoBusqueda = tk.StringVar(value="dni")
        radios = tk.Frame(con, bg=e.TARJETA)
        radios.pack(anchor="w", pady=(8, 0))
        ttk.Radiobutton(radios, text="DNI", value="dni", variable=self.tipoBusqueda).pack(side="left")
        ttk.Radiobutton(radios, text="Número de socio", value="socio",
                        variable=self.tipoBusqueda).pack(side="left", padx=(14, 0))
        busqueda = tk.Frame(con, bg=e.TARJETA)
        busqueda.pack(fill="x", pady=(8, 0))
        self.identificador = ttk.Entry(busqueda)
        self.identificador.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.identificador.bind("<Return>", lambda ev: self.consultar())
        ttk.Button(busqueda, text="Buscar", style="Primario.TButton",
                   command=self.consultar).pack(side="right")

        self.ficha = tk.Frame(con, bg=e.TARJETA)
        self.ficha.pack(fill="both", expand=True, pady=(18, 0))

    def _limpiarFicha(self):
        for hijo in self.ficha.winfo_children():
            hijo.destroy()

    #Ficha con los datos de una persona y una etiqueta de socio / no socio
    def mostrarFicha(self, p):
        self._limpiarFicha()
        cab = tk.Frame(self.ficha, bg=e.TARJETA)
        cab.pack(fill="x")
        iniciales = (p["nombre"][:1] + p["apellidos"][:1]).upper()
        tk.Label(cab, text=iniciales, bg=e.NAVY, fg="white", font=e.fuente(14, "bold"),
                 width=3, height=1, pady=8).pack(side="left")
        nombre = tk.Frame(cab, bg=e.TARJETA, padx=12)
        nombre.pack(side="left", fill="x")
        tk.Label(nombre, text=f"{p['nombre']} {p['apellidos']}", bg=e.TARJETA, fg=e.TEXTO,
                 font=e.fuente(13, "bold")).pack(anchor="w")
        if p["numSocio"] is not None:
            texto, fondo, color = f"SOCIO Nº {p['numSocio']}", e.OK_FONDO, e.OK_TEXTO
        else:
            texto, fondo, color = "NO SOCIO", e.DIA_FONDO, e.TEXTO_SUAVE
        tk.Label(nombre, text=texto, bg=fondo, fg=color, font=e.fuente(8, "bold"),
                 padx=8, pady=2).pack(anchor="w", pady=(4, 0))

        datos = tk.Frame(self.ficha, bg=e.TARJETA)
        datos.pack(fill="x", pady=(16, 0))
        filas = [("DNI", p["dni"]), ("Fecha de nacimiento", p["fechaNacimiento"] or "—"),
                 ("Teléfono", p["telefono"] or "—"), ("Correo", p["correo"] or "—")]
        if p["numSocio"] is not None:
            filas.append(("Socio desde", p["fechaAltaSocio"]))
        for i, (etiqueta, valor) in enumerate(filas):
            tk.Label(datos, text=etiqueta, bg=e.TARJETA, fg=e.TEXTO_SUAVE,
                     font=e.fuente(9)).grid(row=i, column=0, sticky="w", pady=3)
            tk.Label(datos, text=valor, bg=e.TARJETA, fg=e.TEXTO).grid(row=i, column=1, sticky="w",
                                                                       padx=(18, 0), pady=3)

    def registrar(self):
        v = {clave: entrada.get() for clave, entrada in self.campos.items()}
        try:
            mensaje = self.app.personas.registrarNoSocio(v["dni"], v["nombre"], v["apellidos"],
                                                         v["fecha"], v["telefono"], v["correo"])
        except PersonaError as error:
            self.aviso.mostrar(str(error), "error")
            if error.persona is not None:
                self.identificador.delete(0, "end")
                self.mostrarFicha(error.persona)
            return
        self.aviso.mostrar(mensaje, "ok")
        self.identificador.delete(0, "end")
        self.mostrarFicha(self.app.personas.getPersonaPorDni(v["dni"]))
        for entrada in self.campos.values():
            entrada.delete(0, "end")

    def consultar(self):
        self.aviso.ocultar()
        texto = self.identificador.get()
        if self.tipoBusqueda.get() == "dni":
            persona = self.app.personas.getPersonaPorDni(texto)
        else:
            try:
                persona = self.app.personas.getPersonaPorNumSocio(validate_positive_int(texto))
            except ValidationError as error:
                self.aviso.mostrar(f"Número de socio no válido. {error}", "error")
                return
        if persona is None:
            self._limpiarFicha()
            self.aviso.mostrar("No existe ninguna persona con ese identificador", "info")
        else:
            self.mostrarFicha(persona)

#--------------------------------------------------------------------------------------------
class PaginaOfertas(Pagina):
    '''HU1/HU2/HU3/HU4: crear la oferta del curso, definir periodos y añadir/modificar actividades.'''

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(self, "Ofertas y actividades",
                 "Crea la oferta del curso, define los periodos de inscripción y gestiona las actividades")
        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))

        ofertaCard = tarjeta(self, fill="x")
        ttk.Label(ofertaCard, text="Oferta del curso", style="Seccion.TLabel").pack(anchor="w")
        self.infoOferta = tk.Label(ofertaCard, text="Cargando...", bg=e.TARJETA, fg=e.TEXTO_SUAVE,
                                   font=e.fuente(9), justify="left")
        self.infoOferta.pack(anchor="w", pady=(4, 10))

        filaOferta = tk.Frame(ofertaCard, bg=e.TARJETA)
        filaOferta.pack(fill="x")
        self.curso = campo(filaOferta, "Curso (ej. 2026-2027)")
        ttk.Button(filaOferta, text="Crear oferta", style="Primario.TButton",
                   command=self.crearOferta).pack(side="left", padx=(12, 0), pady=(18, 0))

        filaPeriodos = tk.Frame(ofertaCard, bg=e.TARJETA)
        filaPeriodos.pack(fill="x", pady=(14, 0))
        self.inicioSocios = campo(filaPeriodos, "Inicio insc. socios")
        self.finSocios = campo(filaPeriodos, "Fin insc. socios")
        self.inicioNoSocios = campo(filaPeriodos, "Inicio insc. no socios")
        self.finNoSocios = campo(filaPeriodos, "Fin insc. no socios")
        ttk.Button(filaPeriodos, text="Definir periodos", style="Secundario.TButton",
                   command=self.definirPeriodos).pack(side="left", padx=(12, 0), pady=(18, 0))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True, pady=(18, 0))
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.columnconfigure(1, weight=0, minsize=e.px(300))
        cuerpo.rowconfigure(0, weight=1)

        izq = tarjeta(cuerpo)
        izq.contenedor.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(izq, text="Actividades de la oferta", style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))
        marco, self.tablaActividades = tabla(izq, [
            ("id", "ID", 36, False), ("actividad", "Actividad", 160, True),
            ("plazas", "Plazas", 56, False), ("horario", "Horario", 170, True),
            ("fechas", "Periodo", 150, False)], altura=12)
        marco.pack(fill="both", expand=True)
        self.tablaActividades.bind("<<TreeviewSelect>>", lambda ev: self._cargarSeleccion())

        der = tarjeta(cuerpo)
        der.contenedor.grid(row=0, column=1, sticky="nsew")
        self.tituloFormulario = ttk.Label(der, text="Añadir actividad", style="Seccion.TLabel")
        self.tituloFormulario.pack(anchor="w", pady=(0, 10))
        self.modalidad = campo(der, "Modalidad (1 Nat., 2 Pilates, 3 Acond., 4 Pádel, 5 Tenis)")
        self.nivel = campo(der, "Nivel (1 Iniciación, 2 Medio, 3 Avanzado)")
        self.plazas = campo(der, "Plazas")
        self.fechaInicio = campo(der, "Fecha inicio (AAAA-MM-DD)")
        self.fechaFin = campo(der, "Fecha fin (AAAA-MM-DD)")
        self.dia = campo(der, "Día semana (1 lunes...7 domingo)")
        self.horaInicio = campo(der, "Hora inicio (HH:MM)")
        self.horaFin = campo(der, "Hora fin (HH:MM)")
        botones = tk.Frame(der, bg=e.TARJETA)
        botones.pack(fill="x", pady=(14, 0))
        self.botonGuardar = ttk.Button(botones, text="Añadir", style="Primario.TButton",
                                       command=self.guardar)
        self.botonGuardar.pack(side="left")
        ttk.Button(botones, text="Nueva actividad", style="Secundario.TButton",
                  command=self._limpiarFormulario).pack(side="left", padx=(10, 0))

        self.idOferta = None
        self.idActividadSeleccionada = None

    def refrescar(self):
        self.aviso.ocultar()
        oferta = self.app.ofertas.getOfertaActiva()
        if oferta is None:
            self.infoOferta.configure(text="No hay ninguna oferta activa todavía.")
            self.tablaActividades.delete(*self.tablaActividades.get_children())
            self.idOferta = None
            return
        self.idOferta = oferta["id"]
        periodos = ("Periodos sin definir" if oferta["inicioInscripcionSocios"] is None else
                   f"Socios: {oferta['inicioInscripcionSocios']} a {oferta['finInscripcionSocios']} · "
                   f"No socios: {oferta['inicioInscripcionNoSocios']} a {oferta['finInscripcionNoSocios']}")
        self.infoOferta.configure(
            text=f"Curso {oferta['curso']} · {oferta['fechaInicio']} a {oferta['fechaFin']} · {oferta['estado']}\n"
                 f"{periodos}")
        self._cargarActividades()
        self._limpiarFormulario()

    def _cargarActividades(self):
        self.tablaActividades.delete(*self.tablaActividades.get_children())
        for a in self.app.actividades.getActividadesDeOferta(self.idOferta):
            horarios = self.app.actividades.getHorarios(a["id"])
            horario = ", ".join(describirFranja(h) for h in horarios) or "sin horario"
            self.tablaActividades.insert("", "end", iid=str(a["id"]), values=(
                a["id"], describirActividad(a), a["plazas"], horario,
                f"{fechaCorta(a['fechaInicio'])} – {fechaCorta(a['fechaFin'])}"))

    def _rellenar(self, entrada, valor):
        entrada.delete(0, "end")
        entrada.insert(0, valor)

    def _limpiarFormulario(self):
        self.idActividadSeleccionada = None
        self.tituloFormulario.configure(text="Añadir actividad")
        self.botonGuardar.configure(text="Añadir")
        for entrada in (self.modalidad, self.nivel, self.plazas, self.fechaInicio, self.fechaFin,
                       self.dia, self.horaInicio, self.horaFin):
            entrada.delete(0, "end")
        self.tablaActividades.selection_remove(*self.tablaActividades.selection())

    def _cargarSeleccion(self):
        sel = self.tablaActividades.selection()
        if not sel:
            return
        a = self.app.actividades.getActividad(int(sel[0]))
        self.idActividadSeleccionada = a["id"]
        self.tituloFormulario.configure(text=f"Modificar actividad {a['id']}")
        self.botonGuardar.configure(text="Guardar cambios")
        self._rellenar(self.modalidad, a["idModalidad"])
        self._rellenar(self.nivel, a["idNivel"])
        self._rellenar(self.plazas, a["plazas"])
        self._rellenar(self.fechaInicio, a["fechaInicio"])
        self._rellenar(self.fechaFin, a["fechaFin"])
        horarios = self.app.actividades.getHorarios(a["id"])
        if horarios:
            self._rellenar(self.dia, horarios[0]["diaSemana"])
            self._rellenar(self.horaInicio, horarios[0]["horaInicio"])
            self._rellenar(self.horaFin, horarios[0]["horaFin"])

    def crearOferta(self):
        curso = self.curso.get().strip()
        try:
            mensaje = self.app.ofertas.crearOferta(curso)
        except OfertaError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.curso.delete(0, "end")
        self.refrescar()
        self.aviso.mostrar(mensaje, "ok")

    def definirPeriodos(self):
        if self.idOferta is None:
            self.aviso.mostrar("Primero crea la oferta del curso", "info")
            return
        try:
            mensaje = self.app.ofertas.definirPeriodos(
                self.idOferta, self.inicioSocios.get().strip(), self.finSocios.get().strip(),
                self.inicioNoSocios.get().strip(), self.finNoSocios.get().strip())
        except OfertaError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.refrescar()
        self.aviso.mostrar(mensaje, "ok")

    def _leerFormulario(self):
        return (int(self.modalidad.get()), int(self.nivel.get()), self.fechaInicio.get().strip(),
               self.fechaFin.get().strip(), int(self.plazas.get()),
               [(int(self.dia.get()), self.horaInicio.get().strip(), self.horaFin.get().strip())])

    def guardar(self):
        if self.idOferta is None:
            self.aviso.mostrar("Primero crea la oferta del curso", "info")
            return
        try:
            idModalidad, idNivel, fechaInicio, fechaFin, plazas, horarios = self._leerFormulario()
        except ValueError:
            self.aviso.mostrar("Revisa los campos numéricos (modalidad, nivel, plazas, día)", "error")
            return
        try:
            if self.idActividadSeleccionada is None:
                mensaje = self.app.actividades.anadirActividad(
                    self.idOferta, idModalidad, idNivel, fechaInicio, fechaFin, plazas, horarios)
            else:
                mensaje = self.app.actividades.modificarActividad(
                    self.idActividadSeleccionada, idModalidad, idNivel, fechaInicio, fechaFin,
                    plazas, horarios)
        except ActividadError as error:
            self.aviso.mostrar(str(error), "error")
            return
        self.refrescar()
        self.aviso.mostrar(mensaje, "ok")
#--------------------------------------------------------------------------------------------
class PaginaInscripciones(Pagina):
    """Inscribir una persona registrada en una actividad."""

    def __init__(self, master, app):
        super().__init__(master, app)
        cabecera(
            self,
            "Inscripciones",
            "Identifica a la persona y selecciona la actividad"
        )

        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(0, 14))

        formulario = tarjeta(self, fill="x")

        self.tipoBusqueda = tk.StringVar(value="dni")
        radios = tk.Frame(formulario, bg=e.TARJETA)
        radios.pack(anchor="w")

        ttk.Radiobutton(
            radios, text="DNI", value="dni",
            variable=self.tipoBusqueda
        ).pack(side="left")

        ttk.Radiobutton(
            radios, text="Número de socio", value="socio",
            variable=self.tipoBusqueda
        ).pack(side="left", padx=(14, 0))

        self.identificador = campo(
            formulario, "DNI o número de socio"
        )

        self.infoPeriodos = tk.Label(
            formulario, text="", bg=e.TARJETA,
            fg=e.TEXTO_SUAVE, justify="left",
            anchor="w", font=e.fuente(9)
        )
        self.infoPeriodos.pack(anchor="w", pady=(12, 0))

        ttk.Button(
            self, text="Inscribir",
            style="Primario.TButton",
            command=self.inscribir
        ).pack(anchor="e", pady=(14, 0))

        actividades = tarjeta(
            self, fill="both", expand=True, pady=(14, 0)
        )
        ttk.Label(
            actividades, text="Selecciona una actividad",
            style="Seccion.TLabel"
        ).pack(anchor="w", pady=(0, 10))

        marco, self.tablaActividades = tabla(actividades, [
            ("id", "ID", 40, False),
            ("actividad", "Actividad", 180, True),
            ("plazas", "Plazas totales", 100, False),
            ("horario", "Horario", 220, True),
            ("periodo", "Periodo", 180, False),
        ])
        marco.pack(fill="both", expand=True)

    def refrescar(self):
        self.aviso.ocultar()
        self.tablaActividades.delete(
            *self.tablaActividades.get_children()
        )

        oferta = self.app.ofertas.getOfertaActiva()
        if oferta is None:
            self.infoPeriodos.configure(text="No hay oferta activa")
            self.aviso.mostrar("No hay oferta activa", "info")
            return

        self.infoPeriodos.configure(
            text=(
                "Periodo de socios: "
                f"{oferta['inicioInscripcionSocios'] or 'sin definir'}"
                " a "
                f"{oferta['finInscripcionSocios'] or 'sin definir'}"
                "\nPeriodo de no socios: "
                f"{oferta['inicioInscripcionNoSocios'] or 'sin definir'}"
                " a "
                f"{oferta['finInscripcionNoSocios'] or 'sin definir'}"
            )
        )

        actividades = self.app.actividades.getActividadesDeOferta(
            oferta["id"]
        )
        for actividad in actividades:
            horarios = self.app.actividades.getHorarios(
                actividad["id"]
            )
            horario = ", ".join(
                describirFranja(h) for h in horarios
            ) or "Sin horario"

            self.tablaActividades.insert(
                "", "end", iid=str(actividad["id"]),
                values=(
                    actividad["id"],
                    describirActividad(actividad),
                    actividad["plazas"],
                    horario,
                    f"{fechaCorta(actividad['fechaInicio'])} – "
                    f"{fechaCorta(actividad['fechaFin'])}",
                )
            )

        if not actividades:
            self.aviso.mostrar(
                "La oferta no tiene actividades", "info"
            )

    def inscribir(self):
        seleccion = self.tablaActividades.selection()
        if not seleccion:
            self.aviso.mostrar(
                "Selecciona una actividad", "info"
            )
            return

        identificador = self.identificador.get().strip()
        if not identificador:
            self.aviso.mostrar(
                "Indica el DNI o el número de socio", "info"
            )
            return

        try:
            argumentos = {}
            if self.tipoBusqueda.get() == "dni":
                argumentos["dni"] = identificador
            else:
                argumentos["numSocio"] = validate_positive_int(
                    identificador
                )

            mensaje = self.app.inscripciones.inscribir(
                int(seleccion[0]), **argumentos
            )
        except (InscripcionError, ValidationError) as error:
            self.aviso.mostrar(str(error), "error")
            return

        actividad = self.tablaActividades.item(
            seleccion[0], "values"
        )[1]
        tipo = "info" if "lista de espera" in mensaje else "ok"
        self.aviso.mostrar(
            f"{mensaje}. Actividad: {actividad}", tipo
        )