import os
import tempfile
import unittest

from src.config import DATA_PATH, SCHEMA_PATH
from src.util.database import Database

#Las pruebas de la interfaz gráfica se saltan si no hay Tkinter o no hay pantalla disponible
try:
    import tkinter
    from src.gui.app import CentroDeportivoApp
    _raiz = tkinter.Tk()
    _raiz.destroy()
    HAY_TK = True
except Exception:
    HAY_TK = False


@unittest.skipUnless(HAY_TK, "Tkinter o pantalla no disponibles")
class TestGui(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db = Database(self.tmp.name)
        db.executeScript(SCHEMA_PATH)
        db.executeScript(DATA_PATH)
        self.app = CentroDeportivoApp(self.tmp.name)
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        os.unlink(self.tmp.name)

    def testInicioMuestraResumen(self):
        valores = self.app.paginas["inicio"].valores
        self.assertEqual(str(valores["instalaciones"][0].cget("text")), "6")
        self.assertEqual(str(valores["sinInstalacion"][0].cget("text")), "5")
        self.assertEqual(str(valores["socios"][0].cget("text")), "5")

    def testNavegacion(self):
        for clave in ("asignar", "ocupacion", "personas", "inicio"):
            self.app.mostrar(clave)
            self.assertEqual(self.app.actual, clave)

    def testAsignarColisionYExito(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.tablaActividades.selection_set("4")
        p.tablaInstalaciones.selection_set("4")
        p.asignar()
        self.assertEqual(p.aviso.tipo, "error")
        self.assertIn("Colisión con Pádel medio, lunes 18:00–19:00", p.aviso.mensaje)
        p.tablaActividades.selection_set("4")
        p.tablaInstalaciones.selection_set("5")
        p.asignar()
        self.assertEqual(p.aviso.tipo, "ok")
        self.assertNotIn("4", p.tablaActividades.get_children())

    def testAsignarMarcaCapacidadInsuficiente(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.tablaActividades.selection_set("7")
        p._marcarCapacidad()
        self.assertEqual(p.tablaInstalaciones.item("2", "tags"), ("noCabe",))
        self.assertEqual(p.tablaInstalaciones.item("3", "tags"), "")

    def testAsignarSinSeleccion(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.asignar()
        self.assertEqual(p.aviso.mensaje, "Selecciona una actividad y una instalación")

    def testOcupacionLista(self):
        self.app.mostrar("ocupacion")
        p = self.app.paginas["ocupacion"]
        p.combo.current(0)
        p.consultar()
        dias = p.lista.get_children()
        self.assertEqual(len(dias), 7)
        lunes = [p.lista.item(i, "values")[:2] for i in p.lista.get_children(dias[0])]
        self.assertEqual(lunes, [("08:00–09:00", "Ocupada"), ("09:00–21:00", "Libre"),
                                 ("21:00–22:00", "Ocupada")])

    def testOcupacionLibreYFechasIncoherentes(self):
        self.app.mostrar("ocupacion")
        p = self.app.paginas["ocupacion"]
        p.combo.current(2)
        p.consultar()
        self.assertEqual(p.aviso.mensaje, "La instalación está libre en todo el periodo (8:00–22:00)")
        p.desde.insert(0, "2027-01-01")
        p.hasta.insert(0, "2026-12-31")
        p.consultar()
        self.assertEqual(p.aviso.tipo, "error")

    def testPersonasRegistroYDuplicado(self):
        self.app.mostrar("personas")
        p = self.app.paginas["personas"]
        for clave, valor in (("dni", "30000001-h"), ("nombre", "Sara"), ("apellidos", "Díaz"),
                             ("correo", "sara@example.com")):
            p.campos[clave].insert(0, valor)
        p.registrar()
        self.assertEqual(p.aviso.tipo, "ok")
        p.campos["dni"].insert(0, "10000001a")
        p.campos["nombre"].insert(0, "X")
        p.campos["apellidos"].insert(0, "Y")
        p.campos["telefono"].insert(0, "1")
        p.registrar()
        self.assertEqual(p.aviso.mensaje, "Esta persona ya es socia")

    def testPersonasConsulta(self):
        self.app.mostrar("personas")
        p = self.app.paginas["personas"]
        p.tipoBusqueda.set("socio")
        p.identificador.insert(0, "3")
        p.consultar()
        textos = [w.cget("text") for w in p.ficha.winfo_children()[0].winfo_children()[1].winfo_children()]
        self.assertIn("SOCIO Nº 3", textos)
        p.identificador.delete(0, "end")
        p.identificador.insert(0, "99")
        p.consultar()
        self.assertEqual(p.aviso.mensaje, "No existe ninguna persona con ese identificador")


if __name__ == '__main__':
    unittest.main()
