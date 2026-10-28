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
    insert into Nivel(id,nombre) values(2,'Medio');
    insert into Instalacion(id,nombre,capacidad) values(1,'Pista de pádel 1',4);
"""


class TestModificarActividad(unittest.TestCase):

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

    def crearActividad(self, idModalidad=4, idNivel=2, dia=1, inicio='18:00', fin='19:00',
                       idInstalacion=None):
        self.model.anadirActividad(self.idOferta, idModalidad, idNivel, '2026-10-01', '2027-06-30',
                                   4, [(dia, inicio, fin)])
        idActividad = self.db.executeQuery("select max(id) as id from Actividad")[0]["id"]
        if idInstalacion:
            self.db.executeUpdateQuery(
                "update Actividad set idInstalacion = ? where id = ?", idInstalacion, idActividad)
        return idActividad

    def testModificaPlazasYHorario(self):
        idActividad = self.crearActividad()
        msg = self.model.modificarActividad(idActividad, 4, 2, '2026-10-01', '2027-06-30',
                                            8, [(1, '19:00', '20:00')])
        self.assertEqual(msg, "Actividad Pádel Medio modificada")
        actualizada = self.model.getActividad(idActividad)
        self.assertEqual(actualizada["plazas"], 8)

    def testActividadInexistente(self):
        with self.assertRaisesRegex(ActividadError, "No existe la actividad 99"):
            self.model.modificarActividad(99, 4, 2, '2026-10-01', '2027-06-30', 4, [(1, '18:00', '19:00')])

    def testPlazasMenoresQueInscritos(self):
        idActividad = self.crearActividad()
        with self.assertRaisesRegex(ActividadError, "no pueden ser inferiores"):
            self.model.modificarActividad(idActividad, 4, 2, '2026-10-01', '2027-06-30',
                                          2, [(1, '18:00', '19:00')], plazasOcupadas=3)

    def testHorarioFueraDeRango(self):
        idActividad = self.crearActividad()
        with self.assertRaisesRegex(ActividadError, "fuera de rango"):
            self.model.modificarActividad(idActividad, 4, 2, '2026-10-01', '2027-06-30',
                                          4, [(1, '07:00', '08:00')])

    def testColisionConOtraActividadMismaInstalacion(self):
        idA = self.crearActividad(dia=1, inicio='18:00', fin='19:00', idInstalacion=1)
        idB = self.crearActividad(dia=2, inicio='10:00', fin='11:00', idInstalacion=1)
        with self.assertRaisesRegex(ActividadError, "Colisión con Pádel medio"):
            self.model.modificarActividad(idB, 4, 2, '2026-10-01', '2027-06-30',
                                          4, [(1, '18:30', '19:30')])

    def testSinColisionSiCambiaADiaLibre(self):
        idA = self.crearActividad(dia=1, inicio='18:00', fin='19:00', idInstalacion=1)
        idB = self.crearActividad(dia=2, inicio='10:00', fin='11:00', idInstalacion=1)
        msg = self.model.modificarActividad(idB, 4, 2, '2026-10-01', '2027-06-30',
                                            4, [(3, '10:00', '11:00')])
        self.assertEqual(msg, "Actividad Pádel Medio modificada")


if __name__ == '__main__':
    unittest.main()