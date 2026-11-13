import datetime
import os
import tempfile
import unittest
from unittest.mock import patch

from src.config import DATA_PATH, DATA_SPRINT2_PATH, SCHEMA_PATH
from src.ofertas.ofertaAnteriorModel import OfertaAnteriorError, OfertaAnteriorModel
from src.util.database import Database

#HU16 con data.sql + dataSprint2.sql: oferta actual 1 (2026-2027, inscripciones sin abrir) y oferta
#anterior 2 (2025-2026). Actividades anteriores: 11 Pádel medio (4 plazas, 4 inscritos, 2 en espera,
#lunes y miércoles 18-19, Pista de pádel 1), 12 Natación iniciación (20 plazas, 2 inscritos),
#13 Pilates medio (15 plazas, 2 inscritos y 1 cancelada), 14 Tenis iniciación (4 inscritos, 1 en espera)
#y 15 Acondicionamiento físico general avanzado (sin inscripciones).
HOY = datetime.date(2026, 9, 15)


class BaseOfertaAnterior(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.db = Database(self.db_path)
        for script in (SCHEMA_PATH, DATA_PATH, DATA_SPRINT2_PATH):
            self.db.executeScript(script)
        self.model = OfertaAnteriorModel(db_path=self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def actividad(self, idActividad):
        return self.db.executeQuery("select * from Actividad where id = ?", idActividad)[0]

    def horarios(self, idActividad):
        return [(h["diaSemana"], h["horaInicio"], h["horaFin"]) for h in self.db.executeQuery(
            "select * from Horario where idActividad = ? order by diaSemana", idActividad)]


class TestOfertaAnterior(BaseOfertaAnterior):

    #CA2: se usa la oferta de la temporada anterior
    def testOfertaAnterior(self):
        actual, anterior = self.model.comprobarDisponible(HOY)
        self.assertEqual((actual["curso"], anterior["curso"]), ("2026-2027", "2025-2026"))

    def testSinOfertaAnterior(self):
        self.db.executeScriptBatch("delete from Inscripcion; delete from Horario where idActividad > 10;"
                                   "delete from Actividad where idOferta = 2; delete from Oferta where id = 2;")
        with self.assertRaisesRegex(OfertaAnteriorError, "No hay oferta de la temporada anterior"):
            self.model.comprobarDisponible(HOY)

    def testUnaOfertaInactivaPosteriorNoCuenta(self):
        #Solo cuenta una oferta que termine antes de que empiece la actual
        self.db.executeUpdateQuery("insert into Oferta(id,curso,fechaInicio,fechaFin,estado) "
                                   "values(3,'2027-2028','2027-10-01','2028-06-30','INACTIVA')")
        self.assertEqual(self.model.comprobarDisponible(HOY)[1]["curso"], "2025-2026")

    def testSinOfertaActiva(self):
        self.db.executeUpdateQuery("update Oferta set estado = 'INACTIVA' where id = 1")
        with self.assertRaisesRegex(OfertaAnteriorError, "No hay una oferta activa"):
            self.model.comprobarDisponible(HOY)

    #CA1: solo antes de abrir las inscripciones de la oferta actual
    def testInscripcionesAbiertas(self):
        self.db.executeUpdateQuery("update Oferta set inicioInscripcionSocios = '2026-09-01' where id = 1")
        with self.assertRaisesRegex(OfertaAnteriorError, "ya están abiertas"):
            self.model.anadirDesdeAnterior(11, hoy=HOY)

    def testInscripcionesDefinidasPeroNoAbiertas(self):
        self.db.executeUpdateQuery("update Oferta set inicioInscripcionSocios = '2026-09-20' where id = 1")
        self.model.anadirDesdeAnterior(11, hoy=HOY)
        #El primer día del periodo ya cuenta como abierto
        with self.assertRaises(OfertaAnteriorError):
            self.model.anadirDesdeAnterior(11, hoy=datetime.date(2026, 9, 20))

    #CA3: demanda de cada actividad (inscritos confirmados, lista de espera, % e instalación)
    def testDemanda(self):
        acts = {a["id"]: a for a in self.model.getActividadesConDemanda(2)}
        self.assertEqual(sorted(acts), [11, 12, 13, 14, 15])
        padel = acts[11]
        self.assertEqual((padel["inscritos"], padel["espera"], padel["ocupacion"], padel["instalacion"]),
                         (4, 2, 100, "Pista de pádel 1"))
        self.assertEqual((padel["dias"], padel["horaInicio"], padel["horaFin"]), ([1, 3], "18:00", "19:00"))
        self.assertEqual((acts[12]["inscritos"], acts[12]["ocupacion"]), (2, 10))
        #Las canceladas no cuentan como inscritos
        self.assertEqual(acts[13]["inscritos"], 2)
        self.assertFalse(acts[13]["sinDatos"])

    #CA3 y CA8: sin inscripciones se indica "Sin datos" y la ocupación es 0 %
    def testSinDatos(self):
        afg = next(a for a in self.model.getActividadesConDemanda(2) if a["id"] == 15)
        self.assertTrue(afg["sinDatos"])
        self.assertEqual(afg["ocupacion"], 0)

    #CA4 y CA7: precarga los datos y se registra en la oferta actual sin instalación
    def testAnadirConDatosPrecargados(self):
        res = self.model.anadirDesdeAnterior(11, hoy=HOY)
        nueva = self.actividad(res["id"])
        self.assertEqual((nueva["idOferta"], nueva["idModalidad"], nueva["idNivel"], nueva["plazas"]),
                         (1, 4, 2, 4))
        self.assertEqual((nueva["fechaInicio"], nueva["fechaFin"]), ("2026-10-01", "2027-06-30"))
        self.assertIsNone(nueva["idInstalacion"])
        self.assertEqual(self.horarios(res["id"]), [(1, "18:00", "19:00"), (3, "18:00", "19:00")])
        self.assertEqual(res["mensaje"], "Actividad Pádel medio añadida a la oferta 2026-2027: "
                                         "lunes, miércoles 18:00–19:00, 4 plazas, del 2026-10-01 al 2027-06-30")

    #CA4: el responsable puede cambiar plazas y periodicidad
    def testAnadirAjustandoDatos(self):
        res = self.model.anadirDesdeAnterior(11, plazas=8, dias=[2, 4], horaInicio="17:00",
                                             horaFin="18:30", hoy=HOY)
        self.assertEqual(self.actividad(res["id"])["plazas"], 8)
        self.assertEqual(self.horarios(res["id"]), [(2, "17:00", "18:30"), (4, "17:00", "18:30")])

    #CA7: la actividad de la oferta anterior no se modifica
    def testNoModificaLaAnterior(self):
        antes = (self.actividad(11), self.horarios(11))
        self.model.anadirDesdeAnterior(11, plazas=8, dias=[5], hoy=HOY)
        self.assertEqual((self.actividad(11), self.horarios(11)), antes)

    #CA5: mismas validaciones que "Añadir una actividad"
    def testValidaciones(self):
        casos = [({"plazas": 0}, "plazas"), ({"dias": []}, "al menos un día"),
                 ({"horaInicio": "07:00"}, "Horario"), ({"horaInicio": "19:00", "horaFin": "18:00"}, "Horario")]
        for argumentos, mensaje in casos:
            with self.subTest(argumentos=argumentos):
                with self.assertRaisesRegex(OfertaAnteriorError, mensaje):
                    self.model.anadirDesdeAnterior(11, hoy=HOY, **argumentos)
        self.assertEqual(self.db.executeQuery("select count(*) as n from Actividad where idOferta = 1")[0]["n"], 10)

    def testActividadQueNoEsDeLaOfertaAnterior(self):
        with self.assertRaisesRegex(OfertaAnteriorError, "no pertenece a la oferta 2025-2026"):
            self.model.anadirDesdeAnterior(1, hoy=HOY)

    #CA8: se puede añadir dos veces la misma actividad (se admiten repetidas)
    def testAnadirDosVeces(self):
        primera = self.model.anadirDesdeAnterior(14, hoy=HOY)["id"]
        segunda = self.model.anadirDesdeAnterior(14, hoy=HOY)["id"]
        self.assertNotEqual(primera, segunda)


try:
    import tkinter  # noqa: F401
    from src.gui.app import SECCIONES, CentroDeportivoApp
    HAY_TK = True
except ImportError:
    HAY_TK = False


@unittest.skipUnless(HAY_TK, "Tkinter no disponible")
class TestGuiOfertaAnterior(BaseOfertaAnterior):

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

    def setUp(self):
        super().setUp()
        self.app.update()
        for pagina in self.app.paginas.values():
            pagina.destroy()
        from src.ofertas.ofertaAnteriorModel import OfertaAnteriorModel as Modelo
        self.app.ofertaAnterior = Modelo(self.db_path)
        self.app.paginas = {clave: clase(self.app.contenido, self.app) for clave, _, clase in SECCIONES}
        self.app.actual = None

    def mostrar(self):
        with patch("src.ofertas.ofertaAnteriorModel.datetime") as dt:
            dt.date.today.return_value = HOY
            self.app.mostrar("ofertaAnterior")
        return self.app.paginas["ofertaAnterior"]

    def testListaConDemanda(self):
        p = self.mostrar()
        self.assertEqual(len(p.tablaAnterior.get_children()), 5)
        valores = p.tablaAnterior.item("11", "values")
        self.assertEqual(list(valores[2:]), ["4", "4", "2", "100 %", "Pista de pádel 1"])
        self.assertEqual(p.tablaAnterior.item("15", "values")[3], "Sin datos")
        self.assertIn("2025-2026", p.titulo.cget("text"))

    def testPrecargaYAnade(self):
        p = self.mostrar()
        p.tablaAnterior.selection_set("11")
        p._precargar()
        self.assertEqual((p.horaInicio.get(), p.horaFin.get(), p.plazas.get()), ("18:00", "19:00", "4"))
        self.assertTrue(p.dias[1].get() and p.dias[3].get() and not p.dias[2].get())
        p.plazas.delete(0, "end")
        p.plazas.insert(0, "6")
        with patch("src.ofertas.ofertaAnteriorModel.datetime") as dt:
            dt.date.today.return_value = HOY
            p.anadir()
        self.assertEqual(p.aviso.tipo, "ok")
        self.assertIn("6 plazas", p.aviso.mensaje)

    def testInscripcionesAbiertasBloquea(self):
        self.db.executeUpdateQuery("update Oferta set inicioInscripcionSocios = '2026-09-01' where id = 1")
        p = self.mostrar()
        self.assertIn("ya están abiertas", p.aviso.mensaje)
        self.assertEqual(len(p.tablaAnterior.get_children()), 0)

    def testPlazasNoValidas(self):
        p = self.mostrar()
        p.tablaAnterior.selection_set("12")
        p._precargar()
        p.plazas.delete(0, "end")
        p.plazas.insert(0, "cero")
        p.anadir()
        self.assertEqual(p.aviso.tipo, "error")


if __name__ == "__main__":
    unittest.main()
