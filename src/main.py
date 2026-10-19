import logging

from src.config import DATA_PATH, DB_PATH, SCHEMA_PATH
from src.employees.employeeView import EmployeeView
from src.instalaciones.instalacionView import InstalacionView
from src.util.database import Database

logger = logging.getLogger(__name__)


def main():
    '''
    Inicialización de la aplicación:
    Crea el esquema de la BBDD, realiza una carga inicial de datos en la BD y muestra un menú.

    Nota: se recrea el esquema y se recargan los datos en cada ejecución.
    '''
    logger.info("Inicializando la base de datos %s", DB_PATH)
    db = Database(DB_PATH)
    db.executeScript(SCHEMA_PATH)
    db.executeScript(DATA_PATH)

    choices = {"1": EmployeeView().run,
               "2": InstalacionView().run}
    while True:
        print(""" Centro Deportivo Inteligente: \n
              1.- Empleados (ejemplo del profesor) \n
              2.- Instalaciones \n
              0.- Salir
              """)
        choice = input("Introducir opción: ")
        if choice == "0":
            print("Cerrando la aplicación.")
            return
        action = choices.get(choice)
        if not action:
            print("{0} no es una opción valida".format(choice))
            continue
        action()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()
