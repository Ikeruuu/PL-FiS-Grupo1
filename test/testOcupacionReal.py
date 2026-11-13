import datetime
import os
import tempfile
import unittest

from src.config import DATA_PATH, DATA_SPRINT2_PATH, SCHEMA_PATH
from src.inscripciones.asistenciaModel import AsistenciaModel
from src.inscripciones.ocupacionRealModel import OcupacionRealError, OcupacionRealModel, diferencia
from src.util.database import Database

#HU18 con data.sql + dataSprint2.sql y "hoy" = 13/11/2026:
#Act. 1 Pádel medio (Pista de pádel 1): 4 plazas, 4 inscritos, asistencia 4, 3, 4, 3 -> media 3,5 (sesión del 14/10 cancelada)
#Act. 2 Natación iniciación (Piscina): 20 plazas, 4 inscritos (1 cancelada no cuenta), asistencia 4, 3, 4 -> media 3,67
#Act. 3 Pilates iniciación (Sala polivalente): 12 plazas, 5 inscritos, asistencia 2, 2, 1 -> media 1,67 (diferencia 67 %)
HOY = datetime.date(2026, 11, 13)


class BaseOcupacionReal(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.db = Database(self.db_path)
        for script in (SCHEMA_PATH, DATA_PATH, DATA_SPRINT2_PATH):
            self.db.executeScript(script)
        self.model = OcupacionRealModel(self.db_path, hoyFijo=HOY)

    def tearDown(self):
        os.unlink(self.db_path)

    def informe(self, **filtros):
        return {f["id"]: f for f in self.model.getInforme(**filtros)["actividades"]}


class TestOcupacionReal(BaseOcupacionReal):

    #CA2: plazas, inscritos (planificada), asistencia media (real, sobre plazas y sobre inscritos) y diferencia
    def testDatosPorActividad(self):
        padel = self.informe()[1]
        self.assertEqual((padel["instalacion"], padel["plazas"], padel["inscritos"], padel["planificada"]),
                         ("Pista de pádel 1", 4, 4, 100))
        self.assertEqual(padel["mediaAsistentes"], 3.5)
        self.assertEqual((padel["realSobrePlazas"], padel["realSobreInscritos"], padel["diferencia"]), (88, 88, 12))

    def testDosPorcentajesDistintos(self):
        natacion = self.informe()[2]
        self.assertEqual((natacion["planificada"], natacion["realSobrePlazas"], natacion["realSobreInscritos"]),
                         (20, 18, 92))

    #CA2 y CA5: diferencia = (inscritos - media) / inscritos; se destaca a partir del 50 %
    def testDiferenciaYDestacado(self):
        informe = self.informe()
        self.assertEqual(informe[3]["diferencia"], 67)
        self.assertTrue(informe[3]["destacada"])
        self.assertFalse(informe[1]["destacada"])

    def testFormulaDeLaDiferencia(self):
        self.assertEqual(diferencia(10, 4), 60)
        self.assertEqual(diferencia(10, 5), 50)
        self.assertIsNone(diferencia(0, 0))
        self.assertIsNone(diferencia(5, None))

    #CA3: los inscritos se cuentan en el momento de la consulta; las canceladas no cuentan
    def testInscritosAlConsultar(self):
        self.assertEqual(self.informe()[2]["inscritos"], 4)
        self.db.executeUpdateQuery("update Inscripcion set estado = 'CANCELADA' where idActividad = 3 and idPersona = 2")
        self.assertEqual(self.informe()[3]["inscritos"], 4)

    #CA4: solo cuentan las sesiones registradas; las canceladas no
    def testSesiones(self):
        padel = self.informe()[1]
        self.assertEqual((padel["sesionesRegistradas"], padel["sesionesTotales"]), (4, 11))

    #CA6: sin sesiones registradas -> sin datos y fuera de los totales
    def testSinDatos(self):
        tenis = self.informe()[8]
        self.assertTrue(tenis["sinDatos"])
        self.assertIsNone(tenis["diferencia"])
        totales = {t["instalacion"] for t in self.model.getInforme()["totales"]}
        self.assertEqual(totales, {"Piscina", "Pista de pádel 1", "Sala polivalente"})

    #CA7: orden de mayor a menor diferencia (sin datos al final) y totales por instalación
    def testOrdenYTotales(self):
        ids = [f["id"] for f in self.model.getInforme()["actividades"]]
        self.assertEqual(ids[:3], [3, 1, 2])
        sala = next(t for t in self.model.getInforme()["totales"] if t["instalacion"] == "Sala polivalente")
        self.assertEqual((sala["plazas"], sala["inscritos"], sala["diferencia"]), (12, 5, 67))

    #CA8: una actividad con 0 inscritos no da error
    def testCeroInscritos(self):
        afg = self.informe()[7]
        self.assertEqual((afg["inscritos"], afg["planificada"]), (0, 0))
        self.assertIsNone(afg["realSobreInscritos"])

    #CA1: periodo y filtros
    def testPeriodo(self):
        #En octubre del 1 al 10 solo hay dos sesiones de pádel registradas (5 y 7)
        padel = self.informe(desde="2026-10-01", hasta="2026-10-10")[1]
        self.assertEqual((padel["sesionesRegistradas"], padel["mediaAsistentes"]), (2, 3.5))

    def testPeriodoSinActividades(self):
        with self.assertRaisesRegex(OcupacionRealError, "No hay actividades"):
            self.model.getInforme(desde="2030-01-01", hasta="2030-02-01")

    def testFechasIncoherentes(self):
        with self.assertRaisesRegex(OcupacionRealError, "Fechas incoherentes"):
            self.model.getInforme(desde="2027-01-01", hasta="2026-12-31")

    def testFiltroInstalacion(self):
        self.assertEqual(set(self.informe(idInstalacion=1)), {2, 9, 10})

    def testFiltroActividad(self):
        self.assertEqual(set(self.informe(idActividad=3)), {3})

    def testUsaLaAsistenciaDeLaHU17(self):
        asistencia = AsistenciaModel(self.db_path, hoyFijo=HOY)
        ids = {p["idInscripcion"]: True for p in asistencia.getHojaAsistencia(3, "2026-10-26", "09:00")}
        asistencia.registrarAsistencia(3, "2026-10-26", "09:00", ids)
        #Ahora la media de Pilates es (2 + 2 + 1 + 5) / 4 = 2,5 -> diferencia 50 %, sigue destacada
        pilates = self.informe()[3]
        self.assertEqual((pilates["mediaAsistentes"], pilates["diferencia"], pilates["destacada"]), (2.5, 50, True))


try:
    import tkinter  # noqa: F401
    from src.gui.app import SECCIONES, CentroDeportivoApp
    HAY_TK = True
except ImportError:
    HAY_TK = False


@unittest.skipUnless(HAY_TK, "Tkinter no disponible")
class TestGuiOcupacionReal(BaseOcupacionReal):

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        cls.dbApp = tmp.name
        cls.addClassCleanup(os.unlink, cls.dbApp)
        Database(cls.dbApp).executeScript(SCHEMA_PATH)
        cls.app = CentroDeportivoApp(cls.dbApp)
        cls.addClassCleanup(cls.app.destroy)
        cls.app.withdraw()

    def tearDown(self):
        self.app.update()
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.app.update()
        for pagina in self.app.paginas.values():
            pagina.destroy()
        self.app.ocupacionReal = OcupacionRealModel(self.db_path, hoyFijo=HOY)
        self.app.paginas = {clave: clase(self.app.contenido, self.app) for clave, _, clase in SECCIONES}
        self.app.actual = None
        self.app.mostrar("ocupacionReal")
        self.p = self.app.paginas["ocupacionReal"]

    def testInformeCursoCompleto(self):
        self.p.consultar()
        filas = self.p.tablaInforme.get_children()
        self.assertEqual(filas[0], "3")
        self.assertEqual(self.p.tablaInforme.item("3", "tags"), ("destacada",))
        self.assertEqual(self.p.tablaInforme.item("3", "values")[6], "67 %")
        self.assertEqual(self.p.tablaInforme.item("8", "values")[4], "Sin datos")
        self.assertEqual(len(self.p.tablaTotales.get_children()), 3)

    def testFiltroInstalacion(self):
        self.p.comboInstalacion.current(1)  #Piscina
        self.p.consultar()
        self.assertEqual(set(self.p.tablaInforme.get_children()), {"2", "9", "10"})

    def testFechasIncompletas(self):
        self.p.desde.insert(0, "2026-10-01")
        self.p.consultar()
        self.assertIn("las dos fechas", self.p.aviso.mensaje)

    def testFechasIncoherentes(self):
        self.p.desde.insert(0, "2027-01-01")
        self.p.hasta.insert(0, "2026-12-31")
        self.p.consultar()
        self.assertEqual(self.p.aviso.tipo, "info")
        self.assertIn("incoherentes", self.p.aviso.mensaje)


if __name__ == "__main__":
    unittest.main()
