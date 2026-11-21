from src.config import DB_PATH
from src.inscripciones.comun import conectar, describirHorario


class RankingDemandaModel:
    SIN_ACTIVIDADES = "No hay actividades en la temporada actual"

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    def consultarRanking(self):
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

            # Consultamos los horarios aparte para que una inscripción
            # no se cuente varias veces por los días de la actividad.
            filas = conn.execute(
                """SELECT a.id, m.nombre AS modalidad, n.nombre AS nivel,
                          a.plazas,
                          COUNT(CASE WHEN i.estado = 'CONFIRMADA'
                                     THEN i.id END) AS inscritos,
                          COUNT(CASE WHEN i.estado = 'EN_ESPERA'
                                     THEN i.id END) AS espera,
                          COUNT(CASE WHEN i.estado IN ('CONFIRMADA', 'EN_ESPERA')
                                     THEN i.id END) AS demandaTotal
                   FROM Actividad a
                   JOIN Modalidad m ON m.id = a.idModalidad
                   JOIN Nivel n ON n.id = a.idNivel
                   LEFT JOIN Inscripcion i ON i.idActividad = a.id
                   WHERE a.idOferta = ?
                   GROUP BY a.id, m.nombre, n.nombre, a.plazas
                   ORDER BY demandaTotal DESC, m.nombre, n.nombre, a.id""",
                (oferta["id"],)
            ).fetchall()

            actividades = []

            for fila in filas:
                actividad = dict(fila)

                actividad["horario"] = describirHorario(
                    conn, actividad["id"]
                )

                actividad["altaDemanda"] = actividad["espera"] > 0

                # Equivale a menos del 50 %, sin redondeos.
                actividad["bajaDemanda"] = (
                    actividad["inscritos"] * 2 < actividad["plazas"]
                )

                actividades.append(actividad)

            return {
                "oferta": dict(oferta),
                "actividades": actividades,
                "mensaje": "" if actividades else self.SIN_ACTIVIDADES,
            }