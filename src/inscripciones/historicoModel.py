"""Validación, importación y consulta de inscripciones históricas (#36496–#36498)."""
import csv
import hashlib
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO
from pathlib import Path

from src.config import DB_PATH, SCHEMA_HISTORICO_PATH
from src.inscripciones.comun import conectar
from src.personas.personaModel import normalizarDni
from src.util.database import Database
from src.util.unexpectedException import UnexpectedException


class HistoricoError(Exception):
    """Error que se muestra al usuario."""


@dataclass(frozen=True)
class Incidencia:
    linea: int
    motivo: str


@dataclass(frozen=True)
class Solicitud:
    temporada: str
    modalidad: int
    nivel: int
    plazas: int
    tipo: str
    identificador: str
    estado: str
    fecha: str


@dataclass(frozen=True)
class ValidacionHistorica:
    ruta: Path
    huella: bytes
    solicitudes: tuple[Solicitud, ...]
    incidencias: tuple[Incidencia, ...]
    descartadas: int


def claveTexto(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return re.sub(r"[^a-z0-9]", "", texto)


CABECERAS = {
    "temporada": ("temporada", "año", "curso", "año/temporada", "oferta"),
    "categoría": ("categoría", "modalidad", "actividad"),
    "nivel": ("nivel",),
    "plazas": ("plazas", "plazas ofertadas"),
    "NSocio": ("NSocio", "Nº Socio", "numSocio", "número de socio"),
    "no socio": ("identificación de no socio", "identificador no socio", "no socio", "DNI"),
    "estado": ("estado", "estado de la solicitud", "estado solicitud"),
    "fecha": ("fecha", "fecha de inscripción", "fecha inscripción", "fecha de solicitud"),
}
ESTADOS = {
    "confirmada": "CONFIRMADA",
    "inscrita": "CONFIRMADA",
    "inscrito": "CONFIRMADA",
    "enlistaespera": "EN_ESPERA",
    "enlistadeespera": "EN_ESPERA",
    "listaespera": "EN_ESPERA",
    "listadeespera": "EN_ESPERA",
    "enespera": "EN_ESPERA",
    "pendienteaceptacion": "PENDIENTE_ACEPTACION",
    "pendientedeaceptacion": "PENDIENTE_ACEPTACION",
    "cancelada": "CANCELADA",
}


def anioCurso(texto):
    curso = re.sub(r"\s+", "", texto).replace("–", "-")
    partes = re.fullmatch(r"([0-9]{4})(?:[-/]([0-9]{4}|[0-9]{2}))?", curso)
    if not partes:
        return None
    inicio = int(partes[1])
    fin = partes[2]
    if not 1 <= inicio < 9999:
        return None
    if fin is not None and not f"{inicio + 1:04d}".endswith(fin):
        return None
    return inicio


class HistoricoModel:
    def __init__(self, db_path=None):
        self.db = Database(DB_PATH if db_path is None else db_path)

    @staticmethod
    def _leer(ruta):
        try:
            return ruta.read_bytes()
        except OSError as error:
            raise HistoricoError("No se puede leer el fichero CSV seleccionado.") from error

    def validar(self, ruta, hoy=None):
        """Devuelve las filas aptas y un informe por línea. Solo lee la base de datos."""
        ruta = Path(ruta).resolve()
        datos = self._leer(ruta)
        huella = hashlib.sha256(datos).digest()
        try:
            contenido = datos.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise HistoricoError("Guarda el fichero CSV con codificación UTF-8.") from error

        cabecera = next((linea for linea in contenido.splitlines() if linea.strip()), "")
        delimitador = ";" if cabecera.count(";") > cabecera.count(",") else ","
        lector = csv.reader(StringIO(contenido, newline=""), delimiter=delimitador, strict=True)
        try:
            campos = next((fila for fila in lector if any(c.strip() for c in fila)), [])
        except csv.Error as error:
            return ValidacionHistorica(ruta, huella, (), (Incidencia(1, f"Cabecera CSV: {error}"),), 0)
        if not campos:
            return ValidacionHistorica(ruta, huella, (), (Incidencia(1, "El fichero no contiene una cabecera"),), 0)

        lineaCabecera = lector.line_num
        indices, incidencias = self._leerCabecera(campos, lineaCabecera)
        modalidades = {claveTexto(m["nombre"]): m["id"]
                       for m in self.db.executeQuery("SELECT id, nombre FROM Modalidad")}
        niveles = {claveTexto(n["nombre"]): n["id"]
                   for n in self.db.executeQuery("SELECT id, nombre FROM Nivel")}
        personas = self.db.executeQuery("SELECT id, dni, numSocio FROM Persona")
        socios = {str(p["numSocio"]): p["id"] for p in personas if p["numSocio"] is not None}
        dniRegistrados = {normalizarDni(p["dni"]): p["id"] for p in personas}
        ofertasActivas = self.db.executeQuery("SELECT curso, fechaInicio FROM Oferta WHERE estado = 'ACTIVA'")
        hoy = hoy if hoy is not None else date.today()
        limite = hoy.year - (hoy <= date(hoy.year, 6, 30))
        if ofertasActivas:
            activa = ofertasActivas[0]
            limite = anioCurso(activa["curso"]) or date.fromisoformat(activa["fechaInicio"]).year

        solicitudes, descartadas = [], 0
        vistas, plazasActividad = {}, {}
        while True:
            linea = lector.line_num + 1
            try:
                valores = next(lector)
            except StopIteration:
                break
            except csv.Error as error:
                incidencias.append(Incidencia(linea, f"Fila CSV: {error}"))
                descartadas += 1
                continue
            if not any(c.strip() for c in valores):
                continue
            if not indices:
                descartadas += 1
                continue
            if len(valores) != len(campos):
                incidencias.append(Incidencia(linea, f"Se esperaban {len(campos)} columnas y hay {len(valores)}"))
                descartadas += 1
                continue

            fila = {campo: valores[indice].strip() for campo, indice in indices.items()}
            solicitud, errores = self._validarFila(fila, modalidades, niveles, limite)
            if solicitud is not None:
                actividad = (solicitud.temporada, solicitud.modalidad, solicitud.nivel)
                registro = socios if solicitud.tipo == "SOCIO" else dniRegistrados
                idPersona = registro.get(solicitud.identificador)
                persona = (("PERSONA", idPersona) if idPersona is not None
                           else (solicitud.tipo, solicitud.identificador))
                clave = (*actividad, *persona)
                if clave in vistas:
                    errores.append(f"Inscripción duplicada (primera fila válida: {vistas[clave]})")
                if actividad in plazasActividad:
                    plazas, primeraLinea = plazasActividad[actividad]
                    if solicitud.plazas != plazas:
                        errores.append(f"Las plazas de la actividad difieren de las de la línea {primeraLinea}")
                if not errores:
                    vistas[clave] = linea
                    plazasActividad.setdefault(actividad, (solicitud.plazas, linea))
                    solicitudes.append(solicitud)
            if errores:
                descartadas += 1
                incidencias.extend(Incidencia(linea, motivo) for motivo in errores)

        if not solicitudes and not incidencias:
            incidencias.append(Incidencia(lineaCabecera, "El fichero no contiene solicitudes"))
        return ValidacionHistorica(ruta, huella, tuple(solicitudes), tuple(incidencias), descartadas)

    @staticmethod
    def _leerCabecera(campos, linea):
        indices, errores = {}, []
        claves = [claveTexto(campo) for campo in campos]
        for campo, alias in CABECERAS.items():
            opciones = {claveTexto(nombre) for nombre in alias}
            coincidencias = [i for i, clave in enumerate(claves) if clave in opciones]
            if len(coincidencias) == 1:
                indices[campo] = coincidencias[0]
            elif len(coincidencias) > 1:
                errores.append(f"La columna {campo} aparece más de una vez")
            elif campo not in ("NSocio", "no socio"):
                errores.append(f"Falta la columna obligatoria {campo}")
        if not {"NSocio", "no socio"}.intersection(indices):
            errores.append("Falta una columna de identificación (NSocio o identificación de no socio)")
        return ({} if errores else indices), [Incidencia(linea, error) for error in errores]

    @staticmethod
    def _validarFila(fila, modalidades, niveles, limite):
        obligatorios = ("temporada", "categoría", "nivel", "plazas", "estado", "fecha")
        errores = [f"Falta el dato obligatorio {campo}" for campo in obligatorios if not fila[campo]]
        socio = fila.get("NSocio", "")
        if re.fullmatch(r"[0-9]+", socio):
            socio = socio.lstrip("0") or "0"
        if socio and (not re.fullmatch(r"[0-9]+", socio) or socio == "0"):
            errores.append("NSocio debe ser un número de socio positivo")
        noSocio = normalizarDni(fila.get("no socio"))
        if bool(socio) == bool(noSocio):
            errores.append("Indica un NSocio o una identificación de no socio")

        inicio = anioCurso(fila["temporada"])
        if fila["temporada"] and inicio is None:
            errores.append("La temporada debe indicar un año o un curso")
        elif inicio is not None and inicio >= limite:
            errores.append("La temporada debe ser anterior a la actual")
        modalidad = modalidades.get(claveTexto(fila["categoría"]))
        if fila["categoría"] and modalidad is None:
            errores.append(f"Categoría desconocida: {fila['categoría']}")
        nivel = niveles.get(claveTexto(fila["nivel"]))
        if fila["nivel"] and nivel is None:
            errores.append(f"Nivel desconocido: {fila['nivel']}")
        estado = ESTADOS.get(claveTexto(fila["estado"]))
        if fila["estado"] and estado is None:
            errores.append(f"Estado de solicitud desconocido: {fila['estado']}")
        plazas = None
        if fila["plazas"]:
            try:
                plazas = int(fila["plazas"])
            except ValueError:
                pass
            if plazas is None or not 0 < plazas < 2**63:
                errores.append("Las plazas deben ser un número entero positivo")

        fecha = None
        if fila["fecha"]:
            try:
                textoFecha = fila["fecha"]
                if "/" in textoFecha:
                    fecha = datetime.strptime(textoFecha, "%d/%m/%Y").date()
                else:
                    fecha = date.fromisoformat(textoFecha)
            except ValueError:
                errores.append("Fecha inválida. Usa AAAA-MM-DD o DD/MM/AAAA")

        if errores:
            return None, errores
        return Solicitud(f"{inicio:04d}-{inicio + 1:04d}", modalidad, nivel, plazas,
                         "SOCIO" if socio else "NO_SOCIO", socio or noSocio, estado, fecha.isoformat()), []

    def importar(self, validacion):
        """Importa el contenido validado en una transacción y devuelve (importadas, descartadas)."""
        if not isinstance(validacion, ValidacionHistorica):
            raise HistoricoError("Valida el fichero CSV antes de importarlo.")
        if not validacion.solicitudes:
            raise HistoricoError("El fichero validado no contiene registros válidos para importar.")
        if hashlib.sha256(self._leer(validacion.ruta)).digest() != validacion.huella:
            raise HistoricoError("El fichero ha cambiado. Vuelve a validarlo antes de importarlo.")

        try:
            self.db.executeScript(SCHEMA_HISTORICO_PATH)
            with conectar(self.db.db_path) as conn, conn:
                conn.execute("BEGIN IMMEDIATE")
                temporadas = {s.temporada for s in validacion.solicitudes}
                anteriores = {f[0] for f in conn.execute("SELECT DISTINCT temporada FROM ActividadHistorica")}
                repetidas = sorted(temporadas & anteriores)
                if repetidas:
                    raise HistoricoError(f"Ya se importaron inscripciones de: {', '.join(repetidas)}.")
                ids = {}
                for s in validacion.solicitudes:
                    actividad = (s.temporada, s.modalidad, s.nivel)
                    if actividad not in ids:
                        cursor = conn.execute("""
                            INSERT INTO ActividadHistorica(temporada, idModalidad, idNivel, plazas)
                            VALUES (?, ?, ?, ?)""", (*actividad, s.plazas))
                        ids[actividad] = cursor.lastrowid
                    conn.execute("""
                        INSERT INTO InscripcionHistorica(idActividad, tipo, identificador, estado, fecha)
                        VALUES (?, ?, ?, ?, ?)""",
                                 (ids[actividad], s.tipo, s.identificador, s.estado, s.fecha))
        except (sqlite3.DatabaseError, UnexpectedException) as error:
            raise HistoricoError("No se han podido guardar las inscripciones históricas.") from error
        return len(validacion.solicitudes), validacion.descartadas

    def getTemporadas(self):
        if not self.db.executeQuery("""
            SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ActividadHistorica'
        """):
            return []
        return [fila["temporada"] for fila in self.db.executeQuery("""
            SELECT DISTINCT temporada FROM ActividadHistorica ORDER BY temporada DESC
        """)]

    def consultar(self, temporada, idModalidad=None, idNivel=None):
        """Devuelve las plazas ofertadas y la demanda por categoría y nivel."""
        if not temporada or temporada not in self.getTemporadas():
            return []
        return self.db.executeQuery("""
            SELECT a.idModalidad, a.idNivel, m.nombre AS categoria, n.nombre AS nivel, a.plazas,
                   COUNT(i.id) AS solicitudes,
                   COUNT(CASE WHEN i.estado = 'CONFIRMADA' THEN 1 END) AS inscripciones
            FROM ActividadHistorica a
            JOIN Modalidad m ON m.id = a.idModalidad
            JOIN Nivel n ON n.id = a.idNivel
            LEFT JOIN InscripcionHistorica i ON i.idActividad = a.id
            WHERE a.temporada = ? AND (? IS NULL OR a.idModalidad = ?) AND (? IS NULL OR a.idNivel = ?)
            GROUP BY a.id
            ORDER BY m.nombre COLLATE NOCASE, n.id
        """, temporada, idModalidad, idModalidad, idNivel, idNivel)
