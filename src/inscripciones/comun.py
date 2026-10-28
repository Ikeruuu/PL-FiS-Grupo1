'''
Consultas comunes a las historias de inscripciones: buscar a una persona por su identificador,
calcular las plazas ocupadas de una actividad y el orden de su lista de espera.

Todas las funciones reciben una conexión sqlite3 abierta (con row_factory = sqlite3.Row) para
poder usarse dentro de la misma transacción que modifica las inscripciones.
'''
import sqlite3
from contextlib import contextmanager

from src.instalaciones.instalacionModel import DIAS_SEMANA
from src.personas.personaModel import normalizarDni

#Estados que ocupan plaza en una actividad (las solicitudes en espera y las canceladas no)
ESTADOS_CON_PLAZA = ("CONFIRMADA", "PENDIENTE_ACEPTACION")


class IdentificacionError(Exception):
    '''La persona no se ha podido identificar. El mensaje se muestra tal cual al usuario.'''


@contextmanager
def conectar(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


#Busca a la persona por DNI o por número de socio (el mismo criterio que la inscripción)
def buscarPersona(conn, dni=None, numSocio=None):
    if dni is not None and dni.strip():
        persona = conn.execute("select * from Persona where dni = ?",
                               (normalizarDni(dni),)).fetchone()
    elif numSocio is not None:
        persona = conn.execute("select * from Persona where numSocio = ?",
                               (numSocio,)).fetchone()
    else:
        raise IdentificacionError("Indica el DNI o el número de socio")
    if persona is None:
        raise IdentificacionError("No existe ninguna persona registrada con ese identificador")
    return persona


def plazasOcupadas(conn, idActividad):
    return conn.execute(
        f"""select count(*) from Inscripcion
            where idActividad = ? and estado in {ESTADOS_CON_PLAZA}""",
        (idActividad,)).fetchone()[0]


#Solicitudes en lista de espera de una actividad en su orden: primero los socios
#(tienen prioridad) y, dentro de cada grupo, por orden de llegada
def listaEspera(conn, idActividad):
    return conn.execute(
        """select i.* from Inscripcion i
           join Persona p on p.id = i.idPersona
           where i.idActividad = ? and i.estado = 'EN_ESPERA'
           order by p.numSocio is null, i.fechaSolicitud, i.id""",
        (idActividad,)).fetchall()


#Días de la semana en que se imparte la actividad, ordenados (1=lunes ... 7=domingo)
def diasActividad(conn, idActividad):
    filas = conn.execute(
        "select distinct diaSemana from Horario where idActividad = ? order by diaSemana",
        (idActividad,)).fetchall()
    return tuple(f["diaSemana"] for f in filas)


#"lunes y miércoles", "martes, jueves y viernes"
def describirDias(dias):
    nombres = [DIAS_SEMANA[d] for d in sorted(dias)]
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


#"lunes 18:00–19:00, miércoles 18:00–19:00"
def describirHorario(conn, idActividad):
    filas = conn.execute(
        """select diaSemana, horaInicio, horaFin from Horario
           where idActividad = ? order by diaSemana, horaInicio""",
        (idActividad,)).fetchall()
    return ", ".join(f"{DIAS_SEMANA[f['diaSemana']]} {f['horaInicio']}–{f['horaFin']}"
                     for f in filas) or "Sin horario"
