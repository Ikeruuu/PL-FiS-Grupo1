import os
import tempfile
import unittest

from src.config import SCHEMA_PATH, DATA_PATH
from src.inscripciones.consultaInscritosModel import (
    ConsultaInscritosError,
    ConsultaInscritosModel,
)
from src.util.database import Database


class TestConsultaInscritos(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.addCleanup(os.unlink, self.db_path)

        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)
        self.db.executeUpdateQuery("delete from Inscripcion")
        self.model = ConsultaInscritosModel(self.db_path)

    def solicitud(self, dni, estado="CONFIRMADA", actividad=1):
        fecha = "2026-09-10T10:00:00"
        self.db.executeUpdateQuery(
            """insert into Inscripcion (
                   idPersona, idActividad, fechaSolicitud,
                   fechaInscripcion, estado
               )
               select id, ?, ?, ?, ?
               from Persona where dni = ?""",
            actividad,
            fecha,
            fecha if estado == "CONFIRMADA" else None,
            estado,
            dni
        )

    def testMuestraDatosDelInscrito(self):
        self.solicitud("10000001A")

        resultado = self.model.consultarInscritos(1)
        inscrito = resultado["inscritos"][0]

        self.assertEqual(inscrito["dni"], "10000001A")
        self.assertEqual(inscrito["nombre"], "Marta")
        self.assertEqual(inscrito["apellidos"], "García López")
        self.assertEqual(inscrito["numSocio"], 1)
        self.assertEqual(
            inscrito["fechaInscripcion"],
            "2026-09-10T10:00:00"
        )

    def testIncluyeNoSociosConfirmados(self):
        self.solicitud("20000001F")

        resultado = self.model.consultarInscritos(1)

        self.assertEqual(len(resultado["inscritos"]), 1)
        self.assertIsNone(resultado["inscritos"][0]["numSocio"])

    def testExcluyeEsperaCanceladasYPendientes(self):
        self.solicitud("10000001A", "CONFIRMADA")
        self.solicitud("10000002B", "EN_ESPERA")
        self.solicitud("10000003C", "CANCELADA")
        self.solicitud("10000004D", "PENDIENTE_ACEPTACION")

        resultado = self.model.consultarInscritos(1)

        self.assertEqual(
            [p["dni"] for p in resultado["inscritos"]],
            ["10000001A"]
        )
        self.assertEqual(resultado["plazasTotales"], 4)
        self.assertEqual(resultado["plazasOcupadas"], 1)
        self.assertEqual(resultado["plazasReservadas"], 1)
        self.assertEqual(resultado["plazasDisponibles"], 2)

    def testActividadSinInscritos(self):
        resultado = self.model.consultarInscritos(1)

        self.assertEqual(resultado["inscritos"], [])
        self.assertEqual(resultado["plazasTotales"], 4)
        self.assertEqual(resultado["plazasOcupadas"], 0)
        self.assertEqual(resultado["plazasReservadas"], 0)
        self.assertEqual(resultado["plazasDisponibles"], 4)

    def testActividadCompleta(self):
        for dni in (
            "10000001A", "10000002B",
            "10000003C", "10000004D"
        ):
            self.solicitud(dni)

        resultado = self.model.consultarInscritos(1)

        self.assertEqual(resultado["plazasOcupadas"], 4)
        self.assertEqual(resultado["plazasDisponibles"], 0)

    def testNoMezclaActividades(self):
        self.solicitud("10000001A", actividad=1)
        self.solicitud("10000002B", actividad=2)

        resultado = self.model.consultarInscritos(1)

        self.assertEqual(len(resultado["inscritos"]), 1)
        self.assertEqual(
            resultado["inscritos"][0]["dni"], "10000001A"
        )

    def testMuestraModalidadNivelYHorario(self):
        resultado = self.model.consultarInscritos(1)

        self.assertEqual(
            resultado["actividad"]["modalidad"], "Pádel"
        )
        self.assertEqual(
            resultado["actividad"]["nivel"], "Medio"
        )
        self.assertIn("lunes 18:00", resultado["horario"])
        self.assertIn("miércoles 18:00", resultado["horario"])

    def testActividadInexistente(self):
        with self.assertRaisesRegex(
            ConsultaInscritosError, "La actividad no existe"
        ):
            self.model.consultarInscritos(999)

    def testConsultaNoModificaInscripciones(self):
        self.solicitud("10000001A")
        self.solicitud("10000002B", "EN_ESPERA")
        antes = self.db.executeQuery(
            "select * from Inscripcion order by id"
        )

        self.model.consultarInscritos(1)

        despues = self.db.executeQuery(
            "select * from Inscripcion order by id"
        )
        self.assertEqual(antes, despues)

    def testConsultaReflejaCambiosPosteriores(self):
        self.solicitud("10000001A")
        primero = self.model.consultarInscritos(1)
        self.assertEqual(primero["plazasOcupadas"], 1)

        self.db.executeUpdateQuery(
            """update Inscripcion set estado = 'CANCELADA'
               where idActividad = 1"""
        )

        segundo = self.model.consultarInscritos(1)
        self.assertEqual(segundo["inscritos"], [])
        self.assertEqual(segundo["plazasDisponibles"], 4)


if __name__ == "__main__":
    unittest.main()