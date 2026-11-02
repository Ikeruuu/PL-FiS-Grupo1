
"""
Inicia el Centro Deportivo en modo demostración.

Utiliza una base de datos independiente:
database_demo.db

No modifica la base de datos habitual.
"""

import sqlite3
from pathlib import Path

from src.config import SCHEMA_PATH, DATA_PATH
from src.gui.app import ejecutar


BASE_DIR = Path(__file__).resolve().parent
DB_DEMO = BASE_DIR / "database_demo.db"


def preparar_base_demo():
    # Conservar la base demo si ya existe
    if DB_DEMO.exists():
        print("Base demo existente. Se conservan sus datos.")
        return

    print("Creando base de datos de demostración...")

    try:
        with sqlite3.connect(DB_DEMO) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Crear tablas y cargar datos iniciales
            schema = Path(SCHEMA_PATH).read_text(encoding="utf-8")
            datos = Path(DATA_PATH).read_text(encoding="utf-8")

            conn.executescript(schema)
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

            conn.commit()

        print("Base demo creada correctamente.")

    except Exception:
        # Se ejecuta después de cerrar la conexión SQLite
        if DB_DEMO.exists():
            DB_DEMO.unlink()
        raise


if __name__ == "__main__":
    preparar_base_demo()
    print("Iniciando Centro Deportivo en MODO DEMO...")
    ejecutar(str(DB_DEMO))
