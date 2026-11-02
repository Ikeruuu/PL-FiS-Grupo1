from src.util.database import Database
from src.config import DB_PATH
from datetime import date

class ActividadError(Exception):
    pass


class ActividadModel:

    #Categorías y niveles fijos del cliente (coinciden con data.sql)
    MODALIDADES = {1: 'Natación', 2: 'Pilates', 3: 'Acondicionamiento físico general',
                   4: 'Pádel', 5: 'Tenis'}
    NIVELES = {1: 'Iniciación', 2: 'Medio', 3: 'Avanzado'}

    def __init__(self, db_path=None):
        self.db = Database(DB_PATH if db_path is None else db_path)


        
    def _validarFechas(self, idOferta, fechaInicio, fechaFin):
        # Obtener el periodo de la oferta.
        filas = self.db.executeQuery(
            "SELECT fechaInicio, fechaFin FROM Oferta WHERE id = ?",
            idOferta
        )

        if not filas:
            raise ActividadError(f"No existe la oferta {idOferta}")

        # Validar que las fechas existen y tienen formato correcto.
        try:
            inicio = date.fromisoformat(fechaInicio)
            fin = date.fromisoformat(fechaFin)
        except (ValueError, TypeError):
            raise ActividadError(
                "Las fechas deben ser válidas y tener formato AAAA-MM-DD"
            )

        # Validar orden cronológico.
        if inicio > fin:
            raise ActividadError(
                "La fecha de inicio no puede ser posterior a la de fin"
            )

        inicioOferta = date.fromisoformat(filas[0]["fechaInicio"])
        finOferta = date.fromisoformat(filas[0]["fechaFin"])

        # La actividad debe estar dentro del periodo de la oferta.
        if inicio < inicioOferta or fin > finOferta:
            raise ActividadError(
                "Las fechas de la actividad deben estar "
                "dentro del periodo de la oferta"
            )


    #HU3: añade una actividad a la oferta actual, con su periodicidad (horarios) y plazas.
    #horarios es una lista de tuplas (diaSemana, horaInicio, horaFin).
    def anadirActividad(self, idOferta, idModalidad, idNivel, fechaInicio, fechaFin, plazas, horarios):
        oferta = self.db.executeQuery("select * from Oferta where id = ?", idOferta)
        if not oferta:
            raise ActividadError(f"No existe la oferta {idOferta}")

        self._validarFechas(idOferta, fechaInicio, fechaFin)

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


    #HU1: modifica una actividad existente (categoria, nivel, horarios, instalacion, plazas)
    def modificarActividad(self, idActividad, idModalidad, idNivel, fechaInicio, fechaFin,
                           plazas, horarios, plazasOcupadas=0):
        actividad = self.getActividad(idActividad)
        if actividad is None:
            raise ActividadError(f"No existe la actividad {idActividad}")

        self._validarFechas(
            actividad["idOferta"],
            fechaInicio,
            fechaFin
        )
        
        if idModalidad not in self.MODALIDADES:
            raise ActividadError("Modalidad no válida")
        if idNivel not in self.NIVELES:
            raise ActividadError("Nivel no válido")

                
        if plazas <= 0:
            raise ActividadError("Las plazas deben ser mayores que 0")

        # Consultar cuántas personas ocupan plaza realmente.
        # CONFIRMADA y PENDIENTE_ACEPTACION ocupan plaza.
        resultado = self.db.executeQuery(
            """
            SELECT COUNT(*) AS total
            FROM Inscripcion
            WHERE idActividad = ?
            AND estado IN ('CONFIRMADA', 'PENDIENTE_ACEPTACION')
            """,
            idActividad
        )

        plazasOcupadasReales = resultado[0]["total"]

        # Impedir reducir las plazas por debajo de las ocupadas.
        if plazas < plazasOcupadasReales:
            raise ActividadError(
                f"Las plazas ({plazas}) no pueden ser inferiores "
                f"a las personas ya inscritas ({plazasOcupadasReales})"
            )


        if not horarios:
            raise ActividadError("Debe indicarse al menos un horario")
        for dia, inicio, fin in horarios:
            if not (1 <= dia <= 7):
                raise ActividadError(f"Día de la semana no válido: {dia}")
            if not ('08:00' <= inicio < fin <= '22:00'):
                raise ActividadError(f"Horario fuera de rango o incoherente: {inicio}-{fin}")


        idInstalacion = actividad["idInstalacion"]

        if idInstalacion is not None:

            # Consultar la capacidad máxima de la instalación
            instalaciones = self.db.executeQuery(
                "SELECT nombre, capacidad FROM Instalacion WHERE id = ?",
                idInstalacion
            )

            if not instalaciones:
                raise ActividadError(
                    "La instalación asignada no existe"
                )

            instalacion = instalaciones[0]
            capacidad = instalacion["capacidad"]

            # Comprobar que las plazas no superan la capacidad
            if plazas > capacidad:
                raise ActividadError(
                    f"La actividad tiene {plazas} plazas y "
                    f"la instalación {instalacion['nombre']} "
                    f"admite como máximo {capacidad}"
                )

            # Mantener la comprobación de colisiones
            self._validarSinColision(
                idInstalacion,
                idActividad,
                fechaInicio,
                fechaFin,
                horarios
            )


        self.db.executeUpdateQuery(
            """update Actividad set idModalidad = ?, idNivel = ?, fechaInicio = ?, fechaFin = ?, plazas = ?
               where id = ?""",
            idModalidad, idNivel, fechaInicio, fechaFin, plazas, idActividad)

        self.db.executeUpdateQuery("delete from Horario where idActividad = ?", idActividad)
        for dia, inicio, fin in horarios:
            self.db.executeUpdateQuery(
                "insert into Horario (idActividad, diaSemana, horaInicio, horaFin) values (?, ?, ?, ?)",
                idActividad, dia, inicio, fin)

        return f"Actividad {self.MODALIDADES[idModalidad]} {self.NIVELES[idNivel]} modificada"

    #Comprueba colisión de horarios con otras actividades en la misma instalación, excluyendo la propia
    def _validarSinColision(self, idInstalacion, idActividadPropia, fechaInicio, fechaFin, horarios):
        otras = self.db.executeQuery(
            """select a.id, m.nombre as modalidad, n.nombre as nivel, a.fechaInicio, a.fechaFin,
                      h.diaSemana, h.horaInicio, h.horaFin
               from Actividad a
               join Modalidad m on m.id = a.idModalidad
               join Nivel n on n.id = a.idNivel
               join Horario h on h.idActividad = a.id
               where a.idInstalacion = ? and a.id != ?""",
            idInstalacion, idActividadPropia)

        for dia, inicio, fin in horarios:
            for fila in otras:
                if fila["diaSemana"] != dia:
                    continue
                if fechaFin < fila["fechaInicio"] or fila["fechaFin"] < fechaInicio:
                    continue
                if inicio < fila["horaFin"] and fila["horaInicio"] < fin:
                    raise ActividadError(
                        f"Colisión con {fila['modalidad']} {fila['nivel'].lower()}, "
                        f"{self._nombreDia(dia)} {fila['horaInicio']}–{fila['horaFin']}")

    _DIAS = {1: 'lunes', 2: 'martes', 3: 'miércoles', 4: 'jueves', 5: 'viernes', 6: 'sábado', 7: 'domingo'}

    def _nombreDia(self, dia):
        return self._DIAS[dia]

    def getActividadesDeOferta(self, idOferta):
        return self.db.executeQuery(
            """select a.*, m.nombre as modalidad, n.nombre as nivel
               from Actividad a
               join Modalidad m on m.id = a.idModalidad
               join Nivel n on n.id = a.idNivel
               where a.idOferta = ? order by a.id""", idOferta)

    def getHorarios(self, idActividad):
        return self.db.executeQuery(
            "select diaSemana, horaInicio, horaFin from Horario where idActividad = ? order by diaSemana, horaInicio",
            idActividad)