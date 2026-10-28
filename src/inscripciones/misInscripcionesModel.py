from src.config import DB_PATH
from src.inscripciones.comun import (
    buscarPersona,
    conectar,
    describirHorario,
    listaEspera,
)

#Orden en que se muestran los estados: primero lo que tiene plaza, al final lo cancelado
_ORDEN_ESTADO = {"CONFIRMADA": 0, "PENDIENTE_ACEPTACION": 1, "EN_ESPERA": 2, "CANCELADA": 3}


class MisInscripcionesModel:
    '''
    HU "Consultar las actividades en las que estoy inscrito" (RedKanban 35336).
    La persona se identifica por DNI o número de socio (igual que al inscribirse) y se listan
    todas sus inscripciones: con plaza, en lista de espera (posición y total) y canceladas.
    '''

    SIN_INSCRIPCIONES = "No está inscrito en ninguna actividad"

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    def consultarInscripciones(self, dni=None, numSocio=None):
        '''
        Devuelve (persona, lista, mensaje). mensaje es None si hay inscripciones y el texto
        a mostrar si no las hay. Lanza IdentificacionError si la persona no existe.
        '''
        with conectar(self.db_path) as conn:
            persona = dict(buscarPersona(conn, dni, numSocio))
            filas = conn.execute(
                """select i.id as idInscripcion, i.estado, i.fechaSolicitud, i.fechaInscripcion,
                          i.fechaCancelacion, i.cancelaDesde,
                          a.id as idActividad, a.fechaInicio, a.fechaFin,
                          m.nombre as modalidad, n.nombre as nivel,
                          ins.nombre as instalacion
                   from Inscripcion i
                   join Actividad a on a.id = i.idActividad
                   join Modalidad m on m.id = a.idModalidad
                   join Nivel n on n.id = a.idNivel
                   left join Instalacion ins on ins.id = a.idInstalacion
                   where i.idPersona = ?""",
                (persona["id"],)).fetchall()

            lista = []
            for f in filas:
                fila = dict(f)
                fila["horario"] = describirHorario(conn, f["idActividad"])
                fila["instalacion"] = f["instalacion"] or "Sin asignar"
                fila["posicion"] = fila["totalEspera"] = None
                if f["estado"] == "EN_ESPERA":
                    espera = [e["id"] for e in listaEspera(conn, f["idActividad"])]
                    fila["posicion"] = espera.index(f["idInscripcion"]) + 1
                    fila["totalEspera"] = len(espera)
                fila["descripcionEstado"] = describirEstado(fila)
                lista.append(fila)

        lista.sort(key=lambda x: (_ORDEN_ESTADO[x["estado"]], x["fechaInicio"], x["modalidad"]))
        if not lista:
            return persona, [], self.SIN_INSCRIPCIONES
        return persona, lista, None


#Texto del estado tal como lo ve la persona
def describirEstado(fila):
    estado = fila["estado"]
    if estado == "CONFIRMADA":
        return "Inscrito"
    if estado == "PENDIENTE_ACEPTACION":
        return "Plaza pendiente de aceptar"
    if estado == "EN_ESPERA":
        return f"En lista de espera (posición {fila['posicion']} de {fila['totalEspera']})"
    if fila.get("cancelaDesde"):
        anio, mes, _ = fila["cancelaDesde"].split("-")
        return f"Cancelada (desde {mes}/{anio})"
    return "Cancelada"
