import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from demo_local import preparar_base_demo
from src.config import DATA_PATH
from src.inscripciones.historicoModel import HistoricoModel
from src.instalaciones.modalidadInstalacionModel import ModalidadInstalacionModel


class TestDemoLocal(unittest.TestCase):
    def testConservaLaBaseAntiguaYReutilizaLaCompatible(self):
        with tempfile.TemporaryDirectory() as carpeta:
            anterior = Path(carpeta) / "database_demo.db"
            self.assertEqual(preparar_base_demo(anterior), anterior)
            with closing(sqlite3.connect(anterior)) as conn:
                conn.execute("DROP TABLE InstalacionModalidad")
                conn.commit()
            contenidoAnterior = anterior.read_bytes()

            actual = preparar_base_demo(anterior)
            self.assertEqual(actual.name, "database_demo_v2.db")
            self.assertTrue(ModalidadInstalacionModel(actual).getConfiguracion())
            modelo = HistoricoModel(actual)
            csv = DATA_PATH.with_name("historico_ejemplo.csv")
            self.assertEqual(modelo.importar(modelo.validar(csv)), (4, 0))

            self.assertEqual(preparar_base_demo(anterior), actual)
            self.assertEqual(HistoricoModel(actual).getTemporadas(), ["2024-2025"])
            self.assertEqual(anterior.read_bytes(), contenidoAnterior)
