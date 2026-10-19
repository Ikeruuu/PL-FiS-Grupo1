import datetime
import re

from src.config import DB_PATH
from src.util.database import Database


class PersonaError(Exception):
    '''
    Indica que no se puede registrar la persona. El mensaje se muestra tal cual al usuario.
    Si el motivo es que ya existe, persona contiene sus datos para mostrarlos.
    '''

    def __init__(self, mensaje, persona=None):
        super().__init__(mensaje)
        self.persona = persona


#Normaliza un DNI: mayúsculas y sin espacios ni guiones ("12345678-z" -> "12345678Z")
def normalizarDni(dni):
    return re.sub(r"[\s\-]", "", dni or "").upper()


#Quita espacios sobrantes al principio, al final y entre palabras
def normalizarTexto(texto):
    return " ".join((texto or "").split())


class PersonaModel:
    '''
    Objetos de negocio (model) de la HU8 "Gestionar los datos de personas (socios y no socios)".
    Los socios ya están en el sistema (datos de prueba); esta historia registra no socios y
    consulta cualquier persona por DNI o por número de socio.
    '''

    COLUMNAS = "id, dni, nombre, apellidos, fechaNacimiento, telefono, correo, numSocio, fechaAltaSocio"

    def __init__(self, db_path=None):
        self.db = Database(db_path if db_path else DB_PATH)

    #Obtiene una persona por su DNI (se normaliza antes de buscar). None si no existe
    def getPersonaPorDni(self, dni):
        res = self.db.executeQuery(f"select {self.COLUMNAS} from Persona where dni = ?",
                                   normalizarDni(dni))
        return res[0] if len(res) == 1 else None

    #Obtiene una persona por su número de socio. None si no existe
    def getPersonaPorNumSocio(self, num_socio):
        res = self.db.executeQuery(f"select {self.COLUMNAS} from Persona where numSocio = ?",
                                   num_socio)
        return res[0] if len(res) == 1 else None

    #Comprueba los datos de un no socio y devuelve la lista de errores (vacía si son correctos)
    def validarNoSocio(self, dni, nombre, apellidos, fecha_nacimiento, telefono, correo, hoy=None):
        errores = []
        faltan = [campo for campo, valor in (("DNI", dni), ("nombre", nombre), ("apellidos", apellidos))
                  if not valor]
        if faltan:
            errores.append("Faltan campos obligatorios: " + ", ".join(faltan))
        if not telefono and not correo:
            errores.append("Hay que indicar al menos un medio de contacto (teléfono o correo)")
        if correo and "@" not in correo:
            errores.append("El correo no es válido: debe contener @")
        if fecha_nacimiento:
            try:
                nacimiento = datetime.date.fromisoformat(fecha_nacimiento)
            except ValueError:
                errores.append("La fecha de nacimiento debe tener el formato AAAA-MM-DD")
            else:
                if nacimiento > (hoy if hoy else datetime.date.today()):
                    errores.append("La fecha de nacimiento no puede ser futura")
        return errores

    #Registra una persona no socia. Devuelve el mensaje de éxito o lanza PersonaError con el motivo
    def registrarNoSocio(self, dni, nombre, apellidos, fecha_nacimiento=None, telefono=None,
                         correo=None, hoy=None):
        dni = normalizarDni(dni)
        nombre = normalizarTexto(nombre)
        apellidos = normalizarTexto(apellidos)
        telefono = normalizarTexto(telefono) or None
        correo = normalizarTexto(correo) or None
        fecha_nacimiento = normalizarTexto(fecha_nacimiento) or None

        errores = self.validarNoSocio(dni, nombre, apellidos, fecha_nacimiento, telefono, correo, hoy)
        if errores:
            raise PersonaError("\n".join(errores))

        existente = self.getPersonaPorDni(dni)
        if existente is not None:
            if existente["numSocio"] is not None:
                raise PersonaError("Esta persona ya es socia", existente)
            raise PersonaError("Ya existe una persona con ese DNI", existente)

        query = """insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio)
                   values (null,?,?,?,?,?,?,null,null)
                """
        self.db.executeUpdateQuery(query, dni, nombre, apellidos, fecha_nacimiento, telefono, correo)
        return f"Persona registrada como no socia: {nombre} {apellidos} ({dni})"
