import datetime
import os
import tempfile
import unittest
from unittest.mock import patch

from src.config import SCHEMA_PATH
from src.instalaciones.instalacionModel import InstalacionModel
from src.instalaciones.instalacionView import InstalacionView
from src.instalaciones.ocupacionModel import (
    OcupacionError,
    OcupacionModel,
    calcularHuecos,
    periodoCurso,
)
from src.util.database import Database

#Datos de prueba de la HU "Consultar la ocupación de una instalación"
#Instalación 1: lunes 08-09 y 21-22 (todo el curso), martes 10-11 (todo el curso) y
#martes 11-12 (solo de enero a junio). Instalación 2 sin actividades.
TEST_DATA = """
    insert into Modalidad(id,nombre) values(1,'Natación');
    insert into Nivel(id,nombre) values(1,'Iniciación');
    insert into Nivel(id,nombre) values(2,'Medio');
    insert into Instalacion(id,nombre,capacidad) values(1,'Piscina',25);
    insert into Instalacion(id,nombre,capacidad) values(2,'Gimnasio',20);
    insert into Oferta(id,curso,fechaInicio,fechaFin,estado) values(1,'2026-2027','2026-10-01','2027-06-30','ACTIVA');
    insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(1,1,1,1,'2026-10-01','2027-06-30',10,1);
    insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(2,1,1,2,'2027-01-01','2027-06-30',10,1);
    insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(3,1,1,2,'2026-10-01','2027-06-30',10,null);
    insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(1,1,'08:00','09:00');
    insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(1,1,'21:00','22:00');
    insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(1,2,'10:00','11:00');
    insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(2,2,'11:00','12:00');
    insert into Horario(idActividad,diaSemana,horaInicio,horaFin) values(3,3,'10:00','11:00');
"""


def franja(inicio, fin):
    return {"horaInicio": inicio, "horaFin": fin}


class TestCalcularHuecos(unittest.TestCase):

    def testDiaSinFranjas(self):
        self.assertEqual(calcularHuecos([]), [("08:00", "22:00")])

    def testFranjaIntermedia(self):
        self.assertEqual(calcularHuecos([franja("10:00", "11:00")]),
                         [("08:00", "10:00"), ("11:00", "22:00")])

    #CA7: una franja que empieza a las 8:00 o termina a las 22:00 no deja hueco en ese extremo
    def testExtremos(self):
        self.assertEqual(calcularHuecos([franja("08:00", "09:00"), franja("21:00", "22:00")]),
                         [("09:00", "21:00")])

    #CA7: franjas contiguas no dejan hueco entre ellas
    def testContiguas(self):
        self.assertEqual(calcularHuecos([franja("17:00", "18:00"), franja("18:00", "19:00")]),
                         [("08:00", "17:00"), ("19:00", "22:00")])

    #Franjas solapadas (misma hora en periodos distintos) o contenidas
    def testSolapadas(self):
        self.assertEqual(calcularHuecos([franja("10:00", "12:00"), franja("10:30", "11:00")]),
                         [("08:00", "10:00"), ("12:00", "22:00")])

    def testDiaCompleto(self):
        self.assertEqual(calcularHuecos([franja("08:00", "22:00")]), [])


class TestPeriodoCurso(unittest.TestCase):

    def testPeriodoCurso(self):
        self.assertEqual(periodoCurso(datetime.date(2026, 10, 18)), ("2026-10-01", "2027-06-30"))
        self.assertEqual(periodoCurso(datetime.date(2027, 3, 1)), ("2026-10-01", "2027-06-30"))
        self.assertEqual(periodoCurso(datetime.date(2027, 8, 1)), ("2027-10-01", "2028-06-30"))


class TestOcupacion(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScriptBatch(TEST_DATA)
        self.model = OcupacionModel(db_path=self.db_path)
        self.hoy = datetime.date(2026, 10, 18)

    def tearDown(self):
        os.unlink(self.db_path)

    #CA1: sin periodo se usa el curso completo
    def testCursoCompletoPorDefecto(self):
        res = self.model.consultarOcupacion(1, hoy=self.hoy)
        self.assertEqual((res["fechaInicio"], res["fechaFin"]), ("2026-10-01", "2027-06-30"))
        self.assertEqual(sorted(res["dias"]), [1, 2])
        lunes = res["dias"][1]
        self.assertEqual([(f["horaInicio"], f["horaFin"]) for f in lunes["ocupadas"]],
                         [("08:00", "09:00"), ("21:00", "22:00")])
        self.assertEqual(lunes["libres"], [("09:00", "21:00")])
        martes = res["dias"][2]
        self.assertEqual(martes["libres"], [("08:00", "10:00"), ("12:00", "22:00")])

    #CA4: cada franja ocupada indica actividad (modalidad y nivel) y fechas
    def testDatosDeLaFranja(self):
        f = self.model.consultarOcupacion(1, hoy=self.hoy)["dias"][2]["ocupadas"][1]
        self.assertEqual((f["modalidad"], f["nivel"], f["fechaInicio"], f["fechaFin"]),
                         ("Natación", "Medio", "2027-01-01", "2027-06-30"))

    #CA7: solo aparecen actividades cuyo periodo se solapa con el consultado
    def testPeriodoSinSolape(self):
        res = self.model.consultarOcupacion(1, "2026-10-01", "2026-12-31")
        self.assertEqual(len(res["dias"][2]["ocupadas"]), 1)
        self.assertEqual(res["dias"][2]["libres"], [("08:00", "10:00"), ("11:00", "22:00")])

    def testPeriodoSolapadoUnSoloDia(self):
        res = self.model.consultarOcupacion(1, "2026-12-01", "2027-01-01")
        self.assertEqual(len(res["dias"][2]["ocupadas"]), 2)

    #CA6: instalación sin actividades en el periodo
    def testInstalacionLibre(self):
        self.assertEqual(self.model.consultarOcupacion(2, hoy=self.hoy)["dias"], {})
        self.assertEqual(self.model.consultarOcupacion(1, "2027-07-01", "2027-07-31")["dias"], {})

    #CA2: instalación inexistente
    def testInstalacionInexistente(self):
        with self.assertRaisesRegex(OcupacionError, "No existe la instalación 99"):
            self.model.consultarOcupacion(99)

    #CA3: fechas incoherentes
    def testFechasIncoherentes(self):
        with self.assertRaisesRegex(OcupacionError, "Fechas incoherentes"):
            self.model.consultarOcupacion(1, "2027-01-01", "2026-12-31")

    #Vista
    def vista(self):
        return InstalacionView(InstalacionModel(db_path=self.db_path), self.model)

    def salida(self, entradas):
        with patch("builtins.input", side_effect=entradas), patch("builtins.print") as mock_print:
            self.vista().consultarOcupacion()
        return [" ".join(str(a) for a in c.args) for c in mock_print.call_args_list]

    def testVistaListaPorDiaYHora(self):
        lineas = self.salida(["1", "2026-10-01", "2027-06-30"])
        inicio = lineas.index("Martes")
        self.assertEqual(lineas[inicio:inicio + 5], [
            "Martes",
            "  08:00–10:00  Libre",
            "  10:00–11:00  Ocupada: Natación iniciación (2026-10-01 a 2027-06-30)",
            "  11:00–12:00  Ocupada: Natación medio (2027-01-01 a 2027-06-30)",
            "  12:00–22:00  Libre",
        ])
        self.assertIn("  08:00–22:00  Libre", lineas[lineas.index("Domingo"):])

    def testVistaInstalacionLibre(self):
        lineas = self.salida(["2", "2026-10-01", "2027-06-30"])
        self.assertEqual(lineas[-1], "La instalación está libre en todo el periodo (8:00–22:00)")

    def testVistaFechasIncoherentes(self):
        lineas = self.salida(["1", "2027-01-01", "2026-12-31"])
        self.assertEqual(lineas[-1], "Fechas incoherentes: la fecha de inicio es posterior a la de fin")

    def testVistaInstalacionInexistente(self):
        lineas = self.salida(["99", ""])
        self.assertEqual(lineas[-1], "No existe la instalación 99")

    def testVistaSinInstalaciones(self):
        self.db.executeScriptBatch("delete from Horario; delete from Actividad; delete from Instalacion;")
        lineas = self.salida([])
        self.assertEqual(lineas, ["No hay instalaciones registradas"])

    def testVistaFechaMalFormada(self):
        lineas = self.salida(["2", "18/10/2026", "2026-10-01", "2027-06-30"])
        self.assertIn("La fecha debe tener el formato AAAA-MM-DD.", lineas)


if __name__ == '__main__':
    unittest.main()
