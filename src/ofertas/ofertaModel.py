import datetime

from src.util.database import Database
from src.config import DB_PATH


class OfertaError(Exception):
    pass


class OfertaModel:

    def __init__(self, db_path=None):
        self.db = Database(DB_PATH if db_path is None else db_path)

    #HU4: crea la oferta de un curso. Si no se indican fechas, usa octubre->junio del curso.
    def crearOferta(self, curso, fechaInicio=None, fechaFin=None):
        if not curso or not curso.strip():
            raise OfertaError("El curso es obligatorio")

        if fechaInicio is None or fechaFin is None:
            anioInicio = int(curso.split('-')[0])
            fechaInicio = f"{anioInicio}-10-01"
            fechaFin = f"{anioInicio + 1}-06-30"

        activas = self.db.executeQuery(
            "select count(*) as n from Oferta where estado = 'ACTIVA'")
        if activas[0]["n"] > 0:
            raise OfertaError("Ya existe una oferta activa")

        self.db.executeUpdateQuery(
            "insert into Oferta (curso, fechaInicio, fechaFin, estado) values (?, ?, ?, 'ACTIVA')",
            curso.strip(), fechaInicio, fechaFin)

        return f"Oferta {curso} creada ({fechaInicio} a {fechaFin})"

    #HU2: define los periodos de inscripción de socios y no socios de una oferta.
    def definirPeriodos(self, idOferta, inicioSocios, finSocios, inicioNoSocios, finNoSocios):
        oferta = self.getOferta(idOferta)
        if oferta is None:
            raise OfertaError(f"No existe la oferta {idOferta}")

        if oferta["inicioInscripcionSocios"] is not None:
            raise OfertaError("La oferta ya tiene periodos de inscripción definidos")

        if finSocios >= inicioNoSocios:
            raise OfertaError("El periodo de socios debe ser anterior al de no socios, sin solape")

        if finNoSocios >= oferta["fechaInicio"]:
            raise OfertaError("Los periodos deben finalizar antes del inicio de la oferta")

        self.db.executeUpdateQuery(
            """update Oferta set inicioInscripcionSocios = ?, finInscripcionSocios = ?,
               inicioInscripcionNoSocios = ?, finInscripcionNoSocios = ? where id = ?""",
            inicioSocios, finSocios, inicioNoSocios, finNoSocios, idOferta)

        return "Periodos de inscripción definidos correctamente"

    def getOferta(self, idOferta):
        filas = self.db.executeQuery("select * from Oferta where id = ?", idOferta)
        return filas[0] if filas else None

    def getOfertaActiva(self):
        filas = self.db.executeQuery("select * from Oferta where estado = 'ACTIVA'")
        return filas[0] if filas else None