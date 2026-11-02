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
        import re
        import datetime

        # 1. Comprobar que se ha indicado el curso
        if not curso or not curso.strip():
            raise OfertaError("El curso es obligatorio")

        curso = curso.strip()

        # 2. Validar el formato del curso
        # Se aceptan "2026" y "2026-2027"
        if re.fullmatch(r"[0-9]{4}", curso):
            anioInicio = int(curso)
            anioFin = anioInicio + 1

        elif re.fullmatch(r"[0-9]{4}-[0-9]{4}", curso):
            anioInicio, anioFin = map(int, curso.split("-"))

            if anioFin != anioInicio + 1:
                raise OfertaError(
                    "El segundo año del curso debe ser "
                    "el siguiente al primero"
                )
        else:
            raise OfertaError(
                "El curso debe tener formato AAAA o AAAA-AAAA"
            )

        # 3. Proponer fechas por defecto si no se indican
        if fechaInicio is None and fechaFin is None:
            fechaInicio = f"{anioInicio}-10-01"
            fechaFin = f"{anioFin}-06-30"

        # 4. Comprobar campos obligatorios
        if not fechaInicio or not fechaFin:
            raise OfertaError(
                "Las fechas de inicio y fin son obligatorias"
            )

        # 5. Comprobar que las fechas son reales
        try:
            inicio = datetime.date.fromisoformat(fechaInicio)
            fin = datetime.date.fromisoformat(fechaFin)
        except (ValueError, TypeError):
            raise OfertaError(
                "Las fechas deben tener formato AAAA-MM-DD "
                "y ser válidas"
            )

        # 6. La fecha final debe ser posterior a la inicial
        if fin <= inicio:
            raise OfertaError(
                "La fecha de fin debe ser posterior "
                "a la de inicio"
            )

        # 7. Comprobar que no existe otra oferta activa
        activas = self.db.executeQuery(
            "SELECT COUNT(*) AS n FROM Oferta WHERE estado = 'ACTIVA'"
        )

        if activas[0]["n"] > 0:
            raise OfertaError("Ya existe una oferta activa")

        # 8. Guardar la nueva oferta
        self.db.executeUpdateQuery(
            """
            INSERT INTO Oferta
            (curso, fechaInicio, fechaFin, estado)
            VALUES (?, ?, ?, 'ACTIVA')
            """,
            curso,
            inicio.isoformat(),
            fin.isoformat()
        )

        # 9. Mostrar confirmación
        return (
            f"Oferta {curso} creada "
            f"({inicio.isoformat()} a {fin.isoformat()})"
        )

    #HU2: define los periodos de inscripción de socios y no socios de una oferta.

    def definirPeriodos(self, idOferta, inicioSocios, finSocios,
                        inicioNoSocios, finNoSocios):

        oferta = self.getOferta(idOferta)

        if oferta is None:
            raise OfertaError(f"No existe la oferta {idOferta}")

        # No se pueden redefinir periodos ya guardados.
        if oferta["inicioInscripcionSocios"] is not None:
            raise OfertaError(
                "La oferta ya tiene periodos de inscripción definidos"
            )

        # Comprobar que todas las fechas son obligatorias.
        fechas = {
            "Inicio socios": inicioSocios,
            "Fin socios": finSocios,
            "Inicio no socios": inicioNoSocios,
            "Fin no socios": finNoSocios
        }

        for nombre, valor in fechas.items():
            if not valor or not valor.strip():
                raise OfertaError(f"El campo {nombre} es obligatorio")

            try:
                datetime.date.fromisoformat(valor)
            except ValueError:
                raise OfertaError(
                    f"Fecha incorrecta en {nombre}. Usa AAAA-MM-DD"
                )

        # Comprobar orden de cada periodo.
        if inicioSocios > finSocios:
            raise OfertaError(
                "El inicio del periodo de socios no puede "
                "ser posterior a su fin"
            )

        if inicioNoSocios > finNoSocios:
            raise OfertaError(
                "El inicio del periodo de no socios no puede "
                "ser posterior a su fin"
            )

        # Los periodos no pueden solaparse.
        if finSocios >= inicioNoSocios:
            raise OfertaError(
                "El periodo de socios debe ser anterior "
                "al de no socios, sin solape"
            )

        # Ambos deben terminar antes de comenzar la oferta.
        if finNoSocios >= oferta["fechaInicio"]:
            raise OfertaError(
                "Los periodos deben finalizar antes "
                "del inicio de la oferta"
            )

        self.db.executeUpdateQuery(
            """UPDATE Oferta
            SET inicioInscripcionSocios = ?,
                finInscripcionSocios = ?,
                inicioInscripcionNoSocios = ?,
                finInscripcionNoSocios = ?
            WHERE id = ?""",
            inicioSocios, finSocios,
            inicioNoSocios, finNoSocios, idOferta
        )

        return "Periodos de inscripción definidos correctamente"


    def getOferta(self, idOferta):
        filas = self.db.executeQuery("select * from Oferta where id = ?", idOferta)
        return filas[0] if filas else None

    def getOfertaActiva(self):
        filas = self.db.executeQuery("select * from Oferta where estado = 'ACTIVA'")
        return filas[0] if filas else None