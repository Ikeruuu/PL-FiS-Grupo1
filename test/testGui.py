import os
import tempfile
import unittest
from unittest import mock

from src.config import DATA_PATH, SCHEMA_PATH
from src.util.database import Database

#Las pruebas de la interfaz gráfica se saltan si no hay Tkinter o no hay pantalla disponible
try:
    import tkinter
    from src.gui.app import CentroDeportivoApp
    _raiz = tkinter.Tk()
    _raiz.destroy()
    HAY_TK = True
except Exception:
    HAY_TK = False


@unittest.skipUnless(HAY_TK, "Tkinter o pantalla no disponibles")
class TestGui(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db = Database(self.tmp.name)
        db.executeScript(SCHEMA_PATH)
        db.executeScript(DATA_PATH)
        self.app = CentroDeportivoApp(self.tmp.name)
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        os.unlink(self.tmp.name)

    def testInicioMuestraResumen(self):
        valores = self.app.paginas["inicio"].valores
        self.assertEqual(str(valores["instalaciones"][0].cget("text")), "6")
        self.assertEqual(str(valores["sinInstalacion"][0].cget("text")), "5")
        self.assertEqual(str(valores["socios"][0].cget("text")), "5")

    #El nombre del centro y las opciones del menú caben enteros en la barra lateral
    def testNombreNoSeCorta(self):
        self.app.update_idletasks()
        lateral = self.app.botones["inicio"].master
        marca = lateral.winfo_children()[0]
        ancho = int(lateral.cget("width"))
        for etiqueta in marca.winfo_children():
            self.assertLessEqual(etiqueta.winfo_reqwidth() + 2 * int(marca.cget("padx")), ancho,
                                 etiqueta.cget("text"))
        for boton in self.app.botones.values():
            self.assertLessEqual(boton.winfo_reqwidth(), ancho, boton.cget("text"))

    def testNavegacion(self):
        for clave in ("asignar", "ocupacion", "personas", "ofertaDisponible", "misInscripciones",
                      "cancelar", "inicio"):
            self.app.mostrar(clave)
            self.assertEqual(self.app.actual, clave)

    def testAsignarColisionYExito(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.tablaActividades.selection_set("4")
        p.tablaInstalaciones.selection_set("4")
        p.asignar()
        self.assertEqual(p.aviso.tipo, "error")
        self.assertIn("Colisión con Pádel medio, lunes 18:00–19:00", p.aviso.mensaje)
        p.tablaActividades.selection_set("4")
        p.tablaInstalaciones.selection_set("5")
        p.asignar()
        self.assertEqual(p.aviso.tipo, "ok")
        self.assertNotIn("4", p.tablaActividades.get_children())

    def testAsignarMarcaCapacidadInsuficiente(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.tablaActividades.selection_set("7")
        p._marcarCapacidad()
        self.assertEqual(p.tablaInstalaciones.item("2", "tags"), ("noCabe",))
        self.assertEqual(p.tablaInstalaciones.item("3", "tags"), "")

    def testAsignarSinSeleccion(self):
        self.app.mostrar("asignar")
        p = self.app.paginas["asignar"]
        p.asignar()
        self.assertEqual(p.aviso.mensaje, "Selecciona una actividad y una instalación")

    def testOcupacionLista(self):
        self.app.mostrar("ocupacion")
        p = self.app.paginas["ocupacion"]
        p.combo.current(0)
        p.consultar()
        dias = p.lista.get_children()
        self.assertEqual(len(dias), 7)
        lunes = [p.lista.item(i, "values")[:2] for i in p.lista.get_children(dias[0])]
        self.assertEqual(lunes, [("08:00–09:00", "Ocupada"), ("09:00–21:00", "Libre"),
                                 ("21:00–22:00", "Ocupada")])

    def testOcupacionLibreYFechasIncoherentes(self):
        self.app.mostrar("ocupacion")
        p = self.app.paginas["ocupacion"]
        p.combo.current(2)
        p.consultar()
        self.assertEqual(p.aviso.mensaje, "La instalación está libre en todo el periodo (8:00–22:00)")
        p.desde.insert(0, "2027-01-01")
        p.hasta.insert(0, "2026-12-31")
        p.consultar()
        self.assertEqual(p.aviso.tipo, "error")

    def testPersonasRegistroYDuplicado(self):
        self.app.mostrar("personas")
        p = self.app.paginas["personas"]
        for clave, valor in (("dni", "30000001-h"), ("nombre", "Sara"), ("apellidos", "Díaz"),
                             ("correo", "sara@example.com")):
            p.campos[clave].insert(0, valor)
        p.registrar()
        self.assertEqual(p.aviso.tipo, "ok")
        p.campos["dni"].insert(0, "10000001a")
        p.campos["nombre"].insert(0, "X")
        p.campos["apellidos"].insert(0, "Y")
        p.campos["telefono"].insert(0, "1")
        p.registrar()
        self.assertEqual(p.aviso.mensaje, "Esta persona ya es socia")

    def testPersonasConsulta(self):
        self.app.mostrar("personas")
        p = self.app.paginas["personas"]
        p.tipoBusqueda.set("socio")
        p.identificador.insert(0, "3")
        p.consultar()
        textos = [w.cget("text") for w in p.ficha.winfo_children()[0].winfo_children()[1].winfo_children()]
        self.assertIn("SOCIO Nº 3", textos)
        p.identificador.delete(0, "end")
        p.identificador.insert(0, "99")
        p.consultar()
        self.assertEqual(p.aviso.mensaje, "No existe ninguna persona con ese identificador")

    def testOfertasCrearYListar(self):
        self.app.mostrar("ofertas")
        p = self.app.paginas["ofertas"]
        p.modalidad.insert(0, "1")
        p.nivel.insert(0, "1")
        p.plazas.insert(0, "10")
        p.fechaInicio.insert(0, "2026-10-01")
        p.fechaFin.insert(0, "2027-06-30")
        p.dia.insert(0, "1")
        p.horaInicio.insert(0, "18:00")
        p.horaFin.insert(0, "19:00")
        p.guardar()
        self.assertEqual(p.aviso.tipo, "ok")
        # data.sql precarga 10 actividades en la oferta 1; con la nueva añadida suman 11
        self.assertEqual(len(p.tablaActividades.get_children()), 11)

    def testOfertasModificarActividad(self):
        self.app.mostrar("ofertas")
        p = self.app.paginas["ofertas"]
        p.modalidad.insert(0, "1")
        p.nivel.insert(0, "1")
        p.plazas.insert(0, "10")
        p.fechaInicio.insert(0, "2026-10-01")
        p.fechaFin.insert(0, "2027-06-30")
        p.dia.insert(0, "1")
        p.horaInicio.insert(0, "18:00")
        p.horaFin.insert(0, "19:00")
        p.guardar()
        
        idActividad = max(p.tablaActividades.get_children(), key=int)
        p.tablaActividades.selection_set(idActividad)
        # Cargar manualmente la selección (selection_set no dispara <<TreeviewSelect>> en Tkinter)
        p._cargarSeleccion()
        
        p.plazas.delete(0, "end")
        p.plazas.insert(0, "15")
        p.guardar()
        self.assertEqual(p.aviso.tipo, "ok")

    #---- HU 35334 / 35335 / 35336 (José María) ----
    def _periodos(self):
        self.app.ofertas.db.executeUpdateQuery(
            """update Oferta set inicioInscripcionSocios = '2026-09-01',
                   finInscripcionSocios = '2026-09-15', inicioInscripcionNoSocios = '2026-09-16',
                   finInscripcionNoSocios = '2026-09-30' where id = 1""")

    def _solicitud(self, idPersona, idActividad, estado, fecha="2026-09-02T10:00:00"):
        self.app.ofertas.db.executeUpdateQuery(
            """insert into Inscripcion (idPersona, idActividad, fechaSolicitud, fechaInscripcion,
               estado) values (?, ?, ?, ?, ?)""",
            idPersona, idActividad, fecha, fecha if estado == "CONFIRMADA" else None, estado)

    def testConsultaOfertaConFiltros(self):
        self._periodos()
        self.app.mostrar("ofertaDisponible")
        p = self.app.paginas["ofertaDisponible"]
        p.fecha.delete(0, "end")
        p.fecha.insert(0, "2026-09-10")
        p.consultar()
        self.assertEqual(len(p.lista.get_children()), 10)
        p.modalidad.current(4)   #Pádel
        p.consultar()
        self.assertEqual(sorted(p.lista.get_children(), key=int), ["1", "4", "5"])
        valores = p.lista.item("1", "values")
        self.assertEqual(valores[1], "lunes y miércoles")
        self.assertEqual(valores[4], "30,00 €")
        self.assertEqual(valores[6], "Socios")
        p.modalidad.current(5)   #Tenis
        p.nivel.current(3)       #Avanzado
        p.consultar()
        self.assertEqual(p.aviso.mensaje,
                         "Ninguna actividad abierta a inscripción cumple los filtros indicados")

    def testConsultaOfertaFueraDePlazo(self):
        self.app.mostrar("ofertaDisponible")
        p = self.app.paginas["ofertaDisponible"]
        p.consultar()
        self.assertEqual(p.aviso.mensaje, "No hay actividades abiertas a inscripción en este momento")

    def testMisInscripciones(self):
        self._solicitud(1, 1, "CONFIRMADA")
        self._solicitud(2, 4, "CONFIRMADA")
        self._solicitud(1, 4, "EN_ESPERA", "2026-09-03T10:00:00")
        self.app.mostrar("misInscripciones")
        p = self.app.paginas["misInscripciones"]
        p.identificador.insert(0, "10000001A")
        p.consultar()
        estados = [p.lista.item(i, "values")[4] for i in p.lista.get_children()]
        self.assertEqual(estados, ["Inscrito", "En lista de espera (posición 1 de 1)"])
        p.identificador.delete(0, "end")
        p.identificador.insert(0, "20000002G")
        p.consultar()
        self.assertEqual(p.aviso.mensaje, "No está inscrito en ninguna actividad")
        p.identificador.delete(0, "end")
        p.identificador.insert(0, "NOEXISTE")
        p.consultar()
        self.assertEqual(p.aviso.tipo, "error")

    def testCancelarConConfirmacion(self):
        self._solicitud(1, 1, "CONFIRMADA")
        self.app.mostrar("cancelar")
        p = self.app.paginas["cancelar"]
        p.identificador.insert(0, "10000001A")
        p.buscar()
        p.lista.selection_set("1")
        p.fecha.delete(0, "end")
        p.fecha.insert(0, "2026-11-20")
        p.mes.insert(0, "2026-12")
        p.cancelar()
        self.assertIn("Fuera de plazo", p.aviso.mensaje)
        p.fecha.delete(0, "end")
        p.fecha.insert(0, "2026-11-05")
        p.lista.selection_set("1")
        with mock.patch("src.gui.paginas.messagebox.askyesno", return_value=False):
            p.cancelar()
        self.assertEqual(p.aviso.mensaje, "Cancelación anulada; no se ha modificado nada")
        p.lista.selection_set("1")
        with mock.patch("src.gui.paginas.messagebox.askyesno", return_value=True) as pregunta:
            p.cancelar()
        self.assertIn("Se cancelará la inscripción en Pádel medio a partir de diciembre de 2026",
                      pregunta.call_args[0][1])
        self.assertEqual(p.aviso.tipo, "ok")
        self.assertEqual(p.lista.get_children(), ())

if __name__ == '__main__':
    unittest.main()
