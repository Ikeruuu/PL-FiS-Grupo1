from src.config import DB_PATH
from src.inscripciones.comun import conectar, describirHorario


class ConsultaInscritosError(Exception):
    """Error de consulta que se muestra al usuario."""
    pass


class ConsultaInscritosModel:

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    def consultarInscritos(self, idActividad):
        with conectar(self.db_path) as conn:
            #Mantiene una vista consistente durante toda la consulta.
            conn.execute("BEGIN")

            actividad = conn.execute(
                """select a.*, m.nombre as modalidad,
                          n.nombre as nivel
                   from Actividad a
                   join Modalidad m on m.id = a.idModalidad
                   join Nivel n on n.id = a.idNivel
                   where a.id = ?""",
                (idActividad,)
            ).fetchone()

            if actividad is None:
                raise ConsultaInscritosError(
                    "La actividad no existe"
                )

            inscritos = conn.execute(
                """select p.dni, p.nombre, p.apellidos,
                          p.numSocio, i.fechaInscripcion
                   from Inscripcion i
                   join Persona p on p.id = i.idPersona
                   where i.idActividad = ?
                     and i.estado = 'CONFIRMADA'
                   order by p.apellidos, p.nombre, p.dni""",
                (idActividad,)
            ).fetchall()

            pendientes = conn.execute(
                """select count(*) from Inscripcion
                   where idActividad = ?
                     and estado = 'PENDIENTE_ACEPTACION'""",
                (idActividad,)
            ).fetchone()[0]

            ocupadas = len(inscritos)
            disponibles = max(
                0, actividad["plazas"] - ocupadas - pendientes
            )

            return {
                "actividad": dict(actividad),
                "horario": describirHorario(conn, idActividad),
                "inscritos": [dict(fila) for fila in inscritos],
                "plazasTotales": actividad["plazas"],
                "plazasOcupadas": ocupadas,
                "plazasReservadas": pendientes,
                "plazasDisponibles": disponibles,
            }