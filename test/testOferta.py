import os
import tempfile
import unittest

from src.config import SCHEMA_PATH
from src.ofertas.ofertaModel import OfertaError, OfertaModel
from src.util.database import Database


class TestOferta(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.model = OfertaModel(db_path=self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    #HU4 CA: se crea con estado ACTIVA y fechas por defecto octubre->junio
    def testCrearOfertaFechasPorDefecto(self):
        msg = self.model.crearOferta('2026-2027')
        self.assertEqual(msg, "Oferta 2026-2027 creada (2026-10-01 a 2027-06-30)")
        oferta = self.model.getOfertaActiva()
        self.assertEqual(oferta["estado"], "ACTIVA")

    #HU4 CA: no se puede crear una segunda oferta activa
    def testNoSePuedeCrearDosOfertasActivas(self):
        self.model.crearOferta('2026-2027')
        with self.assertRaisesRegex(OfertaError, "Ya existe una oferta activa"):
            self.model.crearOferta('2027-2028')

    #HU2 CA: periodo de socios antes que el de no socios, sin solape
    def testDefinirPeriodosCorrectos(self):
        self.model.crearOferta('2026-2027')
        oferta = self.model.getOfertaActiva()
        msg = self.model.definirPeriodos(oferta["id"], '2026-06-01', '2026-06-30',
                                         '2026-07-01', '2026-09-30')
        self.assertEqual(msg, "Periodos de inscripción definidos correctamente")

    def testPeriodosSolapados(self):
        self.model.crearOferta('2026-2027')
        oferta = self.model.getOfertaActiva()
        with self.assertRaisesRegex(OfertaError, "anterior al de no socios"):
            self.model.definirPeriodos(oferta["id"], '2026-06-01', '2026-07-15',
                                       '2026-07-01', '2026-09-30')

    #HU2 CA: ambos periodos deben acabar antes de que empiece la oferta
    def testPeriodosDespuesDeEmpezarOferta(self):
        self.model.crearOferta('2026-2027')
        oferta = self.model.getOfertaActiva()
        with self.assertRaisesRegex(OfertaError, "antes del inicio de la oferta"):
            self.model.definirPeriodos(oferta["id"], '2026-06-01', '2026-06-30',
                                       '2026-07-01', '2026-10-15')

    #HU2 CA: inmutabilidad, no se pueden redefinir
    def testPeriodosYaDefinidosNoSeModifican(self):
        self.model.crearOferta('2026-2027')
        oferta = self.model.getOfertaActiva()
        self.model.definirPeriodos(oferta["id"], '2026-06-01', '2026-06-30',
                                   '2026-07-01', '2026-09-30')
        with self.assertRaisesRegex(OfertaError, "ya tiene periodos"):
            self.model.definirPeriodos(oferta["id"], '2026-06-01', '2026-06-30',
                                       '2026-07-01', '2026-09-30')

    def testOfertaInexistente(self):
        with self.assertRaisesRegex(OfertaError, "No existe la oferta 99"):
            self.model.definirPeriodos(99, '2026-06-01', '2026-06-30', '2026-07-01', '2026-09-30')


if __name__ == '__main__':
    unittest.main()