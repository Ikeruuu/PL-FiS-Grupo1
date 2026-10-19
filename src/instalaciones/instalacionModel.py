from src.config import DB_PATH
from src.util.database import Database

DIAS_SEMANA = {1: "lunes", 2: "martes", 3: "miércoles", 4: "jueves",
               5: "viernes", 6: "sábado", 7: "domingo"}


class AsignacionError(Exception):
    '''
    Indica que no se puede asignar la instalación a la actividad porque no se cumple
    alguna regla de negocio de la HU3. El mensaje se muestra tal cual al usuario.
    '''


class InstalacionModel:
    '''
    Objetos de negocio (model) de la HU3 "Asignar una instalación a una actividad".
    Contiene las consultas a la base de datos y las reglas de la historia (capacidad,
    colisiones y una única instalación por actividad). La vista (InstalacionView)
    invoca estos métodos y muestra sus resultados.
    '''

    def __init__(self, db_path=None):
        self.db = Database(db_path if db_path else DB_PATH)

    #Lista de instalaciones registradas
    def getInstalaciones(self):
        query = "select id, nombre, capacidad from Instalacion order by id"
        return self.db.executeQuery(query)

    #Obtiene una instalación por su id (None si no existe)
    def getInstalacion(self, id_instalacion):
        query = "select id, nombre, capacidad from Instalacion where id = ?"
        res = self.db.executeQuery(query, id_instalacion)
        return res[0] if len(res) == 1 else None

    #Número total de actividades registradas
    def countActividades(self):
        return self.db.executeQuery("select count(*) as total from Actividad")[0]["total"]

    #Actividades que todavía no tienen instalación asignada
    def getActividadesSinInstalacion(self):
        query = """select Actividad.id, Modalidad.nombre as modalidad, Nivel.nombre as nivel,
                          Actividad.fechaInicio, Actividad.fechaFin, Actividad.plazas
                   from Actividad
                   inner join Modalidad on Modalidad.id = Actividad.idModalidad
                   inner join Nivel on Nivel.id = Actividad.idNivel
                   where Actividad.idInstalacion is null
                   order by Actividad.id
                """
        return self.db.executeQuery(query)

    #Obtiene una actividad por su id con su modalidad, nivel e instalación (None si no existe)
    def getActividad(self, id_actividad):
        query = """select Actividad.id, Modalidad.nombre as modalidad, Nivel.nombre as nivel,
                          Actividad.fechaInicio, Actividad.fechaFin, Actividad.plazas,
                          Actividad.idInstalacion
                   from Actividad
                   inner join Modalidad on Modalidad.id = Actividad.idModalidad
                   inner join Nivel on Nivel.id = Actividad.idNivel
                   where Actividad.id = ?
                """
        res = self.db.executeQuery(query, id_actividad)
        return res[0] if len(res) == 1 else None

    #Horario semanal de una actividad
    def getHorarios(self, id_actividad):
        query = """select diaSemana, horaInicio, horaFin from Horario
                   where idActividad = ? order by diaSemana, horaInicio
                """
        return self.db.executeQuery(query, id_actividad)

    #Actividades ya asignadas a la instalación que colisionan con la actividad indicada.
    #Hay colisión si coincide el día de la semana, se solapan las franjas horarias y se
    #solapan los periodos de fechas. Las comparaciones estrictas (<) hacen que dos franjas
    #contiguas (una termina a las 18:00 y otra empieza a las 18:00) no colisionen.
    def getColisiones(self, id_actividad, id_instalacion):
        query = """select distinct Otra.id, Modalidad.nombre as modalidad, Nivel.nombre as nivel,
                          HOtra.diaSemana, HOtra.horaInicio, HOtra.horaFin
                   from Actividad Nueva
                   inner join Horario HNueva on HNueva.idActividad = Nueva.id
                   inner join Actividad Otra on Otra.idInstalacion = ? and Otra.id <> Nueva.id
                   inner join Horario HOtra on HOtra.idActividad = Otra.id
                   inner join Modalidad on Modalidad.id = Otra.idModalidad
                   inner join Nivel on Nivel.id = Otra.idNivel
                   where Nueva.id = ?
                     and HNueva.diaSemana = HOtra.diaSemana
                     and HNueva.horaInicio < HOtra.horaFin and HOtra.horaInicio < HNueva.horaFin
                     and Nueva.fechaInicio <= Otra.fechaFin and Otra.fechaInicio <= Nueva.fechaFin
                   order by HOtra.diaSemana, HOtra.horaInicio, Otra.id
                """
        return self.db.executeQuery(query, id_instalacion, id_actividad)

    #Asigna la instalación a la actividad si se cumplen todas las reglas de la HU3.
    #Devuelve el mensaje de éxito o lanza AsignacionError con el motivo.
    def asignarInstalacion(self, id_actividad, id_instalacion):
        actividad = self.getActividad(id_actividad)
        if actividad is None:
            raise AsignacionError(f"No existe la actividad {id_actividad}")
        instalacion = self.getInstalacion(id_instalacion)
        if instalacion is None:
            raise AsignacionError(f"No existe la instalación {id_instalacion}")

        if actividad["idInstalacion"] is not None:
            raise AsignacionError("La actividad ya tiene instalación asignada")

        if actividad["plazas"] > instalacion["capacidad"]:
            raise AsignacionError(
                f"La actividad tiene {actividad['plazas']} plazas y la instalación "
                f"admite {instalacion['capacidad']}")

        colisiones = self.getColisiones(id_actividad, id_instalacion)
        if colisiones:
            detalle = "\n".join(f"  - Colisión con {describirActividad(c)}, "
                                f"{describirFranja(c)}" for c in colisiones)
            raise AsignacionError(
                f"No se puede asignar {instalacion['nombre']}: está ocupada.\n{detalle}")

        query = "update Actividad set idInstalacion = ? where id = ? and idInstalacion is null"
        self.db.executeUpdateQuery(query, id_instalacion, id_actividad)
        return (f"Instalación {instalacion['nombre']} asignada a la actividad "
                f"{describirActividad(actividad)}")


#Texto de una actividad, por ejemplo "Pádel medio"
def describirActividad(actividad):
    return f"{actividad['modalidad']} {actividad['nivel'].lower()}"


#Texto de una franja horaria, por ejemplo "lunes 18:00–19:00"
def describirFranja(franja):
    return f"{DIAS_SEMANA[franja['diaSemana']]} {franja['horaInicio']}–{franja['horaFin']}"
