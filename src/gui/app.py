'''
Ventana principal de la interfaz gráfica del Centro Deportivo Inteligente:
barra lateral de navegación y área de contenido con una página por funcionalidad.
'''
import logging
import tkinter as tk
from tkinter import font as tkfont

from src.gui import estilos as e
from src.gui.paginas import PaginaAsignar, PaginaInicio, PaginaOcupacion, PaginaPersonas
from src.instalaciones.instalacionModel import InstalacionModel
from src.instalaciones.ocupacionModel import OcupacionModel
from src.personas.personaModel import PersonaModel
from src.util.unexpectedException import UnexpectedException

logger = logging.getLogger(__name__)

SECCIONES = [("inicio", "Inicio", PaginaInicio),
             ("asignar", "Asignar instalación", PaginaAsignar),
             ("ocupacion", "Ocupación", PaginaOcupacion),
             ("personas", "Personas", PaginaPersonas)]


class CentroDeportivoApp(tk.Tk):

    def __init__(self, db_path=None):
        e.activarAltaResolucion()
        super().__init__()
        self.title("Centro Deportivo Inteligente")
        e.configurarEstilos(self)
        self._ajustarTamano()
        self.report_callback_exception = self._errorInesperado

        self.instalaciones = InstalacionModel(db_path)
        self.ocupacion = OcupacionModel(db_path)
        self.personas = PersonaModel(db_path)

        self._crearLateral()
        self.contenido = tk.Frame(self, bg=e.FONDO)
        self.contenido.pack(side="left", fill="both", expand=True)
        self.paginas = {clave: clase(self.contenido, self) for clave, _, clase in SECCIONES}
        self.actual = None
        self.mostrar("inicio")

    #Tamaño inicial según la escala de la pantalla, sin pasar nunca del 92 % de ella, y centrada
    def _ajustarTamano(self):
        pantallaAncho, pantallaAlto = self.winfo_screenwidth(), self.winfo_screenheight()
        ancho = min(e.px(1280), int(pantallaAncho * 0.92))
        alto = min(e.px(760), int(pantallaAlto * 0.88))
        self.minsize(min(e.px(1040), ancho), min(e.px(620), alto))
        x, y = (pantallaAncho - ancho) // 2, max(0, (pantallaAlto - alto) // 3)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _crearLateral(self):
        #El ancho de la barra se calcula a partir del texto más largo, para que nunca se corte
        margen = e.px(22)
        textoMarca = tkfont.Font(font=e.fuente(14, "bold")).measure("Centro Deportivo")
        textoMenu = max(tkfont.Font(font=e.fuente(11, "bold")).measure(t) for _, t, _ in SECCIONES)
        ancho = max(e.px(230), textoMarca + 2 * margen + e.px(8), textoMenu + 2 * margen + e.px(8))
        lateral = tk.Frame(self, bg=e.NAVY, width=ancho)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)

        marca = tk.Frame(lateral, bg=e.NAVY, padx=margen, pady=e.px(26))
        marca.pack(fill="x")
        tk.Label(marca, text="CD", bg=e.ACENTO, fg="white", font=e.fuente(11, "bold"),
                 padx=e.px(8), pady=e.px(4)).pack(anchor="w", pady=(0, e.px(12)))
        tk.Label(marca, text="Centro Deportivo", bg=e.NAVY, fg="white", anchor="w",
                 font=e.fuente(14, "bold")).pack(fill="x")
        tk.Label(marca, text="Inteligente", bg=e.NAVY, fg=e.TEXTO_LATERAL, anchor="w",
                 font=e.fuente(11)).pack(fill="x")

        tk.Label(lateral, text="MENÚ", bg=e.NAVY, fg="#7A8BA3", font=e.fuente(8, "bold"),
                 padx=margen).pack(anchor="w", pady=(e.px(8), e.px(6)))
        self.botones = {}
        for clave, texto, _ in SECCIONES:
            boton = tk.Label(lateral, text=texto, bg=e.NAVY, fg=e.TEXTO_LATERAL, anchor="w",
                             font=e.fuente(11), padx=margen, pady=e.px(11), cursor="hand2")
            boton.pack(fill="x")
            boton.bind("<Button-1>", lambda ev, c=clave: self.mostrar(c))
            boton.bind("<Enter>", lambda ev, c=clave: self._hover(c, True))
            boton.bind("<Leave>", lambda ev, c=clave: self._hover(c, False))
            self.botones[clave] = boton

        tk.Label(lateral, text="FIS · Curso 2026-27", bg=e.NAVY, fg="#7A8BA3",
                 font=e.fuente(8), padx=margen, pady=e.px(18)).pack(side="bottom", anchor="w")

    def _hover(self, clave, dentro):
        if clave != self.actual:
            self.botones[clave].configure(bg=e.NAVY_HOVER if dentro else e.NAVY)

    def mostrar(self, clave):
        if self.actual:
            self.paginas[self.actual].pack_forget()
            self.botones[self.actual].configure(bg=e.NAVY, fg=e.TEXTO_LATERAL, font=e.fuente(11))
        self.actual = clave
        self.botones[clave].configure(bg=e.NAVY_ACTIVO, fg="white", font=e.fuente(11, "bold"))
        pagina = self.paginas[clave]
        pagina.refrescar()
        pagina.pack(fill="both", expand=True)

    #Los errores de base de datos se registran y se muestran sin cerrar la aplicación
    def _errorInesperado(self, tipo, valor, traza):
        logger.error("Error inesperado de la aplicación", exc_info=(tipo, valor, traza))
        pagina = self.paginas.get(self.actual)
        aviso = getattr(pagina, "aviso", None)
        texto = ("Error inesperado (detalle en el registro). Inténtelo de nuevo."
                 if isinstance(valor, UnexpectedException) else f"Error inesperado: {valor}")
        if aviso is not None:
            aviso.mostrar(texto, "error")


def ejecutar(db_path=None):
    app = CentroDeportivoApp(db_path)
    app.mainloop()
