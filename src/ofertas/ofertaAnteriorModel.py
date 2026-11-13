import datetime

from src.config import DB_PATH
from src.instalaciones.instalacionModel import DIAS_SEMANA
from src.ofertas.actividadModel import ActividadError, ActividadModel
from src.util.database import Database


class OfertaAnteriorError(Exception):
    '''Error de la HU16. El mensaje se muestra tal cual al usuario.'''


#Texto de la periodicidad, por ejemplo "lunes, miércoles 18:00–19:00"
def describirPeriodicidad(dias, horaInicio, horaFin):
    return f"{', '.join(DIAS_SEMANA[d] for d in sorted(dias))} {horaInicio}–{horaFin}"


class OfertaAnteriorModel:
    '''
    Objetos de negocio de la HU16 "Añadir a la oferta actual una actividad de la oferta anterior".
    Amplía la HU "Añadir una actividad" (#35263): reutiliza ActividadModel.anadirActividad, de
    modo que las validaciones (modalidades, niveles, plazas, horario) son las mismas.
    '''

    def __init__(self, db_path=None):
        self.db = Database(db_path if db_path else DB_PATH)
        self.actividades = ActividadModel(db_path)

    def getOfertaActiva(self):
        filas = self.db.executeQuery("select * from Oferta where estado = 'ACTIVA'")
        return filas[0] if filas else None

    #Oferta de la temporada anterior: la última oferta inactiva que termina antes de la actual
    def getOfertaAnterior(self, ofertaActiva=None):
        actual = ofertaActiva if ofertaActiva else self.getOfertaActiva()
        if actual is None:
            return None
        filas = self.db.executeQuery("""select * from Oferta
                                        where estado = 'INACTIVA' and fechaFin < ?
                                        order by fechaFin desc limit 1""", actual["fechaInicio"])
        return filas[0] if filas else None

    #Las inscripciones de una oferta están abiertas desde el inicio del periodo de socios
    @staticmethod
    def inscripcionesAbiertas(oferta, hoy=None):
        hoy = (hoy if hoy else datetime.date.today()).isoformat()
        inicio = oferta["inicioInscripcionSocios"]
        return inicio is not None and hoy >= inicio

    #Comprueba que se puede añadir y devuelve (oferta actual, oferta anterior)
    def comprobarDisponible(self, hoy=None):
        actual = self.getOfertaActiva()
        if actual is None:
            raise OfertaAnteriorError("No hay una oferta activa a la que añadir actividades")
        if self.inscripcionesAbiertas(actual, hoy):
            raise OfertaAnteriorError(
                "Las inscripciones de la oferta actual ya están abiertas: no se pueden añadir actividades")
        anterior = self.getOfertaAnterior(actual)
        if anterior is None:
            raise OfertaAnteriorError("No hay oferta de la temporada anterior")
        return actual, anterior

    #Actividades de una oferta con su periodicidad y su demanda (inscritos, espera, ocupación)
    def getActividadesConDemanda(self, idOferta):
        actividades = self.db.executeQuery("""
            select a.id, a.idModalidad, a.idNivel, m.nombre as modalidad, n.nombre as nivel, a.plazas,
                   i.nombre as instalacion,
                   (select count(*) from Inscripcion x where x.idActividad = a.id
                      and x.estado = 'CONFIRMADA') as inscritos,
                   (select count(*) from Inscripcion x where x.idActividad = a.id
                      and x.estado = 'EN_ESPERA') as espera,
                   (select count(*) from Inscripcion x where x.idActividad = a.id) as solicitudes
            from Actividad a
            inner join Modalidad m on m.id = a.idModalidad
            inner join Nivel n on n.id = a.idNivel
            left join Instalacion i on i.id = a.idInstalacion
            where a.idOferta = ?
            order by m.nombre, a.idNivel, a.id""", idOferta)
        for a in actividades:
            horarios = self.db.executeQuery("""select diaSemana, horaInicio, horaFin from Horario
                                               where idActividad = ? order by diaSemana""", a["id"])
            a["dias"] = [h["diaSemana"] for h in horarios]
            a["horaInicio"] = horarios[0]["horaInicio"] if horarios else None
            a["horaFin"] = horarios[0]["horaFin"] if horarios else None
            a["ocupacion"] = round(100 * a["inscritos"] / a["plazas"]) if a["plazas"] else 0
            a["sinDatos"] = a["solicitudes"] == 0
        return actividades

    #Añade a la oferta actual una copia de una actividad de la oferta anterior. Se pueden cambiar
    #las plazas y la periodicidad (días, hora de inicio y fin, la misma para todos los días).
    #La actividad se registra sin instalación y la de la oferta anterior no se modifica.
    def anadirDesdeAnterior(self, idActividadAnterior, plazas=None, dias=None, horaInicio=None,
                            horaFin=None, hoy=None):
        actual, anterior = self.comprobarDisponible(hoy)
        origen = next((a for a in self.getActividadesConDemanda(anterior["id"])
                       if a["id"] == idActividadAnterior), None)
        if origen is None:
            raise OfertaAnteriorError(
                f"La actividad {idActividadAnterior} no pertenece a la oferta {anterior['curso']}")

        plazas = origen["plazas"] if plazas is None else plazas
        dias = origen["dias"] if dias is None else sorted(set(dias))
        horaInicio = origen["horaInicio"] if horaInicio is None else horaInicio
        horaFin = origen["horaFin"] if horaFin is None else horaFin
        if not dias:
            raise OfertaAnteriorError("Hay que indicar al menos un día de la semana")

        try:
            self.actividades.anadirActividad(actual["id"], origen["idModalidad"], origen["idNivel"],
                                             actual["fechaInicio"], actual["fechaFin"], plazas,
                                             [(d, horaInicio, horaFin) for d in dias])
        except ActividadError as error:
            raise OfertaAnteriorError(str(error)) from error

        idNueva = self.db.executeQuery("select max(id) as id from Actividad where idOferta = ?",
                                       actual["id"])[0]["id"]
        return {"id": idNueva, "modalidad": origen["modalidad"], "nivel": origen["nivel"],
                "plazas": plazas, "dias": dias, "horaInicio": horaInicio, "horaFin": horaFin,
                "fechaInicio": actual["fechaInicio"], "fechaFin": actual["fechaFin"],
                "curso": actual["curso"],
                "mensaje": (f"Actividad {origen['modalidad']} {origen['nivel'].lower()} añadida a la oferta "
                            f"{actual['curso']}: {describirPeriodicidad(dias, horaInicio, horaFin)}, "
                            f"{plazas} plazas, del {actual['fechaInicio']} al {actual['fechaFin']}")}
