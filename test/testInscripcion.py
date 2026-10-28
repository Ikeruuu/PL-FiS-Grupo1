import datetime
import os
import tempfile
import unittest

from src.config import SCHEMA_PATH, DATA_PATH
from src.inscripciones.inscripcionModel import (
    InscripcionError,
    InscripcionModel,
)
from src.util.database import Database


HOY_SOCIOS = datetime.date(2026, 9, 10)
HOY_NO_SOCIOS = datetime.date(2026, 9, 22)


class TestInscripcion(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.addCleanup(os.unlink, self.db_path)

        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)

        self.db.executeUpdateQuery(
            """update Oferta
               set inicioInscripcionSocios = '2026-09-01',
                   finInscripcionSocios = '2026-09-15',
                   inicioInscripcionNoSocios = '2026-09-16',
                   finInscripcionNoSocios = '2026-09-30'
               where id = 1"""
        )
        self.model = InscripcionModel(self.db_path)

    def solicitar(self, actividad=1, dni="10000001A", hoy=HOY_SOCIOS):
        return self.model.inscribir(actividad, dni=dni, hoy=hoy)

    def solicitudes(self):
        return self.db.executeQuery(
            "select * from Inscripcion order by id"
        )

    def testInscripcionDeSocioPorDni(self):
        mensaje = self.solicitar()
        self.assertIn("confirmada", mensaje)
        filas = self.solicitudes()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["estado"], "CONFIRMADA")
        self.assertIsNotNone(filas[0]["fechaInscripcion"])

    def testInscripcionPorNumeroSocio(self):
        self.model.inscribir(1, numSocio=2, hoy=HOY_SOCIOS)
        fila = self.solicitudes()[0]
        persona = self.db.executeQuery(
            "select dni from Persona where id = ?", fila["idPersona"]
        )[0]
        self.assertEqual(persona["dni"], "10000002B")

    def testNormalizaDni(self):
        self.solicitar(dni=" 10000001-a ")
        self.assertEqual(len(self.solicitudes()), 1)

    def testInscripcionDeNoSocio(self):
        self.solicitar(dni="20000001F", hoy=HOY_NO_SOCIOS)
        self.assertEqual(
            self.solicitudes()[0]["estado"], "CONFIRMADA"
        )

    def testPersonaInexistente(self):
        with self.assertRaisesRegex(
            InscripcionError, "registrada previamente"
        ):
            self.solicitar(dni="NOEXISTE")
        self.assertEqual(self.solicitudes(), [])

    def testActividadInexistente(self):
        with self.assertRaisesRegex(
            InscripcionError, "actividad no existe"
        ):
            self.solicitar(actividad=999)
        self.assertEqual(self.solicitudes(), [])

    def testFaltaIdentificador(self):
        with self.assertRaisesRegex(InscripcionError, "Indica el DNI"):
            self.model.inscribir(1, hoy=HOY_SOCIOS)

    def testDniYNumeroSocioNoCoinciden(self):
        with self.assertRaisesRegex(
            InscripcionError, "misma persona"
        ):
            self.model.inscribir(
                1, dni="10000001A", numSocio=2, hoy=HOY_SOCIOS
            )
        self.assertEqual(self.solicitudes(), [])

    def testRechazaFueraDePlazo(self):
        for dni, fecha in [
            ("10000001A", datetime.date(2026, 8, 31)),
            ("10000001A", HOY_NO_SOCIOS),
            ("20000001F", HOY_SOCIOS),
            ("20000001F", datetime.date(2026, 10, 1)),
        ]:
            with self.subTest(dni=dni, fecha=fecha):
                with self.assertRaisesRegex(
                    InscripcionError, "fuera del periodo"
                ):
                    self.solicitar(dni=dni, hoy=fecha)

        self.assertEqual(self.solicitudes(), [])

    def testAceptaFechasLimiteDelPeriodo(self):
        for dia in (1, 15):
            with self.subTest(dia=dia):
                self.db.executeUpdateQuery("delete from Inscripcion")
                self.solicitar(hoy=datetime.date(2026, 9, dia))
                self.assertEqual(
                    self.solicitudes()[0]["estado"], "CONFIRMADA"
                )

    def testPeriodoSinConfigurar(self):
        self.db.executeUpdateQuery(
            """update Oferta
               set inicioInscripcionSocios = null,
                   finInscripcionSocios = null"""
        )
        with self.assertRaisesRegex(
            InscripcionError, "no está configurado"
        ):
            self.solicitar()

    def testOfertaInactiva(self):
        self.db.executeUpdateQuery(
            "update Oferta set estado = 'INACTIVA'"
        )
        with self.assertRaisesRegex(InscripcionError, "no está activa"):
            self.solicitar()

    def testNoDuplicaInscripcionConfirmada(self):
        self.solicitar()
        with self.assertRaisesRegex(
            InscripcionError, "Ya existe una solicitud"
        ):
            self.solicitar()
        self.assertEqual(len(self.solicitudes()), 1)

    def testSinPlazasEntraEnEsperaYNoSeDuplica(self):
        self.db.executeUpdateQuery(
            "update Actividad set plazas = 1 where id = 1"
        )
        self.solicitar()
        mensaje = self.solicitar(dni="10000002B")
        self.assertIn("lista de espera", mensaje)

        with self.assertRaisesRegex(
            InscripcionError, "Ya existe una solicitud"
        ):
            self.solicitar(dni="10000002B")

        filas = self.solicitudes()
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[1]["estado"], "EN_ESPERA")
        self.assertIsNone(filas[1]["fechaInscripcion"])

    def testRechazaSolapeDeHorarios(self):
        # Actividad 1: lunes 18:00-19:00.
        # Actividad 4: lunes 18:30-19:30.
        self.solicitar(actividad=1)
        with self.assertRaisesRegex(
            InscripcionError, "coincide en horario"
        ):
            self.solicitar(actividad=4)
        self.assertEqual(len(self.solicitudes()), 1)

    def testPermiteHorariosConsecutivos(self):
        # Actividad 5 empieza a las 19:00, cuando termina la 1.
        self.solicitar(actividad=1)
        self.solicitar(actividad=5)
        self.assertEqual(len(self.solicitudes()), 2)

    def testPermiteMismoHorarioEnFechasDistintas(self):
        # Actividad 3 termina en diciembre.
        # Actividad 6 empieza en enero, con el mismo horario.
        self.solicitar(actividad=3)
        self.solicitar(actividad=6)
        self.assertEqual(len(self.solicitudes()), 2)

    def testReutilizaSolicitudCancelada(self):
        self.solicitar()
        idOriginal = self.solicitudes()[0]["id"]
        self.db.executeUpdateQuery(
            """update Inscripcion
               set estado = 'CANCELADA', fechaInscripcion = null
               where id = ?""",
            idOriginal
        )

        self.solicitar()

        filas = self.solicitudes()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id"], idOriginal)
        self.assertEqual(filas[0]["estado"], "CONFIRMADA")

    def testPlazaPendienteDeAceptarReservaCapacidad(self):
        self.db.executeUpdateQuery(
            "update Actividad set plazas = 1 where id = 1"
        )
        self.solicitar()
        self.db.executeUpdateQuery(
            """update Inscripcion
               set estado = 'PENDIENTE_ACEPTACION',
                   fechaInscripcion = null"""
        )

        self.solicitar(dni="10000002B")

        self.assertEqual(
            self.solicitudes()[1]["estado"], "EN_ESPERA"
        )


if __name__ == "__main__":
    unittest.main()