from tkinter import font as tkfont, ttk

from src.gui import estilos as e
from src.gui.componentes import Aviso, cabecera, tabla, tarjeta
from src.gui.paginas import Pagina


class PaginaOcupacionPlazas(Pagina):

    def __init__(self, master, app):
        super().__init__(master, app)

        cabecera(
            self,
            "Plazas y ocupación",
            "Consulta las plazas ofertadas, los inscritos y la lista de espera"
        )

        controles = tarjeta(self, fill="x")

        self.temporada = ttk.Label(
            controles, text="", style="Seccion.TLabel"
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
            ("actividad", "Actividad y nivel", 240, False),
            ("horario", "Días y horarios", 380, False),
            ("plazas", "Plazas ofertadas", 140, False),
            ("inscritos", "Inscritos activos", 140, False),
            ("espera", "En espera", 100, False),
            ("ocupacion", "Ocupación", 140, False),
            ("indicacion", "Indicaciones", 350, False),
        ], altura=10)

        self.fuenteTabla = tkfont.Font(font=e.fuente(10))

        # Rojo suave para grupos con espera.
        # Amarillo para grupos con ocupación baja.
        self.lista.tag_configure(
            "espera", background="#FEE2E2"
        )
        self.lista.tag_configure(
            "baja", background="#FEF3C7"
        )

        barra = ttk.Scrollbar(
            resultado,
            orient="horizontal",
            command=self.lista.xview
        )
        self.lista.configure(xscrollcommand=barra.set)

        barra.pack(side="bottom", fill="x")
        marco.pack(fill="both", expand=True)

    def refrescar(self):
        self.aviso.ocultar()
        self.lista.delete(*self.lista.get_children())

        resultado = self.app.ocupacionPlazas.consultarOcupacion()
        oferta = resultado["oferta"]

        self.temporada.configure(
            text=(
                f"Temporada {oferta['curso']}"
                if oferta else "Sin temporada activa"
            )
        )

        anchos = {
            "actividad": e.px(240),
            "horario": e.px(380),
        }

        for actividad in resultado["actividades"]:
            nombre = (
                f"{actividad['modalidad']} · {actividad['nivel']}"
            )

            # Ajustar el ancho para mostrar nombres y horarios completos.
            for columna, texto in (
                ("actividad", nombre),
                ("horario", actividad["horario"])
            ):
                anchos[columna] = max(
                    anchos[columna],
                    self.fuenteTabla.measure(texto) + e.px(24)
                )

            indicaciones = []

            if actividad["conEspera"]:
                indicaciones.append("Con lista de espera")

            if actividad["bajaOcupacion"]:
                indicaciones.append("Ocupación inferior al 50 %")

            porcentaje = actividad["ocupacion"]

            ocupacion = (
                "No calculable" if porcentaje is None
                else f"{porcentaje:.2f} %".replace(".", ",")
            )

            etiqueta = (
                "espera" if actividad["conEspera"]
                else "baja" if actividad["bajaOcupacion"]
                else ""
            )

            self.lista.insert(
                "", "end",
                values=(
                    actividad["id"],
                    nombre,
                    actividad["horario"],
                    actividad["plazas"],
                    actividad["inscritos"],
                    actividad["espera"],
                    ocupacion,
                    "; ".join(indicaciones) or "Sin alertas",
                ),
                tags=(etiqueta,) if etiqueta else ()
            )

        for columna, ancho in anchos.items():
            self.lista.column(columna, width=ancho)

        if resultado["mensaje"]:
            self.aviso.mostrar(resultado["mensaje"], "info")