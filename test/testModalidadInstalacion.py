import os
import tempfile
import unittest
from unittest.mock import patch

from src.config import DATA_PATH, SCHEMA_PATH
from src.instalaciones.instalacionModel import AsignacionError, InstalacionModel, ModalidadNoAdmitida
from src.instalaciones.instalacionView import InstalacionView
from src.instalaciones.modalidadInstalacionModel import (
    ConfirmacionRequerida,
    ModalidadInstalacionError,
    ModalidadInstalacionModel,
)
from src.util.database import Database

#HU19 con los datos de prueba de data.sql (configuración validada por el PO):
#Piscina(1)=Natación; Sala(2) y Gimnasio(3)=Pilates y AFG; Pistas de pádel(4,5)=Pádel; Tenis(6)=Tenis
#Actividades sin instalación: 4 Pádel iniciación (lunes 18:30), 6 Pilates medio, 7 AFG medio (20 plazas), 8 Tenis
PISCINA, SALA, GIMNASIO, PADEL1, PADEL2, TENIS = 1, 2, 3, 4, 5, 6
NATACION, PILATES, AFG, PADEL, TENIS_M = 1, 2, 3, 4, 5


class BaseDatos(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)
        self.instalaciones = InstalacionModel(db_path=self.db_path)
        self.modalidades = ModalidadInstalacionModel(db_path=self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def instalacionDe(self, idActividad):
        return self.db.executeQuery("select idInstalacion from Actividad where id = ?",
                                    idActividad)[0]["idInstalacion"]


class TestConfiguracion(BaseDatos):

    #CA1: valores iniciales validados por el PO
    def testConfiguracionInicial(self):
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(PISCINA), [NATACION])
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(SALA), [PILATES, AFG])
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(GIMNASIO), [PILATES, AFG])
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(PADEL1), [PADEL])
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(TENIS), [TENIS_M])
        config = {c["nombre"]: c["modalidades"] for c in self.modalidades.getConfiguracion()}
        self.assertEqual(config["Piscina"], ["Natación"])

    #CA1: la configuración se puede modificar
    def testModificarConfiguracion(self):
        msg = self.modalidades.guardarModalidades(GIMNASIO, [PILATES, AFG, PADEL])
        self.assertEqual(msg, "Modalidades de Gimnasio guardadas")
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(GIMNASIO), [PILATES, AFG, PADEL])

    def testGuardarSinModalidades(self):
        self.modalidades.guardarModalidades(PADEL2, [])
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(PADEL2), [])

    #CA6: instalación o modalidad inexistentes
    def testInstalacionInexistente(self):
        with self.assertRaisesRegex(ModalidadInstalacionError, "No existe la instalación 99"):
            self.modalidades.guardarModalidades(99, [NATACION])

    def testModalidadInexistente(self):
        with self.assertRaisesRegex(ModalidadInstalacionError, "No existe la modalidad 99"):
            self.modalidades.guardarModalidades(PISCINA, [NATACION, 99])
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(PISCINA), [NATACION])

    #CA5: quitar una modalidad con actividades asignadas pide confirmación
    def testQuitarModalidadConActividadesPideConfirmacion(self):
        #La Piscina tiene asignadas las actividades 2, 9 y 10 de natación
        with self.assertRaises(ConfirmacionRequerida) as ctx:
            self.modalidades.guardarModalidades(PISCINA, [])
        self.assertEqual([a["id"] for a in ctx.exception.afectadas], [2, 9, 10])
        self.assertIn("quedarían incoherentes", str(ctx.exception))
        #Sin confirmar, no cambia nada
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(PISCINA), [NATACION])

    def testQuitarModalidadConfirmando(self):
        self.modalidades.guardarModalidades(PISCINA, [], confirmar=True)
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(PISCINA), [])

    def testQuitarModalidadSinActividadesNoPideConfirmacion(self):
        #El Gimnasio no tiene actividades asignadas
        self.modalidades.guardarModalidades(GIMNASIO, [PILATES])
        self.assertEqual(self.modalidades.getModalidadesAdmitidas(GIMNASIO), [PILATES])


class TestAsignacion(BaseDatos):

    #CA2: instalación compatible, se asigna sin avisar
    def testAsignaCompatible(self):
        self.instalaciones.asignarInstalacion(4, PADEL2)
        self.assertEqual(self.instalacionDe(4), PADEL2)

    #CA2: instalación incompatible avisa y no asigna sin confirmación
    def testIncompatibleAvisa(self):
        with self.assertRaises(ModalidadNoAdmitida) as ctx:
            self.instalaciones.asignarInstalacion(8, PISCINA)
        self.assertEqual(str(ctx.exception), "Piscina no admite Tenis. ¿Asignar igualmente?")
        self.assertIsNone(self.instalacionDe(8))

    def testIncompatibleConfirmadoAsigna(self):
        self.instalaciones.asignarInstalacion(8, PISCINA, confirmarModalidad=True)
        self.assertEqual(self.instalacionDe(8), PISCINA)

    #CA2: capacidad y colisión siguen bloqueando aunque se confirme
    def testCapacidadBloqueaAunqueSeConfirme(self):
        with self.assertRaisesRegex(AsignacionError, "20 plazas"):
            self.instalaciones.asignarInstalacion(7, PADEL1, confirmarModalidad=True)

    def testCapacidadAntesQueModalidad(self):
        #AFG (20 plazas) en la pista de pádel: el motivo es la capacidad, no la modalidad
        with self.assertRaises(AsignacionError) as ctx:
            self.instalaciones.asignarInstalacion(7, PADEL1)
        self.assertNotIsInstance(ctx.exception, ModalidadNoAdmitida)

    def testColisionBloqueaAunqueSeConfirme(self):
        with self.assertRaisesRegex(AsignacionError, "Colisión"):
            self.instalaciones.asignarInstalacion(4, PADEL1, confirmarModalidad=True)

    def testInstalacionesCompatibles(self):
        self.assertEqual(self.instalaciones.getInstalacionesCompatibles(7), {SALA, GIMNASIO})
        self.assertEqual(self.instalaciones.getInstalacionesCompatibles(4), {PADEL1, PADEL2})


class TestInforme(BaseDatos):

    #CA4: sin incoherencias con los datos iniciales
    def testSinIncoherencias(self):
        self.assertEqual(self.modalidades.getIncoherencias(), [])

    #CA4: el informe lista la asignación confirmada y no modifica datos
    def testInformeListaIncoherencias(self):
        self.instalaciones.asignarInstalacion(8, PISCINA, confirmarModalidad=True)
        incoherencias = self.modalidades.getIncoherencias()
        self.assertEqual([(a["id"], a["instalacion"], a["modalidad"]) for a in incoherencias],
                         [(8, "Piscina", "Tenis")])
        self.assertEqual(self.instalacionDe(8), PISCINA)

    def testInformeTrasQuitarModalidad(self):
        self.modalidades.guardarModalidades(PISCINA, [], confirmar=True)
        self.assertEqual([a["id"] for a in self.modalidades.getIncoherencias()], [2, 9, 10])


class TestConsola(BaseDatos):

    def salida(self, entradas):
        view = InstalacionView(self.instalaciones)
        with patch("builtins.input", side_effect=entradas), patch("builtins.print") as mock_print:
            view.asignarInstalacion()
        return [" ".join(str(a) for a in c.args) for c in mock_print.call_args_list]

    def testConsolaConfirma(self):
        lineas = self.salida(["8", str(PISCINA), "s"])
        self.assertIn("Instalación Piscina asignada a la actividad Tenis iniciación", lineas)

    def testConsolaCancela(self):
        lineas = self.salida(["8", str(PISCINA), "n"])
        self.assertIn("Asignación cancelada", lineas)
        self.assertIsNone(self.instalacionDe(8))


try:
    import tkinter  # noqa: F401
    from src.gui.app import SECCIONES, CentroDeportivoApp
    HAY_TK = True
except ImportError:
    HAY_TK = False


@unittest.skipUnless(HAY_TK, "Tkinter no disponible")
class TestGuiModalidades(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        cls.db_path = tmp.name
        cls.addClassCleanup(os.unlink, cls.db_path)
        db = Database(cls.db_path)
        db.executeScript(SCHEMA_PATH)
        db.executeScript(DATA_PATH)
        cls.app = CentroDeportivoApp(cls.db_path)
        cls.addClassCleanup(cls.app.destroy)
        cls.app.withdraw()

    def setUp(self):
        self.app.update()
        for pagina in self.app.paginas.values():
            pagina.destroy()
        db = Database(self.db_path)
        db.executeScript(SCHEMA_PATH)
        db.executeScript(DATA_PATH)
        self.app.paginas = {clave: clase(self.app.contenido, self.app) for clave, _, clase in SECCIONES}
        self.app.actual = None

    def instalacionDe(self, idActividad):
        return Database(self.db_path).executeQuery(
            "select idInstalacion from Actividad where id = ?", idActividad)[0]["idInstalacion"]

    def testAsignarMarcaNoAdmitidas(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.tablaActividades.selection_set("8")
        p._marcarCapacidad()
        self.assertEqual(p.tablaInstalaciones.item(str(PISCINA), "tags"), ("noModalidad",))
        self.assertEqual(p.tablaInstalaciones.item(str(TENIS), "tags"), "")

    def testAsignarIncompatibleConfirmando(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.tablaActividades.selection_set("8")
        p.tablaInstalaciones.selection_set(str(PISCINA))
        with patch.object(self.app, "confirmar", return_value=True) as confirmar:
            p.asignar()
        confirmar.assert_called_once()
        self.assertEqual(p.aviso.tipo, "ok")
        self.assertEqual(self.instalacionDe(8), PISCINA)

    def testAsignarIncompatibleCancelando(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.tablaActividades.selection_set("8")
        p.tablaInstalaciones.selection_set(str(PISCINA))
        with patch.object(self.app, "confirmar", return_value=False):
            p.asignar()
        self.assertEqual(p.aviso.mensaje, "Asignación cancelada")
        self.assertIsNone(self.instalacionDe(8))

    def testPaginaModalidadesGuardar(self):
        self.app.mostrar("modalidades")
        p = self.app.paginas["modalidades"]
        self.assertEqual(p.tablaConfig.item(str(PISCINA), "values")[1], "Natación")
        p.tablaConfig.selection_set(str(GIMNASIO))
        p._cargarSeleccion()
        self.assertTrue(p.variables[PILATES].get())
        p.variables[PADEL].set(True)
        p.guardar()
        self.assertEqual(p.aviso.mensaje, "Modalidades de Gimnasio guardadas")
        self.assertIn("Pádel", p.tablaConfig.item(str(GIMNASIO), "values")[1])

    def testPaginaModalidadesQuitarConActividades(self):
        self.app.mostrar("modalidades")
        p = self.app.paginas["modalidades"]
        self.assertEqual(p.resumenInforme.cget("text"), "No hay asignaciones incoherentes")
        p.tablaConfig.selection_set(str(PISCINA))
        p._cargarSeleccion()
        p.variables[NATACION].set(False)
        with patch.object(self.app, "confirmar", return_value=False):
            p.guardar()
        self.assertEqual(p.aviso.mensaje, "No se ha guardado ningún cambio")
        with patch.object(self.app, "confirmar", return_value=True):
            p.guardar()
        self.assertEqual(len(p.tablaIncoherencias.get_children()), 3)


if __name__ == "__main__":
    unittest.main()
