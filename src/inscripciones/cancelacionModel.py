import datetime

from src.config import DB_PATH
from src.inscripciones.comun import (
    ESTADOS_CON_PLAZA,
    IdentificacionError,
    buscarPersona,
    conectar,
    listaEspera,
    plazasOcupadas,
)

_MESES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio",
          8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}


class CancelacionError(IdentificacionError):
    '''No se puede cancelar. El mensaje se muestra tal cual al usuario.'''


#"2026-12" -> date(2026, 12, 1). Admite también "2026-12-01".
def leerMes(mes):
    texto = (mes or "").strip()
    try:
        anio, numero = (int(x) for x in texto.split("-")[:2])
        return datetime.date(anio, numero, 1)
    except ValueError:
        raise CancelacionError("El mes debe tener el formato AAAA-MM (por ejemplo 2026-12)")


def nombreMes(fecha):
    return f"{_MESES[fecha.month]} de {fecha.year}"


def mesAnterior(fecha):
    return (fecha - datetime.timedelta(days=1)).replace(day=1)


class CancelacionModel:
    '''
    HU "Cancelar una inscripción en una actividad" (RedKanban 35335).
    - Antes de que empiece la actividad se puede cancelar en cualquier momento.
    - Con la actividad ya comenzada se cancela a partir de un mes concreto, y la solicitud se
      hace entre el 1 y el 15 del mes anterior (para diciembre, del 1 al 15 de noviembre).
    - Una solicitud en lista de espera se puede retirar en cualquier momento.
    - La inscripción no se borra: queda en estado CANCELADA. Si libera una plaza y hay lista de
      espera, la primera persona de la lista pasa a tener la plaza (pendiente de aceptar, que
      gestiona la HU de lista de espera).
    La vista llama primero a comprobarCancelacion para pedir confirmación y después a cancelar.
    '''

    def __init__(self, db_path=None):
        self.db_path = DB_PATH if db_path is None else db_path

    @staticmethod
    def _hoy(hoy):
        hoy = datetime.date.today() if hoy is None else hoy
        return datetime.date.fromisoformat(hoy) if isinstance(hoy, str) else hoy

    #Comprueba todas las reglas sin modificar nada. Devuelve un dict con lo que se va a cancelar.
    def _validar(self, conn, idActividad, dni, numSocio, mes, hoy):
        persona = buscarPersona(conn, dni, numSocio)
        actividad = conn.execute(
            """select a.*, m.nombre as modalidad, n.nombre as nivel from Actividad a
               join Modalidad m on m.id = a.idModalidad join Nivel n on n.id = a.idNivel
               where a.id = ?""", (idActividad,)).fetchone()
        if actividad is None:
            raise CancelacionError("La actividad no existe")
        inscripcion = conn.execute(
            "select * from Inscripcion where idPersona = ? and idActividad = ?",
            (persona["id"], idActividad)).fetchone()
        if inscripcion is None:
            raise CancelacionError(
                "No existe ninguna inscripción ni solicitud de esta persona en la actividad")
        if inscripcion["estado"] == "CANCELADA":
            raise CancelacionError("La inscripción en esta actividad ya está cancelada")

        nombre = f"{actividad['modalidad']} {actividad['nivel'].lower()}"
        resultado = {"persona": persona, "actividad": actividad, "inscripcion": inscripcion,
                     "nombreActividad": nombre, "cancelaDesde": None}

        #Retirar una solicitud de la lista de espera no tiene plazo
        if inscripcion["estado"] == "EN_ESPERA":
            resultado["resumen"] = f"Se retirará la solicitud en lista de espera de {nombre}"
            return resultado

        inicio = datetime.date.fromisoformat(actividad["fechaInicio"])
        fin = datetime.date.fromisoformat(actividad["fechaFin"])
        if hoy > fin:
            raise CancelacionError("La actividad ya ha terminado y no se puede cancelar")
        if hoy < inicio:
            resultado["resumen"] = (f"Se cancelará la inscripción en {nombre} "
                                    "(la actividad aún no ha comenzado)")
            return resultado

        #Actividad ya comenzada: hace falta el mes y estar dentro del plazo
        if mes is None or not str(mes).strip():
            raise CancelacionError("La actividad ya ha comenzado: indica el mes a partir del "
                                   "cual quieres cancelar (AAAA-MM)")
        desde = leerMes(mes)
        if desde <= hoy.replace(day=1):
            raise CancelacionError("El mes de cancelación debe ser posterior al mes actual")
        if desde > fin:
            raise CancelacionError(f"La actividad termina el {fin.strftime('%d/%m/%Y')}; "
                                   "el mes indicado es posterior")
        anterior = mesAnterior(desde)
        if not (hoy.replace(day=1) == anterior and hoy.day <= 15):
            raise CancelacionError(
                f"Fuera de plazo: para cancelar a partir de {nombreMes(desde)} la solicitud "
                f"debe hacerse entre el 1 y el 15 de {nombreMes(anterior)}")
        resultado["cancelaDesde"] = desde.isoformat()
        resultado["resumen"] = (f"Se cancelará la inscripción en {nombre} "
                                f"a partir de {nombreMes(desde)}")
        return resultado

    def comprobarCancelacion(self, idActividad, dni=None, numSocio=None, mes=None, hoy=None):
        '''Devuelve el texto para pedir confirmación, o lanza CancelacionError.'''
        with conectar(self.db_path) as conn:
            return self._validar(conn, idActividad, dni, numSocio, mes, self._hoy(hoy))["resumen"]

    def cancelar(self, idActividad, dni=None, numSocio=None, mes=None, hoy=None):
        '''Cancela (ya confirmado por el usuario) y devuelve el mensaje de confirmación.'''
        hoy = self._hoy(hoy)
        ahora = datetime.datetime.now().isoformat(timespec="microseconds")
        with conectar(self.db_path) as conn:
            try:
                #Una única transacción para que la plaza liberada no se asigne dos veces
                conn.execute("BEGIN IMMEDIATE")
                datos = self._validar(conn, idActividad, dni, numSocio, mes, hoy)
                inscripcion = datos["inscripcion"]
                conn.execute(
                    """update Inscripcion set estado = 'CANCELADA', fechaCancelacion = ?,
                       cancelaDesde = ? where id = ?""",
                    (ahora, datos["cancelaDesde"], inscripcion["id"]))

                if inscripcion["estado"] == "EN_ESPERA":
                    mensaje = (f"Solicitud en lista de espera de {datos['nombreActividad']} "
                               "cancelada")
                else:
                    mensaje = f"Inscripción en {datos['nombreActividad']} cancelada"
                    if datos["cancelaDesde"]:
                        mensaje += (" a partir de "
                                    f"{nombreMes(datetime.date.fromisoformat(datos['cancelaDesde']))}")
                    if self._asignarPlazaLiberada(conn, datos["actividad"]):
                        mensaje += (". La plaza liberada pasa a la primera persona de la lista "
                                    "de espera")
                conn.commit()
                return mensaje
            except Exception:
                conn.rollback()
                raise

    #Si queda una plaza libre y hay lista de espera, la primera persona pasa a tener plaza
    #(pendiente de aceptar). Devuelve True si se ha asignado.
    def _asignarPlazaLiberada(self, conn, actividad):
        if plazasOcupadas(conn, actividad["id"]) >= actividad["plazas"]:
            return False
        espera = listaEspera(conn, actividad["id"])
        if not espera:
            return False
        conn.execute("update Inscripcion set estado = 'PENDIENTE_ACEPTACION' where id = ?",
                     (espera[0]["id"],))
        return True
