import os
import tempfile
import unittest

from src.config import DATA_PATH, SCHEMA_PATH
from src.inscripciones.comun import IdentificacionError
from src.inscripciones.misInscripcionesModel import MisInscripcionesModel
from src.util.database import Database


class TestMisInscripciones(unittest.TestCase):
    '''HU Consultar las actividades en las que estoy inscrito (RedKanban 35336).'''

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.addCleanup(os.unlink, self.db_path)
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)
        self.model = MisInscripcionesModel(self.db_path)

    def solicitud(self, idPersona, idActividad, estado, fecha="2026-09-02T10:00:00",
                  cancelaDesde=None):
        self.db.executeUpdateQuery(
            """insert into Inscripcion (idPersona, idActividad, fechaSolicitud, fechaInscripcion,
               estado, fechaCancelacion, cancelaDesde) values (?, ?, ?, ?, ?, ?, ?)""",
            idPersona, idActividad, fecha, fecha if estado == "CONFIRMADA" else None, estado,
            fecha if estado == "CANCELADA" else None, cancelaDesde)

    #Lista todas las inscripciones con modalidad, nivel, horario, instalación y estado
    def testListaConTodosLosEstados(self):
        self.solicitud(1, 1, "CONFIRMADA")
        self.solicitud(1, 2, "PENDIENTE_ACEPTACION")
        self.solicitud(1, 3, "CANCELADA")
        self.solicitud(1, 4, "EN_ESPERA")
        persona, lista, mensaje = self.model.consultarInscripciones(dni="10000001A")
        self.assertIsNone(mensaje)
        self.assertEqual(persona["nombre"], "Marta")
        self.assertEqual([f["descripcionEstado"] for f in lista],
                         ["Inscrito", "Plaza pendiente de aceptar",
                          "En lista de espera (posición 1 de 1)", "Cancelada"])
        padel = lista[0]
        self.assertEqual((padel["modalidad"], padel["nivel"]), ("Pádel", "Medio"))
        self.assertEqual(padel["horario"], "lunes 18:00–19:00, miércoles 18:00–19:00")
        self.assertEqual(padel["instalacion"], "Pista de pádel 1")
        self.assertEqual(lista[2]["instalacion"], "Sin asignar")

    #En lista de espera: posición y total («posición 3 de 3»); los socios van primero
    def testPosicionEnListaDeEspera(self):
        self.solicitud(6, 1, "EN_ESPERA", "2026-09-01T09:00:00")   #no socio
        self.solicitud(2, 1, "EN_ESPERA", "2026-09-02T09:00:00")
        self.solicitud(3, 1, "EN_ESPERA", "2026-09-03T09:00:00")
        _, lista, _ = self.model.consultarInscripciones(dni="20000001F")
        self.assertEqual(lista[0]["descripcionEstado"], "En lista de espera (posición 3 de 3)")
        _, lista, _ = self.model.consultarInscripciones(numSocio=2)
        self.assertEqual((lista[0]["posicion"], lista[0]["totalEspera"]), (1, 3))

    #Las posiciones se actualizan cuando alguien deja la lista
    def testPosicionTrasCancelarOtro(self):
        self.solicitud(2, 1, "EN_ESPERA", "2026-09-02T09:00:00")
        self.solicitud(3, 1, "EN_ESPERA", "2026-09-03T09:00:00")
        self.db.executeUpdateQuery(
            "update Inscripcion set estado = 'CANCELADA', fechaCancelacion = 'x' where idPersona = 2")
        _, lista, _ = self.model.consultarInscripciones(numSocio=3)
        self.assertEqual(lista[0]["descripcionEstado"], "En lista de espera (posición 1 de 1)")

    #Cancelada con la actividad ya comenzada: indica desde qué mes
    def testCanceladaDesdeMes(self):
        self.solicitud(1, 1, "CANCELADA", cancelaDesde="2026-12-01")
        _, lista, _ = self.model.consultarInscripciones(dni="10000001A")
        self.assertEqual(lista[0]["descripcionEstado"], "Cancelada (desde 12/2026)")

    def testPersonaSinInscripciones(self):
        persona, lista, mensaje = self.model.consultarInscripciones(dni="20000002G")
        self.assertEqual(lista, [])
        self.assertEqual(mensaje, "No está inscrito en ninguna actividad")
        self.assertEqual(persona["nombre"], "Elena")

    def testPersonaInexistente(self):
        with self.assertRaisesRegex(IdentificacionError, "No existe ninguna persona registrada"):
            self.model.consultarInscripciones(dni="00000000X")
        with self.assertRaisesRegex(IdentificacionError, "No existe ninguna persona registrada"):
            self.model.consultarInscripciones(numSocio=99)

    def testSinIdentificador(self):
        with self.assertRaisesRegex(IdentificacionError, "Indica el DNI"):
            self.model.consultarInscripciones()

    #El DNI se normaliza igual que en el resto del proyecto
    def testDniNormalizado(self):
        self.solicitud(1, 1, "CONFIRMADA")
        _, lista, _ = self.model.consultarInscripciones(dni=" 10000001-a ")
        self.assertEqual(len(lista), 1)


if __name__ == "__main__":
    unittest.main()
