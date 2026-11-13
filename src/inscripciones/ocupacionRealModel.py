'''
HU18 "Comparar la ocupación planificada con la real".

Para cada actividad (con su instalación) en un periodo se comparan los inscritos (ocupación planificada)
con la asistencia media de las sesiones registradas (ocupación real). La diferencia se calcula como
(inscritos - asistencia media) / inscritos * 100 y se destacan las actividades con una diferencia igual o
superior al umbral (50 %, provisional según el PO). Usa el resumen de asistencia de la HU17.
'''
import datetime

from src.config import DB_PATH
from src.inscripciones.asistenciaModel import AsistenciaModel, porcentaje
from src.util.database import Database

#Umbral provisional validado con el PO: diferencia a partir de la cual se destaca una actividad
UMBRAL_DIFERENCIA = 50


class OcupacionRealError(Exception):
    '''Error de la HU18. El mensaje se muestra tal cual al usuario.'''


def diferencia(inscritos, mediaAsistentes):
    if not inscritos or mediaAsistentes is None:
        return None
    return round(100 * (inscritos - mediaAsistentes) / inscritos)


class OcupacionRealModel:

    def __init__(self, db_path=None, hoyFijo=None):
        self.db = Database(db_path if db_path else DB_PATH)
        self.asistencia = AsistenciaModel(db_path, hoyFijo)

    def getInstalaciones(self):
        return self.db.executeQuery("select id, nombre from Instalacion order by id")

    def getActividades(self):
        return self.db.executeQuery("""select a.id, m.nombre as modalidad, n.nombre as nivel
                                       from Actividad a
                                       inner join Oferta o on o.id = a.idOferta and o.estado = 'ACTIVA'
                                       inner join Modalidad m on m.id = a.idModalidad
                                       inner join Nivel n on n.id = a.idNivel
                                       order by m.nombre, a.idNivel, a.id""")

    #Periodo por defecto: el curso de la oferta activa
    def periodoPorDefecto(self):
        filas = self.db.executeQuery("select fechaInicio, fechaFin from Oferta where estado = 'ACTIVA'")
        if not filas:
            raise OcupacionRealError("No hay una oferta activa")
        return filas[0]["fechaInicio"], filas[0]["fechaFin"]

    def getInforme(self, desde=None, hasta=None, idInstalacion=None, idActividad=None, hoy=None):
        if desde is None or hasta is None:
            desde, hasta = self.periodoPorDefecto()
        for fecha in (desde, hasta):
            try:
                datetime.date.fromisoformat(fecha)
            except ValueError as error:
                raise OcupacionRealError("Las fechas deben tener el formato AAAA-MM-DD") from error
        if desde > hasta:
            raise OcupacionRealError("Fechas incoherentes: la fecha de inicio es posterior a la de fin")

        condiciones, argumentos = ["a.fechaInicio <= ?", "a.fechaFin >= ?"], [hasta, desde]
        if idInstalacion is not None:
            condiciones.append("a.idInstalacion = ?")
            argumentos.append(idInstalacion)
        if idActividad is not None:
            condiciones.append("a.id = ?")
            argumentos.append(idActividad)
        actividades = self.db.executeQuery(f"""
            select a.id, m.nombre as modalidad, n.nombre as nivel, a.plazas, a.idInstalacion,
                   coalesce(i.nombre, 'Sin instalación') as instalacion,
                   (select count(*) from Inscripcion x where x.idActividad = a.id
                      and x.estado = 'CONFIRMADA') as inscritos
            from Actividad a
            inner join Modalidad m on m.id = a.idModalidad
            inner join Nivel n on n.id = a.idNivel
            left join Instalacion i on i.id = a.idInstalacion
            where {" and ".join(condiciones)}""", *argumentos)
        if not actividades:
            raise OcupacionRealError("No hay actividades en el periodo indicado")

        filas = []
        for a in actividades:
            r = self.asistencia.getResumen(a["id"], hoy, desde, hasta)
            media = r["mediaAsistentes"]
            dif = diferencia(a["inscritos"], media)
            filas.append({**a,
                          "planificada": porcentaje(a["inscritos"], a["plazas"]),
                          "mediaAsistentes": media,
                          "realSobrePlazas": None if media is None else porcentaje(media, a["plazas"]),
                          "realSobreInscritos": None if media is None else porcentaje(media, a["inscritos"]),
                          "diferencia": dif,
                          "sesionesRegistradas": r["registradas"], "sesionesTotales": r["totales"],
                          "sinDatos": r["registradas"] == 0,
                          "destacada": dif is not None and dif >= UMBRAL_DIFERENCIA})
        #De mayor a menor diferencia; las que no tienen datos, al final
        filas.sort(key=lambda f: (f["sinDatos"], f["diferencia"] is None, -(f["diferencia"] or 0), f["id"]))
        return {"desde": desde, "hasta": hasta, "actividades": filas, "totales": self._totales(filas)}

    #Totales por instalación de las actividades con datos de asistencia
    @staticmethod
    def _totales(filas):
        totales = {}
        for f in filas:
            if f["sinDatos"]:
                continue
            t = totales.setdefault(f["instalacion"], {"instalacion": f["instalacion"], "plazas": 0,
                                                     "inscritos": 0, "mediaAsistentes": 0.0})
            t["plazas"] += f["plazas"]
            t["inscritos"] += f["inscritos"]
            t["mediaAsistentes"] += f["mediaAsistentes"]
        for t in totales.values():
            t["planificada"] = porcentaje(t["inscritos"], t["plazas"])
            t["realSobrePlazas"] = porcentaje(t["mediaAsistentes"], t["plazas"])
            t["diferencia"] = diferencia(t["inscritos"], t["mediaAsistentes"])
        return sorted(totales.values(), key=lambda t: t["instalacion"])
