# SampleProject

Proyecto de ejemplo (patrón modelo-vista) para la gestión de compañías y empleados
sobre SQLite, con interfaz de consola.

## Estructura

```
SampleProject
├── doc/               Historias de usuario que se implementan (ejemplo)
├── resources/
│   ├── schema.sql     Esquema de la base de datos (se borra y recrea en cada arranque)
│   └── data.sql       Carga inicial de datos
├── src/               Código fuente
│   ├── main.py        Punto de entrada y configuración del logging (mensajes)
│   ├── config.py      Rutas de la base de datos y scripts SQL
│   ├── employees/     Capa de empleados (modelo y vista)
│   ├── instalaciones/ HU3 Asignar instalación y HU9 Consultar ocupación (modelos y vista)
│   ├── personas/      HU8 Gestionar los datos de personas (modelo y vista)
│   ├── ofertas/       Oferta, actividades y consulta de la oferta disponible
│   ├── inscripciones/ Inscribirse, consultar mis inscripciones y cancelar
│   ├── gui/           Interfaz gráfica (Tkinter): ventana principal y pantallas
│   └── util/          Acceso a datos, validaciones y excepciones
└── test/              Tests unitarios (unittest / pytest)
```

## Requisitos

- Python 3.10+ (probado con 3.11)
- SQLite (incluido en la librería estándar)

## Instalación (entorno virtual)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

En PowerShell, activa el entorno antes de usar el comando instalado:

```powershell
. .\.venv\Scripts\Activate.ps1
sample-project
```

Si no quieres activar el entorno, ejecuta el lanzador con su ruta completa:

```powershell
.\.venv\Scripts\sample-project.exe
```

## Ejecución

```powershell
# Interfaz gráfica (por defecto)
python -m src.main

# Menú de consola
python -m src.main --consola
```

En VS Code, abre **Ejecutar y depurar** y selecciona **Ejecutar SampleProject**.
La configuración usa `src.main` como módulo para que los imports del paquete
`src` se resuelvan correctamente.

La interfaz gráfica usa Tkinter (incluido en Python para Windows) y tiene cuatro pantallas:
**Inicio** (resumen del centro), **Asignar instalación** (HU3), **Ocupación** (HU9) y
**Personas** (HU8). Usa los mismos modelos que la consola, así que las reglas de negocio
son las mismas. Si Tkinter no está disponible, se abre el menú de consola.

Además, **Oferta disponible** (consultar la oferta abierta a inscripción con filtros),
**Mis inscripciones** (estado de todas las inscripciones de una persona) y **Cancelar
inscripción** (con confirmación y plazos). Ver `doc/HU-consultar-oferta.txt`,
`doc/HU-mis-inscripciones.txt` y `doc/HU-cancelar-inscripcion.txt`.

> Nota: en cada arranque se **borra y recrea** el esquema y se recargan los datos
> iniciales (fíjate en `src/main.py`). En consola, el menú principal se cierra con la opción 0.
> La HU3 está en **2.- Instalaciones > 1.- Asignar instalación a una actividad** y la HU9 en
> **2.- Instalaciones > 2.- Consultar ocupación de una instalación**. La HU8 está en **3.- Personas**.

## Tests

```powershell
# pytest
.venv\Scripts\python.exe -m pytest test

# unittest
.venv\Scripts\python.exe -m unittest discover -s test
```

Los tests usan una base de datos temporal por cada test; no tocan `CompanyDB.db`.
Las reglas de validación de entradas están separadas en
`src/util/validation.py` y se prueban independientemente de la consola.

## Registro de errores (logging)

Los errores de acceso a datos se registran a través de `logging`
(`src/util/database.py`) con su traza completa y se muestran al usuario en la vista
como un mensaje genérico, sin interrumpir el menú. El nivel y formato se configuran
en `src/main.py`.