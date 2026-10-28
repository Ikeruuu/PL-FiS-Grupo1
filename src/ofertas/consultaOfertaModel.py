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
        '''
        Devuelve (lista, mensaje). lista contiene un dict por actividad; mensaje es None si hay
        resultados o el texto a mostrar si no los hay. dias es una colección de días de la
        semana (1=lunes ... 7=domingo) y selecciona las actividades con esa periodicidad exacta.
        '''
        hoy = datetime.date.today() if hoy is None else hoy
        if isinstance(hoy, str):
            hoy = datetime.date.fromisoformat(hoy)
        dias = tuple(sorted(set(dias))) if dias else None

        with conectar(self.db_path) as conn:
            oferta = conn.execute("select * from Oferta where estado = 'ACTIVA'").fetchone()
            abierta = self.abiertaPara(oferta, hoy) if oferta is not None else None
            if abierta is None:
                return [], self.SIN_ABIERTAS

            actividades = conn.execute(
                """select a.*, m.nombre as modalidad, n.nombre as nivel,
                          ins.nombre as instalacion
                   from Actividad a
                   join Modalidad m on m.id = a.idModalidad
                   join Nivel n on n.id = a.idNivel
                   left join Instalacion ins on ins.id = a.idInstalacion
                   where a.idOferta = ? and a.fechaFin >= ?
                   order by m.nombre, a.idNivel, a.id""",
                (oferta["id"], hoy.isoformat())).fetchall()

            resultado = []
            for a in actividades:
                diasA = diasActividad(conn, a["id"])
                if idModalidad is not None and a["idModalidad"] != idModalidad:
                    continue
                if idNivel is not None and a["idNivel"] != idNivel:
                    continue
                if dias is not None and diasA != dias:
                    continue
                libres = max(a["plazas"] - plazasOcupadas(conn, a["id"]), 0)
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
