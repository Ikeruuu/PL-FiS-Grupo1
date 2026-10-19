import logging
import sys

from src.config import DATA_PATH, DB_PATH, SCHEMA_PATH
from src.employees.employeeView import EmployeeView
from src.instalaciones.instalacionView import InstalacionView
from src.personas.personaView import PersonaView
from src.util.database import Database

logger = logging.getLogger(__name__)


def menuConsola():
    '''Menú principal en modo consola (se usa con la opción --consola).'''
    choices = {"1": EmployeeView().run,
               "2": InstalacionView().run,
               "3": PersonaView().run}
    while True:
        print(""" Centro Deportivo Inteligente: \n
              1.- Empleados (ejemplo del profesor) \n
              2.- Instalaciones \n
              3.- Personas \n
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


def main(argv=None):
    '''
    Inicialización de la aplicación:
    Crea el esquema de la BBDD, realiza una carga inicial de datos en la BD y abre la interfaz
    gráfica. Con la opción --consola se usa el menú de consola.

    Nota: se recrea el esquema y se recargan los datos en cada ejecución.
    '''
    argv = sys.argv[1:] if argv is None else argv
    logger.info("Inicializando la base de datos %s", DB_PATH)
    db = Database(DB_PATH)
    db.executeScript(SCHEMA_PATH)
    db.executeScript(DATA_PATH)

    if "--consola" in argv:
        menuConsola()
        return
    try:
        from src.gui.app import ejecutar
        ejecutar()
    except ImportError:
        logger.warning("Tkinter no está disponible; se usa el menú de consola")
        menuConsola()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()
