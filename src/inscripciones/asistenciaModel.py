'''
HU17 "Registrar y consultar la asistencia a cada sesión".

Una sesión es una fecha concreta del horario semanal de una actividad dentro de su periodo
(por ejemplo, el lunes 12/10/2026 de 18:00 a 19:00). No se guardan como tabla: se calculan a partir
de Horario y de las fechas de la actividad. Se guarda la asistencia de cada inscrito (S/N) y las
sesiones canceladas por causa de fuerza mayor.
'''
import datetime

from src.config import DB_PATH
from src.instalaciones.instalacionModel import DIAS_SEMANA
from src.util.database import Database

#Estados de una sesión
REGISTRADA, SIN_REGISTRAR, CANCELADA, FUTURA = "Registrada", "Sin registrar", "Cancelada", "Futura"


class AsistenciaError(Exception):
    '''Error de la HU17. El mensaje se muestra tal cual al usuario.'''


def porcentaje(parte, total):
    return round(100 * parte / total) if total else None


#"2026-10-12" -> "lunes 12/10/2026"
def describirFecha(fecha):
    d = datetime.date.fromisoformat(fecha)
    return f"{DIAS_SEMANA[d.isoweekday()]} {d.strftime('%d/%m/%Y')}"


class AsistenciaModel:

    #hoyFijo permite fijar la fecha de "hoy" (pruebas o demostración); por defecto es la fecha real
    def __init__(self, db_path=None, hoyFijo=None):
        self.db = Database(db_path if db_path else DB_PATH)
        self.hoyFijo = hoyFijo

    def _hoy(self, hoy):
        return hoy if hoy else self.hoyFijo if self.hoyFijo else datetime.date.today()

    def getActividad(self, idActividad):
        filas = self.db.executeQuery("""select a.id, a.fechaInicio, a.fechaFin, a.plazas, a.idInstalacion,
                                               m.nombre as modalidad, n.nombre as nivel
                                        from Actividad a
                                        inner join Modalidad m on m.id = a.idModalidad
                                        inner join Nivel n on n.id = a.idNivel
                                        where a.id = ?""", idActividad)
        return filas[0] if filas else None

    #Actividades de la oferta activa, para elegir en la pantalla
    def getActividadesOfertaActiva(self):
        return self.db.executeQuery("""select a.id, m.nombre as modalidad, n.nombre as nivel
                                       from Actividad a
                                       inner join Oferta o on o.id = a.idOferta and o.estado = 'ACTIVA'
                                       inner join Modalidad m on m.id = a.idModalidad
                                       inner join Nivel n on n.id = a.idNivel
                                       order by m.nombre, a.idNivel, a.id""")

    #Inscritos confirmados en este momento (sin lista de espera ni cancelados)
    def getInscritos(self, idActividad):
        return self.db.executeQuery("""select i.id as idInscripcion, p.dni, p.nombre, p.apellidos
                                       from Inscripcion i inner join Persona p on p.id = i.idPersona
                                       where i.idActividad = ? and i.estado = 'CONFIRMADA'
                                       order by p.apellidos, p.nombre""", idActividad)

    #Todas las sesiones del calendario de la actividad, ordenadas, con su estado y su asistencia
    def getSesiones(self, idActividad, hoy=None, desde=None, hasta=None):
        actividad = self.getActividad(idActividad)
        if actividad is None:
            raise AsistenciaError(f"No existe la actividad {idActividad}")
        hoy = self._hoy(hoy).isoformat()
        horarios = self.db.executeQuery("select diaSemana, horaInicio, horaFin from Horario where idActividad = ?",
                                        idActividad)
        inicio = datetime.date.fromisoformat(max(actividad["fechaInicio"], desde or actividad["fechaInicio"]))
        fin = datetime.date.fromisoformat(min(actividad["fechaFin"], hasta or actividad["fechaFin"]))

        canceladas = {(c["fecha"], c["horaInicio"]) for c in self.db.executeQuery(
            "select fecha, horaInicio from SesionCancelada where idActividad = ?", idActividad)}
        registros = {(r["fecha"], r["horaInicio"]): r for r in self.db.executeQuery(
            """select a.fecha, a.horaInicio, count(*) as registrados, sum(a.asistio) as asistentes
               from Asistencia a inner join Inscripcion i on i.id = a.idInscripcion
               where i.idActividad = ? group by a.fecha, a.horaInicio""", idActividad)}

        sesiones = []
        for h in horarios:
            dia = inicio + datetime.timedelta(days=(h["diaSemana"] - inicio.isoweekday()) % 7)
            while dia <= fin:
                fecha = dia.isoformat()
                clave = (fecha, h["horaInicio"])
                registro = registros.get(clave)
                if clave in canceladas:
                    estado = CANCELADA
                elif registro is not None:
                    estado = REGISTRADA
                elif fecha > hoy:
                    estado = FUTURA
                else:
                    estado = SIN_REGISTRAR
                asistentes = registro["asistentes"] if registro and estado == REGISTRADA else None
                inscritos = registro["registrados"] if registro and estado == REGISTRADA else None
                sesiones.append({"fecha": fecha, "horaInicio": h["horaInicio"], "horaFin": h["horaFin"],
                                 "estado": estado, "asistentes": asistentes, "inscritos": inscritos,
                                 "porcentaje": porcentaje(asistentes, inscritos) if inscritos else
                                 (0 if inscritos == 0 else None)})
                dia += datetime.timedelta(days=7)
        return sorted(sesiones, key=lambda s: (s["fecha"], s["horaInicio"]))

    #Sesiones de hoy o pasadas (las que se pueden registrar o consultar)
    def getSesionesHastaHoy(self, idActividad, hoy=None):
        hoy = self._hoy(hoy)
        sesiones = [s for s in self.getSesiones(idActividad, hoy) if s["fecha"] <= hoy.isoformat()]
        if not sesiones:
            raise AsistenciaError("La actividad aún no ha tenido sesiones")
        return sesiones

    def _buscarSesion(self, idActividad, fecha, horaInicio, hoy):
        sesion = next((s for s in self.getSesiones(idActividad, hoy)
                       if s["fecha"] == fecha and s["horaInicio"] == horaInicio), None)
        if sesion is None:
            raise AsistenciaError(f"La actividad no tiene sesión el {fecha} a las {horaInicio}")
        return sesion

    #Inscritos de la sesión con lo registrado (asistio = True/False, o None si aún no se registró)
    def getHojaAsistencia(self, idActividad, fecha, horaInicio, hoy=None):
        sesion = self._buscarSesion(idActividad, fecha, horaInicio, hoy)
        if sesion["estado"] == FUTURA:
            raise AsistenciaError("No se puede registrar asistencia de una sesión futura")
        if sesion["estado"] == CANCELADA:
            raise AsistenciaError("La sesión está cancelada: no se registra asistencia")
        inscritos = self.getInscritos(idActividad)
        if not inscritos:
            raise AsistenciaError("No hay inscritos en esta actividad")
        marcados = {r["idInscripcion"]: bool(r["asistio"]) for r in self.db.executeQuery(
            """select a.idInscripcion, a.asistio from Asistencia a
               inner join Inscripcion i on i.id = a.idInscripcion
               where i.idActividad = ? and a.fecha = ? and a.horaInicio = ?""", idActividad, fecha, horaInicio)}
        for p in inscritos:
            p["asistio"] = marcados.get(p["idInscripcion"])
        return inscritos

    #Registra (o corrige) la asistencia de una sesión. asistencias: {idInscripcion: True/False}.
    #Los inscritos que no aparezcan se guardan como "no asistió".
    def registrarAsistencia(self, idActividad, fecha, horaInicio, asistencias, hoy=None):
        inscritos = self.getHojaAsistencia(idActividad, fecha, horaInicio, hoy)
        ids = {p["idInscripcion"] for p in inscritos}
        ajenos = set(asistencias) - ids
        if ajenos:
            raise AsistenciaError("Solo se puede registrar la asistencia de personas inscritas en la actividad")
        corrige = any(p["asistio"] is not None for p in inscritos)
        ahora = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        with self.db._connect() as (conn, curs):
            curs.executemany("""insert or replace into Asistencia(idInscripcion, fecha, horaInicio, asistio, fechaRegistro)
                                values (?, ?, ?, ?, ?)""",
                             [(i, fecha, horaInicio, 1 if asistencias.get(i) else 0, ahora) for i in sorted(ids)])
            conn.commit()
        asistentes = sum(1 for i in ids if asistencias.get(i))
        return (f"Asistencia {'corregida' if corrige else 'registrada'}: {describirFecha(fecha)} {horaInicio}, "
                f"{asistentes} de {len(ids)} ({porcentaje(asistentes, len(ids))} %)")

    #Cancela una sesión por causa de fuerza mayor. Es definitivo.
    def cancelarSesion(self, idActividad, fecha, horaInicio, hoy=None):
        sesion = self._buscarSesion(idActividad, fecha, horaInicio, hoy)
        if sesion["estado"] == CANCELADA:
            raise AsistenciaError("La sesión ya está cancelada")
        if sesion["estado"] == REGISTRADA:
            raise AsistenciaError("La sesión ya tiene asistencia registrada: no se puede cancelar")
        self.db.executeUpdateQuery("""insert into SesionCancelada(idActividad, fecha, horaInicio, fechaCancelacion)
                                      values (?, ?, ?, ?)""", idActividad, fecha, horaInicio,
                                   datetime.datetime.now().isoformat(sep=" ", timespec="seconds"))
        return f"Sesión del {describirFecha(fecha)} {horaInicio} cancelada"

    #Resumen de la actividad: sesiones hasta hoy y media de asistencia de las registradas
    def getResumen(self, idActividad, hoy=None, desde=None, hasta=None):
        hoy = self._hoy(hoy)
        sesiones = [s for s in self.getSesiones(idActividad, hoy, desde, hasta) if s["fecha"] <= hoy.isoformat()]
        registradas = [s for s in sesiones if s["estado"] == REGISTRADA]
        validas = [s for s in sesiones if s["estado"] != CANCELADA]
        media = (sum(s["asistentes"] for s in registradas) / len(registradas)) if registradas else None
        mediaPct = (sum(s["porcentaje"] for s in registradas) / len(registradas)) if registradas else None
        return {"sesiones": sesiones, "registradas": len(registradas), "totales": len(validas),
                "canceladas": sum(1 for s in sesiones if s["estado"] == CANCELADA),
                "mediaAsistentes": media, "mediaPorcentaje": None if mediaPct is None else round(mediaPct)}
