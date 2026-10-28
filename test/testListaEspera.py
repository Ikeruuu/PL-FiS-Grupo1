import os
import tempfile
import unittest

from src.config import SCHEMA_PATH, DATA_PATH
from src.inscripciones.cancelacionModel import CancelacionModel
from src.inscripciones.comun import IdentificacionError
from src.inscripciones.listaEsperaModel import (
    ListaEsperaError,
    ListaEsperaModel,
)
from src.util.database import Database


class TestListaEspera(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.addCleanup(os.unlink, self.db_path)

        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)

        #Cada prueba prepara sus propias solicitudes.
        self.db.executeUpdateQuery("delete from Inscripcion")
        self.db.executeUpdateQuery(
            "update Actividad set plazas = 1 where id = 1"
        )
        self.model = ListaEsperaModel(self.db_path)

    def solicitud(self, dni, estado="EN_ESPERA",
                  fecha="2026-09-10T10:00:00"):
        persona = self.db.executeQuery(
            "select id from Persona where dni = ?", dni
        )[0]
        fechaInscripcion = fecha if estado == "CONFIRMADA" else None

        self.db.executeUpdateQuery(
            """insert into Inscripcion (
                   idPersona, idActividad, fechaSolicitud,
                   fechaInscripcion, estado
               ) values (?, 1, ?, ?, ?)""",
            persona["id"], fecha, fechaInscripcion, estado
        )

    def estadoGuardado(self, dni):
        return self.db.executeQuery(
            """select i.estado from Inscripcion i
               join Persona p on p.id = i.idPersona
               where p.dni = ? and i.idActividad = 1""",
            dni
        )[0]["estado"]

    def testSociosTienenPrioridadAunqueLleguenDespues(self):
        self.solicitud(
            "20000001F", fecha="2026-09-10T09:00:00"
        )
        self.solicitud(
            "10000001A", fecha="2026-09-10T10:00:00"
        )

        socio = self.model.consultarEstado(1, dni="10000001A")
        noSocio = self.model.consultarEstado(1, dni="20000001F")

        self.assertEqual(socio["posicion"], 1)
        self.assertEqual(noSocio["posicion"], 2)
        self.assertEqual(socio["totalEspera"], 2)

    def testDentroDelGrupoSeRespetaOrdenDeLlegada(self):
        self.solicitud(
            "10000002B", fecha="2026-09-10T09:00:00"
        )
        self.solicitud(
            "10000001A", fecha="2026-09-10T10:00:00"
        )

        resultado = self.model.consultarEstado(
            1, dni="10000002B"
        )
        self.assertEqual(resultado["posicion"], 1)

    def testConsultaPorNumeroDeSocio(self):
        self.solicitud("10000001A")
        resultado = self.model.consultarEstado(1, numSocio=1)
        self.assertEqual(resultado["persona"]["dni"], "10000001A")
        self.assertEqual(resultado["estado"], "EN_ESPERA")

    def testConsultaConfirmadaSinPosicion(self):
        self.solicitud("10000001A", estado="CONFIRMADA")
        resultado = self.model.consultarEstado(
            1, dni="10000001A"
        )
        self.assertEqual(resultado["estado"], "CONFIRMADA")
        self.assertIsNone(resultado["posicion"])

    def testConsultaNoModificaSolicitudes(self):
        self.solicitud("10000001A")
        antes = self.db.executeQuery(
            "select * from Inscripcion order by id"
        )

        self.model.consultarEstado(1, dni="10000001A")

        despues = self.db.executeQuery(
            "select * from Inscripcion order by id"
        )
        self.assertEqual(antes, despues)

    def testConsultaSinSolicitud(self):
        with self.assertRaisesRegex(
            ListaEsperaError, "No existe una solicitud"
        ):
            self.model.consultarEstado(1, dni="10000001A")

    def testPersonaInexistente(self):
        with self.assertRaises(IdentificacionError):
            self.model.consultarEstado(1, dni="NOEXISTE")

    def testActividadInexistente(self):
        with self.assertRaisesRegex(
            ListaEsperaError, "actividad no existe"
        ):
            self.model.consultarEstado(999, dni="10000001A")

    def testOfrecePlazaAlSocioYReservaSinConfirmar(self):
        self.solicitud(
            "20000001F", fecha="2026-09-10T09:00:00"
        )
        self.solicitud(
            "10000001A", fecha="2026-09-10T10:00:00"
        )

        self.assertEqual(self.model.ofrecerPlazas(1), 1)
        self.assertEqual(
            self.estadoGuardado("10000001A"),
            "PENDIENTE_ACEPTACION"
        )
        self.assertEqual(
            self.estadoGuardado("20000001F"), "EN_ESPERA"
        )

        resultado = self.model.consultarEstado(
            1, dni="10000001A"
        )
        self.assertIsNone(
            resultado["solicitud"]["fechaInscripcion"]
        )
        self.assertIsNone(resultado["posicion"])

        #La plaza pendiente ya está reservada.
        self.assertEqual(self.model.ofrecerPlazas(1), 0)

    def testNoOfreceSiNoQuedanPlazas(self):
        self.solicitud("10000001A", estado="CONFIRMADA")
        self.solicitud("10000002B")

        self.assertEqual(self.model.ofrecerPlazas(1), 0)
        self.assertEqual(
            self.estadoGuardado("10000002B"), "EN_ESPERA"
        )

    def testOfreceSoloLasPlazasDisponibles(self):
        self.db.executeUpdateQuery(
            "update Actividad set plazas = 2 where id = 1"
        )
        self.solicitud(
            "10000001A", fecha="2026-09-10T09:00:00"
        )
        self.solicitud(
            "10000002B", fecha="2026-09-10T10:00:00"
        )
        self.solicitud(
            "20000001F", fecha="2026-09-10T11:00:00"
        )

        self.assertEqual(self.model.ofrecerPlazas(1), 2)
        self.assertEqual(
            self.estadoGuardado("20000001F"), "EN_ESPERA"
        )

    def testSinListaNoOfrecePlazas(self):
        self.assertEqual(self.model.ofrecerPlazas(1), 0)

    def testOfrecerEnActividadInexistente(self):
        with self.assertRaises(ListaEsperaError):
            self.model.ofrecerPlazas(999)

    def testCancelacionDeChemaOfrecePlazaYActualizaPosicion(self):
        self.solicitud("10000001A", estado="CONFIRMADA")
        self.solicitud(
            "20000001F", fecha="2026-09-10T09:00:00"
        )
        self.solicitud(
            "10000002B", fecha="2026-09-10T10:00:00"
        )

        CancelacionModel(self.db_path).cancelar(
            1, dni="10000001A", hoy="2026-09-11"
        )

        socio = self.model.consultarEstado(
            1, dni="10000002B"
        )
        noSocio = self.model.consultarEstado(
            1, dni="20000001F"
        )
        self.assertEqual(
            socio["estado"], "PENDIENTE_ACEPTACION"
        )
        self.assertEqual(noSocio["posicion"], 1)
        self.assertEqual(noSocio["totalEspera"], 1)
    def testAceptaPlazaPendiente(self):
        self.solicitud("10000001A")
        self.model.ofrecerPlazas(1)

        mensaje = self.model.aceptarPlaza(
            1, dni="10000001A"
        )

        resultado = self.model.consultarEstado(
            1, dni="10000001A"
        )
        self.assertIn("confirmada", mensaje)
        self.assertEqual(resultado["estado"], "CONFIRMADA")
        self.assertIsNotNone(
            resultado["solicitud"]["fechaInscripcion"]
        )
        self.assertIsNone(resultado["posicion"])

    def testNoAceptaSiSigueEnEspera(self):
        self.solicitud("10000001A")

        with self.assertRaisesRegex(
            ListaEsperaError, "pendiente de aceptar"
        ):
            self.model.aceptarPlaza(1, dni="10000001A")

        self.assertEqual(
            self.estadoGuardado("10000001A"), "EN_ESPERA"
        )

    def testNoAceptaDosVeces(self):
        self.solicitud("10000001A")
        self.model.ofrecerPlazas(1)
        self.model.aceptarPlaza(1, dni="10000001A")

        antes = self.model.consultarEstado(
            1, dni="10000001A"
        )["solicitud"]

        with self.assertRaises(ListaEsperaError):
            self.model.aceptarPlaza(1, dni="10000001A")

        despues = self.model.consultarEstado(
            1, dni="10000001A"
        )["solicitud"]
        self.assertEqual(antes, despues)

    def testAceptarSinSolicitud(self):
        with self.assertRaisesRegex(
            ListaEsperaError, "No existe una solicitud"
        ):
            self.model.aceptarPlaza(1, dni="10000001A")

    def testAceptarConSolapeNoConfirma(self):
        self.solicitud(
            "10000001A", estado="PENDIENTE_ACEPTACION"
        )

        #Actividad 4: lunes 18:30-19:30.
        #Se solapa con la actividad 1: lunes 18:00-19:00.
        self.db.executeUpdateQuery(
            """insert into Inscripcion (
                   idPersona, idActividad, fechaSolicitud,
                   fechaInscripcion, estado
               )
               select id, 4, ?, ?, 'CONFIRMADA'
               from Persona where dni = ?""",
            "2026-09-10T10:00:00",
            "2026-09-10T10:00:00",
            "10000001A"
        )

        with self.assertRaisesRegex(
            ListaEsperaError, "coincide en horario"
        ):
            self.model.aceptarPlaza(1, dni="10000001A")

        self.assertEqual(
            self.estadoGuardado("10000001A"),
            "PENDIENTE_ACEPTACION"
        )

    def testAceptaPlazaOfrecidaTrasCancelacion(self):
        self.solicitud("10000001A", estado="CONFIRMADA")
        self.solicitud("10000002B")

        CancelacionModel(self.db_path).cancelar(
            1, dni="10000001A", hoy="2026-09-11"
        )
        self.model.aceptarPlaza(1, numSocio=2)

        self.assertEqual(
            self.estadoGuardado("10000002B"), "CONFIRMADA"
        )
        self.assertEqual(
            self.estadoGuardado("10000001A"), "CANCELADA"
        )
    def testRechazarRetiraYOfreceAlSiguiente(self):
        self.solicitud(
            "10000001A", estado="PENDIENTE_ACEPTACION"
        )
        self.solicitud(
            "20000001F", fecha="2026-09-10T09:00:00"
        )
        self.solicitud(
            "10000002B", fecha="2026-09-10T10:00:00"
        )

        self.model.rechazarPlaza(1, dni="10000001A")

        self.assertEqual(
            self.estadoGuardado("10000001A"), "CANCELADA"
        )
        self.assertEqual(
            self.estadoGuardado("10000002B"),
            "PENDIENTE_ACEPTACION"
        )
        resultado = self.model.consultarEstado(
            1, dni="20000001F"
        )
        self.assertEqual(resultado["posicion"], 1)

    def testRechazarSinPersonasEsperando(self):
        self.solicitud(
            "10000001A", estado="PENDIENTE_ACEPTACION"
        )

        self.model.rechazarPlaza(1, numSocio=1)

        resultado = self.model.consultarEstado(
            1, dni="10000001A"
        )
        self.assertEqual(resultado["estado"], "CANCELADA")
        self.assertIsNotNone(
            resultado["solicitud"]["fechaCancelacion"]
        )
        self.assertEqual(resultado["totalEspera"], 0)
        self.assertEqual(self.model.ofrecerPlazas(1), 0)

    def testNoRechazaInscripcionConfirmada(self):
        self.solicitud("10000001A", estado="CONFIRMADA")

        with self.assertRaisesRegex(
            ListaEsperaError, "pendiente de aceptar"
        ):
            self.model.rechazarPlaza(1, dni="10000001A")

        self.assertEqual(
            self.estadoGuardado("10000001A"), "CONFIRMADA"
        )

    def testNoRechazaDosVeces(self):
        self.solicitud(
            "10000001A", estado="PENDIENTE_ACEPTACION"
        )
        self.model.rechazarPlaza(1, dni="10000001A")

        with self.assertRaises(ListaEsperaError):
            self.model.rechazarPlaza(1, dni="10000001A")


if __name__ == "__main__":
    unittest.main()