import datetime
import os
import tempfile
import unittest
from unittest.mock import patch

from src.config import SCHEMA_PATH
from src.personas.personaModel import PersonaError, PersonaModel, normalizarDni
from src.personas.personaView import PersonaView
from src.util.database import Database
from src.util.unexpectedException import UnexpectedException

#Datos de prueba de la HU8: dos socios (números 1 y 2 por antigüedad) y un no socio
TEST_DATA = """
    insert into Persona(dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values('10000001A','Marta','García López','1975-03-12','600111001',null,1,'2005-09-01');
    insert into Persona(dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values('10000002B','Luis','Fernández Díaz',null,null,'luis@example.com',2,'2009-01-15');
    insert into Persona(dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values('20000001F','Jorge','Sánchez Vega',null,'611222001',null,null,null);
"""

HOY = datetime.date(2026, 10, 18)


class TestPersona(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScriptBatch(TEST_DATA)
        self.model = PersonaModel(db_path=self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def registrar(self, dni="30000001H", nombre="Sara", apellidos="Díaz Mon",
                  fecha="2000-01-01", telefono="622000000", correo="sara@example.com"):
        return self.model.registrarNoSocio(dni, nombre, apellidos, fecha, telefono, correo, hoy=HOY)

    def totalPersonas(self):
        return self.db.executeQuery("select count(*) as n from Persona")[0]["n"]

    #CA2 Registro de un no socio con todos los datos
    def testRegistraNoSocio(self):
        msg = self.registrar()
        self.assertEqual(msg, "Persona registrada como no socia: Sara Díaz Mon (30000001H)")
        p = self.model.getPersonaPorDni("30000001H")
        self.assertEqual((p["nombre"], p["apellidos"], p["fechaNacimiento"], p["telefono"], p["correo"]),
                         ("Sara", "Díaz Mon", "2000-01-01", "622000000", "sara@example.com"))
        self.assertIsNone(p["numSocio"])
        self.assertIsNone(p["fechaAltaSocio"])

    #CA3 Basta con un medio de contacto; la fecha de nacimiento es opcional
    def testRegistraConSoloUnContacto(self):
        self.registrar(dni="1", telefono="", correo="a@b.es", fecha="")
        self.registrar(dni="2", telefono="600", correo="")
        self.assertIsNone(self.model.getPersonaPorDni("1")["telefono"])
        self.assertIsNone(self.model.getPersonaPorDni("1")["fechaNacimiento"])
        self.assertIsNone(self.model.getPersonaPorDni("2")["correo"])

    #CA3 Campos obligatorios: se indica cuál falta y no se guarda
    def testFaltanObligatorios(self):
        with self.assertRaisesRegex(PersonaError, "Faltan campos obligatorios: DNI, apellidos"):
            self.registrar(dni="  ", apellidos="")
        self.assertEqual(self.totalPersonas(), 3)

    def testFaltaContacto(self):
        with self.assertRaisesRegex(PersonaError, "al menos un medio de contacto"):
            self.registrar(telefono=" ", correo="")
        self.assertEqual(self.totalPersonas(), 3)

    #CA4 Validaciones
    def testCorreoSinArroba(self):
        with self.assertRaisesRegex(PersonaError, "El correo no es válido"):
            self.registrar(correo="sara.example.com")

    def testFechaNacimientoFutura(self):
        with self.assertRaisesRegex(PersonaError, "no puede ser futura"):
            self.registrar(fecha="2026-10-19")
        self.registrar(fecha="2026-10-18")  #hoy no es futura

    def testFechaMalFormada(self):
        with self.assertRaisesRegex(PersonaError, "formato AAAA-MM-DD"):
            self.registrar(fecha="18/10/2000")

    def testVariosErroresALaVez(self):
        with self.assertRaises(PersonaError) as ctx:
            self.registrar(nombre="", correo="mal", fecha="2030-01-01")
        self.assertEqual(str(ctx.exception).count("\n"), 2)

    #CA4 El DNI no se valida en formato (sin restricciones de identificación en este sprint)
    def testDniSinFormatoConcreto(self):
        self.registrar(dni="X1234567")
        self.assertIsNotNone(self.model.getPersonaPorDni("X1234567"))

    #CA5 Duplicados
    def testDniDeSocio(self):
        with self.assertRaises(PersonaError) as ctx:
            self.registrar(dni="10000001A")
        self.assertEqual(str(ctx.exception), "Esta persona ya es socia")
        self.assertEqual(ctx.exception.persona["numSocio"], 1)
        self.assertEqual(self.totalPersonas(), 3)

    def testDniDeNoSocio(self):
        with self.assertRaises(PersonaError) as ctx:
            self.registrar(dni="20000001F")
        self.assertEqual(str(ctx.exception), "Ya existe una persona con ese DNI")
        self.assertEqual(ctx.exception.persona["nombre"], "Jorge")
        self.assertEqual(self.totalPersonas(), 3)

    #CA7 Normalización: mismo DNI escrito de otra forma
    def testNormalizacionDni(self):
        self.assertEqual(normalizarDni(" 12345678-z "), "12345678Z")
        self.assertEqual(normalizarDni("12 345 678 z"), "12345678Z")
        with self.assertRaisesRegex(PersonaError, "Ya existe una persona con ese DNI"):
            self.registrar(dni="20000001-f")
        with self.assertRaisesRegex(PersonaError, "Esta persona ya es socia"):
            self.registrar(dni="10000001 a")

    def testNormalizacionTexto(self):
        self.registrar(nombre="  Sara  ", apellidos=" Díaz   Mon ")
        p = self.model.getPersonaPorDni("30000001H")
        self.assertEqual((p["nombre"], p["apellidos"]), ("Sara", "Díaz Mon"))

    #CA6 Consulta por DNI o número de socio
    def testConsultaPorDni(self):
        self.assertEqual(self.model.getPersonaPorDni("10000002b")["numSocio"], 2)
        self.assertIsNone(self.model.getPersonaPorDni("20000001F")["numSocio"])
        self.assertIsNone(self.model.getPersonaPorDni("99999999Z"))

    def testConsultaPorNumSocio(self):
        self.assertEqual(self.model.getPersonaPorNumSocio(1)["dni"], "10000001A")
        self.assertIsNone(self.model.getPersonaPorNumSocio(99))

    #CA1 Socios precargados: número secuencial por antigüedad y único
    def testNumSocioUnico(self):
        with self.assertRaises(UnexpectedException):
            self.db.executeUpdateQuery(
                "insert into Persona(dni,nombre,apellidos,telefono,numSocio,fechaAltaSocio) values('X','A','B','1',1,'2020-01-01')")

    def testSociosDeDatosDePrueba(self):
        from src.config import DATA_PATH
        db = Database(self.db_path)
        db.executeScript(SCHEMA_PATH)
        db.executeScript(DATA_PATH)
        socios = db.executeQuery("select numSocio from Persona where numSocio is not null order by fechaAltaSocio")
        self.assertEqual([s["numSocio"] for s in socios], list(range(1, len(socios) + 1)))

    #Vista
    def salida(self, metodo, entradas):
        view = PersonaView(self.model)
        with patch("builtins.input", side_effect=entradas), patch("builtins.print") as mock_print:
            getattr(view, metodo)()
        return [" ".join(str(a) for a in c.args) for c in mock_print.call_args_list]

    def testVistaRegistro(self):
        lineas = self.salida("registrarNoSocio",
                             ["30000001-h", "Sara", "Díaz Mon", "", "622000000", ""])
        self.assertIn("Persona registrada como no socia: Sara Díaz Mon (30000001H)", lineas)

    def testVistaRegistroDuplicadoMuestraDatos(self):
        lineas = self.salida("registrarNoSocio", ["10000001A", "M", "G", "", "1", ""])
        self.assertIn("Esta persona ya es socia", lineas)
        self.assertIn("Nombre: Marta García López", lineas)
        self.assertIn("Tipo: socio (número de socio 1, alta 2005-09-01)", lineas)

    def testVistaConsultaPorNumSocio(self):
        lineas = self.salida("consultarPersona", ["2", "2"])
        self.assertIn("DNI: 10000002B", lineas)
        self.assertIn("Tipo: socio (número de socio 2, alta 2009-01-15)", lineas)

    def testVistaConsultaNoSocio(self):
        lineas = self.salida("consultarPersona", ["1", "20000001f"])
        self.assertIn("Tipo: no socio", lineas)

    def testVistaConsultaInexistente(self):
        self.assertEqual(self.salida("consultarPersona", ["1", "99999999Z"])[-1],
                         "No existe ninguna persona con ese identificador")
        self.assertEqual(self.salida("consultarPersona", ["2", "99"])[-1],
                         "No existe ninguna persona con ese identificador")


if __name__ == '__main__':
    unittest.main()
