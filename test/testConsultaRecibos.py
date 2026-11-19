import unittest

from src.recibos.comun import ReciboError
from src.recibos.consultaRecibosModel import ConsultaRecibosModel
from test.testRemesa import BaseRecibos

#HU15 con data.sql + dataSprint2.sql: remesa de octubre de 2026 con el resultado del banco importado
#Pádel medio (act. 1): 4 cobrados -> ingresos 120 €
#Natación iniciación (act. 2): 3 cobrados y 1 devuelto -> ingresos 75 €, devuelto 25 €
#Pilates iniciación (act. 3): 3 cobrados, 1 devuelto y 1 emitido -> 60 €, pendiente 20 €, devuelto 20 €


class TestConsultaRecibos(BaseRecibos):

    def setUp(self):
        super().setUp()
        self.consulta = ConsultaRecibosModel(self.db_path)

    def resumen(self, **filtros):
        return {f["idActividad"]: f for f in self.consulta.consultar(**filtros)["resumen"]}

    #CA: ingresos (solo cobrados), pendiente (emitidos) y devuelto por actividad
    def testResumenPorActividad(self):
        r = self.resumen()
        self.assertEqual((r[1]["ingresos"], r[1]["pendiente"], r[1]["devuelto"]), (120, 0, 0))
        self.assertEqual((r[2]["ingresos"], r[2]["pendiente"], r[2]["devuelto"]), (75, 0, 25))
        self.assertEqual((r[3]["ingresos"], r[3]["pendiente"], r[3]["devuelto"]), (60, 20, 20))

    #Ordenado por ingresos de mayor a menor, con las actividades sin recibos a 0 y fila de totales
    def testOrdenYTotales(self):
        r = self.consulta.consultar()
        self.assertEqual(r["temporada"]["curso"], "2026-2027")
        self.assertEqual([f["idActividad"] for f in r["resumen"]][:3], [1, 2, 3])
        sinRecibos = [f for f in r["resumen"] if f["idActividad"] not in (1, 2, 3)]
        self.assertEqual(len(sinRecibos), 7)
        self.assertTrue(all(f["ingresos"] == f["pendiente"] == f["devuelto"] == 0 for f in sinRecibos))
        self.assertEqual(r["totales"], {"ingresos": 255, "pendiente": 20, "devuelto": 45, "recibos": 13})
        self.assertEqual(len(r["recibos"]), 13)
        self.assertIsNone(r["mensaje"])

    #El filtro de estado solo afecta al listado: el resumen muestra siempre las tres cantidades
    def testFiltroEstado(self):
        r = self.consulta.consultar(estado="DEVUELTO")
        self.assertEqual(len(r["recibos"]), 2)
        self.assertTrue(all(rec["estado"] == "DEVUELTO" for rec in r["recibos"]))
        self.assertEqual(r["totales"]["ingresos"], 255)
        with self.assertRaises(ReciboError):
            self.consulta.consultar(estado="PAGADO")

    def testFiltroActividad(self):
        r = self.consulta.consultar(idActividad=3)
        self.assertEqual([f["idActividad"] for f in r["resumen"]], [3])
        self.assertEqual(len(r["recibos"]), 5)
        self.assertEqual(r["recibos"][0]["socio"], "Luis Fernández Díaz (10000002B)")
        with self.assertRaises(ReciboError):
            self.consulta.consultar(idOferta=2, idActividad=3)

    #Los recibos nuevos (HU13) y el resultado del banco (HU14) se reflejan en la consulta
    def testIncluyeRemesaNueva(self):
        self.remesas.emitirRemesa("2026-11")
        r = self.consulta.consultar()
        self.assertEqual((len(r["recibos"]), r["totales"]["pendiente"]), (26, 340))
        self.assertEqual(r["recibos"][0]["mes"], "2026-11")

    #Temporada sin recibos: mensaje y resumen a 0
    def testTemporadaSinRecibos(self):
        r = self.consulta.consultar(idOferta=2)
        self.assertEqual(r["mensaje"], "No hay recibos para los filtros seleccionados")
        self.assertEqual(r["totales"]["ingresos"], 0)
        self.assertEqual(len(r["resumen"]), 5)

    def testSinFiltroDeEstadoQueCoincida(self):
        r = self.consulta.consultar(idActividad=1, estado="DEVUELTO")
        self.assertEqual(r["mensaje"], "No hay recibos para los filtros seleccionados")
        self.assertEqual(r["resumen"][0]["ingresos"], 120)

    #Sin temporada se usa la vigente; la vigente aparece la primera en el filtro
    def testTemporadas(self):
        self.assertEqual([t["curso"] for t in self.consulta.getTemporadas()], ["2026-2027", "2025-2026"])
        self.db.executeUpdateQuery("update Oferta set estado = 'INACTIVA'")
        with self.assertRaises(ReciboError):
            self.consulta.consultar()

    def testActividadesDeLaTemporada(self):
        nombres = [a["nombre"] for a in self.consulta.getActividades(2)]
        self.assertEqual(len(nombres), 5)
        self.assertIn("Pádel medio", nombres)


if __name__ == '__main__':
    unittest.main()
