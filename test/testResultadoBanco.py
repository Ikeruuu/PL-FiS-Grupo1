import os
import unittest

from src.recibos.comun import ReciboError
from src.recibos.resultadoBancoModel import ResultadoBancoModel
from test.testRemesa import HOY, BaseRecibos


class TestResultadoBanco(BaseRecibos):
    '''HU14. Cada prueba emite la remesa de noviembre de 2026 (13 recibos) antes de importar.'''

    def setUp(self):
        super().setUp()
        self.remesas.emitirRemesa("2026-11")
        self.ids = [r["id"] for r in self.db.executeQuery("select id from Recibo where mes = '2026-11' order by id")]
        self.banco = ResultadoBancoModel(self.db_path, carpeta=self.carpeta, hoyFijo=HOY)

    def escribir(self, *lineas, mes="2026-11"):
        with open(os.path.join(self.carpeta, f"resultado_{mes}.txt"), "w", encoding="utf-8") as fichero:
            fichero.write("\n".join(lineas))

    def estado(self, idRecibo):
        return self.db.executeQuery("select estado from Recibo where id = ?", idRecibo)[0]["estado"]

    #CA: cada recibo pasa a COBRADO o DEVUELTO y se muestra el resumen
    def testActualizaEstados(self):
        a, b, c = self.ids[:3]
        self.escribir(f"{a};COBRADO", f"{b};DEVUELTO", f"{c};COBRADO")
        r = self.banco.importarResultado("2026-11")
        self.assertEqual((r["cobrados"], r["devueltos"], r["erroneos"]), (2, 1, 0))
        self.assertEqual([self.estado(i) for i in (a, b, c)], ["COBRADO", "DEVUELTO", "COBRADO"])
        self.assertEqual(r["mensaje"], "Resultado del banco de noviembre de 2026 importado: "
                                       "2 cobrado(s), 1 devuelto(s) y 0 erróneo(s)")
        fecha = self.db.executeQuery("select fechaResultado from Recibo where id = ?", a)[0]["fechaResultado"]
        self.assertIsNotNone(fecha)

    #Los recibos que no aparecen en el fichero se quedan emitidos
    def testNoAparecenSeQuedanEmitidos(self):
        self.escribir(f"{self.ids[0]};COBRADO")
        self.banco.importarResultado("2026-11")
        self.assertEqual(self.estado(self.ids[1]), "EMITIDO")

    #Recibos que no existen, de otra remesa o ya procesados: error con su línea y no se modifican
    def testRecibosErroneos(self):
        self.escribir(f"{self.ids[0]};COBRADO", "999;COBRADO")
        self.banco.importarResultado("2026-11")
        self.escribir(f"{self.ids[0]};DEVUELTO", "999;COBRADO", f"{self.ids[1]};COBRADO")
        r = self.banco.importarResultado("2026-11")
        self.assertEqual((r["cobrados"], r["devueltos"], r["erroneos"]), (1, 0, 2))
        self.assertEqual(r["errores"], [
            {"linea": 1, "motivo": f"El recibo {self.ids[0]} ya estaba procesado (cobrado)"},
            {"linea": 2, "motivo": "El recibo 999 no existe"}])
        self.assertEqual(self.estado(self.ids[0]), "COBRADO")

    def testReciboDeOtraRemesa(self):
        self.db.executeUpdateQuery("insert into Remesa(mes, fechaEmision, fichero) values ('2026-09', '2026-09-01', 'x')")
        self.db.executeUpdateQuery("""insert into Recibo(idInscripcion, mes, importe, estado)
                                      select idInscripcion, '2026-09', importe, 'EMITIDO' from Recibo where id = ?""",
                                   self.ids[0])
        otro = self.db.executeQuery("select id from Recibo where mes = '2026-09'")[0]["id"]
        self.escribir(f"{otro};COBRADO")
        resultado = self.banco.importarResultado("2026-11")
        self.assertEqual(resultado["errores"][0]["motivo"],
                         f"El recibo {otro} no pertenece a la remesa de noviembre de 2026")
        self.assertEqual(self.estado(otro), "EMITIDO")

    #Líneas mal formadas o con un resultado distinto de COBRADO / DEVUELTO
    def testLineasMalFormadas(self):
        self.escribir("abc;COBRADO", f"{self.ids[0]};PAGADO", f"{self.ids[1]}", f"{self.ids[2]};COBRADO;extra",
                      "", f"{self.ids[3]};devuelto")
        r = self.banco.importarResultado("2026-11")
        self.assertEqual([e["linea"] for e in r["errores"]], [1, 2, 3, 4])
        self.assertIn("no es un número", r["errores"][0]["motivo"])
        self.assertIn("no válido", r["errores"][1]["motivo"])
        self.assertEqual((r["devueltos"], self.estado(self.ids[3])), (1, "DEVUELTO"))

    #Id repetido: la primera línea se procesa y la segunda es un error
    def testIdRepetido(self):
        self.escribir(f"{self.ids[0]};COBRADO", f"{self.ids[0]};DEVUELTO")
        r = self.banco.importarResultado("2026-11")
        self.assertEqual((r["cobrados"], r["erroneos"]), (1, 1))
        self.assertIn("repetido", r["errores"][0]["motivo"])
        self.assertEqual(self.estado(self.ids[0]), "COBRADO")

    #Importar dos veces el mismo fichero: la segunda vez todo sale erróneo y no cambia nada
    def testImportarDosVeces(self):
        self.escribir(f"{self.ids[0]};COBRADO", f"{self.ids[1]};DEVUELTO")
        self.banco.importarResultado("2026-11")
        r = self.banco.importarResultado("2026-11")
        self.assertEqual((r["cobrados"], r["devueltos"], r["erroneos"]), (0, 0, 2))
        self.assertEqual(self.estado(self.ids[1]), "DEVUELTO")

    def testFicheroNoExiste(self):
        with self.assertRaises(ReciboError) as ctx:
            self.banco.importarResultado("2026-11")
        self.assertIn("No se encuentra el fichero resultado_2026-11.txt", str(ctx.exception))

    def testFicheroVacio(self):
        self.escribir("", "  ")
        with self.assertRaises(ReciboError) as ctx:
            self.banco.importarResultado("2026-11")
        self.assertEqual(str(ctx.exception), "El fichero no contiene resultados")

    def testRemesaNoEmitida(self):
        self.escribir("1;COBRADO", mes="2026-09")
        with self.assertRaises(ReciboError) as ctx:
            self.banco.importarResultado("2026-09")
        self.assertEqual(str(ctx.exception), "No se ha emitido la remesa de septiembre de 2026")

    #Sin mes se usa el actual
    def testMesPorDefecto(self):
        self.escribir(f"{self.ids[0]};COBRADO")
        self.assertEqual(self.banco.importarResultado()["mes"], "2026-11")

    #Fichero de prueba que simula la respuesta del banco: uno de cada cuatro devuelto
    def testGenerarFicheroPrueba(self):
        ruta = self.banco.generarFicheroPrueba("2026-11")
        self.assertTrue(ruta.endswith("resultado_2026-11.txt"))
        self.assertEqual(len(self.lineasFichero("resultado_2026-11.txt")), 13)
        r = self.banco.importarResultado("2026-11")
        self.assertEqual((r["cobrados"], r["devueltos"], r["erroneos"]), (10, 3, 0))
        with self.assertRaises(ReciboError):
            self.banco.generarFicheroPrueba("2026-11")
        with self.assertRaises(ReciboError):
            self.banco.generarFicheroPrueba("2026-09")


if __name__ == '__main__':
    unittest.main()
