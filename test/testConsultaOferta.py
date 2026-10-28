import datetime
import os
import tempfile
import unittest

from src.config import DATA_PATH, SCHEMA_PATH
from src.ofertas.consultaOfertaModel import (
    ConsultaOfertaModel,
    describirCuota,
    describirPlazas,
)
from src.util.database import Database

#Periodos de prueba: socios del 1 al 15 de septiembre y no socios del 16 al 30
HOY_SOCIOS = datetime.date(2026, 9, 10)
HOY_NO_SOCIOS = datetime.date(2026, 9, 20)


class TestConsultaOferta(unittest.TestCase):
    '''HU Consultar la oferta de actividades disponibles (RedKanban 35334).'''

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.addCleanup(os.unlink, self.db_path)
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)
        self.db.executeUpdateQuery(
            """update Oferta set inicioInscripcionSocios = '2026-09-01',
                   finInscripcionSocios = '2026-09-15', inicioInscripcionNoSocios = '2026-09-16',
                   finInscripcionNoSocios = '2026-09-30' where id = 1""")
        self.model = ConsultaOfertaModel(self.db_path)

    def ids(self, lista):
        return sorted(a["id"] for a in lista)

    #Sin filtros se muestran todas las actividades de la oferta con periodo abierto
    def testSinFiltrosMuestraTodas(self):
        lista, mensaje = self.model.consultarOferta(hoy=HOY_SOCIOS)
        self.assertIsNone(mensaje)
        self.assertEqual(self.ids(lista), list(range(1, 11)))

    #Cada actividad muestra modalidad, nivel, periodicidad, horario, instalación, cuota y plazas
    def testDatosDeCadaActividad(self):
        lista, _ = self.model.consultarOferta(hoy=HOY_SOCIOS)
        padel = next(a for a in lista if a["id"] == 1)
        self.assertEqual(padel["modalidad"], "Pádel")
        self.assertEqual(padel["nivel"], "Medio")
        self.assertEqual(padel["periodicidad"], "lunes y miércoles")
        self.assertEqual(padel["horario"], "lunes 18:00–19:00, miércoles 18:00–19:00")
        self.assertEqual(padel["instalacion"], "Pista de pádel 1")
        self.assertEqual(padel["cuota"], 30)
        self.assertEqual(describirCuota(padel["cuota"]), "30,00 €")
        self.assertEqual((padel["plazas"], padel["libres"]), (4, 4))
        sinInstalacion = next(a for a in lista if a["id"] == 4)
        self.assertEqual(sinInstalacion["instalacion"], "Sin asignar")

    #Para quién está abierta: socios en su periodo, no socios en el suyo
    def testAbiertaParaSegunPeriodo(self):
        lista, _ = self.model.consultarOferta(hoy=HOY_SOCIOS)
        self.assertEqual({a["abiertaPara"] for a in lista}, {"socios"})
        lista, _ = self.model.consultarOferta(hoy=HOY_NO_SOCIOS)
        self.assertEqual({a["abiertaPara"] for a in lista}, {"no socios"})
        self.db.executeUpdateQuery("update Oferta set inicioInscripcionNoSocios = '2026-09-05'")
        lista, _ = self.model.consultarOferta(hoy=HOY_SOCIOS)
        self.assertEqual({a["abiertaPara"] for a in lista}, {"ambos"})

    #Fuera de los periodos (o sin periodos definidos / sin oferta activa) no hay oferta abierta
    def testSinPeriodoAbierto(self):
        for hoy in (datetime.date(2026, 8, 31), datetime.date(2026, 10, 1)):
            with self.subTest(hoy=hoy):
                self.assertEqual(self.model.consultarOferta(hoy=hoy),
                                 ([], ConsultaOfertaModel.SIN_ABIERTAS))
        self.db.executeUpdateQuery("update Oferta set estado = 'INACTIVA'")
        self.assertEqual(self.model.consultarOferta(hoy=HOY_SOCIOS),
                         ([], ConsultaOfertaModel.SIN_ABIERTAS))

    def testPeriodosSinDefinir(self):
        self.db.executeUpdateQuery(
            """update Oferta set inicioInscripcionSocios = null, finInscripcionSocios = null,
               inicioInscripcionNoSocios = null, finInscripcionNoSocios = null""")
        self.assertEqual(self.model.consultarOferta(hoy=HOY_SOCIOS)[1],
                         ConsultaOfertaModel.SIN_ABIERTAS)

    #Límites del periodo incluidos
    def testFechasLimite(self):
        for hoy in ("2026-09-01", "2026-09-15", "2026-09-16", "2026-09-30"):
            with self.subTest(hoy=hoy):
                self.assertIsNone(self.model.consultarOferta(hoy=hoy)[1])

    #Filtros por modalidad, nivel y periodicidad, por separado y combinados
    def testFiltros(self):
        lista, _ = self.model.consultarOferta(idModalidad=4, hoy=HOY_SOCIOS)
        self.assertEqual(self.ids(lista), [1, 4, 5])
        lista, _ = self.model.consultarOferta(idNivel=1, hoy=HOY_SOCIOS)
        self.assertEqual(self.ids(lista), [2, 3, 4, 8])
        lista, _ = self.model.consultarOferta(idModalidad=4, idNivel=3, hoy=HOY_SOCIOS)
        self.assertEqual(self.ids(lista), [5])

    #La periodicidad es el conjunto de días: lunes y miércoles no es lo mismo que solo lunes
    def testFiltroPeriodicidad(self):
        lista, _ = self.model.consultarOferta(dias=[3, 1], hoy=HOY_SOCIOS)
        self.assertEqual(self.ids(lista), [1, 5])
        lista, _ = self.model.consultarOferta(dias=[1], hoy=HOY_SOCIOS)
        self.assertEqual(self.ids(lista), [3, 4, 6, 9])
        self.assertIn((1, 3), self.model.getPeriodicidades())

    def testNingunaCumpleFiltros(self):
        lista, mensaje = self.model.consultarOferta(idModalidad=5, idNivel=3, hoy=HOY_SOCIOS)
        self.assertEqual(lista, [])
        self.assertEqual(mensaje, ConsultaOfertaModel.SIN_RESULTADOS)

    #Las completas aparecen indicando que la inscripción pasaría a lista de espera.
    #Las solicitudes en espera y las canceladas no ocupan plaza.
    def testActividadCompletaYPlazasLibres(self):
        for idPersona, estado in ((1, "CONFIRMADA"), (2, "PENDIENTE_ACEPTACION"),
                                  (3, "CONFIRMADA"), (4, "CONFIRMADA"),
                                  (5, "EN_ESPERA"), (6, "CANCELADA")):
            self.db.executeUpdateQuery(
                """insert into Inscripcion (idPersona, idActividad, fechaSolicitud,
                   fechaInscripcion, estado, fechaCancelacion) values (?, 1, '2026-09-02', ?, ?, ?)""",
                idPersona, "2026-09-02" if estado == "CONFIRMADA" else None, estado,
                "2026-09-03" if estado == "CANCELADA" else None)
        self.db.executeUpdateQuery(
            """insert into Inscripcion (idPersona, idActividad, fechaSolicitud, fechaInscripcion,
               estado) values (1, 3, '2026-09-02', '2026-09-02', 'CONFIRMADA')""")
        lista, _ = self.model.consultarOferta(hoy=HOY_SOCIOS)
        completa = next(a for a in lista if a["id"] == 1)
        self.assertTrue(completa["completa"])
        self.assertEqual(describirPlazas(completa), "Completa (lista de espera)")
        pilates = next(a for a in lista if a["id"] == 3)
        self.assertEqual(describirPlazas(pilates), "11 de 12")

    #Actividades sin cuota registrada
    def testCuotaNoIndicada(self):
        self.db.executeUpdateQuery("update Actividad set cuota = null where id = 1")
        lista, _ = self.model.consultarOferta(idModalidad=4, idNivel=2, hoy=HOY_SOCIOS)
        self.assertEqual(describirCuota(lista[0]["cuota"]), "No indicada")


if __name__ == "__main__":
    unittest.main()
