
"""
Inicia el Centro Deportivo en modo demostración.

Utiliza una base de datos de demostración independiente.
Si la base existente tiene un esquema anterior, crea otra y conserva la original.
"""

import sqlite3
from contextlib import closing
from itertools import count
from pathlib import Path

from src.config import DATA_PATH, DATA_SPRINT2_PATH, SCHEMA_PATH
from src.gui.app import ejecutar


BASE_DIR = Path(__file__).resolve().parent
DB_DEMO = BASE_DIR / "database_demo.db"


def columnasDeTablas(conn):
    return set(conn.execute("""
        SELECT tabla.name, columna.name
        FROM sqlite_master AS tabla
        JOIN pragma_table_info(tabla.name) AS columna
        WHERE tabla.type = 'table'
    """))


def preparar_base_demo(ruta=DB_DEMO):
    esquema = SCHEMA_PATH.read_text(encoding="utf-8")
    with closing(sqlite3.connect(":memory:")) as referencia:
        referencia.executescript(esquema)
        necesarias = columnasDeTablas(referencia)

    for version in count(1):
        candidata = (ruta if version == 1
                     else ruta.with_name(f"{ruta.stem}_v{version}{ruta.suffix}"))
        try:
            candidata.open("xb").close()
        except FileExistsError:
            with closing(sqlite3.connect(candidata.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
                if necesarias <= columnasDeTablas(conn):
                    print(f"Base demo existente. Se conservan sus datos: {candidata.name}")
                    return candidata
            print(f"Se conserva {candidata.name} con su esquema anterior.")
            continue

        _inicializar_base_demo(candidata, esquema)
        return candidata


def _inicializar_base_demo(ruta, esquema):
    print(f"Creando base de datos de demostración: {ruta.name}")
    try:
        with closing(sqlite3.connect(ruta)) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Crear tablas y cargar datos iniciales
            datos = DATA_PATH.read_text(encoding="utf-8")

            conn.executescript(esquema)
            conn.executescript(datos)

            # Primero modificar el fin de la actividad 3.
            # Así evitamos que el inicio quede después del fin.
            conn.execute(
                """
                UPDATE Actividad
                SET fechaFin = '2027-03-31'
                WHERE id = 3
                """
            )

            # Ahora podemos modificar el inicio
            # de las actividades sin incumplir las restricciones.
            conn.execute(
                """
                UPDATE Actividad
                SET fechaInicio = '2027-01-01'
                WHERE fechaInicio < '2027-01-01'
                """
            )

            # Actualizar la oferta y abrir los periodos de prueba
            conn.execute(
                """
                UPDATE Oferta
                SET fechaInicio = '2027-01-01',
                    fechaFin = '2027-06-30',
                    inicioInscripcionSocios = '2026-11-01',
                    finInscripcionSocios = '2026-11-15',
                    inicioInscripcionNoSocios = '2026-11-16',
                    finInscripcionNoSocios = '2026-12-15'
                WHERE id = 1
                """
            )

            # Datos de ejemplo del Sprint 2 (oferta anterior, asistencia...).
            # Se cargan después de los ajustes anteriores para que estos solo
            # afecten a las actividades de la oferta actual.
            conn.executescript(
                DATA_SPRINT2_PATH.read_text(encoding="utf-8")
            )

            conn.commit()

        print("Base demo creada correctamente.")

    except Exception:
        # Se ejecuta después de cerrar la conexión SQLite
        ruta.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    ruta_demo = preparar_base_demo()
    print("Iniciando Centro Deportivo en MODO DEMO...")
    ejecutar(str(ruta_demo))
