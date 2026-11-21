import tempfile
import unittest
from pathlib import Path

from src.config import SCHEMA_PATH, DATA_PATH
from src.inscripciones.ocupacionPlazasModel import OcupacionPlazasModel
from src.util.database import Database


class TestOcupacionPlazas(unittest.TestCase):

    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.db_path = Path(temporal.name) / "ocupacion.db"
        self.db = Database(self.db_path)

        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)
        self.db.executeUpdateQuery("DELETE FROM Asistencia")
        self.db.executeUpdateQuery("DELETE FROM Inscripcion")

        self.modelo = OcupacionPlazasModel(self.db_path)

    def solicitud(self, persona, actividad=1, estado="CONFIRMADA"):
        fecha = "2026-09-10"

        self.db.executeUpdateQuery(
            """INSERT INTO Inscripcion
                   (idPersona, idActividad, fechaSolicitud,
                    fechaInscripcion, estado)
               VALUES (?, ?, ?, ?, ?)""",
            persona,
            actividad,
            fecha,
            fecha if estado == "CONFIRMADA" else None,
            estado
        )

    def actividad(self, identificador=1):
        return next(
            a for a in self.modelo.consultarOcupacion()["actividades"]
            if a["id"] == identificador
        )

    def testCuentaEstadosSinDuplicarHorarios(self):
        self.solicitud(1)
        self.solicitud(2)
        self.solicitud(3, estado="EN_ESPERA")
        self.solicitud(4, estado="CANCELADA")
        self.solicitud(5, estado="PENDIENTE_ACEPTACION")

        a = self.actividad()

        self.assertEqual(
            (a["inscritos"], a["espera"], a["ocupacion"]),
            (2, 1, 50)
        )
        self.assertTrue(a["conEspera"])
        self.assertIn("lunes", a["horario"])
        self.assertIn("miércoles", a["horario"])

    def testMenosDel50SeDestacaYExactamente50No(self):
        self.solicitud(1)
        self.assertTrue(self.actividad()["bajaOcupacion"])

        self.solicitud(2)
        self.assertEqual(self.actividad()["ocupacion"], 50)
        self.assertFalse(self.actividad()["bajaOcupacion"])

    def testSinInscritosMuestraCero(self):
        filas = self.modelo.consultarOcupacion()["actividades"]

        self.assertEqual(len(filas), 10)
        self.assertTrue(all(
            a["inscritos"] == 0 and a["ocupacion"] == 0
            for a in filas
        ))

    def testCeroPlazasNoSePuedeCalcular(self):
        # Simula datos antiguos solo en esta base temporal.
        self.db.executeScriptBatch("""
            PRAGMA ignore_check_constraints = ON;
            UPDATE Actividad SET plazas = 0 WHERE id = 1;
        """)

        a = self.actividad()

        self.assertIsNone(a["ocupacion"])
        self.assertFalse(a["bajaOcupacion"])

    def testLosGruposSeMuestranPorSeparado(self):
        self.solicitud(1, actividad=1)
        self.solicitud(2, actividad=4)
        self.solicitud(3, actividad=4)

        self.assertEqual(self.actividad(1)["inscritos"], 1)
        self.assertEqual(self.actividad(4)["inscritos"], 2)

    def testLasDosIndicacionesSonIndependientes(self):
        self.solicitud(1)
        self.solicitud(2, estado="EN_ESPERA")

        a = self.actividad()

        self.assertTrue(a["conEspera"])
        self.assertTrue(a["bajaOcupacion"])

    def testNoIncluyeOtraTemporada(self):
        self.db.executeUpdateQuery("""
            INSERT INTO Oferta
                (id, curso, fechaInicio, fechaFin, estado)
            VALUES
                (99, '2025-2026', '2025-10-01', '2026-06-30', 'INACTIVA')
        """)
        self.db.executeUpdateQuery("""
            INSERT INTO Actividad
                (id, idOferta, idModalidad, idNivel,
                 fechaInicio, fechaFin, plazas)
            VALUES
                (99, 99, 1, 1, '2025-10-01', '2026-06-30', 30)
        """)

        ids = [
            a["id"]
            for a in self.modelo.consultarOcupacion()["actividades"]
        ]

        self.assertNotIn(99, ids)

    def testTemporadaSinActividades(self):
        self.db.executeUpdateQuery("DELETE FROM Horario")
        self.db.executeUpdateQuery("DELETE FROM Actividad")

        resultado = self.modelo.consultarOcupacion()

        self.assertEqual(resultado["actividades"], [])
        self.assertEqual(
            resultado["mensaje"], self.modelo.SIN_ACTIVIDADES
        )

    def testSinOfertaActiva(self):
        self.db.executeUpdateQuery(
            "UPDATE Oferta SET estado = 'INACTIVA'"
        )

        resultado = self.modelo.consultarOcupacion()

        self.assertIsNone(resultado["oferta"])
        self.assertEqual(resultado["actividades"], [])
        self.assertEqual(
            resultado["mensaje"], self.modelo.SIN_ACTIVIDADES
        )

    def testConsultaNoModificaLosDatos(self):
        antes = self.db_path.read_bytes()

        self.modelo.consultarOcupacion()

        self.assertEqual(self.db_path.read_bytes(), antes)