import datetime

from src.config import DB_PATH
from src.util.database import Database

#Horario de apertura del centro (indicado por el cliente): de 8:00 a 22:00 todos los días
APERTURA = "08:00"
CIERRE = "22:00"


class OcupacionError(Exception):
    '''
    Indica que no se puede realizar la consulta de ocupación (instalación inexistente o
    fechas incoherentes). El mensaje se muestra tal cual al usuario.
    '''


#Periodo del curso (octubre a junio) que corresponde a una fecha.
#De julio a septiembre se toma el curso que empieza en octubre.
def periodoCurso(hoy=None):
    hoy = hoy if hoy else datetime.date.today()
    inicio = hoy.year if hoy.month >= 7 else hoy.year - 1
    return f"{inicio}-10-01", f"{inicio + 1}-06-30"


#Huecos libres de un día dentro del horario del centro.
#franjas: lista de franjas ocupadas del día ordenadas por horaInicio.
#Con max() se cubren franjas solapadas (misma hora en periodos distintos) y franjas
#contiguas, que no dejan hueco entre ellas.
def calcularHuecos(franjas, apertura=APERTURA, cierre=CIERRE):
    huecos = []
    cursor = apertura
    for franja in franjas:
        inicio = max(franja["horaInicio"], apertura)
        if inicio > cursor and cursor < cierre:
            huecos.append((cursor, min(inicio, cierre)))
        cursor = max(cursor, franja["horaFin"])
    if cursor < cierre:
        huecos.append((cursor, cierre))
    return huecos


class OcupacionModel:
    '''
    Objetos de negocio (model) de la HU "Consultar la ocupación de una instalación".
    Obtiene las franjas ocupadas de una instalación en un periodo y calcula sus huecos libres.
    '''

    def __init__(self, db_path=None):
        self.db = Database(db_path if db_path else DB_PATH)

    #Franjas semanales de las actividades asignadas a la instalación cuyo periodo se solapa
    #con el consultado (basta con que coincida un día)
    def getFranjasOcupadas(self, id_instalacion, fecha_inicio, fecha_fin):
        query = """select Horario.diaSemana, Horario.horaInicio, Horario.horaFin,
                          Actividad.id as idActividad, Modalidad.nombre as modalidad, Nivel.nombre as nivel,
                          Actividad.fechaInicio, Actividad.fechaFin
                   from Actividad
                   inner join Horario on Horario.idActividad = Actividad.id
                   inner join Modalidad on Modalidad.id = Actividad.idModalidad
                   inner join Nivel on Nivel.id = Actividad.idNivel
                   where Actividad.idInstalacion = ?
                     and Actividad.fechaInicio <= ? and Actividad.fechaFin >= ?
                   order by Horario.diaSemana, Horario.horaInicio, Horario.horaFin, Actividad.id
                """
        return self.db.executeQuery(query, id_instalacion, fecha_fin, fecha_inicio)

    #Consulta la ocupación de una instalación en un periodo (por defecto, el curso completo).
    #Devuelve un diccionario con la instalación, el periodo y, para cada día de la semana
    #con actividad, sus franjas ocupadas y sus huecos libres. Lanza OcupacionError si la
    #instalación no existe o las fechas son incoherentes.
    def consultarOcupacion(self, id_instalacion, fecha_inicio=None, fecha_fin=None, hoy=None):
        res = self.db.executeQuery("select id, nombre, capacidad from Instalacion where id = ?",
                                   id_instalacion)
        if len(res) != 1:
            raise OcupacionError(f"No existe la instalación {id_instalacion}")
        if fecha_inicio is None or fecha_fin is None:
            fecha_inicio, fecha_fin = periodoCurso(hoy)
        if fecha_inicio > fecha_fin:
            raise OcupacionError("Fechas incoherentes: la fecha de inicio es posterior a la de fin")

        dias = {}
        for franja in self.getFranjasOcupadas(id_instalacion, fecha_inicio, fecha_fin):
            dias.setdefault(franja["diaSemana"], []).append(franja)
        ocupacion = {dia: {"ocupadas": franjas, "libres": calcularHuecos(franjas)}
                     for dia, franjas in sorted(dias.items())}
        return {"instalacion": res[0], "fechaInicio": fecha_inicio, "fechaFin": fecha_fin,
                "dias": ocupacion}
