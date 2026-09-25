from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración actual: SQLite no necesita un driver adicional porque forma parte
# de la librería estándar de Python. Para otro gestor, es preferible guardar la
# cadena de conexión en una variable de entorno y no incluir credenciales aquí.
#
# Ejemplo para Oracle:
#   DATABASE_URL=oracle+oracledb://usuario:contraseña@servidor:1521/?service_name=ORCL
#
# En ese caso habría que:
#   1. Cambiar `src/util/database.py` para usar SQLAlchemy u oracledb en vez
#      de sqlite3 y adaptar la ejecución de scripts al dialecto de Oracle.
#   2. Añadir el driver en pyproject.toml:
#          [project.optional-dependencies]
#          oracle = ["oracledb>=2.0"]
#   3. Instalarlo con: pip install -e ".[oracle]"
# La variable DATABASE_URL se cargaría desde el entorno (por ejemplo, desde un
# fichero .env excluido de Git), nunca desde este módulo.
DB_PATH = BASE_DIR / "CompanyDB.db"
SCHEMA_PATH = BASE_DIR / "resources" / "schema.sql"
DATA_PATH = BASE_DIR / "resources" / "data.sql"