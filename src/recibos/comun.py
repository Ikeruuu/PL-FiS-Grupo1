'''
Funciones comunes del bloque de control económico (Sprint 2):
HU13 Emitir la remesa mensual de recibos, HU14 Importar el resultado del banco y
HU15 Consultar los recibos y los ingresos por actividad.
'''
import datetime
import re
import sqlite3
from contextlib import contextmanager

#Estados de un recibo (en la base de datos se guardan en mayúsculas)
EMITIDO, COBRADO, DEVUELTO = "EMITIDO", "COBRADO", "DEVUELTO"
ESTADOS_RECIBO = (EMITIDO, COBRADO, DEVUELTO)

_MESES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio",
          8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}


class ReciboError(Exception):
    '''Error del bloque de recibos. El mensaje se muestra tal cual al usuario.'''


@contextmanager
def conectar(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


#Fecha de hoy (las pruebas pueden fijarla con un date o con un texto AAAA-MM-DD)
def fechaHoy(hoy=None):
    if hoy is None:
        return datetime.date.today()
    return datetime.date.fromisoformat(hoy) if isinstance(hoy, str) else hoy


#"2026-11" -> date(2026, 11, 1)
def leerMes(mes):
    texto = (mes or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", texto):
        raise ReciboError("El mes debe tener el formato AAAA-MM (por ejemplo 2026-11)")
    anio, numero = (int(x) for x in texto.split("-"))
    if not 1 <= numero <= 12:
        raise ReciboError("El mes debe tener el formato AAAA-MM (por ejemplo 2026-11)")
    return datetime.date(anio, numero, 1)


#date(2026, 11, 1) -> "2026-11"
def textoMes(fecha):
    return f"{fecha.year:04d}-{fecha.month:02d}"


#date(2026, 11, 1) o "2026-11" -> "noviembre de 2026"
def nombreMes(fecha):
    if isinstance(fecha, str):
        fecha = leerMes(fecha)
    return f"{_MESES[fecha.month]} de {fecha.year}"


#Último día del mes de la fecha
def ultimoDia(fecha):
    siguiente = (fecha.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return siguiente - datetime.timedelta(days=1)


#30 -> "30,00 €"
def describirImporte(importe):
    return f"{importe:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


#Nombre corto de la actividad: "Pádel medio"
def describirActividad(modalidad, nivel):
    return f"{modalidad} {nivel.lower()}"
