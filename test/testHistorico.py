import tempfile
import unittest
from pathlib import Path

from src.config import DATA_PATH, SCHEMA_PATH
from src.inscripciones.historicoModel import HistoricoError, HistoricoModel
from src.util.database import Database


class TestHistorico(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / "historico.csv"
        self.db = Database(Path(carpeta.name) / "prueba.db")
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)
        self.modelo = HistoricoModel(self.db.db_path)

    def fichero(self, *filas):
        cabecera = "temporada;categoría;nivel;plazas;NSocio;DNI;estado;fecha"
        self.ruta.write_text("\n".join((cabecera, *filas)), encoding="utf-8-sig")
        return self.ruta

    def testValidaSinModificarInscripciones(self):
        ruta = self.fichero(
            "2024;Natación;Iniciación;10;0001;;Confirmada;10/09/2024",
            "2024-2025;Natación;Iniciación;10;;10000001A;Confirmada;2024-09-10",
            "2026;Pilates;Medio;0;;;Desconocido;2026-02-31",
        )
        antes = self.db.executeQuery("SELECT * FROM Inscripcion")
        resultado = self.modelo.validar(ruta)
        self.assertEqual(len(resultado.solicitudes), 1)
        self.assertEqual(resultado.solicitudes[0].identificador, "1")
        self.assertEqual(resultado.solicitudes[0].fecha, "2024-09-10")
        self.assertEqual(resultado.descartadas, 2)
        self.assertEqual({i.linea for i in resultado.incidencias}, {3, 4})
        self.assertTrue(any("Fecha inválida" in i.motivo for i in resultado.incidencias))
        self.assertEqual(self.db.executeQuery("SELECT * FROM Inscripcion"), antes)

    def testRechazaCabeceraIncompleta(self):
        self.ruta.write_text("temporada,categoría\n2024,Natación\n", encoding="utf-8")
        resultado = self.modelo.validar(self.ruta)
        self.assertFalse(resultado.solicitudes)
        self.assertEqual(resultado.descartadas, 1)
        self.assertTrue(all(i.linea == 1 for i in resultado.incidencias))

    def testImportaFilasValidasYPersisteLosDatos(self):
        ruta = self.fichero(
            "2024;Natación;Iniciación;10;1;;Confirmada;2024-09-10",
            "2024;Natación;Iniciación;10;2;;En espera;2024-09-12",
            "2024;Natación;Iniciación;10;3;;Desconocido;2024-09-12",
        )
        validacion = self.modelo.validar(ruta)
        antes = self.db.executeQuery("SELECT * FROM Inscripcion")
        self.assertEqual(self.modelo.importar(validacion), (2, 1))
        with self.assertRaisesRegex(HistoricoError, "Ya se importaron.*2024-2025"):
            self.modelo.importar(validacion)
        self.assertEqual(self.db.executeQuery("SELECT COUNT(*) AS total FROM ActividadHistorica"),
                         [{"total": 1}])
        self.assertEqual(self.db.executeQuery("SELECT COUNT(*) AS total FROM InscripcionHistorica"),
                         [{"total": 2}])
        self.assertEqual(self.db.executeQuery("SELECT * FROM Inscripcion"), antes)

    def testExigeVolverAValidarSiCambiaElCSV(self):
        ruta = self.fichero("2024;Natación;Iniciación;10;1;;Confirmada;2024-09-10")
        validacion = self.modelo.validar(ruta)
        self.fichero("2024;Natación;Iniciación;10;2;;Confirmada;2024-09-10")
        with self.assertRaisesRegex(HistoricoError, "fichero ha cambiado"):
            self.modelo.importar(validacion)
