import logging

from src.instalaciones.instalacionModel import (
    AsignacionError,
    InstalacionModel,
    describirActividad,
    describirFranja,
)
from src.util.unexpectedException import UnexpectedException
from src.util.validation import ValidationError, validate_positive_int

logger = logging.getLogger(__name__)


class InstalacionView:
    '''
    Vista (entrada y salida por consola) de la HU3 "Asignar una instalación a una actividad".
    La lógica y el acceso a datos están en InstalacionModel (instalacionModel.py).
    '''

    def __init__(self, model=None):
        self.model = model if model else InstalacionModel()
        self.choices = {"1": self.asignarInstalacion}

    def displayMenu(self):
        print(""" Instalaciones: \n
              1.- Asignar instalación a una actividad \n
              0.- Volver
              """)

    def run(self):
        while True:
            self.displayMenu()
            choice = input("Introducir opción: ")
            if choice == "0":
                return
            action = self.choices.get(choice)
            if not action:
                print("{0} no es una opción valida".format(choice))
                continue
            try:
                action()
            except UnexpectedException:
                logger.error("Error inesperado de la aplicación", exc_info=True)
                print("Error inesperado (detalle en el registro). Inténtelo de nuevo.")

    #Vista para la HU3 Asignar una instalación a una actividad
    def asignarInstalacion(self):
        if self.model.countActividades() == 0:
            print("No hay actividades registradas")
            return
        actividades = self.model.getActividadesSinInstalacion()
        if not actividades:
            print("Todas las actividades tienen instalación asignada")
            return
        instalaciones = self.model.getInstalaciones()
        if not instalaciones:
            print("No hay instalaciones registradas")
            return

        print("Actividades sin instalación asignada:")
        for a in actividades:
            horario = ", ".join(describirFranja(h) for h in self.model.getHorarios(a["id"]))
            print(f"  {a['id']:>3}  {describirActividad(a)} | {a['fechaInicio']} a {a['fechaFin']}"
                  f" | {a['plazas']} plazas | {horario or 'sin horario'}")
        id_actividad = self._read_id("Id de la actividad (vacío para cancelar): ")
        if id_actividad is None:
            return

        print("Instalaciones:")
        for i in instalaciones:
            print(f"  {i['id']:>3}  {i['nombre']} (capacidad {i['capacidad']})")
        id_instalacion = self._read_id("Id de la instalación (vacío para cancelar): ")
        if id_instalacion is None:
            return

        try:
            print(self.model.asignarInstalacion(id_actividad, id_instalacion))
        except AsignacionError as error:
            logger.warning("%s", error)
            print(error)

    #Lee un identificador entero positivo; devuelve None si se deja vacío
    def _read_id(self, prompt):
        while True:
            value = input(prompt)
            if not value.strip():
                return None
            try:
                return validate_positive_int(value)
            except ValidationError as error:
                logger.warning("%s", error)
                print(error)
