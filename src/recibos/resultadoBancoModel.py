'''
HU14 "Importar el resultado del banco para saber qué recibos se han cobrado".

Se lee el fichero resultado_AAAA-MM.txt (simula la respuesta del banco, sin cabecera) con una
línea por recibo: id;resultado, donde el resultado es COBRADO o DEVUELTO. Cada recibo emitido de la
remesa de ese mes pasa al estado indicado; solo se registra el estado (el tratamiento de los
devueltos o no recibidos irá en otras historias). Las líneas erróneas se informan con su número de
línea y no modifican nada.
'''
import datetime
from pathlib import Path

from src.config import BANCO_DIR, DB_PATH
from src.recibos.comun import (
    COBRADO,
    DEVUELTO,
    EMITIDO,
    ReciboError,
    conectar,
    fechaHoy,
    leerMes,
    nombreMes,
    textoMes,
)

RESULTADOS = (COBRADO, DEVUELTO)


def nombreFicheroResultado(mes):
    return f"resultado_{mes}.txt"


class ResultadoBancoModel:

    def __init__(self, db_path=None, carpeta=None, hoyFijo=None):
        self.db_path = db_path if db_path else DB_PATH
        self.carpeta = Path(carpeta) if carpeta else BANCO_DIR
        self.hoyFijo = hoyFijo

    def mesPorDefecto(self, hoy=None):
        return textoMes(fechaHoy(hoy if hoy is not None else self.hoyFijo))

    def _mes(self, mes):
        primero = leerMes(mes) if mes is not None and str(mes).strip() else \
            fechaHoy(self.hoyFijo).replace(day=1)
        return textoMes(primero)

    def rutaFichero(self, mes):
        return self.carpeta / nombreFicheroResultado(self._mes(mes))

    #Comprueba una línea del fichero. Devuelve (idRecibo, resultado) o lanza ValueError con el motivo
    @staticmethod
    def _leerLinea(texto):
        campos = [c.strip() for c in texto.split(";")]
        if len(campos) != 2:
            raise ValueError("formato incorrecto, se espera id;resultado")
        try:
            idRecibo = int(campos[0])
        except ValueError:
            raise ValueError(f"el id del recibo «{campos[0]}» no es un número") from None
        resultado = campos[1].upper()
        if resultado not in RESULTADOS:
            raise ValueError(f"resultado «{campos[1]}» no válido (debe ser COBRADO o DEVUELTO)")
        return idRecibo, resultado

    def importarResultado(self, mes=None):
        '''
        Importa el fichero del banco del mes y actualiza el estado de los recibos.
        Devuelve un resumen: cobrados, devueltos, erroneos y la lista de errores (línea y motivo).
        Lanza ReciboError si no se puede importar el fichero.
        '''
        mes = self._mes(mes)
        nombre = nombreMes(mes)
        ruta = self.rutaFichero(mes)
        if not ruta.exists():
            raise ReciboError(f"No se encuentra el fichero {ruta.name} en la carpeta {self.carpeta}")
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise ReciboError(f"No se puede leer el fichero {ruta.name}: {error}") from error
        if not any(linea.strip() for linea in lineas):
            raise ReciboError("El fichero no contiene resultados")

        ahora = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        cobrados, devueltos, errores, vistos = 0, 0, [], set()
        with conectar(self.db_path) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                if not conn.execute("select 1 from Remesa where mes = ?", (mes,)).fetchone():
                    raise ReciboError(f"No se ha emitido la remesa de {nombre}")
                for numero, linea in enumerate(lineas, start=1):
                    if not linea.strip():
                        continue
                    try:
                        idRecibo, resultado = self._leerLinea(linea)
                    except ValueError as error:
                        errores.append({"linea": numero, "motivo": str(error).capitalize()})
                        continue
                    motivo = self._comprobarRecibo(conn, idRecibo, mes, nombre, vistos)
                    vistos.add(idRecibo)
                    if motivo:
                        errores.append({"linea": numero, "motivo": motivo})
                        continue
                    conn.execute("update Recibo set estado = ?, fechaResultado = ? where id = ?",
                                 (resultado, ahora, idRecibo))
                    if resultado == COBRADO:
                        cobrados += 1
                    else:
                        devueltos += 1
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        mensaje = (f"Resultado del banco de {nombre} importado: {cobrados} cobrado(s), "
                   f"{devueltos} devuelto(s) y {len(errores)} erróneo(s)")
        return {"mes": mes, "cobrados": cobrados, "devueltos": devueltos, "erroneos": len(errores),
                "errores": errores, "mensaje": mensaje}

    #Devuelve el motivo por el que no se puede actualizar el recibo, o None si se puede
    @staticmethod
    def _comprobarRecibo(conn, idRecibo, mes, nombre, vistos):
        if idRecibo in vistos:
            return f"El recibo {idRecibo} está repetido en el fichero"
        recibo = conn.execute("select mes, estado from Recibo where id = ?", (idRecibo,)).fetchone()
        if recibo is None:
            return f"El recibo {idRecibo} no existe"
        if recibo["mes"] != mes:
            return f"El recibo {idRecibo} no pertenece a la remesa de {nombre}"
        if recibo["estado"] != EMITIDO:
            return f"El recibo {idRecibo} ya estaba procesado ({recibo['estado'].lower()})"
        return None

    def generarFicheroPrueba(self, mes=None):
        '''
        Simula la respuesta del banco (dato de prueba): escribe resultado_<mes>.txt con todos los
        recibos emitidos de la remesa del mes; uno de cada cuatro sale DEVUELTO y el resto COBRADO.
        Si ya existe, se sustituye. Devuelve la ruta del fichero.
        '''
        mes = self._mes(mes)
        with conectar(self.db_path) as conn:
            if not conn.execute("select 1 from Remesa where mes = ?", (mes,)).fetchone():
                raise ReciboError(f"No se ha emitido la remesa de {nombreMes(mes)}")
            ids = [f["id"] for f in conn.execute(
                "select id from Recibo where mes = ? and estado = ? order by id", (mes, EMITIDO))]
        if not ids:
            raise ReciboError(f"La remesa de {nombreMes(mes)} no tiene recibos pendientes del banco")
        lineas = [f"{idRecibo};{DEVUELTO if i % 4 == 3 else COBRADO}" for i, idRecibo in enumerate(ids)]
        self.carpeta.mkdir(parents=True, exist_ok=True)
        ruta = self.rutaFichero(mes)
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return str(ruta)
