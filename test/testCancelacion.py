import datetime
import os
import tempfile
import unittest

from src.config import DATA_PATH, SCHEMA_PATH
from src.inscripciones.cancelacionModel import CancelacionError, CancelacionModel
from src.inscripciones.comun import IdentificacionError
from src.util.database import Database

#La actividad 3 (Pilates iniciación) va del 2026-10-01 al 2026-12-31 y tiene 12 plazas.
#La actividad 1 (Pádel medio) va del 2026-10-01 al 2027-06-30 y tiene 4 plazas.
ANTES_DE_EMPEZAR = datetime.date(2026, 9, 20)
NOVIEMBRE_EN_PLAZO = datetime.date(2026, 11, 10)


class TestCancelacion(unittest.TestCase):
    '''HU Cancelar una inscripción en una actividad (RedKanban 35335).'''

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.addCleanup(os.unlink, self.db_path)
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)
        self.model = CancelacionModel(self.db_path)

    #Crea una solicitud de la persona (id de Persona) en la actividad con el estado indicado
    def solicitud(self, idPersona, idActividad, estado, fecha="2026-09-02T10:00:00"):
        self.db.executeUpdateQuery(
            """insert into Inscripcion (idPersona, idActividad, fechaSolicitud, fechaInscripcion,
               estado) values (?, ?, ?, ?, ?)""",
            idPersona, idActividad, fecha, fecha if estado == "CONFIRMADA" else None, estado)

    def estado(self, idPersona, idActividad):
        return self.db.executeQuery(
            "select * from Inscripcion where idPersona = ? and idActividad = ?",
            idPersona, idActividad)[0]

    def numSolicitudes(self):
        return self.db.executeQuery("select count(*) as n from Inscripcion")[0]["n"]

    #Antes de que empiece se puede cancelar en cualquier momento, sin indicar mes
    def testCancelarAntesDeEmpezar(self):
        self.solicitud(1, 3, "CONFIRMADA")
        mensaje = self.model.cancelar(3, dni="10000001A", hoy=ANTES_DE_EMPEZAR)
        self.assertEqual(mensaje, "Inscripción en Pilates iniciación cancelada")
        fila = self.estado(1, 3)
        self.assertEqual(fila["estado"], "CANCELADA")
        self.assertIsNotNone(fila["fechaCancelacion"])
        self.assertIsNone(fila["cancelaDesde"])

    #La inscripción no se borra, se guarda como cancelada
    def testNoSeBorra(self):
        self.solicitud(1, 3, "CONFIRMADA")
        self.model.cancelar(3, numSocio=1, hoy=ANTES_DE_EMPEZAR)
        self.assertEqual(self.numSolicitudes(), 1)

    #Comenzada: se cancela a partir de un mes pidiéndolo del 1 al 15 del mes anterior
    def testCancelarComenzadaEnPlazo(self):
        self.solicitud(1, 1, "CONFIRMADA")
        for dia in (1, 15):
            with self.subTest(dia=dia):
                self.db.executeUpdateQuery(
                    "update Inscripcion set estado = 'CONFIRMADA', fechaCancelacion = null")
                mensaje = self.model.cancelar(1, dni="10000001A", mes="2026-12",
                                              hoy=datetime.date(2026, 11, dia))
                self.assertEqual(mensaje,
                                 "Inscripción en Pádel medio cancelada a partir de diciembre de 2026")
                self.assertEqual(self.estado(1, 1)["cancelaDesde"], "2026-12-01")

    #Del 16 en adelante, o con más de un mes de antelación, está fuera de plazo
    def testCancelarComenzadaFueraDePlazo(self):
        self.solicitud(1, 1, "CONFIRMADA")
        for hoy, mes in ((datetime.date(2026, 11, 16), "2026-12"),
                         (datetime.date(2026, 10, 10), "2026-12")):
            with self.subTest(hoy=hoy, mes=mes):
                with self.assertRaisesRegex(
                        CancelacionError,
                        "Fuera de plazo: para cancelar a partir de diciembre de 2026 la solicitud "
                        "debe hacerse entre el 1 y el 15 de noviembre de 2026"):
                    self.model.cancelar(1, dni="10000001A", mes=mes, hoy=hoy)
        self.assertEqual(self.estado(1, 1)["estado"], "CONFIRMADA")

    #Cambio de año: para cancelar desde enero se pide del 1 al 15 de diciembre
    def testCambioDeAnio(self):
        self.solicitud(1, 1, "CONFIRMADA")
        mensaje = self.model.cancelar(1, dni="10000001A", mes="2027-01",
                                      hoy=datetime.date(2026, 12, 3))
        self.assertIn("enero de 2027", mensaje)

    def testComenzadaSinMes(self):
        self.solicitud(1, 1, "CONFIRMADA")
        with self.assertRaisesRegex(CancelacionError, "indica el mes"):
            self.model.cancelar(1, dni="10000001A", hoy=NOVIEMBRE_EN_PLAZO)

    def testMesIncorrecto(self):
        self.solicitud(1, 3, "CONFIRMADA")
        for mes, texto in (("diciembre", "formato AAAA-MM"), ("2026-13", "formato AAAA-MM"),
                           ("2026-11", "posterior al mes actual"),
                           ("2027-01", "termina el 31/12/2026")):
            with self.subTest(mes=mes):
                with self.assertRaisesRegex(CancelacionError, texto):
                    self.model.cancelar(3, dni="10000001A", mes=mes, hoy=NOVIEMBRE_EN_PLAZO)

    def testActividadTerminada(self):
        self.solicitud(1, 3, "CONFIRMADA")
        with self.assertRaisesRegex(CancelacionError, "ya ha terminado"):
            self.model.cancelar(3, dni="10000001A", mes="2027-02", hoy=datetime.date(2027, 1, 5))

    #En lista de espera se puede retirar siempre y se actualizan las posiciones de los demás
    def testCancelarEnListaDeEspera(self):
        self.solicitud(2, 1, "EN_ESPERA", "2026-09-02T10:00:00")
        self.solicitud(3, 1, "EN_ESPERA", "2026-09-02T11:00:00")
        mensaje = self.model.cancelar(1, dni="10000002B", hoy=datetime.date(2027, 3, 20))
        self.assertEqual(mensaje, "Solicitud en lista de espera de Pádel medio cancelada")
        self.assertEqual(self.estado(2, 1)["estado"], "CANCELADA")
        self.assertEqual(self.estado(3, 1)["estado"], "EN_ESPERA")

    #Al liberar una plaza, la primera persona de la lista de espera pasa a tener la plaza
    #(pendiente de aceptar); los socios tienen prioridad y, entre iguales, el orden de llegada
    def testPlazaLiberadaParaElPrimeroDeLaLista(self):
        for idPersona in (1, 2, 3, 4):
            self.solicitud(idPersona, 1, "CONFIRMADA")
        self.solicitud(6, 1, "EN_ESPERA", "2026-09-20T09:00:00")   #no socio, llegó antes
        self.solicitud(5, 1, "EN_ESPERA", "2026-09-21T09:00:00")   #socia
        mensaje = self.model.cancelar(1, dni="10000001A", hoy=ANTES_DE_EMPEZAR)
        self.assertIn("pasa a la primera persona de la lista de espera", mensaje)
        self.assertEqual(self.estado(5, 1)["estado"], "PENDIENTE_ACEPTACION")
        self.assertEqual(self.estado(6, 1)["estado"], "EN_ESPERA")

    #Si quedaban plazas libres no hay nadie esperando y no se asigna nada
    def testSinListaDeEspera(self):
        self.solicitud(1, 1, "CONFIRMADA")
        mensaje = self.model.cancelar(1, dni="10000001A", hoy=ANTES_DE_EMPEZAR)
        self.assertNotIn("lista de espera", mensaje)

    #Retirarse de la lista de espera no libera plaza ni asciende a nadie
    def testCancelarEsperaNoAsignaPlaza(self):
        self.db.executeUpdateQuery("update Actividad set plazas = 1 where id = 1")
        self.solicitud(1, 1, "CONFIRMADA")
        self.solicitud(2, 1, "EN_ESPERA", "2026-09-02T10:00:00")
        self.solicitud(3, 1, "EN_ESPERA", "2026-09-02T11:00:00")
        self.model.cancelar(1, dni="10000002B", hoy=ANTES_DE_EMPEZAR)
        self.assertEqual(self.estado(3, 1)["estado"], "EN_ESPERA")

    def testSinInscripcion(self):
        with self.assertRaisesRegex(CancelacionError, "No existe ninguna inscripción ni solicitud"):
            self.model.cancelar(1, dni="10000001A", hoy=ANTES_DE_EMPEZAR)

    def testYaCancelada(self):
        self.solicitud(1, 3, "CONFIRMADA")
        self.model.cancelar(3, dni="10000001A", hoy=ANTES_DE_EMPEZAR)
        with self.assertRaisesRegex(CancelacionError, "ya está cancelada"):
            self.model.cancelar(3, dni="10000001A", hoy=ANTES_DE_EMPEZAR)

    def testPersonaOActividadInexistente(self):
        with self.assertRaisesRegex(IdentificacionError, "No existe ninguna persona"):
            self.model.cancelar(1, dni="99999999Z", hoy=ANTES_DE_EMPEZAR)
        with self.assertRaisesRegex(IdentificacionError, "Indica el DNI"):
            self.model.cancelar(1, hoy=ANTES_DE_EMPEZAR)
        with self.assertRaisesRegex(CancelacionError, "La actividad no existe"):
            self.model.cancelar(99, dni="10000001A", hoy=ANTES_DE_EMPEZAR)

    #La comprobación previa (para pedir confirmación) no modifica nada
    def testComprobarNoModifica(self):
        self.solicitud(1, 1, "CONFIRMADA")
        resumen = self.model.comprobarCancelacion(1, dni="10000001A", mes="2026-12",
                                                  hoy=NOVIEMBRE_EN_PLAZO)
        self.assertEqual(resumen,
                         "Se cancelará la inscripción en Pádel medio a partir de diciembre de 2026")
        self.assertEqual(self.estado(1, 1)["estado"], "CONFIRMADA")

    #Una inscripción cancelada deja de contar como plaza ocupada
    def testCanceladaNoOcupaPlaza(self):
        from src.inscripciones.comun import conectar, plazasOcupadas
        self.solicitud(1, 1, "CONFIRMADA")
        self.model.cancelar(1, dni="10000001A", hoy=ANTES_DE_EMPEZAR)
        with conectar(self.db_path) as conn:
            self.assertEqual(plazasOcupadas(conn, 1), 0)


if __name__ == "__main__":
    unittest.main()
