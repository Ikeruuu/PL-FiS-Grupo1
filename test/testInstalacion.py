import os
import tempfile
import unittest
from unittest.mock import patch

from src.config import SCHEMA_PATH
from src.instalaciones.instalacionModel import AsignacionError, InstalacionModel
from src.instalaciones.instalacionView import InstalacionView
from src.util.database import Database

#Datos de prueba de la HU3 "Asignar una instalación a una actividad"
#Actividad 1 (Pádel medio) ya ocupa la instalación 1 los lunes de 18:00 a 19:00 todo el curso
#Actividad 3 (Pilates iniciación) ya ocupa la instalación 2 los lunes de 09:00 a 10:00 de octubre a diciembre
TEST_DATA = """
    insert into Modalidad(id,nombre) values(1,'Pádel');
    insert into Modalidad(id,nombre) values(2,'Pilates');
    insert into Nivel(id,nombre) values(1,'Iniciación');
    insert into Nivel(id,nombre) values(2,'Medio');
    insert into Instalacion(id,nombre,capacidad) values(1,'Pista de pádel 1',4);
    insert into Instalacion(id,nombre,capacidad) values(2,'Sala polivalente',15);
    insert into Instalacion(id,nombre,capacidad) values(3,'Pista de pádel 2',4);
    insert into Oferta(id,curso,fechaInicio,fechaFin,estado) values(1,'2026-2027','2026-10-01','2027-06-30','ACTIVA');
    insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(1,1,1,2,'2026-10-01','2027-06-30',4,1);
    insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(3,1,2,1,'2026-10-01','2026-12-31',12,2);
    insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(1,1,'18:00','19:00');
    insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(3,1,'09:00','10:00');
"""


class TestInstalacion(unittest.TestCase):

    def setUp(self):
        #Base de datos temporal e independiente para cada test
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScriptBatch(TEST_DATA)
        self.model = InstalacionModel(db_path=self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    #Crea una actividad sin instalación con un único horario y devuelve su id
    def nuevaActividad(self, id, dia, inicio, fin, plazas=4, fechaInicio='2026-10-01',
                       fechaFin='2027-06-30', modalidad=1, nivel=1):
        self.db.executeUpdateQuery(
            "insert into Actividad(id,idModalidad,idNivel,fechaInicio,fechaFin,plazas) values(?,?,?,?,?,?)",
            id, modalidad, nivel, fechaInicio, fechaFin, plazas)
        self.db.executeUpdateQuery(
            "insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(?,?,?,?)",
            id, dia, inicio, fin)
        return id

    def instalacionDe(self, id_actividad):
        return self.model.getActividad(id_actividad)["idInstalacion"]

    #CA6 Éxito: instalación libre
    def testAsignaInstalacionLibre(self):
        self.nuevaActividad(10, 2, '18:00', '19:00')
        msg = self.model.asignarInstalacion(10, 1)
        self.assertEqual(msg, "Instalación Pista de pádel 1 asignada a la actividad Pádel iniciación")
        self.assertEqual(self.instalacionDe(10), 1)
        self.assertEqual(self.model.getActividadesSinInstalacion(), [])

    #CA2 No existe la actividad o la instalación
    def testActividadInexistente(self):
        with self.assertRaisesRegex(AsignacionError, "No existe la actividad 99"):
            self.model.asignarInstalacion(99, 1)

    def testInstalacionInexistente(self):
        self.nuevaActividad(10, 2, '18:00', '19:00')
        with self.assertRaisesRegex(AsignacionError, "No existe la instalación 99"):
            self.model.asignarInstalacion(10, 99)
        self.assertIsNone(self.instalacionDe(10))

    #CA3 Capacidad: plazas mayores que la capacidad impiden la asignación
    def testCapacidadSuperada(self):
        self.nuevaActividad(10, 2, '18:00', '19:00', plazas=5)
        with self.assertRaisesRegex(AsignacionError,
                                    "La actividad tiene 5 plazas y la instalación admite 4"):
            self.model.asignarInstalacion(10, 1)
        self.assertIsNone(self.instalacionDe(10))

    #CA7 Plazas iguales a la capacidad sí se puede asignar
    def testCapacidadIgual(self):
        self.nuevaActividad(10, 2, '18:00', '19:00', plazas=4)
        self.model.asignarInstalacion(10, 1)
        self.assertEqual(self.instalacionDe(10), 1)

    #CA4 Colisión: mismo día, franjas solapadas y periodos solapados
    def testColisionIndicaActividadDiaYHora(self):
        self.nuevaActividad(10, 1, '18:30', '19:30')
        with self.assertRaises(AsignacionError) as ctx:
            self.model.asignarInstalacion(10, 1)
        self.assertIn("Colisión con Pádel medio, lunes 18:00–19:00", str(ctx.exception))
        self.assertIsNone(self.instalacionDe(10))

    def testColisionFranjaContenida(self):
        self.nuevaActividad(10, 1, '18:15', '18:45')
        with self.assertRaises(AsignacionError):
            self.model.asignarInstalacion(10, 1)

    def testSinColisionOtroDia(self):
        self.nuevaActividad(10, 3, '18:00', '19:00')
        self.model.asignarInstalacion(10, 1)
        self.assertEqual(self.instalacionDe(10), 1)

    def testSinColisionPeriodosDistintos(self):
        #Misma franja que Pilates iniciación (lunes 09-10) pero de enero a junio
        self.nuevaActividad(10, 1, '09:00', '10:00', plazas=12,
                            fechaInicio='2027-01-01', fechaFin='2027-06-30')
        self.model.asignarInstalacion(10, 2)
        self.assertEqual(self.instalacionDe(10), 2)

    def testColisionPeriodoSolapadoUnDia(self):
        self.nuevaActividad(10, 1, '09:00', '10:00', plazas=12,
                            fechaInicio='2026-12-31', fechaFin='2027-06-30')
        with self.assertRaises(AsignacionError):
            self.model.asignarInstalacion(10, 2)

    def testSinColisionOtraInstalacion(self):
        self.nuevaActividad(10, 1, '18:30', '19:30')
        self.model.asignarInstalacion(10, 3)
        self.assertEqual(self.instalacionDe(10), 3)

    def testColisionConVariosHorarios(self):
        #Actividad con dos sesiones: solo la del lunes choca
        self.nuevaActividad(10, 2, '18:00', '19:00')
        self.db.executeUpdateQuery(
            "insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(10,1,'17:30','18:30')")
        with self.assertRaisesRegex(AsignacionError, "lunes 18:00–19:00"):
            self.model.asignarInstalacion(10, 1)

    #CA7 Horas contiguas: no hay colisión
    def testSinColisionHorasContiguas(self):
        self.nuevaActividad(10, 1, '19:00', '20:00')
        self.nuevaActividad(11, 1, '17:00', '18:00')
        self.model.asignarInstalacion(10, 1)
        self.model.asignarInstalacion(11, 1)
        self.assertEqual(self.instalacionDe(10), 1)
        self.assertEqual(self.instalacionDe(11), 1)

    #CA5 Una sola instalación: no se cambia la ya asignada
    def testActividadYaAsignada(self):
        with self.assertRaisesRegex(AsignacionError, "La actividad ya tiene instalación asignada"):
            self.model.asignarInstalacion(1, 3)
        self.assertEqual(self.instalacionDe(1), 1)

    #CA1 Solo se ofrecen actividades sin instalación
    def testActividadesSinInstalacion(self):
        self.nuevaActividad(10, 2, '18:00', '19:00')
        res = self.model.getActividadesSinInstalacion()
        self.assertEqual([a["id"] for a in res], [10])

    #CA2 Mensajes de la vista cuando no hay datos
    def testVistaTodasAsignadas(self):
        view = InstalacionView(self.model)
        with patch("builtins.print") as mock_print:
            view.asignarInstalacion()
        mock_print.assert_called_with("Todas las actividades tienen instalación asignada")

    def testVistaSinActividades(self):
        self.db.executeScriptBatch("delete from Horario; delete from Actividad;")
        view = InstalacionView(self.model)
        with patch("builtins.print") as mock_print:
            view.asignarInstalacion()
        mock_print.assert_called_with("No hay actividades registradas")

    def testVistaSinInstalaciones(self):
        self.db.executeScriptBatch(
            "delete from Horario; delete from Actividad; delete from Instalacion;"
            "insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas) "
            "values(10,1,1,1,'2026-10-01','2027-06-30',4);")
        view = InstalacionView(self.model)
        with patch("builtins.print") as mock_print:
            view.asignarInstalacion()
        mock_print.assert_called_with("No hay instalaciones registradas")

    #Flujo completo por consola: id no numérico, luego ids válidos
    def testVistaAsignaPorConsola(self):
        self.nuevaActividad(10, 2, '18:00', '19:00')
        view = InstalacionView(self.model)
        with patch("builtins.input", side_effect=["abc", "10", "1"]), \
             patch("builtins.print") as mock_print:
            view.asignarInstalacion()
        mock_print.assert_called_with(
            "Instalación Pista de pádel 1 asignada a la actividad Pádel iniciación")
        self.assertEqual(self.instalacionDe(10), 1)

    def testVistaCancelar(self):
        self.nuevaActividad(10, 2, '18:00', '19:00')
        view = InstalacionView(self.model)
        with patch("builtins.input", side_effect=[""]), patch("builtins.print"):
            view.asignarInstalacion()
        self.assertIsNone(self.instalacionDe(10))

    def nuevaActividad(self, id, dia, inicio, fin, plazas=4, fechaInicio='2026-10-01',
                       fechaFin='2027-06-30', modalidad=1, nivel=1):
        self.db.executeUpdateQuery(
            "insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas) values(?,?,?,?,?,?,?)",
            id, 1, modalidad, nivel, fechaInicio, fechaFin, plazas)
        self.db.executeUpdateQuery(
            "insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(?,?,?,?)",
            id, dia, inicio, fin)
        return id

if __name__ == '__main__':
    unittest.main()
