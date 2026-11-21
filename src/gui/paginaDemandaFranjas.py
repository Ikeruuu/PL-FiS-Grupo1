from tkinter import ttk

from src.gui.componentes import Aviso, cabecera, tabla
from src.gui.paginas import Pagina
from src.inscripciones.demandaFranjasModel import DemandaFranjasError
from src.instalaciones.instalacionModel import DIAS_SEMANA


class PaginaDemandaFranjas(Pagina):

    def __init__(self, master, app):
        super().__init__(master, app)

        cabecera(
            self,
            "Demanda por día y franja",
            "Compara los inscritos, la lista de espera "
            "y la ocupación media"
        )

        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True)

        consulta = ttk.Frame(self.pestanas, padding=12)
        historico = ttk.Frame(self.pestanas, padding=12)

        self.pestanas.add(
            consulta, text="Consultar demanda"
        )
        self.pestanas.add(
            historico, text="Completar horarios históricos"
        )

        self._crearConsulta(consulta)
        self._crearHistorico(historico)

        self.temporadas = []
        self.historicas = []
        self.instalaciones = []
        self.actividadesHistoricas = []

    @staticmethod
    def _combo(master, titulo, ancho):
        marco = ttk.Frame(master)
        marco.pack(
            side="left", fill="x",
            expand=True, padx=(0, 12)
        )

        ttk.Label(marco, text=titulo).pack(anchor="w")

        combo = ttk.Combobox(
            marco, state="readonly", width=ancho
        )
        combo.pack(fill="x")

        return combo

    def _crearConsulta(self, master):
        filtros = ttk.Frame(master)
        filtros.pack(fill="x", pady=(0, 12))

        self.temporada = self._combo(
            filtros, "Temporada", 34
        )
        self.instalacion = self._combo(
            filtros, "Instalación", 24
        )

        self.temporada.bind(
            "<<ComboboxSelected>>",
            lambda ev: self.consultar()
        )
        self.instalacion.bind(
            "<<ComboboxSelected>>",
            lambda ev: self.consultar()
        )

        ttk.Button(
            filtros,
            text="Consultar",
            style="Primario.TButton",
            command=self.consultar
        ).pack(side="right", pady=(18, 0))

        self.aviso = Aviso(master)
        self.aviso.pack(fill="x", pady=(0, 10))

        aclaracion = ttk.Label(
            master,
            justify="left",
            text=(
                "Ocupación media: media de los porcentajes por grupo. "
                "Una actividad cuenta una vez en cada combinación "
                "de día y franja. Los horarios que empiezan a las "
                "20:00 o después no entran en estas franjas."
            )
        )
        aclaracion.pack(fill="x", pady=(0, 10))
        aclaracion.bind(
            "<Configure>",
            lambda ev: aclaracion.configure(
                wraplength=max(200, ev.width)
            )
        )

        marco, self.lista = tabla(master, [
            ("dia", "Día", 110, False),
            ("franja", "Franja horaria", 140, False),
            ("grupos", "Grupos", 75, False),
            ("inscritos", "Inscritos activos", 140, False),
            ("espera", "En espera", 100, False),
            ("total", "Demanda total", 125, False),
            ("ocupacion", "Ocupación media", 150, False),
        ], altura=12)

        self.lista.tag_configure(
            "demanda", background="#DBEAFE"
        )

        barra = ttk.Scrollbar(
            master,
            orient="horizontal",
            command=self.lista.xview
        )
        self.lista.configure(xscrollcommand=barra.set)

        barra.pack(side="bottom", fill="x")
        marco.pack(fill="both", expand=True)

    def _crearHistorico(self, master):
        explicacion = ttk.Label(
            master,
            justify="left",
            text=(
                "Los históricos importados no incluyen el horario "
                "de las clases. Completa aquí la instalación y los "
                "días y horas de cada actividad con información "
                "conocida de esa temporada. Cada fila añadida "
                "representa un inicio semanal de clase."
            )
        )
        explicacion.pack(fill="x", pady=(0, 12))
        explicacion.bind(
            "<Configure>",
            lambda ev: explicacion.configure(
                wraplength=max(200, ev.width)
            )
        )

        fila = ttk.Frame(master)
        fila.pack(fill="x", pady=(0, 10))

        self.temporadaHistorica = self._combo(
            fila, "Temporada importada", 22
        )
        self.actividadHistorica = self._combo(
            fila, "Actividad histórica", 40
        )

        self.temporadaHistorica.bind(
            "<<ComboboxSelected>>",
            lambda ev: self._cambiarHistorica()
        )
        self.actividadHistorica.bind(
            "<<ComboboxSelected>>",
            lambda ev: self._mostrarHorarios()
        )

        fila = ttk.Frame(master)
        fila.pack(fill="x", pady=(0, 12))

        self.instalacionHistorica = self._combo(
            fila, "Instalación", 24
        )
        self.dia = self._combo(
            fila, "Día", 14
        )

        self.dia.configure(
            values=list(DIAS_SEMANA.values())
        )
        self.dia.current(0)

        hora = ttk.Frame(fila)
        hora.pack(side="left", padx=(0, 12))

        ttk.Label(
            hora, text="Hora de inicio (HH:MM)"
        ).pack(anchor="w")

        self.hora = ttk.Entry(hora, width=10)
        self.hora.pack(fill="x")

        ttk.Button(
            fila,
            text="Guardar horario",
            style="Primario.TButton",
            command=self.guardarHorario
        ).pack(side="left", pady=(18, 0))

        self.avisoHistorico = Aviso(master)
        self.avisoHistorico.pack(
            fill="x", pady=(0, 10)
        )

        ttk.Button(
            master,
            text="Quitar horario seleccionado",
            command=self.quitarHorario
        ).pack(anchor="e", pady=(0, 8))

        marco, self.listaHorarios = tabla(master, [
            ("instalacion", "Instalación", 240, True),
            ("dia", "Día", 130, False),
            ("hora", "Hora de inicio", 140, False),
        ], altura=7)

        marco.pack(fill="both", expand=True)

    @staticmethod
    def _ponerOpciones(combo, valores):
        anterior = combo.get()
        combo.configure(values=valores)

        if anterior in valores:
            combo.current(valores.index(anterior))
        elif valores:
            combo.current(0)
        else:
            combo.set("")

    def refrescar(self):
        modelo = self.app.demandaFranjas

        self.temporadas = modelo.getTemporadas()
        self.instalaciones = modelo.getInstalaciones()

        self.historicas = [
            temporada
            for temporada in self.temporadas
            if temporada["clave"].startswith("H:")
        ]

        self._ponerOpciones(
            self.temporada,
            [t["nombre"] for t in self.temporadas]
        )
        self._ponerOpciones(
            self.instalacion,
            ["Todas las instalaciones"] +
            [i["nombre"] for i in self.instalaciones]
        )
        self._ponerOpciones(
            self.temporadaHistorica,
            [t["nombre"] for t in self.historicas]
        )
        self._ponerOpciones(
            self.instalacionHistorica,
            [i["nombre"] for i in self.instalaciones]
        )

        self._cambiarHistorica()
        self.consultar()

    def consultar(self):
        self.aviso.ocultar()
        self.lista.delete(*self.lista.get_children())

        indice = self.temporada.current()

        if indice < 0:
            self.aviso.mostrar(
                "No hay temporadas disponibles.", "info"
            )
            return

        indiceInstalacion = self.instalacion.current()

        idInstalacion = (
            self.instalaciones[indiceInstalacion - 1]["id"]
            if indiceInstalacion > 0 else None
        )

        try:
            resultado = self.app.demandaFranjas.consultar(
                self.temporadas[indice]["clave"],
                idInstalacion
            )
        except DemandaFranjasError as error:
            self.aviso.mostrar(str(error), "error")
            return

        for fila in resultado["filas"]:
            porcentaje = fila["ocupacionMedia"]

            if not fila["grupos"]:
                ocupacion = "Sin grupos"
            elif porcentaje is None:
                ocupacion = "No calculable"
            else:
                ocupacion = (
                    f"{porcentaje:.2f} %".replace(".", ",")
                )

            self.lista.insert(
                "", "end",
                values=(
                    fila["dia"],
                    fila["franja"],
                    fila["grupos"],
                    fila["inscritos"],
                    fila["espera"],
                    fila["demandaTotal"],
                    ocupacion,
                ),
                tags=(
                    ("demanda",)
                    if fila["demandaTotal"] > 0 else ()
                )
            )

        mensajes = [
            resultado["mensaje"],
            *resultado["avisos"]
        ]
        texto = "\n".join(
            mensaje for mensaje in mensajes if mensaje
        )

        if texto:
            self.aviso.mostrar(texto, "info")

    def _cambiarHistorica(self):
        self.avisoHistorico.ocultar()

        indice = self.temporadaHistorica.current()

        temporada = (
            self.historicas[indice]["clave"][2:]
            if indice >= 0 else ""
        )

        self.actividadesHistoricas = (
            self.app.demandaFranjas.getActividadesHistoricas(
                temporada
            )
        )

        self._ponerOpciones(
            self.actividadHistorica,
            [
                f"{a['id']} · {a['modalidad']} · "
                f"{a['nivel']} · {a['plazas']} plazas"
                for a in self.actividadesHistoricas
            ]
        )

        self._mostrarHorarios()

        if not self.historicas:
            self.avisoHistorico.mostrar(
                "Importa primero un CSV en "
                "Histórico de inscripciones.",
                "info"
            )

    def _mostrarHorarios(self):
        self.listaHorarios.delete(
            *self.listaHorarios.get_children()
        )

        indice = self.actividadHistorica.current()

        if indice < 0:
            return

        horarios = (
            self.app.demandaFranjas.getHorariosHistoricos(
                self.actividadesHistoricas[indice]["id"]
            )
        )

        for fila in horarios:
            self.listaHorarios.insert(
                "", "end",
                iid=str(fila["id"]),
                values=(
                    fila["instalacion"],
                    DIAS_SEMANA[fila["diaSemana"]],
                    fila["horaInicio"],
                )
            )

    def guardarHorario(self):
        actividad = self.actividadHistorica.current()
        instalacion = self.instalacionHistorica.current()

        if (
            actividad < 0
            or instalacion < 0
            or self.dia.current() < 0
        ):
            self.avisoHistorico.mostrar(
                "Selecciona actividad, instalación y día.",
                "info"
            )
            return

        try:
            self.app.demandaFranjas.guardarHorarioHistorico(
                self.actividadesHistoricas[actividad]["id"],
                self.instalaciones[instalacion]["id"],
                self.dia.current() + 1,
                self.hora.get()
            )
        except DemandaFranjasError as error:
            self.avisoHistorico.mostrar(
                str(error), "error"
            )
            return

        self._mostrarHorarios()
        self.consultar()

        self.avisoHistorico.mostrar(
            "Horario histórico guardado.", "ok"
        )

    def quitarHorario(self):
        seleccion = self.listaHorarios.selection()

        if not seleccion:
            self.avisoHistorico.mostrar(
                "Selecciona un horario de la tabla.", "info"
            )
            return

        if self.app.confirmar(
            "Quitar horario",
            "¿Quitar el horario histórico seleccionado?"
        ):
            self.app.demandaFranjas.eliminarHorarioHistorico(
                int(seleccion[0])
            )

            self._mostrarHorarios()
            self.consultar()

            self.avisoHistorico.mostrar(
                "Horario histórico quitado.", "ok"
            )