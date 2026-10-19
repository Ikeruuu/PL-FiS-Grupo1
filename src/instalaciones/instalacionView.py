import logging

from src.instalaciones.instalacionModel import (
    DIAS_SEMANA,
    AsignacionError,
    InstalacionModel,
    describirActividad,
    describirFranja,
)
from src.instalaciones.ocupacionModel import APERTURA, CIERRE, OcupacionError, OcupacionModel
from src.util.unexpectedException import UnexpectedException
from src.util.validation import ValidationError, validate_date, validate_positive_int

logger = logging.getLogger(__name__)


class InstalacionView:
    '''
    Vista (entrada y salida por consola) de la HU3 "Asignar una instalación a una actividad".
    La lógica y el acceso a datos están en InstalacionModel (instalacionModel.py).
    '''

    def __init__(self, model=None, ocupacion=None):
        self.model = model if model else InstalacionModel()
        self.ocupacion = ocupacion if ocupacion else OcupacionModel()
        self.choices = {"1": self.asignarInstalacion,
                        "2": self.consultarOcupacion}

    def displayMenu(self):
        print(""" Instalaciones: \n
              1.- Asignar instalación a una actividad \n
              2.- Consultar ocupación de una instalación \n
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

    #Vista para la HU Consultar la ocupación de una instalación
    def consultarOcupacion(self):
        instalaciones = self.model.getInstalaciones()
        if not instalaciones:
            print("No hay instalaciones registradas")
            return
        print("Instalaciones:")
        for i in instalaciones:
            print(f"  {i['id']:>3}  {i['nombre']} (capacidad {i['capacidad']})")
        id_instalacion = self._read_id("Id de la instalación (vacío para cancelar): ")
        if id_instalacion is None:
            return
        fecha_inicio = self._read_date("Fecha de inicio aaaa-mm-dd (vacío para el curso completo): ")
        fecha_fin = None
        if fecha_inicio is not None:
            fecha_fin = self._read_date("Fecha de fin aaaa-mm-dd: ", allow_empty=False)

        try:
            res = self.ocupacion.consultarOcupacion(id_instalacion, fecha_inicio, fecha_fin)
        except OcupacionError as error:
            logger.warning("%s", error)
            print(error)
            return
        self.printOcupacion(res)

    #Muestra la ocupación como lista: para cada día, las franjas ocupadas y libres por hora
    def printOcupacion(self, res):
        print(f"Ocupación de {res['instalacion']['nombre']} del {res['fechaInicio']} al {res['fechaFin']}"
              f" (horario {APERTURA}–{CIERRE})")
        if not res["dias"]:
            print(f"La instalación está libre en todo el periodo ({int(APERTURA[:2])}:00–{CIERRE})")
            return
        for dia, nombre in DIAS_SEMANA.items():
            print(nombre.capitalize())
            ocupacion = res["dias"].get(dia)
            if ocupacion is None:
                print(f"  {APERTURA}–{CIERRE}  Libre")
                continue
            lineas = [(f["horaInicio"], f"  {f['horaInicio']}–{f['horaFin']}  Ocupada: "
                       f"{describirActividad(f)} ({f['fechaInicio']} a {f['fechaFin']})")
                      for f in ocupacion["ocupadas"]]
            lineas += [(inicio, f"  {inicio}–{fin}  Libre") for inicio, fin in ocupacion["libres"]]
            for _, linea in sorted(lineas, key=lambda x: x[0]):
                print(linea)

    #Lee una fecha aaaa-mm-dd; devuelve None si se deja vacía y se permite
    def _read_date(self, prompt, allow_empty=True):
        while True:
            try:
                return validate_date(input(prompt), allow_empty=allow_empty)
            except ValidationError as error:
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
