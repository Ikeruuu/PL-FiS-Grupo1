import os
import tempfile
import unittest

from src.config import SCHEMA_PATH
from src.ofertas.actividadModel import ActividadError, ActividadModel
from src.ofertas.ofertaModel import OfertaModel
from src.util.database import Database

TEST_DATA = """
    insert into Modalidad(id,nombre) values(1,'Natación');
    insert into Modalidad(id,nombre) values(4,'Pádel');
    insert into Nivel(id,nombre) values(1,'Iniciación');
"""


class TestActividad(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScriptBatch(TEST_DATA)
        self.model = ActividadModel(db_path=self.db_path)
        OfertaModel(db_path=self.db_path).crearOferta('2026-2027')
        self.idOferta = self.db.executeQuery("select id from Oferta")[0]["id"]

    def tearDown(self):
        os.unlink(self.db_path)

    def testAnadirActividadCorrecta(self):
        msg = self.model.anadirActividad(self.idOferta, 1, 1, '2026-10-01', '2027-06-30', 10,
                                         [(1, '18:00', '19:00')])
        self.assertEqual(msg, "Actividad Natación Iniciación añadida")

    def testPlazasInvalidas(self):
        with self.assertRaisesRegex(ActividadError, "mayores que 0"):
            self.model.anadirActividad(self.idOferta, 1, 1, '2026-10-01', '2027-06-30', 0,
                                       [(1, '18:00', '19:00')])

    def testMismaActividadEnInstalacionesDistintasPermitida(self):
        #Misma modalidad/nivel/horario, sin instalación asignada todavía: debe permitirse
        self.model.anadirActividad(self.idOferta, 4, 1, '2026-10-01', '2027-06-30', 4,
                                   [(1, '18:00', '19:00')])
        msg = self.model.anadirActividad(self.idOferta, 4, 1, '2026-10-01', '2027-06-30', 4,
                                         [(1, '18:00', '19:00')])
        self.assertEqual(msg, "Actividad Pádel Iniciación añadida")

    def testOfertaInexistente(self):
        with self.assertRaisesRegex(ActividadError, "No existe la oferta 99"):
            self.model.anadirActividad(99, 1, 1, '2026-10-01', '2027-06-30', 10,
                                       [(1, '18:00', '19:00')])

    def testHorarioFueraDeRango(self):
        with self.assertRaisesRegex(ActividadError, "fuera de rango"):
            self.model.anadirActividad(self.idOferta, 1, 1, '2026-10-01', '2027-06-30', 10,
                                       [(1, '07:00', '08:00')])


if __name__ == '__main__':
    unittest.main()