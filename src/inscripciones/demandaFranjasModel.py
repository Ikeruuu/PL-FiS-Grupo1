from datetime import datetime

from src.config import DB_PATH
from src.inscripciones.comun import conectar
from src.instalaciones.instalacionModel import DIAS_SEMANA


FRANJAS = (
    ("08:00", "11:00"),
    ("11:00", "14:00"),
    ("14:00", "17:00"),
    ("17:00", "20:00"),
)


class DemandaFranjasError(Exception):
    pass


def indiceFranja(hora):
    return next(
        (
            i for i, (inicio, fin) in enumerate(FRANJAS)
            if inicio <= hora < fin
        ),
        None
    )


def agruparFranjas(actividades):
    filas = {
        (dia, franja): {
            "diaSemana": dia,
            "dia": DIAS_SEMANA[dia],
            "indiceFranja": franja,
            "franja": f"{inicio}–{fin}",
            "grupos": 0,
            "inscritos": 0,
            "espera": 0,
            "porcentajes": [],
        }
        for dia in range(1, 8)
        for franja, (inicio, fin) in enumerate(FRANJAS)
    }

    fuera = 0
    sinHorario = 0

    for actividad in actividades:
        if not actividad["horarios"]:
            sinHorario += 1

        combinaciones = set()

        for horario in actividad["horarios"]:
            franja = indiceFranja(horario["horaInicio"])

            if franja is None:
                fuera += 1
            else:
                combinaciones.add(
                    (horario["diaSemana"], franja)
                )

        # Cada actividad cuenta una vez por día y franja.
        for clave in combinaciones:
            fila = filas[clave]

            fila["grupos"] += 1
            fila["inscritos"] += actividad["inscritos"]
            fila["espera"] += actividad["espera"]

            porcentaje = (
                100 * actividad["inscritos"] / actividad["plazas"]
                if actividad["plazas"] > 0 else None
            )

            fila["porcentajes"].append(porcentaje)

    for fila in filas.values():
        porcentajes = fila.pop("porcentajes")

        fila["demandaTotal"] = (
            fila["inscritos"] + fila["espera"]
        )

        fila["ocupacionMedia"] = (
            sum(porcentajes) / len(porcentajes)
            if porcentajes and None not in porcentajes
            else None
        )

    resultado = sorted(
        filas.values(),
        key=lambda f: (
            -f["demandaTotal"],
            f["diaSemana"],
            f["indiceFranja"]
        )
    )

    return resultado, fuera, sinHorario


class DemandaFranjasModel:

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    @staticmethod
    def _existe(conn, tabla):
        return conn.execute(
            """SELECT 1 FROM sqlite_master
               WHERE type = 'table' AND name = ?""",
            (tabla,)
        ).fetchone() is not None

    @classmethod
    def _temporadas(cls, conn):
        resultado = []

        ofertas = conn.execute(
            """SELECT id, curso, estado
               FROM Oferta
               ORDER BY estado = 'ACTIVA' DESC,
                        fechaInicio DESC, id DESC"""
        )

        for oferta in ofertas:
            actual = oferta["estado"] == "ACTIVA"
            descripcion = "actual" if actual else "oferta anterior"

            resultado.append({
                "clave": f"O:{oferta['id']}",
                "actual": actual,
                "nombre": f"{oferta['curso']} ({descripcion})",
            })

        if cls._existe(conn, "ActividadHistorica"):
            historicas = conn.execute(
                """SELECT DISTINCT temporada
                   FROM ActividadHistorica
                   ORDER BY temporada DESC"""
            )

            for fila in historicas:
                resultado.append({
                    "clave": f"H:{fila['temporada']}",
                    "actual": False,
                    "nombre": (
                        f"{fila['temporada']} "
                        "(histórico importado)"
                    ),
                })

        return resultado

    def getTemporadas(self):
        with conectar(self.db_path) as conn:
            return self._temporadas(conn)

    def getInstalaciones(self):
        with conectar(self.db_path) as conn:
            return [
                dict(fila)
                for fila in conn.execute(
                    """SELECT id, nombre FROM Instalacion
                       ORDER BY nombre, id"""
                )
            ]

    @classmethod
    def _horariosHistoricos(cls, conn, idActividad=None):
        if not cls._existe(conn, "HorarioHistoricoFranjas"):
            return []

        return [
            dict(fila)
            for fila in conn.execute(
                """SELECT h.*, i.nombre AS instalacion
                   FROM HorarioHistoricoFranjas h
                   JOIN Instalacion i ON i.id = h.idInstalacion
                   WHERE (? IS NULL OR h.idActividad = ?)
                   ORDER BY h.diaSemana, h.horaInicio, h.id""",
                (idActividad, idActividad)
            )
        ]

    def getHorariosHistoricos(self, idActividad):
        with conectar(self.db_path) as conn:
            return self._horariosHistoricos(conn, idActividad)

    def getActividadesHistoricas(self, temporada):
        with conectar(self.db_path) as conn:
            if not self._existe(conn, "ActividadHistorica"):
                return []

            return [
                dict(fila)
                for fila in conn.execute(
                    """SELECT a.id, a.plazas,
                              m.nombre AS modalidad,
                              n.nombre AS nivel
                       FROM ActividadHistorica a
                       JOIN Modalidad m ON m.id = a.idModalidad
                       JOIN Nivel n ON n.id = a.idNivel
                       WHERE a.temporada = ?
                       ORDER BY m.nombre, n.nombre, a.id""",
                    (temporada,)
                )
            ]

    def consultar(self, temporada=None, idInstalacion=None):
        with conectar(self.db_path) as conn:
            conn.execute("BEGIN")

            opciones = self._temporadas(conn)

            if temporada is None:
                temporada = next(
                    (
                        opcion["clave"]
                        for opcion in opciones
                        if opcion["actual"]
                    ),
                    None
                )

            if temporada is None:
                return {
                    "filas": [],
                    "mensaje": "No hay una temporada actual activa.",
                    "avisos": [],
                    "sinHorarioHistorico": 0,
                }

            if temporada not in {
                opcion["clave"] for opcion in opciones
            }:
                raise DemandaFranjasError(
                    "Selecciona una temporada válida."
                )

            if idInstalacion is not None:
                existe = conn.execute(
                    "SELECT 1 FROM Instalacion WHERE id = ?",
                    (idInstalacion,)
                ).fetchone()

                if existe is None:
                    raise DemandaFranjasError(
                        "La instalación seleccionada no existe."
                    )

            origen, identificador = temporada.split(":", 1)

            if origen == "O":
                actividades = self._oferta(
                    conn, identificador, idInstalacion
                )
                pendientes = 0
            else:
                actividades, pendientes = self._historico(
                    conn, identificador, idInstalacion
                )

            avisos = []

            if pendientes:
                avisos.append(
                    f"Hay {pendientes} actividades históricas sin "
                    "instalación y horario completados. "
                    "No se incluyen en el resumen."
                )

            if not actividades:
                mensaje = (
                    "Falta completar la instalación y los horarios "
                    "del histórico importado."
                    if pendientes
                    else "No hay actividades para la temporada "
                         "e instalación seleccionadas."
                )

                return {
                    "filas": [],
                    "mensaje": mensaje,
                    "avisos": avisos,
                    "sinHorarioHistorico": pendientes,
                }

            filas, fuera, sinHorario = agruparFranjas(actividades)

            if fuera:
                avisos.append(
                    f"{fuera} horarios empiezan fuera de "
                    "08:00–20:00 y no entran en las cuatro franjas."
                )

            if sinHorario:
                avisos.append(
                    f"{sinHorario} actividades no tienen horario "
                    "y no se pueden agrupar."
                )

            return {
                "filas": filas,
                "mensaje": "",
                "avisos": avisos,
                "sinHorarioHistorico": pendientes,
            }

    @staticmethod
    def _oferta(conn, idOferta, idInstalacion):
        actividades = {
            fila["id"]: dict(fila)
            for fila in conn.execute(
                """SELECT a.id, a.plazas,
                          COUNT(CASE WHEN i.estado = 'CONFIRMADA'
                                     THEN i.id END) AS inscritos,
                          COUNT(CASE WHEN i.estado = 'EN_ESPERA'
                                     THEN i.id END) AS espera
                   FROM Actividad a
                   LEFT JOIN Inscripcion i ON i.idActividad = a.id
                   WHERE a.idOferta = ?
                     AND (? IS NULL OR a.idInstalacion = ?)
                   GROUP BY a.id, a.plazas""",
                (idOferta, idInstalacion, idInstalacion)
            )
        }

        for actividad in actividades.values():
            actividad["horarios"] = []

        horarios = conn.execute(
            """SELECT h.idActividad, h.diaSemana, h.horaInicio
               FROM Horario h
               JOIN Actividad a ON a.id = h.idActividad
               WHERE a.idOferta = ?
                 AND (? IS NULL OR a.idInstalacion = ?)""",
            (idOferta, idInstalacion, idInstalacion)
        )

        for horario in horarios:
            actividades[horario["idActividad"]]["horarios"].append(
                dict(horario)
            )

        return list(actividades.values())

    @classmethod
    def _historico(cls, conn, temporada, idInstalacion):
        actividades = {
            fila["id"]: dict(fila)
            for fila in conn.execute(
                """SELECT a.id, a.plazas,
                          COUNT(CASE WHEN i.estado = 'CONFIRMADA'
                                     THEN i.id END) AS inscritos,
                          COUNT(CASE WHEN i.estado = 'EN_ESPERA'
                                     THEN i.id END) AS espera
                   FROM ActividadHistorica a
                   LEFT JOIN InscripcionHistorica i
                     ON i.idActividad = a.id
                   WHERE a.temporada = ?
                   GROUP BY a.id, a.plazas""",
                (temporada,)
            )
        }

        for actividad in actividades.values():
            actividad["horarios"] = []

        todos = cls._horariosHistoricos(conn)

        conHorario = {
            horario["idActividad"] for horario in todos
        }

        pendientes = sum(
            identificador not in conHorario
            for identificador in actividades
        )

        for horario in todos:
            if (
                horario["idActividad"] in actividades
                and (
                    idInstalacion is None
                    or horario["idInstalacion"] == idInstalacion
                )
            ):
                actividades[horario["idActividad"]]["horarios"].append(
                    horario
                )

        return [
            actividad
            for actividad in actividades.values()
            if actividad["horarios"]
        ], pendientes

    def guardarHorarioHistorico(
        self, idActividad, idInstalacion, diaSemana, horaInicio
    ):
        try:
            diaSemana = int(diaSemana)
            horaInicio = datetime.strptime(
                horaInicio.strip(), "%H:%M"
            ).strftime("%H:%M")
        except (ValueError, TypeError, AttributeError) as error:
            raise DemandaFranjasError(
                "Indica un día válido y una hora con formato HH:MM."
            ) from error

        if not 1 <= diaSemana <= 7:
            raise DemandaFranjasError(
                "El día debe estar entre lunes y domingo."
            )

        with conectar(self.db_path) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")

            if (
                not self._existe(conn, "ActividadHistorica")
                or not conn.execute(
                    "SELECT 1 FROM ActividadHistorica WHERE id = ?",
                    (idActividad,)
                ).fetchone()
            ):
                raise DemandaFranjasError(
                    "Selecciona una actividad histórica importada."
                )

            if not conn.execute(
                "SELECT 1 FROM Instalacion WHERE id = ?",
                (idInstalacion,)
            ).fetchone():
                raise DemandaFranjasError(
                    "Selecciona una instalación válida."
                )

            conn.execute("""
                CREATE TABLE IF NOT EXISTS HorarioHistoricoFranjas (
                    id INTEGER PRIMARY KEY,
                    idActividad INTEGER NOT NULL
                        REFERENCES ActividadHistorica(id)
                        ON DELETE CASCADE,
                    idInstalacion INTEGER NOT NULL
                        REFERENCES Instalacion(id)
                        ON DELETE CASCADE,
                    diaSemana INTEGER NOT NULL
                        CHECK (diaSemana BETWEEN 1 AND 7),
                    horaInicio TEXT NOT NULL,
                    UNIQUE (idActividad, diaSemana, horaInicio)
                )
            """)

            conn.execute(
                """INSERT INTO HorarioHistoricoFranjas
                       (idActividad, idInstalacion,
                        diaSemana, horaInicio)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(idActividad, diaSemana, horaInicio)
                   DO UPDATE SET
                       idInstalacion = excluded.idInstalacion""",
                (
                    idActividad,
                    idInstalacion,
                    diaSemana,
                    horaInicio
                )
            )

    def eliminarHorarioHistorico(self, idHorario):
        with conectar(self.db_path) as conn, conn:
            if self._existe(conn, "HorarioHistoricoFranjas"):
                conn.execute(
                    "DELETE FROM HorarioHistoricoFranjas WHERE id = ?",
                    (idHorario,)
                )