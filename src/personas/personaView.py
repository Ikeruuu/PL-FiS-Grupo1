import logging

from src.personas.personaModel import PersonaError, PersonaModel
from src.util.unexpectedException import UnexpectedException
from src.util.validation import ValidationError, validate_positive_int

logger = logging.getLogger(__name__)


class PersonaView:
    '''
    Vista (entrada y salida por consola) de la HU8 "Gestionar los datos de personas".
    La lógica y el acceso a datos están en PersonaModel (personaModel.py).
    '''

    def __init__(self, model=None):
        self.model = model if model else PersonaModel()
        self.choices = {"1": self.registrarNoSocio,
                        "2": self.consultarPersona}

    def displayMenu(self):
        print(""" Personas: \n
              1.- Registrar persona no socia \n
              2.- Consultar persona (por DNI o número de socio) \n
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

    #Vista para la HU8: registro de una persona no socia
    def registrarNoSocio(self):
        print("Datos de la persona no socia (los campos opcionales se pueden dejar vacíos)")
        dni = input("DNI: ")
        nombre = input("Nombre: ")
        apellidos = input("Apellidos: ")
        fecha_nacimiento = input("Fecha de nacimiento aaaa-mm-dd (opcional): ")
        telefono = input("Teléfono: ")
        correo = input("Correo: ")
        try:
            print(self.model.registrarNoSocio(dni, nombre, apellidos, fecha_nacimiento, telefono, correo))
        except PersonaError as error:
            logger.warning("%s", error)
            print(error)
            if error.persona is not None:
                self.printPersona(error.persona)

    #Vista para la HU8: consulta de una persona por DNI o por número de socio
    def consultarPersona(self):
        tipo = input("Buscar por 1.- DNI o 2.- Número de socio: ")
        if tipo == "1":
            identificador = input("DNI: ")
            persona = self.model.getPersonaPorDni(identificador)
        elif tipo == "2":
            try:
                identificador = validate_positive_int(input("Número de socio: "))
            except ValidationError as error:
                print(error)
                return
            persona = self.model.getPersonaPorNumSocio(identificador)
        else:
            print("{0} no es una opción valida".format(tipo))
            return
        if persona is None:
            print("No existe ninguna persona con ese identificador")
        else:
            self.printPersona(persona)

    #Muestra los datos de una persona indicando si es socia y su número de socio
    def printPersona(self, persona):
        print("----------------------------------")
        print(f"DNI: {persona['dni']}")
        print(f"Nombre: {persona['nombre']} {persona['apellidos']}")
        print(f"Fecha de nacimiento: {persona['fechaNacimiento'] or '-'}")
        print(f"Teléfono: {persona['telefono'] or '-'}")
        print(f"Correo: {persona['correo'] or '-'}")
        if persona["numSocio"] is not None:
            print(f"Tipo: socio (número de socio {persona['numSocio']}, alta {persona['fechaAltaSocio']})")
        else:
            print("Tipo: no socio")
        print("----------------------------------")
