import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from src.config import SCHEMA_PATH, DATA_PATH
from src.inscripciones.rankingDemandaModel import RankingDemandaModel


class TestRankingDemanda(unittest.TestCase):

    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.db_path = Path(temporal.name) / "ranking.db"

        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.executescript(DATA_PATH.read_text(encoding="utf-8"))
            conn.execute("DELETE FROM Asistencia")
            conn.execute("DELETE FROM Inscripcion")

        self.modelo = RankingDemandaModel(self.db_path)

    def ejecutar(self, sql):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(sql)

    def testExactamenteEl50PorCientoNoEsBajaDemanda(self):
        self.ejecutar(
            "UPDATE Actividad SET plazas = 4 WHERE id = 1"
        )
        self.ejecutar("""
            INSERT INTO Inscripcion
                (idPersona, idActividad, fechaSolicitud,
                 fechaInscripcion, estado)
            VALUES
                (1, 1, '2026-09-10', '2026-09-10', 'CONFIRMADA'),
                (2, 1, '2026-09-10', '2026-09-10', 'CONFIRMADA')
        """)

        resultado = self.modelo.consultarRanking()
        actividad = next(
            a for a in resultado["actividades"] if a["id"] == 1
        )

        # Dos inscritos de cuatro plazas: exactamente el 50 %.
        self.assertEqual(actividad["inscritos"], 2)
        self.assertEqual(actividad["plazas"], 4)
        self.assertFalse(actividad["bajaDemanda"])

    def testTemporadaActualSinActividades(self):
        self.ejecutar(
            "UPDATE Oferta SET estado = 'INACTIVA'"
        )
        self.ejecutar("""
            INSERT INTO Oferta
                (curso, fechaInicio, fechaFin, estado)
            VALUES
                ('2027-2028', '2027-10-01', '2028-06-30', 'ACTIVA')
        """)

        resultado = self.modelo.consultarRanking()

        self.assertEqual(
            resultado["oferta"]["curso"], "2027-2028"
        )
        self.assertEqual(resultado["actividades"], [])
        self.assertEqual(
            resultado["mensaje"],
            "No hay actividades en la temporada actual"
        )


if __name__ == "__main__":
    unittest.main()