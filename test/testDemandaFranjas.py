import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.config import DATA_PATH, SCHEMA_PATH
from src.gui.paginaDemandaFranjas import PaginaDemandaFranjas
from src.inscripciones.demandaFranjasModel import (
    DemandaFranjasError,
    DemandaFranjasModel,
    agruparFranjas,
    indiceFranja,
)
from src.inscripciones.historicoModel import HistoricoModel
from src.util.database import Database


class TestDemandaFranjas(unittest.TestCase):

    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.carpeta = Path(temporal.name)
        self.ruta = self.carpeta / "franjas.db"

        self.db = Database(self.ruta)
        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)

        for tabla in (
            "Asistencia", "Inscripcion", "Horario", "Actividad"
        ):
            self.db.executeUpdateQuery(
                f"DELETE FROM {tabla}"
            )

        self.modelo = DemandaFranjasModel(self.ruta)

    def actividad(
        self, identificador=1, plazas=4,
        instalacion=4, oferta=1
    ):
        self.db.executeUpdateQuery(
            """INSERT INTO Actividad
                   (id, idOferta, idModalidad, idNivel,
                    fechaInicio, fechaFin, plazas, idInstalacion)
               VALUES (
                   ?, ?, 4, 2,
                   '2026-10-01', '2027-06-30', ?, ?
               )""",
            identificador, oferta, plazas, instalacion
        )

    def horario(
        self, actividad=1, dia=1,
        inicio="18:00", fin="19:00"
    ):
        self.db.executeUpdateQuery(
            """INSERT INTO Horario
                   (idActividad, diaSemana, horaInicio, horaFin)
               VALUES (?, ?, ?, ?)""",
            actividad, dia, inicio, fin
        )

    def solicitud(
        self, persona, actividad=1, estado="CONFIRMADA"
    ):
        fecha = "2026-09-10"

        self.db.executeUpdateQuery(
            """INSERT INTO Inscripcion
                   (idPersona, idActividad, fechaSolicitud,
                    fechaInscripcion, estado)
               VALUES (?, ?, ?, ?, ?)""",
            persona,
            actividad,
            fecha,
            fecha if estado == "CONFIRMADA" else None,
            estado
        )

    @staticmethod
    def fila(resultado, dia=1, franja=3):
        return next(
            fila for fila in resultado["filas"]
            if (
                fila["diaSemana"],
                fila["indiceFranja"]
            ) == (dia, franja)
        )

    def importarHistorico(self, dosActividades=False):
        csv = self.carpeta / "historico.csv"

        filas = [
            "temporada,categoría,nivel,plazas,"
            "NSocio,DNI,estado,fecha",

            "2024-2025,Natación,Iniciación,12,"
            "1,,Confirmada,2024-09-10",

            "2024-2025,Natación,Iniciación,12,"
            "2,,En espera,2024-09-11",

            "2024-2025,Natación,Iniciación,12,"
            "3,,Cancelada,2024-09-12",
        ]

        if dosActividades:
            filas.append(
                "2024-2025,Pilates,Medio,10,"
                "1,,Confirmada,2024-09-10"
            )

        csv.write_text(
            "\n".join(filas), encoding="utf-8"
        )

        modelo = HistoricoModel(self.ruta)
        modelo.importar(modelo.validar(csv))

        return self.db.executeQuery(
            "SELECT id FROM ActividadHistorica ORDER BY id"
        )[0]["id"]

    def testLimitesDeLasCuatroFranjas(self):
        casos = {
            "07:59": None,
            "08:00": 0,
            "10:59": 0,
            "11:00": 1,
            "13:30": 1,
            "14:00": 2,
            "16:59": 2,
            "17:00": 3,
            "19:59": 3,
            "20:00": None,
            "21:00": None,
        }

        for hora, esperado in casos.items():
            with self.subTest(hora=hora):
                self.assertEqual(
                    indiceFranja(hora), esperado
                )

    def testCuentaConfirmadasYEsperaPeroNoCanceladasNiPendientes(self):
        self.actividad()
        self.horario()

        estados = (
            "CONFIRMADA",
            "EN_ESPERA",
            "CANCELADA",
            "PENDIENTE_ACEPTACION",
        )

        for persona, estado in enumerate(estados, 1):
            self.solicitud(persona, estado=estado)

        fila = self.fila(self.modelo.consultar())

        self.assertEqual(
            (
                fila["inscritos"],
                fila["espera"],
                fila["demandaTotal"]
            ),
            (1, 1, 2)
        )

    def testCuentaEnCadaDiaSemanal(self):
        self.actividad()
        self.horario(dia=1)
        self.horario(dia=3)

        self.solicitud(1)
        self.solicitud(2, estado="EN_ESPERA")

        resultado = self.modelo.consultar()

        self.assertEqual(
            self.fila(resultado, 1)["demandaTotal"], 2
        )
        self.assertEqual(
            self.fila(resultado, 3)["demandaTotal"], 2
        )

    def testMismoGrupoDosIniciosEnLaMismaFranjaCuentaUnaVez(self):
        self.actividad()

        self.horario(inicio="17:00", fin="18:00")
        self.horario(inicio="19:00", fin="20:00")

        self.solicitud(1)

        fila = self.fila(self.modelo.consultar())

        self.assertEqual(
            (fila["inscritos"], fila["grupos"]),
            (1, 1)
        )

    def testInicioDeterminaLaFranjaAunqueCruceSuFinal(self):
        self.actividad()
        self.horario(
            dia=2, inicio="13:30", fin="14:30"
        )
        self.solicitud(1)

        resultado = self.modelo.consultar()

        self.assertEqual(
            self.fila(resultado, 2, 1)["inscritos"], 1
        )
        self.assertEqual(
            self.fila(resultado, 2, 2)["inscritos"], 0
        )

    def testSuma25InscritosY10EnEspera(self):
        actividades = [
            {
                "plazas": 30,
                "inscritos": 15,
                "espera": 4,
                "horarios": [
                    {"diaSemana": 2, "horaInicio": "13:30"}
                ],
            },
            {
                "plazas": 10,
                "inscritos": 10,
                "espera": 6,
                "horarios": [
                    {"diaSemana": 2, "horaInicio": "11:00"}
                ],
            },
        ]

        filas, _, _ = agruparFranjas(actividades)
        fila = self.fila({"filas": filas}, 2, 1)

        self.assertEqual(
            (
                fila["inscritos"],
                fila["espera"],
                fila["demandaTotal"]
            ),
            (25, 10, 35)
        )
        self.assertEqual(fila["ocupacionMedia"], 75)

    def testMediaPorGrupoNoEsOcupacionPonderada(self):
        self.actividad(1, plazas=4)
        self.actividad(2, plazas=1)

        self.horario(1)
        self.horario(2)

        self.solicitud(1, 1)
        self.solicitud(2, 1)
        self.solicitud(3, 2)

        fila = self.fila(self.modelo.consultar())

        self.assertEqual(
            (fila["grupos"], fila["ocupacionMedia"]),
            (2, 75)
        )

    def testDevuelve28CombinacionesIncluyendoCeros(self):
        self.actividad()
        self.horario()
        self.solicitud(1)

        resultado = self.modelo.consultar()

        self.assertEqual(
            len(resultado["filas"]), 28
        )
        self.assertEqual(
            sum(
                fila["demandaTotal"] == 0
                for fila in resultado["filas"]
            ),
            27
        )

    def testGrupoVacioTieneMediaCeroYFranjaSinGruposNoTieneMedia(self):
        self.actividad()
        self.horario()

        resultado = self.modelo.consultar()

        self.assertEqual(
            self.fila(resultado)["ocupacionMedia"], 0
        )
        self.assertIsNone(
            self.fila(resultado, 2)["ocupacionMedia"]
        )

    def testOrdenDescendenteYEmpatesConsecutivos(self):
        self.actividad()
        self.horario(dia=3)
        self.horario(dia=1)
        self.solicitud(1)

        filas = self.modelo.consultar()["filas"]

        self.assertEqual(
            [f["demandaTotal"] for f in filas],
            sorted(
                (f["demandaTotal"] for f in filas),
                reverse=True
            )
        )
        self.assertEqual(
            [f["diaSemana"] for f in filas[:2]],
            [1, 3]
        )

    def testFiltraInstalacion(self):
        self.actividad(1, instalacion=4)
        self.actividad(2, instalacion=1)

        self.horario(1)
        self.horario(2)

        self.solicitud(1, 1)
        self.solicitud(2, 2)

        resultado = self.modelo.consultar(
            idInstalacion=4
        )

        self.assertEqual(
            self.fila(resultado)["inscritos"], 1
        )
        self.assertEqual(
            self.fila(self.modelo.consultar())["inscritos"],
            2
        )

    def testInstalacionSinActividades(self):
        self.actividad()

        resultado = self.modelo.consultar(
            idInstalacion=1
        )

        self.assertEqual(resultado["filas"], [])
        self.assertIn(
            "No hay actividades", resultado["mensaje"]
        )

    def testInstalacionInexistente(self):
        with self.assertRaises(DemandaFranjasError):
            self.modelo.consultar(idInstalacion=999)

    def testHorarioFueraDeFranjaSeInforma(self):
        self.actividad()
        self.horario(inicio="21:00", fin="22:00")
        self.solicitud(1)

        resultado = self.modelo.consultar()

        self.assertTrue(all(
            fila["demandaTotal"] == 0
            for fila in resultado["filas"]
        ))
        self.assertIn(
            "fuera", " ".join(resultado["avisos"])
        )

    def testActividadSinHorarioSeInforma(self):
        self.actividad()

        self.assertIn(
            "no tienen horario",
            " ".join(self.modelo.consultar()["avisos"])
        )

    def testSeleccionVacia(self):
        resultado = self.modelo.consultar()

        self.assertEqual(resultado["filas"], [])
        self.assertIn(
            "No hay actividades", resultado["mensaje"]
        )

    def testConsultaNoEscribeNiCreaTablas(self):
        self.actividad()
        self.horario()

        antes = self.ruta.read_bytes()

        self.modelo.getTemporadas()
        self.modelo.getInstalaciones()
        self.modelo.consultar()

        self.assertEqual(
            self.ruta.read_bytes(), antes
        )
        self.assertEqual(
            self.db.executeQuery(
                """SELECT name FROM sqlite_master
                   WHERE name = 'HorarioHistoricoFranjas'"""
            ),
            []
        )

    def testOfertaAnteriorTieneSeleccionIndependiente(self):
        self.db.executeUpdateQuery("""
            INSERT INTO Oferta
                (id, curso, fechaInicio, fechaFin, estado)
            VALUES (
                2, '2025-2026',
                '2025-10-01', '2026-06-30', 'INACTIVA'
            )
        """)

        self.actividad(2, oferta=2)
        self.horario(2)
        self.solicitud(1, 2)

        self.assertEqual(
            self.modelo.consultar()["filas"], []
        )
        self.assertEqual(
            self.fila(
                self.modelo.consultar("O:2")
            )["inscritos"],
            1
        )

    def testSinTemporadaActiva(self):
        self.db.executeUpdateQuery(
            "UPDATE Oferta SET estado = 'INACTIVA'"
        )

        self.assertIn(
            "actual activa",
            self.modelo.consultar()["mensaje"]
        )

    def testHistoricoSinHorarioNoInventaDemandaPorFranja(self):
        self.importarHistorico()

        antes = self.ruta.read_bytes()
        resultado = self.modelo.consultar("H:2024-2025")

        self.assertEqual(resultado["filas"], [])
        self.assertEqual(
            resultado["sinHorarioHistorico"], 1
        )
        self.assertIn(
            "Falta completar", resultado["mensaje"]
        )
        self.assertEqual(
            self.ruta.read_bytes(), antes
        )

    def testHistoricoImportadoCompletadoSeConsultaEnCadaDia(self):
        actividad = self.importarHistorico()

        self.modelo.guardarHorarioHistorico(
            actividad, 1, 2, "10:00"
        )
        self.modelo.guardarHorarioHistorico(
            actividad, 1, 4, "10:00"
        )

        resultado = self.modelo.consultar(
            "H:2024-2025", 1
        )

        for dia in (2, 4):
            fila = self.fila(resultado, dia, 0)

            self.assertEqual(
                (
                    fila["inscritos"],
                    fila["espera"],
                    fila["demandaTotal"]
                ),
                (1, 1, 2)
            )

        self.assertEqual(
            resultado["sinHorarioHistorico"], 0
        )
        self.assertEqual(
            self.modelo.consultar(
                "H:2024-2025", 4
            )["filas"],
            []
        )

    def testHistoricoIncompletoAdvierteResumenParcial(self):
        actividad = self.importarHistorico(
            dosActividades=True
        )

        self.modelo.guardarHorarioHistorico(
            actividad, 1, 2, "10:00"
        )

        resultado = self.modelo.consultar("H:2024-2025")

        self.assertEqual(
            resultado["sinHorarioHistorico"], 1
        )
        self.assertIn(
            "No se incluyen",
            " ".join(resultado["avisos"])
        )
        self.assertEqual(
            self.fila(resultado, 2, 0)["inscritos"], 1
        )

    def testGuardarYQuitarHorarioConservaInscripcionesHistoricas(self):
        actividad = self.importarHistorico()

        antes = self.db.executeQuery(
            "SELECT * FROM InscripcionHistorica ORDER BY id"
        )

        self.modelo.guardarHorarioHistorico(
            actividad, 1, 2, "10:00"
        )
        self.modelo.guardarHorarioHistorico(
            actividad, 1, 2, "10:00"
        )

        horarios = self.modelo.getHorariosHistoricos(
            actividad
        )

        self.assertEqual(len(horarios), 1)

        self.modelo.eliminarHorarioHistorico(
            horarios[0]["id"]
        )

        self.assertEqual(
            self.modelo.getHorariosHistoricos(actividad),
            []
        )
        self.assertEqual(
            self.db.executeQuery(
                "SELECT * FROM InscripcionHistorica ORDER BY id"
            ),
            antes
        )

    def testValidaHorarioAntesDeGuardar(self):
        actividad = self.importarHistorico()

        casos = (
            (999, 1, "10:00"),
            (1, 8, "10:00"),
            (1, 2, "25:00"),
        )

        for instalacion, dia, hora in casos:
            with self.subTest(
                instalacion=instalacion,
                dia=dia,
                hora=hora
            ):
                with self.assertRaises(DemandaFranjasError):
                    self.modelo.guardarHorarioHistorico(
                        actividad, instalacion, dia, hora
                    )

        self.assertEqual(
            self.modelo.getHorariosHistoricos(actividad),
            []
        )

    def testRecrearEsquemaSigueSiendoCompatible(self):
        actividad = self.importarHistorico()

        self.modelo.guardarHorarioHistorico(
            actividad, 1, 2, "10:00"
        )

        self.db.executeScript(SCHEMA_PATH)
        self.db.executeScript(DATA_PATH)

        self.assertEqual(
            self.modelo.getTemporadas()[0]["clave"],
            "O:1"
        )

    def testRefrescoDeLaPaginaPresentaLosDatos(self):
        pagina = Mock()

        pagina.temporada.current.return_value = 0
        pagina.instalacion.current.return_value = 0
        pagina.temporadas = [{"clave": "O:1"}]
        pagina.lista.get_children.return_value = ()
        pagina.app.demandaFranjas = self.modelo

        self.actividad()
        self.horario()
        self.solicitud(1)

        PaginaDemandaFranjas.consultar(pagina)

        self.assertEqual(
            pagina.lista.insert.call_count, 28
        )
        self.assertEqual(
            pagina.lista.insert.call_args_list[0]
            .kwargs["values"][6],
            "25,00 %"
        )
        self.assertEqual(
            pagina.lista.insert.call_args_list[1]
            .kwargs["values"][6],
            "Sin grupos"
        )