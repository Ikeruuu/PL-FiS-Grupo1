from src.util.database import Database


class ActividadError(Exception):
    pass


class ActividadModel:

    #Categorías y niveles fijos del cliente (coinciden con data.sql)
    MODALIDADES = {1: 'Natación', 2: 'Pilates', 3: 'Acondicionamiento físico general',
                   4: 'Pádel', 5: 'Tenis'}
    NIVELES = {1: 'Iniciación', 2: 'Medio', 3: 'Avanzado'}

    def __init__(self, db_path=None):
        self.db = Database(db_path) if db_path else Database()

    #HU3: añade una actividad a la oferta actual, con su periodicidad (horarios) y plazas.
    #horarios es una lista de tuplas (diaSemana, horaInicio, horaFin).
    def anadirActividad(self, idOferta, idModalidad, idNivel, fechaInicio, fechaFin, plazas, horarios):
        oferta = self.db.executeQuery("select * from Oferta where id = ?", idOferta)
        if not oferta:
            raise ActividadError(f"No existe la oferta {idOferta}")

        if idModalidad not in self.MODALIDADES:
            raise ActividadError("Modalidad no válida")
        if idNivel not in self.NIVELES:
            raise ActividadError("Nivel no válido")

        if plazas <= 0:
            raise ActividadError("Las plazas deben ser mayores que 0")

        if not horarios:
            raise ActividadError("Debe indicarse al menos un horario")

        for dia, inicio, fin in horarios:
            if not (1 <= dia <= 7):
                raise ActividadError(f"Día de la semana no válido: {dia}")
            if not ('08:00' <= inicio < fin <= '22:00'):
                raise ActividadError(f"Horario fuera de rango o incoherente: {inicio}-{fin}")

        self.db.executeUpdateQuery(
            """insert into Actividad (idOferta, idModalidad, idNivel, fechaInicio, fechaFin, plazas)
            values (?, ?, ?, ?, ?, ?)""",
            idOferta, idModalidad, idNivel, fechaInicio, fechaFin, plazas)

        idActividad = self.db.executeQuery(
            """select max(id) as id from Actividad
            where idOferta = ? and idModalidad = ? and idNivel = ? and fechaInicio = ? and fechaFin = ?""",
            idOferta, idModalidad, idNivel, fechaInicio, fechaFin)[0]["id"]

        for dia, inicio, fin in horarios:
            self.db.executeUpdateQuery(
                "insert into Horario (idActividad, diaSemana, horaInicio, horaFin) values (?, ?, ?, ?)",
                idActividad, dia, inicio, fin)

        return f"Actividad {self.MODALIDADES[idModalidad]} {self.NIVELES[idNivel]} añadida"

    def getActividad(self, idActividad):
        filas = self.db.executeQuery("select * from Actividad where id = ?", idActividad)
        return filas[0] if filas else None