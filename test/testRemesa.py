import datetime
import os
import shutil
import tempfile
import unittest

from src.config import DATA_PATH, DATA_SPRINT2_PATH, SCHEMA_PATH
from src.recibos.comun import ReciboError, describirImporte, leerMes, nombreMes, ultimoDia
from src.recibos.remesaModel import RemesaModel
from src.util.database import Database

#HU13 con data.sql + dataSprint2.sql y "hoy" = 19/11/2026. Inscripciones activas en noviembre:
#Pádel medio (act. 1, 30 €): personas 1, 2, 3 y 4 (la 6 está en lista de espera)
#Natación iniciación (act. 2, 25 €): personas 1, 5, 6 y 7 (la 4 está cancelada)
#Pilates iniciación (act. 3, 20 €): personas 2, 3, 5, 6 y 7
#Total: 13 recibos por 4 x 30 + 4 x 25 + 5 x 20 = 320 €
HOY = datetime.date(2026, 11, 19)


class BaseRecibos(unittest.TestCase):

    SCRIPTS = (SCHEMA_PATH, DATA_PATH, DATA_SPRINT2_PATH)

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.carpeta = tempfile.mkdtemp()
        self.db = Database(self.db_path)
        for script in self.SCRIPTS:
            self.db.executeScript(script)
        self.remesas = RemesaModel(self.db_path, carpeta=self.carpeta, hoyFijo=HOY)

    def tearDown(self):
        os.unlink(self.db_path)
        shutil.rmtree(self.carpeta)

    def lineasFichero(self, nombre):
        with open(os.path.join(self.carpeta, nombre), encoding="utf-8") as fichero:
            return fichero.read().splitlines()

    def recibosDe(self, dni):
        return self.db.executeQuery("""select r.* from Recibo r inner join Inscripcion i on i.id = r.idInscripcion
                                       inner join Persona p on p.id = i.idPersona where p.dni = ?""", dni)


class TestComun(unittest.TestCase):

    def testMeses(self):
        self.assertEqual(leerMes("2026-11"), datetime.date(2026, 11, 1))
        self.assertEqual(nombreMes("2026-02"), "febrero de 2026")
        self.assertEqual(ultimoDia(datetime.date(2028, 2, 1)), datetime.date(2028, 2, 29))
        self.assertEqual(ultimoDia(datetime.date(2026, 12, 1)), datetime.date(2026, 12, 31))
        for mal in ("2026-13", "11-2026", "2026/11", "", "2026-1"):
            with self.subTest(mes=mal), self.assertRaises(ReciboError):
                leerMes(mal)

    def testImporte(self):
        self.assertEqual(describirImporte(30), "30,00 €")
        self.assertEqual(describirImporte(1234.5), "1.234,50 €")


class TestEmitirRemesa(BaseRecibos):

    #CA: un recibo por inscripción activa con la cuota mensual; resumen con número e importe total
    def testEmiteUnReciboPorInscripcionActiva(self):
        r = self.remesas.emitirRemesa("2026-11")
        self.assertEqual((r["mes"], len(r["recibos"]), r["total"]), ("2026-11", 13, 320))
        self.assertIn("13 recibo(s) por 320,00 €", r["mensaje"])
        recibos = self.db.executeQuery("select * from Recibo where mes = '2026-11'")
        self.assertEqual(len(recibos), 13)
        self.assertTrue(all(rec["estado"] == "EMITIDO" for rec in recibos))
        self.assertEqual(sorted({rec["importe"] for rec in recibos}), [20, 25, 30])

    #Cada recibo guarda id, socio, actividad, importe, fecha de emisión y estado
    def testDatosDelRecibo(self):
        self.remesas.emitirRemesa("2026-11")
        recibos = self.remesas.getRecibos("2026-11")
        padel = [r for r in recibos if r["dni"] == "10000001A" and r["modalidad"] == "Pádel"][0]
        self.assertEqual((padel["nivel"], padel["importe"], padel["fechaEmision"], padel["estado"]),
                         ("Medio", 30, "2026-11-19", "EMITIDO"))

    #Fichero remesa_<mes>.txt con id;socio;cuenta;importe;concepto
    def testFichero(self):
        r = self.remesas.emitirRemesa("2026-11")
        self.assertTrue(r["fichero"].endswith("remesa_2026-11.txt"))
        lineas = self.lineasFichero("remesa_2026-11.txt")
        self.assertEqual(len(lineas), 13)
        idRecibo = self.recibosDe("10000001A")[0]["id"]
        self.assertIn(f"{idRecibo};10000001A;ES9121000418450200051332;30.00;"
                      "Cuota de noviembre de 2026 - Pádel medio", lineas)

    #No entran las canceladas, las que están en lista de espera ni las pendientes de aceptar
    def testSoloInscripcionesConfirmadas(self):
        self.db.executeUpdateQuery("""update Inscripcion set estado = 'PENDIENTE_ACEPTACION'
                                      where idPersona = 6 and idActividad = 1""")
        self.remesas.emitirRemesa("2026-11")
        #La persona 4 (10000004D) solo tiene recibo de pádel: su natación está cancelada
        self.assertEqual(len(self.recibosDe("10000004D")), 1)
        #La persona 6 (20000001F) no paga el pádel (pendiente de aceptar), sí natación y pilates
        self.assertEqual(len(self.recibosDe("20000001F")), 2)

    #Una cancelación a partir de un mes posterior sigue pagando hasta entonces
    def testCanceladaAPartirDeUnMesPosterior(self):
        self.db.executeUpdateQuery("""update Inscripcion set estado = 'CANCELADA', cancelaDesde = '2026-12-01'
                                      where idPersona = 1 and idActividad = 1""")
        self.remesas.emitirRemesa("2026-11")
        self.assertEqual(len(self.recibosDe("10000001A")), 2)
        self.db.executeUpdateQuery("update Inscripcion set cancelaDesde = '2026-11-01' where idPersona = 1 and idActividad = 1")
        self.db.executeUpdateQuery("delete from Recibo")
        self.db.executeUpdateQuery("delete from Remesa")
        self.remesas.emitirRemesa("2026-11")
        self.assertEqual(len(self.recibosDe("10000001A")), 1)

    #Una inscripción hecha después del mes no entra; se cobra a partir de la remesa siguiente
    def testInscripcionPosteriorAlMes(self):
        self.db.executeUpdateQuery("""insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado)
                                      values(4,3,'2026-12-02 10:00:00','2026-12-02 10:00:00','CONFIRMADA')""")
        self.remesas.emitirRemesa("2026-11")
        self.assertEqual(len(self.recibosDe("10000004D")), 1)
        r = self.remesas.emitirRemesa("2026-12", hoy="2026-12-03")
        self.assertEqual(len(r["recibos"]), 14)

    #El importe es la cuota completa, aunque la actividad empiece a mitad de mes
    def testSinProrrateo(self):
        self.db.executeUpdateQuery("update Actividad set fechaInicio = '2026-11-16' where id = 1")
        self.remesas.emitirRemesa("2026-11")
        self.assertEqual({r["importe"] for r in self.recibosDe("10000004D")}, {30})

    #Solo actividades cuyo periodo coincide con el mes (pilates termina en diciembre)
    def testActividadTerminada(self):
        r = self.remesas.emitirRemesa("2027-01", hoy="2027-01-02")
        self.assertEqual((len(r["recibos"]), r["total"]), (8, 220))

    #No se puede emitir dos veces la remesa del mismo mes
    def testNoSeEmiteDosVeces(self):
        self.remesas.emitirRemesa("2026-11")
        with self.assertRaises(ReciboError) as ctx:
            self.remesas.emitirRemesa("2026-11")
        self.assertEqual(str(ctx.exception), "La remesa de noviembre de 2026 ya está emitida")
        self.assertEqual(len(self.db.executeQuery("select * from Recibo")), 13)

    def testMesFuturo(self):
        with self.assertRaises(ReciboError) as ctx:
            self.remesas.emitirRemesa("2026-12")
        self.assertIn("mes futuro", str(ctx.exception))
        self.assertFalse(os.path.exists(os.path.join(self.carpeta, "remesa_2026-12.txt")))

    def testMesNoValido(self):
        with self.assertRaises(ReciboError):
            self.remesas.emitirRemesa("noviembre")

    #Sin mes se usa el actual
    def testMesPorDefecto(self):
        self.assertEqual(self.remesas.mesPorDefecto(), "2026-11")
        self.assertEqual(self.remesas.emitirRemesa()["mes"], "2026-11")

    #Sin inscripciones activas: mensaje y no se genera el fichero
    def testSinInscripcionesActivas(self):
        with self.assertRaises(ReciboError) as ctx:
            self.remesas.emitirRemesa("2026-08")
        self.assertEqual(str(ctx.exception), "No hay inscripciones activas en agosto de 2026")
        self.assertEqual(os.listdir(self.carpeta), [])
        self.assertEqual(self.db.executeQuery("select * from Remesa"), [])

    #A quien le falte la cuenta (o la actividad sin cuota) no se le incluye y se informa
    def testIncidencias(self):
        self.db.executeUpdateQuery("update Persona set cuentaBancaria = null where dni = '10000002B'")
        r = self.remesas.emitirRemesa("2026-11")
        self.assertEqual(len(r["recibos"]), 11)
        self.assertEqual(len(r["incidencias"]), 2)
        self.assertIn("Luis Fernández Díaz (10000002B) en Pádel medio: no tiene cuenta bancaria", r["mensaje"])

    #La previsualización no modifica nada
    def testPrepararNoModifica(self):
        previa = self.remesas.prepararRemesa("2026-11")
        self.assertEqual((len(previa["recibos"]), previa["total"]), (13, 320))
        self.assertIn("13 recibo(s) por 320,00 €", RemesaModel.describirPrevia(previa))
        self.assertEqual(self.db.executeQuery("select * from Remesa"), [])
        self.assertEqual(os.listdir(self.carpeta), [])

    def testListadoDeRemesas(self):
        self.remesas.emitirRemesa("2026-11")
        remesas = [r for r in self.remesas.getRemesas() if r["mes"] == "2026-11"]
        self.assertEqual(len(remesas), 1)
        self.assertEqual((remesas[0]["recibos"], remesas[0]["total"], remesas[0]["pendientes"]), (13, 320, 13))


if __name__ == '__main__':
    unittest.main()
