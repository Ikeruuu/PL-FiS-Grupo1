import datetime
import os
import tempfile
import unittest
from unittest.mock import patch

from src.config import DATA_PATH, DATA_SPRINT2_PATH, SCHEMA_PATH
from src.inscripciones.asistenciaModel import (
    CANCELADA,
    FUTURA,
    REGISTRADA,
    SIN_REGISTRAR,
    AsistenciaError,
    AsistenciaModel,
)
from src.util.database import Database

#HU17 con data.sql + dataSprint2.sql y "hoy" = 13/11/2026:
#Act. 1 Pádel medio (lunes y miércoles 18:00): inscritos personas 1-4, la 6 en espera. Registradas 5, 7, 12 y
#19 de octubre; la del 14/10 cancelada. Act. 2 Natación iniciación (martes y jueves 10:00): inscritos 1, 5, 6, 7
#(la 4 cancelada). Act. 6 Pilates medio empieza en 2027. Act. 9 Natación avanzado: sin inscritos.
HOY = datetime.date(2026, 11, 13)


class BaseAsistencia(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.db = Database(self.db_path)
        for script in (SCHEMA_PATH, DATA_PATH, DATA_SPRINT2_PATH):
            self.db.executeScript(script)
        self.model = AsistenciaModel(db_path=self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def sesion(self, idActividad, fecha, hora):
        return next(s for s in self.model.getSesiones(idActividad, HOY)
                    if s["fecha"] == fecha and s["horaInicio"] == hora)

    def idInscripcion(self, idPersona, idActividad):
        return self.db.executeQuery("select id from Inscripcion where idPersona = ? and idActividad = ?",
                                    idPersona, idActividad)[0]["id"]


class TestSesiones(BaseAsistencia):

    #CA1: las sesiones salen del horario semanal dentro del periodo de la actividad
    def testSesionesDelHorario(self):
        sesiones = self.model.getSesiones(1, HOY)
        self.assertEqual([s["fecha"] for s in sesiones[:4]], ["2026-10-05", "2026-10-07", "2026-10-12", "2026-10-14"])
        self.assertTrue(all(datetime.date.fromisoformat(s["fecha"]).isoweekday() in (1, 3) for s in sesiones))
        self.assertEqual(sesiones[-1]["fecha"], "2027-06-30")

    #CA2 y CA8: estados de las sesiones y solo hasta hoy en la consulta
    def testEstados(self):
        self.assertEqual(self.sesion(1, "2026-10-05", "18:00")["estado"], REGISTRADA)
        self.assertEqual(self.sesion(1, "2026-10-14", "18:00")["estado"], CANCELADA)
        self.assertEqual(self.sesion(1, "2026-10-21", "18:00")["estado"], SIN_REGISTRAR)
        self.assertEqual(self.sesion(1, "2026-11-16", "18:00")["estado"], FUTURA)
        self.assertTrue(all(s["fecha"] <= "2026-11-13" for s in self.model.getSesionesHastaHoy(1, HOY)))

    #CA4: actividad inexistente, sin sesiones todavía y sin inscritos
    def testActividadInexistente(self):
        with self.assertRaisesRegex(AsistenciaError, "No existe la actividad 99"):
            self.model.getSesiones(99, HOY)

    def testSinSesionesTodavia(self):
        with self.assertRaisesRegex(AsistenciaError, "aún no ha tenido sesiones"):
            self.model.getSesionesHastaHoy(6, HOY)

    def testSinInscritos(self):
        with self.assertRaisesRegex(AsistenciaError, "No hay inscritos"):
            self.model.getHojaAsistencia(9, "2026-10-05", "08:00", HOY)


class TestRegistro(BaseAsistencia):

    #CA5: solo inscritos confirmados (ni lista de espera ni cancelados)
    def testSoloInscritosConfirmados(self):
        hoja = self.model.getHojaAsistencia(1, "2026-10-21", "18:00", HOY)
        self.assertEqual(sorted(p["dni"] for p in hoja), ["10000001A", "10000002B", "10000003C", "10000004D"])
        self.assertTrue(all(p["asistio"] is None for p in hoja))
        hoja2 = self.model.getHojaAsistencia(2, "2026-10-15", "10:00", HOY)
        self.assertNotIn("10000004D", [p["dni"] for p in hoja2])

    def testNoSePuedeRegistrarANoInscritos(self):
        ajena = self.idInscripcion(5, 2)
        with self.assertRaisesRegex(AsistenciaError, "Solo se puede registrar"):
            self.model.registrarAsistencia(1, "2026-10-21", "18:00", {ajena: True}, HOY)

    #CA6: se marca S/N y se guarda todo junto
    def testRegistrar(self):
        marcas = {self.idInscripcion(1, 1): True, self.idInscripcion(2, 1): True,
                  self.idInscripcion(3, 1): False, self.idInscripcion(4, 1): True}
        msg = self.model.registrarAsistencia(1, "2026-10-21", "18:00", marcas, HOY)
        self.assertEqual(msg, "Asistencia registrada: miércoles 21/10/2026 18:00, 3 de 4 (75 %)")
        s = self.sesion(1, "2026-10-21", "18:00")
        self.assertEqual((s["estado"], s["asistentes"], s["inscritos"], s["porcentaje"]), (REGISTRADA, 3, 4, 75))

    #CA2: las sesiones pasadas se pueden registrar tarde; la de hoy también; las futuras no
    def testSesionDeHoySeRegistra(self):
        self.model.registrarAsistencia(1, "2026-11-16", "18:00", {}, datetime.date(2026, 11, 16))
        estados = {s["fecha"]: s["estado"] for s in self.model.getSesiones(1, datetime.date(2026, 11, 16))}
        self.assertEqual(estados["2026-11-16"], REGISTRADA)

    def testSesionFuturaNoSeRegistra(self):
        with self.assertRaisesRegex(AsistenciaError, "sesión futura"):
            self.model.registrarAsistencia(1, "2026-11-16", "18:00", {}, HOY)

    def testSesionInexistente(self):
        with self.assertRaisesRegex(AsistenciaError, "no tiene sesión"):
            self.model.getHojaAsistencia(1, "2026-10-20", "18:00", HOY)

    #CA7: la asistencia se puede corregir y se guarda la última versión
    def testCorregir(self):
        todos = {p["idInscripcion"]: True for p in self.model.getHojaAsistencia(1, "2026-10-05", "18:00", HOY)}
        self.assertEqual(self.sesion(1, "2026-10-05", "18:00")["asistentes"], 4)
        todos[self.idInscripcion(1, 1)] = False
        msg = self.model.registrarAsistencia(1, "2026-10-05", "18:00", todos, HOY)
        self.assertTrue(msg.startswith("Asistencia corregida"))
        self.assertEqual(self.sesion(1, "2026-10-05", "18:00")["asistentes"], 3)
        self.assertEqual(self.db.executeQuery("select count(*) as n from Asistencia a inner join Inscripcion i "
                                              "on i.id = a.idInscripcion where i.idActividad = 1 "
                                              "and a.fecha = '2026-10-05'")[0]["n"], 4)

    #CA9: 0 asistentes es una sesión registrada con un 0 %
    def testCeroAsistentes(self):
        self.model.registrarAsistencia(1, "2026-10-21", "18:00", {}, HOY)
        s = self.sesion(1, "2026-10-21", "18:00")
        self.assertEqual((s["estado"], s["asistentes"], s["porcentaje"]), (REGISTRADA, 0, 0))


class TestCancelacion(BaseAsistencia):

    #CA3: una sesión se cancela por fuerza mayor; no se registra y no cuenta en las estadísticas
    def testCancelar(self):
        antes = self.model.getResumen(1, HOY)
        msg = self.model.cancelarSesion(1, "2026-10-21", "18:00", HOY)
        self.assertEqual(msg, "Sesión del miércoles 21/10/2026 18:00 cancelada")
        self.assertEqual(self.sesion(1, "2026-10-21", "18:00")["estado"], CANCELADA)
        despues = self.model.getResumen(1, HOY)
        self.assertEqual(despues["totales"], antes["totales"] - 1)
        self.assertEqual(despues["mediaAsistentes"], antes["mediaAsistentes"])

    def testSesionCanceladaNoSeRegistra(self):
        with self.assertRaisesRegex(AsistenciaError, "cancelada"):
            self.model.registrarAsistencia(1, "2026-10-14", "18:00", {}, HOY)

    #CA3: la cancelación es definitiva (no se puede repetir ni deshacer)
    def testCancelarDosVeces(self):
        with self.assertRaisesRegex(AsistenciaError, "ya está cancelada"):
            self.model.cancelarSesion(1, "2026-10-14", "18:00", HOY)

    def testNoSeCancelaUnaRegistrada(self):
        with self.assertRaisesRegex(AsistenciaError, "ya tiene asistencia registrada"):
            self.model.cancelarSesion(1, "2026-10-05", "18:00", HOY)

    def testSePuedeCancelarUnaFutura(self):
        self.model.cancelarSesion(1, "2026-11-16", "18:00", HOY)
        self.assertEqual(self.sesion(1, "2026-11-16", "18:00")["estado"], CANCELADA)


class TestConsulta(BaseAsistencia):

    #CA8: número y porcentaje por sesión y media por actividad
    def testResumen(self):
        r = self.model.getResumen(1, HOY)
        self.assertEqual((r["registradas"], r["canceladas"], r["totales"]), (4, 1, 11))
        self.assertEqual(r["mediaAsistentes"], 3.5)
        self.assertEqual(r["mediaPorcentaje"], 88)

    def testResumenSinRegistros(self):
        r = self.model.getResumen(9, HOY)
        self.assertEqual(r["registradas"], 0)
        self.assertIsNone(r["mediaAsistentes"])

    def testResumenPorPeriodo(self):
        r = self.model.getResumen(1, HOY, desde="2026-10-10", hasta="2026-10-31")
        self.assertEqual([s["fecha"] for s in r["sesiones"]],
                         ["2026-10-12", "2026-10-14", "2026-10-19", "2026-10-21", "2026-10-26", "2026-10-28"])
        self.assertEqual(r["registradas"], 2)


try:
    import tkinter  # noqa: F401
    from src.gui.app import SECCIONES, CentroDeportivoApp
    HAY_TK = True
except ImportError:
    HAY_TK = False


@unittest.skipUnless(HAY_TK, "Tkinter no disponible")
class TestGuiAsistencia(BaseAsistencia):

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
        #Procesa los eventos pendientes antes de borrar la base de datos de la prueba
        self.app.update()
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.app.update()
        for pagina in self.app.paginas.values():
            pagina.destroy()
        self.app.asistencia = AsistenciaModel(self.db_path, hoyFijo=HOY)
        self.app.paginas = {clave: clase(self.app.contenido, self.app) for clave, _, clase in SECCIONES}
        self.app.actual = None

    def pagina(self, idActividad):
        self.app.mostrar("asistencia")
        p = self.app.paginas["asistencia"]
        p.combo.current([a["id"] for a in p.actividades].index(idActividad))
        p._cargarSesiones()
        return p

    def testListaSesionesYResumen(self):
        p = self.pagina(1)
        self.assertEqual(p.tablaSesiones.item("2026-10-05|18:00", "values")[2], REGISTRADA)
        self.assertEqual(p.tablaSesiones.item("2026-10-14|18:00", "values")[2], CANCELADA)
        self.assertNotIn("2026-11-16|18:00", p.tablaSesiones.get_children())
        self.assertIn("4 de 11 sesiones registradas", p.resumen.cget("text"))

    def testRegistrarDesdeLaHoja(self):
        p = self.pagina(1)
        p.tablaSesiones.selection_set("2026-10-21|18:00")
        p._cargarHoja()
        self.assertEqual(len(p.tablaHoja.get_children()), 4)
        p.alternar(p.tablaHoja.get_children()[0])
        p.guardar()
        self.assertEqual(p.aviso.tipo, "ok")
        self.assertIn("3 de 4 (75 %)", p.aviso.mensaje)
        self.assertEqual(p.tablaSesiones.item("2026-10-21|18:00", "values")[2], REGISTRADA)

    def testCancelarSesionConConfirmacion(self):
        p = self.pagina(1)
        p.tablaSesiones.selection_set("2026-10-21|18:00")
        p._cargarHoja()
        with patch.object(self.app, "confirmar", return_value=True):
            p.cancelarSesion()
        self.assertEqual(p.tablaSesiones.item("2026-10-21|18:00", "values")[2], CANCELADA)

    def testSesionCanceladaNoMuestraHoja(self):
        p = self.pagina(1)
        p.tablaSesiones.selection_set("2026-10-14|18:00")
        p._cargarHoja()
        self.assertEqual(len(p.tablaHoja.get_children()), 0)
        self.assertIn("cancelada", p.aviso.mensaje)

    def testActividadSinSesiones(self):
        p = self.pagina(6)
        self.assertIn("aún no ha tenido sesiones", p.aviso.mensaje)


if __name__ == "__main__":
    unittest.main()
