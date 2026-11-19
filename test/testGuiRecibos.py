import datetime
import os
import shutil
import tempfile
import unittest
from unittest import mock

from src.config import DATA_PATH, DATA_SPRINT2_PATH, SCHEMA_PATH
from src.util.database import Database

try:
    import tkinter  # noqa: F401
    from src.gui.app import CentroDeportivoApp
    from src.recibos.remesaModel import RemesaModel
    from src.recibos.resultadoBancoModel import ResultadoBancoModel
    from src.recibos.consultaRecibosModel import ConsultaRecibosModel
    HAY_TK = True
except ImportError:
    HAY_TK = False

HOY = datetime.date(2026, 11, 19)


@unittest.skipUnless(HAY_TK, "Tkinter o pantalla no disponibles")
class TestGuiRecibos(unittest.TestCase):
    '''Pantalla «Recibos» (HU13, HU14 y HU15) con data.sql + dataSprint2.sql y hoy = 19/11/2026.'''

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        cls.db_path = tmp.name
        cls.addClassCleanup(os.unlink, cls.db_path)
        cls.cargarDatos()
        cls.app = CentroDeportivoApp(cls.db_path)
        cls.addClassCleanup(cls.app.destroy)
        cls.app.withdraw()

    @classmethod
    def cargarDatos(cls):
        db = Database(cls.db_path)
        for script in (SCHEMA_PATH, DATA_PATH, DATA_SPRINT2_PATH):
            db.executeScript(script)

    def setUp(self):
        self.app.update()
        self.cargarDatos()
        self.carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.carpeta)
        self.prepararModelos()
        pagina = self.app.paginas["recibos"]
        pagina.destroy()
        self.app.paginas["recibos"] = type(pagina)(self.app.contenido, self.app)
        self.app.actual = None
        self.app.mostrar("recibos")
        self.p = self.app.paginas["recibos"]

    def prepararModelos(self):
        self.app.remesas = RemesaModel(self.db_path, carpeta=self.carpeta, hoyFijo=HOY)
        self.app.resultadosBanco = ResultadoBancoModel(self.db_path, carpeta=self.carpeta, hoyFijo=HOY)
        self.app.consultaRecibos = ConsultaRecibosModel(self.db_path)

    def testEmitirRemesaConConfirmacion(self):
        t = self.p.remesa
        self.assertEqual(t.mes.get(), "2026-11")
        with mock.patch.object(self.app, "confirmar", return_value=False):
            t.emitir()
        self.assertEqual(self.p.aviso.mensaje, "No se ha emitido la remesa")
        self.assertNotIn("2026-11", t.tablaRemesas.get_children())
        with mock.patch.object(self.app, "confirmar", return_value=True) as pregunta:
            t.emitir()
        self.assertIn("13 recibo(s) por 320,00 €", pregunta.call_args[0][1])
        self.assertEqual(self.p.aviso.tipo, "ok")
        self.assertIn("2026-11", t.tablaRemesas.get_children())
        self.assertEqual(len(t.tablaRecibos.get_children()), 13)
        self.assertTrue(os.path.exists(os.path.join(self.carpeta, "remesa_2026-11.txt")))

    def testEmitirRemesaErrores(self):
        t = self.p.remesa
        t.mes.delete(0, "end")
        t.mes.insert(0, "2026-12")
        t.emitir()
        self.assertEqual(self.p.aviso.tipo, "error")
        self.assertIn("mes futuro", self.p.aviso.mensaje)
        t.mes.delete(0, "end")
        t.mes.insert(0, "2026-08")
        t.emitir()
        self.assertEqual(self.p.aviso.mensaje, "No hay inscripciones activas en agosto de 2026")

    def testImportarResultadoDelBanco(self):
        self.app.remesas.emitirRemesa("2026-11")
        self.p.pestanas.select(self.p.resultado)
        self.app.update()
        t = self.p.resultado
        self.assertEqual(t.mes.get(), "2026-11")
        t.importar()
        self.assertEqual(self.p.aviso.tipo, "error")
        self.assertIn("No se encuentra el fichero", self.p.aviso.mensaje)
        t.generarPrueba()
        self.assertIn("resultado_2026-11.txt", self.p.aviso.mensaje)
        with open(os.path.join(self.carpeta, "resultado_2026-11.txt"), "a", encoding="utf-8") as fichero:
            fichero.write("999;COBRADO\n")
        t.importar()
        self.assertEqual(self.p.aviso.tipo, "info")
        self.assertEqual(t.cifras.cget("text"), "10 cobrado(s) · 3 devuelto(s) · 1 erróneo(s)")
        filas = t.tablaErrores.get_children()
        self.assertEqual(t.tablaErrores.item(filas[0], "values")[1], "El recibo 999 no existe")

    def testConsultarRecibosEIngresos(self):
        self.p.pestanas.select(self.p.consulta)
        self.app.update()
        t = self.p.consulta
        self.assertEqual(t.comboTemporada.get(), "2026-2027 (vigente)")
        self.assertEqual(t.comboActividad.get(), "Todas")
        filas = t.tablaResumen.get_children()
        self.assertEqual(t.tablaResumen.item(filas[0], "values")[:2], ("Pádel medio", "120,00 €"))
        self.assertEqual(t.tablaResumen.item("total", "values"),
                         ("Total", "255,00 €", "20,00 €", "45,00 €"))
        self.assertEqual(len(t.tablaRecibos.get_children()), 13)
        t.comboEstado.current(3)
        t.consultar()
        self.assertEqual(len(t.tablaRecibos.get_children()), 2)
        self.assertEqual(t.tablaResumen.item("total", "values")[1], "255,00 €")
        t.comboTemporada.current(1)
        t._cargarActividades()
        t.consultar()
        self.assertEqual(self.p.aviso.mensaje, "No hay recibos para los filtros seleccionados")


if __name__ == '__main__':
    unittest.main()
