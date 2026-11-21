from src.config import DB_PATH
from src.inscripciones.comun import conectar, describirHorario


class OcupacionPlazasModel:
    SIN_ACTIVIDADES = "No hay actividades en la temporada actual"

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    def consultarOcupacion(self):
        with conectar(self.db_path) as conn:
            conn.execute("BEGIN")

            oferta = conn.execute(
                "SELECT * FROM Oferta WHERE estado = 'ACTIVA'"
            ).fetchone()

            if oferta is None:
                return {
                    "oferta": None,
                    "actividades": [],
                    "mensaje": self.SIN_ACTIVIDADES,
                }

            # Los horarios se consultan aparte para no duplicar
            # las inscripciones de actividades con varios días.
            filas = conn.execute(
                """SELECT a.id, m.nombre AS modalidad, n.nombre AS nivel,
                          a.plazas,
                          COUNT(CASE WHEN i.estado = 'CONFIRMADA'
                                     THEN i.id END) AS inscritos,
                          COUNT(CASE WHEN i.estado = 'EN_ESPERA'
                                     THEN i.id END) AS espera
                   FROM Actividad a
                   JOIN Modalidad m ON m.id = a.idModalidad
                   JOIN Nivel n ON n.id = a.idNivel
                   LEFT JOIN Inscripcion i ON i.idActividad = a.id
                   WHERE a.idOferta = ?
                   GROUP BY a.id, m.nombre, n.nombre, a.plazas
                   ORDER BY m.nombre, n.nombre, a.id""",
                (oferta["id"],)
            ).fetchall()

            actividades = []

            for fila in filas:
                actividad = dict(fila)
                plazas = actividad["plazas"]
                inscritos = actividad["inscritos"]

                actividad["horario"] = describirHorario(
                    conn, actividad["id"]
                )
                actividad["ocupacion"] = (
                    inscritos / plazas * 100 if plazas > 0 else None
                )
                actividad["conEspera"] = actividad["espera"] > 0

                # Comparamos sin redondear el porcentaje.
                actividad["bajaOcupacion"] = (
                    plazas > 0 and inscritos * 2 < plazas
                )

                actividades.append(actividad)

            return {
                "oferta": dict(oferta),
                "actividades": actividades,
                "mensaje": "" if actividades else self.SIN_ACTIVIDADES,
            }