'''
Colores, fuentes y estilos ttk de la interfaz gráfica.
Se usa el tema "clam" porque permite personalizar colores en Windows, Linux y macOS.
'''
import os
import sys
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


#Factor de escala de la pantalla (1.0 = 96 ppp; 1.5 = Windows al 150 %). Se calcula al arrancar.
ESCALA = 1.0


#Convierte un tamaño en píxeles de diseño (a 96 ppp) a píxeles reales de la pantalla
def px(valor):
    return int(round(valor * ESCALA))


#En Windows, declara la aplicación "DPI-aware" para que el sistema no la amplíe como una
#imagen (eso es lo que deja las fuentes borrosas en pantallas con escalado al 125 % o 150 %).
#Debe llamarse antes de crear la ventana.
def activarAltaResolucion():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


#Calcula la escala a partir de los píxeles por pulgada reales. La variable de entorno
#CDI_ESCALA permite forzarla (útil para probar cómo se ve en otras pantallas).
def calcularEscala(root):
    global ESCALA
    forzada = os.environ.get("CDI_ESCALA")
    if forzada:
        ESCALA = float(forzada)
        root.tk.call("tk", "scaling", ESCALA * 96 / 72)
    else:
        ESCALA = max(1.0, root.winfo_fpixels("1i") / 96)
    return ESCALA


def fuente(tamano=10, peso="normal"):
    return (FUENTE, tamano, peso)


#Elige la primera fuente disponible del sistema
def elegirFuente(root):
    global FUENTE
    disponibles = set(tkfont.families(root))
    FUENTE = next((f for f in FUENTES_PREFERIDAS if f in disponibles), "TkDefaultFont")
    return FUENTE


def configurarEstilos(root):
    calcularEscala(root)
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
                     focusthickness=0, padding=(px(18), px(9)), font=fuente(10, "bold"))
    estilo.map("Primario.TButton", background=[("active", ACENTO_HOVER), ("disabled", "#9CA3AF")])
    estilo.configure("Secundario.TButton", background=TARJETA, foreground=TEXTO, bordercolor=BORDE,
                     padding=(px(14), px(8)))
    estilo.map("Secundario.TButton", background=[("active", DIA_FONDO)])

    #Entradas
    estilo.configure("TEntry", fieldbackground="white", bordercolor=BORDE, lightcolor=BORDE,
                     padding=px(6))
    estilo.configure("TCombobox", fieldbackground="white", bordercolor=BORDE, padding=px(6))
    estilo.map("TCombobox", fieldbackground=[("readonly", "white")],
               selectbackground=[("readonly", "white")], selectforeground=[("readonly", TEXTO)])

    #Tablas
    estilo.configure("Treeview", background="white", fieldbackground="white", foreground=TEXTO,
                     rowheight=px(30), bordercolor=BORDE, borderwidth=0, font=fuente(10))
    estilo.configure("Treeview.Heading", background=DIA_FONDO, foreground=TEXTO_SUAVE,
                     font=fuente(9, "bold"), relief="flat", padding=(px(8), px(6)))
    estilo.map("Treeview", background=[("selected", "#BFDBFE")], foreground=[("selected", TEXTO)])
    estilo.map("Treeview.Heading", background=[("active", BORDE)])
    return estilo
