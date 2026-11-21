from tkinter import ttk

from src.gui.componentes import Aviso, cabecera, tabla, tarjeta
from src.gui.paginas import Pagina


class PaginaRankingDemanda(Pagina):

    def __init__(self, master, app):
        super().__init__(master, app)

        cabecera(
            self,
            "Ranking de demanda",
            "Compara las inscripciones y la lista de espera "
            "de la temporada actual"
        )

        controles = tarjeta(self, fill="x")

        self.temporada = ttk.Label(
            controles,
            text="",
            style="Seccion.TLabel"
        )
        self.temporada.pack(
            side="left", fill="x", expand=True
        )

        ttk.Button(
            controles,
            text="Actualizar",
            style="Primario.TButton",
            command=self.refrescar
        ).pack(side="right")

        self.aviso = Aviso(self)
        self.aviso.pack(fill="x", pady=(12, 0))

        resultado = tarjeta(
            self, fill="both", expand=True, pady=(12, 0)
        )

        marco, self.lista = tabla(resultado, [
            ("id", "ID", 50, False),
            ("actividad", "Actividad y nivel", 210, True),
            ("horario", "Días y horarios", 380, True),
            ("plazas", "Plazas", 65, False),
            ("inscritos", "Inscritos", 75, False),
            ("espera", "En espera", 80, False),
            ("total", "Demanda total", 110, False),
            ("alta", "Alta demanda", 110, False),
            ("baja", "Baja demanda", 110, False),
        ], altura=12)

        barra = ttk.Scrollbar(
            resultado,
            orient="horizontal",
            command=self.lista.xview
        )
        self.lista.configure(xscrollcommand=barra.set)

        barra.pack(side="bottom", fill="x")
        marco.pack(fill="both", expand=True)

        self.detalle = ttk.Label(
            self, text="", style="Subtitulo.TLabel"
        )
        self.detalle.pack(anchor="w", pady=(10, 0))

        ttk.Label(
            self,
            text="Alta: hay lista de espera. "
                 "Baja: menos del 50 % de plazas cubiertas.",
            style="Subtitulo.TLabel"
        ).pack(anchor="w")

    def refrescar(self):
        self.aviso.ocultar()
        self.lista.delete(*self.lista.get_children())
        self.temporada.configure(text="")
        self.detalle.configure(text="")

        resultado = self.app.rankingDemanda.consultarRanking()
        oferta = resultado["oferta"]

        self.temporada.configure(
            text=(
                f"Temporada {oferta['curso']}"
                if oferta else "Sin temporada activa"
            )
        )

        for actividad in resultado["actividades"]:
            self.lista.insert(
                "", "end",
                values=(
                    actividad["id"],
                    f"{actividad['modalidad']} · {actividad['nivel']}",
                    actividad["horario"],
                    actividad["plazas"],
                    actividad["inscritos"],
                    actividad["espera"],
                    actividad["demandaTotal"],
                    "Sí" if actividad["altaDemanda"] else "No",
                    "Sí" if actividad["bajaDemanda"] else "No",
                )
            )

        if resultado["mensaje"]:
            self.aviso.mostrar(resultado["mensaje"], "info")
        else:
            self.detalle.configure(
                text=f"{len(resultado['actividades'])} actividades, "
                     "de mayor a menor demanda"
            )