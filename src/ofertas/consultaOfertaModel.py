import datetime

from src.config import DB_PATH
from src.inscripciones.comun import (
    conectar,
    describirDias,
    describirHorario,
    diasActividad,
    plazasOcupadas,
)


class ConsultaOfertaModel:
    '''
    HU "Consultar la oferta de actividades disponibles" (RedKanban 35334).
    Lista las actividades de la oferta activa que tienen abierto algún periodo de inscripción
    (el de socios o el de no socios) en la fecha indicada, con filtros opcionales por
    modalidad, nivel y periodicidad (días de la semana en que se imparte).
    '''

    SIN_ABIERTAS = "No hay actividades abiertas a inscripción en este momento"
    SIN_RESULTADOS = "Ninguna actividad abierta a inscripción cumple los filtros indicados"

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    #Para quién está abierta la inscripción en la fecha hoy: "socios", "no socios", "ambos" o None
    @staticmethod
    def abiertaPara(oferta, hoy):
        hoy = hoy.isoformat()

        def dentro(inicio, fin):
            return inicio is not None and fin is not None and inicio <= hoy <= fin

        socios = dentro(oferta["inicioInscripcionSocios"], oferta["finInscripcionSocios"])
        noSocios = dentro(oferta["inicioInscripcionNoSocios"], oferta["finInscripcionNoSocios"])
        if socios and noSocios:
            return "ambos"
        if socios:
            return "socios"
        if noSocios:
            return "no socios"
        return None

    #Periodicidades (conjuntos de días) de las actividades de la oferta activa, para el filtro
    def getPeriodicidades(self):
        with conectar(self.db_path) as conn:
            filas = conn.execute(
                """select a.id from Actividad a join Oferta o on o.id = a.idOferta
                   where o.estado = 'ACTIVA'""").fetchall()
            dias = {diasActividad(conn, f["id"]) for f in filas}
        dias.discard(())
        return sorted(dias)


    def consultarOferta(self, idModalidad=None, idNivel=None, dias=None, hoy=None):
        """
        Consulta las actividades de la oferta activa.

        - hoy="TODAS": muestra todas las actividades, sin filtrar por fecha.
        - hoy=None: utiliza la fecha actual.
        - hoy="AAAA-MM-DD": consulta una fecha concreta.
        """

        # Comprobar si se quieren consultar todas las fechas
        todasFechas = (
            isinstance(hoy, str) and hoy.upper() == "TODAS"
        )

        # Preparar la fecha
        if todasFechas:
            hoy = datetime.date.today()
        else:
            hoy = datetime.date.today() if hoy is None else hoy

            if isinstance(hoy, str):
                hoy = datetime.date.fromisoformat(hoy)

        # Filtro opcional de periodicidad
        dias = tuple(sorted(set(dias))) if dias else None

        with conectar(self.db_path) as conn:

            # Obtener la oferta activa
            oferta = conn.execute(
                "SELECT * FROM Oferta WHERE estado = 'ACTIVA'"
            ).fetchone()

            # Si no hay oferta activa, no hay actividades disponibles
            if oferta is None:
                return [], self.SIN_ABIERTAS

            # Comprobar los periodos de inscripción
            if todasFechas:
                abierta = "según periodo"
            else:
                abierta = self.abiertaPara(oferta, hoy)

                if abierta is None:
                    return [], self.SIN_ABIERTAS

            # Consultar las actividades
            actividades = conn.execute(
                """
                SELECT
                    a.*,
                    m.nombre AS modalidad,
                    n.nombre AS nivel,
                    ins.nombre AS instalacion
                FROM Actividad a
                JOIN Modalidad m
                    ON m.id = a.idModalidad
                JOIN Nivel n
                    ON n.id = a.idNivel
                LEFT JOIN Instalacion ins
                    ON ins.id = a.idInstalacion
                WHERE a.idOferta = ?
                AND (? = 1 OR a.fechaFin >= ?)
                ORDER BY m.nombre, a.idNivel, a.id
                """,
                (
                    oferta["id"],
                    int(todasFechas),
                    hoy.isoformat()
                )
            ).fetchall()

            resultado = []

            for a in actividades:

                diasA = diasActividad(conn, a["id"])

                # Filtro de modalidad
                if (
                    idModalidad is not None
                    and a["idModalidad"] != idModalidad
                ):
                    continue

                # Filtro de nivel
                if (
                    idNivel is not None
                    and a["idNivel"] != idNivel
                ):
                    continue

                # Filtro de periodicidad
                if dias is not None and diasA != dias:
                    continue

                # Calcular plazas libres
                libres = max(
                    a["plazas"] - plazasOcupadas(conn, a["id"]),
                    0
                )

                # Añadir la actividad al resultado
                resultado.append({
                    "id": a["id"],
                    "modalidad": a["modalidad"],
                    "nivel": a["nivel"],
                    "periodicidad": describirDias(diasA) or "Sin horario",
                    "horario": describirHorario(conn, a["id"]),
                    "instalacion": a["instalacion"] or "Sin asignar",
                    "cuota": a["cuota"],
                    "plazas": a["plazas"],
                    "libres": libres,
                    "completa": libres == 0,
                    "abiertaPara": abierta,
                })

        # Comprobar si hay actividades
        if not resultado:
            return [], self.SIN_RESULTADOS

        return resultado, None



#"30,00 €" o "No indicada"
def describirCuota(cuota):
    if cuota is None:
        return "No indicada"
    return f"{cuota:.2f} €".replace(".", ",")


#"3 de 12" o "Completa (lista de espera)": la inscripción pasaría a lista de espera
def describirPlazas(actividad):
    if actividad["completa"]:
        return "Completa (lista de espera)"
    return f"{actividad['libres']} de {actividad['plazas']}"
