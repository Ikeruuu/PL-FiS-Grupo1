import datetime
import sqlite3

from src.config import DB_PATH
from src.personas.personaModel import normalizarDni


class InscripcionError(Exception):
    """Error de inscripción cuyo mensaje se muestra al usuario."""
    pass


class InscripcionModel:

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    def inscribir(self, idActividad, dni=None, numSocio=None, hoy=None):
        """
        Registra la inscripción o la entrada automática en lista de espera.
        hoy permite usar una fecha controlada en las pruebas.
        """
        hoy = datetime.date.today() if hoy is None else hoy
        if isinstance(hoy, str):
            hoy = datetime.date.fromisoformat(hoy)

        fechaSolicitud = datetime.datetime.now().isoformat(
            timespec="microseconds"
        )

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            # Una única transacción evita asignar la misma plaza dos veces.
            conn.execute("BEGIN IMMEDIATE")

            if dni and dni.strip():
                persona = conn.execute(
                    "select * from Persona where dni = ?",
                    (normalizarDni(dni),)
                ).fetchone()

                if (persona is not None and numSocio is not None
                        and persona["numSocio"] != numSocio):
                    raise InscripcionError(
                        "El DNI y el número de socio no corresponden "
                        "a la misma persona"
                    )
            elif numSocio is not None:
                persona = conn.execute(
                    "select * from Persona where numSocio = ?",
                    (numSocio,)
                ).fetchone()
            else:
                raise InscripcionError(
                    "Indica el DNI o el número de socio"
                )

            if persona is None:
                raise InscripcionError(
                    "La persona debe estar registrada previamente"
                )

            actividad = conn.execute(
                """select a.*, o.estado as estadoOferta,
                          o.inicioInscripcionSocios,
                          o.finInscripcionSocios,
                          o.inicioInscripcionNoSocios,
                          o.finInscripcionNoSocios
                   from Actividad a
                   join Oferta o on o.id = a.idOferta
                   where a.id = ?""",
                (idActividad,)
            ).fetchone()

            if actividad is None:
                raise InscripcionError("La actividad no existe")

            existente = conn.execute(
                """select id, estado from Inscripcion
                   where idPersona = ? and idActividad = ?""",
                (persona["id"], idActividad)
            ).fetchone()

            if existente and existente["estado"] != "CANCELADA":
                raise InscripcionError(
                    "Ya existe una solicitud para esta actividad. "
                    f"Estado: {existente['estado']}"
                )

            if actividad["estadoOferta"] != "ACTIVA":
                raise InscripcionError(
                    "La oferta de la actividad no está activa"
                )

            if persona["numSocio"] is not None:
                inicio = actividad["inicioInscripcionSocios"]
                fin = actividad["finInscripcionSocios"]
            else:
                inicio = actividad["inicioInscripcionNoSocios"]
                fin = actividad["finInscripcionNoSocios"]

            if inicio is None or fin is None:
                raise InscripcionError(
                    "El periodo de inscripción no está configurado"
                )

            if not (
                datetime.date.fromisoformat(inicio)
                <= hoy
                <= datetime.date.fromisoformat(fin)
            ):
                raise InscripcionError(
                    "Está fuera del periodo de inscripción "
                    "correspondiente a esta persona"
                )

            solape = conn.execute(
                """select distinct otra.id
                   from Inscripcion i
                   join Actividad otra on otra.id = i.idActividad
                   join Horario h on h.idActividad = otra.id
                   join Horario nuevo on nuevo.idActividad = ?
                   where i.idPersona = ?
                     and i.estado in (
                         'CONFIRMADA', 'PENDIENTE_ACEPTACION'
                     )
                     and otra.id != ?
                     and otra.fechaInicio <= ?
                     and otra.fechaFin >= ?
                     and h.diaSemana = nuevo.diaSemana
                     and h.horaInicio < nuevo.horaFin
                     and nuevo.horaInicio < h.horaFin
                   limit 1""",
                (
                    idActividad,
                    persona["id"],
                    idActividad,
                    actividad["fechaFin"],
                    actividad["fechaInicio"],
                )
            ).fetchone()

            if solape is not None:
                raise InscripcionError(
                    "La actividad coincide en horario con otra "
                    "en la que ya tiene plaza confirmada o pendiente "
                    "de aceptar"
                )

            ocupadas = conn.execute(
                """select count(*) from Inscripcion
                   where idActividad = ?
                     and estado in (
                         'CONFIRMADA', 'PENDIENTE_ACEPTACION'
                     )""",
                (idActividad,)
            ).fetchone()[0]

            # No se adelanta a personas que ya están esperando.
            hayEspera = conn.execute(
                """select 1 from Inscripcion
                   where idActividad = ? and estado = 'EN_ESPERA'
                   limit 1""",
                (idActividad,)
            ).fetchone()

            estado = (
                "CONFIRMADA"
                if ocupadas < actividad["plazas"] and hayEspera is None
                else "EN_ESPERA"
            )
            fechaInscripcion = (
                fechaSolicitud if estado == "CONFIRMADA" else None
            )

            if existente:
                conn.execute(
                    """update Inscripcion
                       set fechaSolicitud = ?, fechaInscripcion = ?,
                           estado = ?
                       where id = ?""",
                    (
                        fechaSolicitud,
                        fechaInscripcion,
                        estado,
                        existente["id"],
                    )
                )
            else:
                conn.execute(
                    """insert into Inscripcion (
                           idPersona, idActividad, fechaSolicitud,
                           fechaInscripcion, estado
                       ) values (?, ?, ?, ?, ?)""",
                    (
                        persona["id"],
                        idActividad,
                        fechaSolicitud,
                        fechaInscripcion,
                        estado,
                    )
                )

            conn.commit()

            if estado == "CONFIRMADA":
                return "Inscripción confirmada correctamente"
            return "Solicitud registrada en lista de espera"

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()