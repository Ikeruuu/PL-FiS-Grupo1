import datetime
import logging
import sys

from src.employees.employeeModel import EmployeeModel
from src.util.unexpectedException import UnexpectedException
from src.util.validation import (
    ValidationError,
    validate_date,
    validate_date_range,
    validate_non_empty,
    validate_salary,
)

logger = logging.getLogger(__name__)


class EmployeeView:
    '''
    Clase que representa la vista (entrada y salida) de datos
    para las funcionalidades relativas a los empleados que estarán
    representadas en la clase EmployeeModel (employeeModel.py)
    '''

    def __init__(self):
        self.empleado = EmployeeModel() #Crea un objeto model que se invocará desde esta vista
        #Crea un diccionario con las opciones (key) y los métodos/acciones que se pueden realizar en este objeto (values)
        self.choices = {"1": self.showEmployees,
                        "2": self.showAvgSalary,
                        "3": self.newEmployee,
                        "4": self.showEmployeesByYears,
                        "5": self.quit
                        }

    def displayMenu(self):
        print(""" Opciones: \n
              1.- Lista empleados por compañía \n
              2.- Salario medio por compañia \n
              3.- Insertar empleado \n
              4.- Lista empleados por antiguedad (no activos) \n
              5.- Salir 
              """)

    #Muestra la lista de opciones y permite la selección
    def run(self):
        while True:
            self.displayMenu()
            choice = input("Introducir opción: ")
            action = self.choices.get(choice)
            if not action:
                print("{0} no es una opción valida".format(choice))
                continue
            try:
                action()
            except UnexpectedException as e:
                #Traza el error para diagnóstico y continúa mostrando el menú
                logger.error("Error inesperado de la aplicación", exc_info=True)
                print("Error inesperado (detalle en el registro). Inténtelo de nuevo.")

    #Vista para la HU Listar los empleados de una compañia
    def showEmployees(self):
        name_company = input("Introducir nombre de compañia: ")
        #Invocación al modelo para obtener el id de la compañia
        id_company = self.empleado.getIdCompany(name_company)
        if id_company is None:
            print("No existe la compañia", name_company)
        else:
            #Invoca al objeto model para obtener la lista de empleados
            res1 = self.empleado.getAllEmployees(name_company)
            #Imprime los resultados  
            self.printResults(res1)
            #Idem para obtener el resumen 
            res2 = self.empleado.getSummaryEmployees(name_company)
            for d in res2:
                print(d)

    #Vista para la HU Mostrar salario medio por compañia.
    def showAvgSalary(self):
        res = self.empleado.getAvgSalary()
        self.printResults(res)

    #Vista para la HU Insertar un empleado en una compañia
    def newEmployee(self):
        name_company = input("Introducir nombre de compañia para el empleado: ")
        id_company = self.empleado.getIdCompany(name_company)
        if id_company is None:
            print("No existe la compañia", name_company)
        else:
            name = self._read_non_empty("Nombre empleado: ")
            salary = self._read_salary()
            birth_date = self._read_date("Fecha nacimiento (aaaa-mm-dd): ", birth_date=True)
            start_date = self._read_date("Fecha alta (aaaa-mm-dd): ")
            end_date = self._read_date("Fecha baja (aaaa-mm-dd): ", allow_empty=True)
            try:
                validate_date_range(start_date, end_date)
            except ValidationError as error:
                logger.warning("%s", error)
                print(error)
                return
            self.empleado.insertEmployee(name, salary, birth_date, start_date, end_date, id_company)

    def _read_non_empty(self, prompt):
        while True:
            try:
                return validate_non_empty(input(prompt))
            except ValidationError as error:
                logger.warning("%s", error)
                print(error)

    def _read_salary(self):
        while True:
            try:
                return validate_salary(input("Salario empleado: "))
            except ValidationError as error:
                logger.warning("%s", error)
                print(error)

    def _read_date(self, prompt, allow_empty=False, birth_date=False):
        while True:
            try:
                return validate_date(input(prompt), allow_empty, birth_date)
            except ValidationError as error:
                logger.warning("%s", error)
                print(error)

    #Vista para la HU Listar empleados con antiguedad superior a un año
    def showEmployeesByYears(self):
        name_company = input("Introducir nombre de compañia: ")
        #Invocación al modelo para obtener el id de la compañia
        id_company = self.empleado.getIdCompany(name_company)
        if id_company is None:
            print("No existe la compañia", name_company)
        else:
            #Invoca al objeto model para obtener la lista de empleados
            current_date = datetime.date.today().strftime("%Y-%m-%d")
            res = self.empleado.getEmployeesByYears(current_date, name_company)
            #Imprime los resultados  
            self.printResults(res)

    def quit(self):
        print("Cerrando opciones.")
        sys.exit(0)

    #Médodo muy general para imprimir los resultados (res) que vienen del model
    def printResults(self, res):
        if len(res) == 0:
            print("No hay resultados")
        else:
            #cabecera
            print(list(res[0].keys())) # Imprime nombres de columnas (keys del diccionario)
            print("----------------------------------")
            #contenido 
            for row in res:
                print([*row.values()]) # Imprime valor de una fila (values del diccionario)
            print("----------------------------------")