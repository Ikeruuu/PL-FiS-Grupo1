'''
Colores, fuentes y estilos ttk de la interfaz gráfica.
Se usa el tema "clam" porque permite personalizar colores en Windows, Linux y macOS.
'''
from tkinter import font as tkfont
from tkinter import ttk

#Paleta
NAVY = "#0B1F33"          #barra lateral
NAVY_HOVER = "#15314D"
NAVY_ACTIVO = "#1E4166"
ACENTO = "#16A34A"        #verde deportivo (acciones principales)
ACENTO_HOVER = "#15803D"
FONDO = "#F3F5F9"         #fondo del contenido
TARJETA = "#FFFFFF"
BORDE = "#DDE3EC"
TEXTO = "#0F172A"
TEXTO_SUAVE = "#64748B"
TEXTO_LATERAL = "#C7D2E0"

OK_FONDO, OK_TEXTO = "#DCFCE7", "#166534"
ERROR_FONDO, ERROR_TEXTO = "#FEE2E2", "#991B1B"
INFO_FONDO, INFO_TEXTO = "#E0EAFF", "#1E3A8A"

OCUPADA_FONDO = "#FDECEC"
LIBRE_FONDO = "#EAF7EE"
DIA_FONDO = "#EEF2F7"
NO_CABE_TEXTO = "#A0AEC0"

#Colores de las tarjetas de resumen (Inicio)
COLORES_TARJETAS = ["#2563EB", "#16A34A", "#F59E0B", "#9333EA"]

FUENTE = "Segoe UI"
#Fuentes preferidas por orden: Windows, Linux (si está instalada), macOS y genéricas
FUENTES_PREFERIDAS = ["Segoe UI", "Inter", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def fuente(tamano=10, peso="normal"):
    return (FUENTE, tamano, peso)


#Elige la primera fuente disponible del sistema
def elegirFuente(root):
    global FUENTE
    disponibles = set(tkfont.families(root))
    FUENTE = next((f for f in FUENTES_PREFERIDAS if f in disponibles), "TkDefaultFont")
    return FUENTE


def configurarEstilos(root):
    elegirFuente(root)
    estilo = ttk.Style(root)
    estilo.theme_use("clam")
    root.configure(bg=FONDO)
    root.option_add("*Font", fuente(10))

    estilo.configure(".", background=FONDO, foreground=TEXTO, font=fuente(10))
    estilo.configure("TFrame", background=FONDO)
    estilo.configure("Tarjeta.TFrame", background=TARJETA)
    estilo.configure("TLabel", background=FONDO, foreground=TEXTO)
    estilo.configure("Tarjeta.TLabel", background=TARJETA)
    estilo.configure("Titulo.TLabel", font=fuente(20, "bold"), foreground=TEXTO)
    estilo.configure("Subtitulo.TLabel", font=fuente(10), foreground=TEXTO_SUAVE)
    estilo.configure("Seccion.TLabel", background=TARJETA, font=fuente(12, "bold"))
    estilo.configure("Campo.TLabel", background=TARJETA, foreground=TEXTO_SUAVE, font=fuente(9))
    estilo.configure("TRadiobutton", background=TARJETA)

    #Botones
    estilo.configure("Primario.TButton", background=ACENTO, foreground="white", borderwidth=0,
                     focusthickness=0, padding=(18, 9), font=fuente(10, "bold"))
    estilo.map("Primario.TButton", background=[("active", ACENTO_HOVER), ("disabled", "#9CA3AF")])
    estilo.configure("Secundario.TButton", background=TARJETA, foreground=TEXTO, bordercolor=BORDE,
                     padding=(14, 8))
    estilo.map("Secundario.TButton", background=[("active", DIA_FONDO)])

    #Entradas
    estilo.configure("TEntry", fieldbackground="white", bordercolor=BORDE, lightcolor=BORDE,
                     padding=6)
    estilo.configure("TCombobox", fieldbackground="white", bordercolor=BORDE, padding=6)
    estilo.map("TCombobox", fieldbackground=[("readonly", "white")],
               selectbackground=[("readonly", "white")], selectforeground=[("readonly", TEXTO)])

    #Tablas
    estilo.configure("Treeview", background="white", fieldbackground="white", foreground=TEXTO,
                     rowheight=30, bordercolor=BORDE, borderwidth=0, font=fuente(10))
    estilo.configure("Treeview.Heading", background=DIA_FONDO, foreground=TEXTO_SUAVE,
                     font=fuente(9, "bold"), relief="flat", padding=(8, 6))
    estilo.map("Treeview", background=[("selected", "#BFDBFE")], foreground=[("selected", TEXTO)])
    estilo.map("Treeview.Heading", background=[("active", BORDE)])
    return estilo
