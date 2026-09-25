import logging

from src.config import DATA_PATH, DB_PATH, SCHEMA_PATH
from src.employees.employeeView import EmployeeView
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

    EmployeeView().run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()
