from src.config import DB_PATH
import datetime
from src.inscripciones.comun import (
    IdentificacionError,
    buscarPersona,
    conectar,
    listaEspera,
    plazasOcupadas,
)


class ListaEsperaError(IdentificacionError):
    """Error que se muestra al usuario."""
    pass


class ListaEsperaModel:

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    def consultarEstado(self, idActividad, dni=None, numSocio=None):
        """Consulta sin modificar solicitudes ni asignar plazas."""
        with conectar(self.db_path) as conn:
            persona = buscarPersona(conn, dni, numSocio)

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
                raise ListaEsperaError("La actividad no existe")

            solicitud = conn.execute(
                """select * from Inscripcion
                   where idPersona = ? and idActividad = ?""",
                (persona["id"], idActividad)
            ).fetchone()

            if solicitud is None:
                raise ListaEsperaError(
                    "No existe una solicitud para esta persona "
                    "y actividad"
                )

            espera = listaEspera(conn, idActividad)
            posicion = None
            if solicitud["estado"] == "EN_ESPERA":
                posicion = next(
                    numero
                    for numero, fila in enumerate(espera, start=1)
                    if fila["id"] == solicitud["id"]
                )

            return {
                "persona": dict(persona),
                "actividad": dict(actividad),
                "solicitud": dict(solicitud),
                "estado": solicitud["estado"],
                "posicion": posicion,
                "totalEspera": len(espera),
            }

    def ofrecerPlazas(self, idActividad):
        """
        Reserva las plazas libres para las primeras personas
        de la lista. Devuelve cuántas ofertas se han realizado.
        No confirma las inscripciones.
        """
        with conectar(self.db_path) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")

                actividad = conn.execute(
                    "select * from Actividad where id = ?",
                    (idActividad,)
                ).fetchone()

                if actividad is None:
                    raise ListaEsperaError("La actividad no existe")

                libres = max(
                    0,
                    actividad["plazas"]
                    - plazasOcupadas(conn, idActividad)
                )
                seleccionadas = listaEspera(
                    conn, idActividad
                )[:libres]

                for solicitud in seleccionadas:
                    conn.execute(
                        """update Inscripcion
                           set estado = 'PENDIENTE_ACEPTACION'
                           where id = ?""",
                        (solicitud["id"],)
                    )

                conn.commit()
                return len(seleccionadas)

            except Exception:
                conn.rollback()
                raise
    def aceptarPlaza(self, idActividad, dni=None, numSocio=None):
        with conectar(self.db_path) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                persona = buscarPersona(conn, dni, numSocio)

                actividad = conn.execute(
                    "select * from Actividad where id = ?",
                    (idActividad,)
                ).fetchone()

                if actividad is None:
                    raise ListaEsperaError("La actividad no existe")

                solicitud = conn.execute(
                    """select * from Inscripcion
                       where idPersona = ? and idActividad = ?""",
                    (persona["id"], idActividad)
                ).fetchone()

                if solicitud is None:
                    raise ListaEsperaError(
                        "No existe una solicitud para esta actividad"
                    )

                if solicitud["estado"] != "PENDIENTE_ACEPTACION":
                    raise ListaEsperaError(
                        "No tiene una plaza pendiente de aceptar"
                    )

                #Comprueba de nuevo los horarios al aceptar.
                solape = conn.execute(
                    """select otra.id
                       from Inscripcion i
                       join Actividad otra on otra.id = i.idActividad
                       join Horario h on h.idActividad = otra.id
                       join Horario nuevo on nuevo.idActividad = ?
                       where i.idPersona = ?
                         and i.idActividad != ?
                         and i.estado in (
                             'CONFIRMADA', 'PENDIENTE_ACEPTACION'
                         )
                         and otra.fechaInicio <= ?
                         and otra.fechaFin >= ?
                         and h.diaSemana = nuevo.diaSemana
                         and h.horaInicio < nuevo.horaFin
                         and nuevo.horaInicio < h.horaFin
                       limit 1""",
                    (
                        idActividad, persona["id"], idActividad,
                        actividad["fechaFin"],
                        actividad["fechaInicio"],
                    )
                ).fetchone()

                if solape is not None:
                    raise ListaEsperaError(
                        "La actividad coincide en horario con otra "
                        "en la que ya tiene una plaza"
                    )

                if plazasOcupadas(conn, idActividad) > actividad["plazas"]:
                    raise ListaEsperaError(
                        "No se puede confirmar: se supera "
                        "la capacidad de la actividad"
                    )

                ahora = datetime.datetime.now().isoformat(
                    timespec="microseconds"
                )
                conn.execute(
                    """update Inscripcion
                       set estado = 'CONFIRMADA',
                           fechaInscripcion = ?,
                           fechaCancelacion = null,
                           cancelaDesde = null
                       where id = ?""",
                    (ahora, solicitud["id"])
                )
                conn.commit()
                return "Plaza aceptada. Inscripción confirmada"

            except Exception:
                conn.rollback()
                raise
    def rechazarPlaza(self, idActividad, dni=None, numSocio=None):
        with conectar(self.db_path) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                persona = buscarPersona(conn, dni, numSocio)

                actividad = conn.execute(
                    "select * from Actividad where id = ?",
                    (idActividad,)
                ).fetchone()

                if actividad is None:
                    raise ListaEsperaError("La actividad no existe")

                solicitud = conn.execute(
                    """select * from Inscripcion
                       where idPersona = ? and idActividad = ?""",
                    (persona["id"], idActividad)
                ).fetchone()

                if solicitud is None:
                    raise ListaEsperaError(
                        "No existe una solicitud para esta actividad"
                    )

                if solicitud["estado"] != "PENDIENTE_ACEPTACION":
                    raise ListaEsperaError(
                        "No tiene una plaza pendiente de aceptar"
                    )

                ahora = datetime.datetime.now().isoformat(
                    timespec="microseconds"
                )
                conn.execute(
                    """update Inscripcion
                       set estado = 'CANCELADA',
                           fechaCancelacion = ?,
                           fechaInscripcion = null,
                           cancelaDesde = null
                       where id = ?""",
                    (ahora, solicitud["id"])
                )

                libres = max(
                    0,
                    actividad["plazas"]
                    - plazasOcupadas(conn, idActividad)
                )
                siguientes = listaEspera(conn, idActividad)[:libres]

                for siguiente in siguientes:
                    conn.execute(
                        """update Inscripcion
                           set estado = 'PENDIENTE_ACEPTACION'
                           where id = ?""",
                        (siguiente["id"],)
                    )

                conn.commit()
                return (
                    "Plaza rechazada. Su solicitud se ha retirado "
                    "de la lista de espera"
                )

            except Exception:
                conn.rollback()
                raise