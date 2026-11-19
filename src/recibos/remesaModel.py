'''
HU13 "Emitir la remesa mensual de recibos de las inscripciones".

Para un mes se genera un recibo por cada inscripción activa, con la cuota mensual de la actividad
como importe (sin prorrateo), y el fichero remesa_AAAA-MM.txt que se envía al banco, con una línea
por recibo: id;socio;cuenta;importe;concepto. No se puede emitir dos veces la remesa del mismo mes
ni la de un mes futuro.

Una inscripción está activa en el mes si:
- está CONFIRMADA (las que están en lista de espera o pendientes de aceptar no pagan), o está
  CANCELADA a partir de un mes posterior (cancelaDesde): hasta ese mes sigue asistiendo;
- se inscribió como muy tarde el último día del mes;
- el periodo de la actividad coincide con el mes;
- no tiene ya un recibo de ese mes.
'''
from pathlib import Path

from src.config import BANCO_DIR, DB_PATH
from src.recibos.comun import (
    EMITIDO,
    ReciboError,
    conectar,
    describirActividad,
    describirImporte,
    fechaHoy,
    leerMes,
    nombreMes,
    textoMes,
    ultimoDia,
)


def nombreFicheroRemesa(mes):
    return f"remesa_{mes}.txt"


class RemesaModel:

    def __init__(self, db_path=None, carpeta=None, hoyFijo=None):
        self.db_path = db_path if db_path else DB_PATH
        self.carpeta = Path(carpeta) if carpeta else BANCO_DIR
        self.hoyFijo = hoyFijo

    def _hoy(self, hoy):
        return fechaHoy(hoy if hoy is not None else self.hoyFijo)

    #Mes que se propone en la pantalla: el actual
    def mesPorDefecto(self, hoy=None):
        return textoMes(self._hoy(hoy))

    def _inscripcionesActivas(self, conn, primero, ultimo, mes):
        return conn.execute(
            """select i.id as idInscripcion, p.dni, p.nombre, p.apellidos, p.cuentaBancaria,
                      a.id as idActividad, a.cuota, m.nombre as modalidad, n.nombre as nivel
               from Inscripcion i
               inner join Persona p on p.id = i.idPersona
               inner join Actividad a on a.id = i.idActividad
               inner join Modalidad m on m.id = a.idModalidad
               inner join Nivel n on n.id = a.idNivel
               where (i.estado = 'CONFIRMADA' or (i.estado = 'CANCELADA' and i.cancelaDesde > ?))
                 and i.fechaInscripcion is not null and substr(i.fechaInscripcion, 1, 10) <= ?
                 and a.fechaInicio <= ? and a.fechaFin >= ?
                 and not exists (select 1 from Recibo r where r.idInscripcion = i.id and r.mes = ?)
               order by a.id, p.apellidos, p.nombre, i.id""",
            (primero.isoformat(), ultimo.isoformat(), ultimo.isoformat(), primero.isoformat(),
             mes)).fetchall()

    #Comprueba las reglas y calcula los recibos sin modificar nada
    def _preparar(self, conn, mes, hoy):
        primero = leerMes(mes) if mes is not None and str(mes).strip() else hoy.replace(day=1)
        mes = textoMes(primero)
        nombre = nombreMes(primero)
        if primero > hoy.replace(day=1):
            raise ReciboError(f"No se puede emitir la remesa de un mes futuro ({nombre})")
        if conn.execute("select 1 from Remesa where mes = ?", (mes,)).fetchone():
            raise ReciboError(f"La remesa de {nombre} ya está emitida")

        activas = self._inscripcionesActivas(conn, primero, ultimoDia(primero), mes)
        if not activas:
            raise ReciboError(f"No hay inscripciones activas en {nombre}")

        recibos, incidencias = [], []
        for fila in activas:
            persona = f"{fila['nombre']} {fila['apellidos']} ({fila['dni']})"
            actividad = describirActividad(fila["modalidad"], fila["nivel"])
            if not fila["cuota"] or fila["cuota"] <= 0:
                incidencias.append(f"{persona} en {actividad}: la actividad no tiene cuota")
            elif not (fila["cuentaBancaria"] or "").strip():
                incidencias.append(f"{persona} en {actividad}: no tiene cuenta bancaria")
            else:
                recibos.append({"idInscripcion": fila["idInscripcion"], "dni": fila["dni"],
                                "persona": persona, "cuenta": fila["cuentaBancaria"].strip(),
                                "idActividad": fila["idActividad"], "actividad": actividad,
                                "importe": round(fila["cuota"], 2),
                                "concepto": f"Cuota de {nombre} - {actividad}"})
        if not recibos:
            raise ReciboError(f"No hay inscripciones activas en {nombre} que se puedan cobrar:\n"
                              + "\n".join(incidencias))
        return {"mes": mes, "nombreMes": nombre, "recibos": recibos, "incidencias": incidencias,
                "total": round(sum(r["importe"] for r in recibos), 2)}

    def prepararRemesa(self, mes=None, hoy=None):
        '''
        Devuelve lo que se va a emitir (para pedir confirmación) sin modificar nada:
        mes, nombreMes, recibos, total e incidencias. Lanza ReciboError si no se puede emitir.
        '''
        with conectar(self.db_path) as conn:
            return self._preparar(conn, mes, self._hoy(hoy))

    @staticmethod
    def describirPrevia(datos):
        texto = (f"Se emitirá la remesa de {datos['nombreMes']} con {len(datos['recibos'])} "
                 f"recibo(s) por {describirImporte(datos['total'])}.")
        if datos["incidencias"]:
            texto += ("\n\nNo se incluyen (se informan en el resumen):\n- "
                      + "\n- ".join(datos["incidencias"]))
        return texto

    def emitirRemesa(self, mes=None, hoy=None):
        '''
        Emite la remesa: guarda los recibos en estado EMITIDO y genera el fichero para el banco.
        Devuelve un resumen con el número de recibos, el importe total, el fichero y las
        incidencias. Lanza ReciboError si no se puede emitir.
        '''
        hoy = self._hoy(hoy)
        fichero = None
        with conectar(self.db_path) as conn:
            try:
                #Una única transacción para que no se emita dos veces la misma remesa
                conn.execute("BEGIN IMMEDIATE")
                datos = self._preparar(conn, mes, hoy)
                nombre = nombreFicheroRemesa(datos["mes"])
                conn.execute("insert into Remesa(mes, fechaEmision, fichero) values (?, ?, ?)",
                             (datos["mes"], hoy.isoformat(), nombre))
                lineas = []
                for r in datos["recibos"]:
                    cursor = conn.execute(
                        "insert into Recibo(idInscripcion, mes, importe, estado) values (?, ?, ?, ?)",
                        (r["idInscripcion"], datos["mes"], r["importe"], EMITIDO))
                    r["id"] = cursor.lastrowid
                    lineas.append(f"{r['id']};{r['dni']};{r['cuenta']};{r['importe']:.2f};{r['concepto']}")
                self.carpeta.mkdir(parents=True, exist_ok=True)
                fichero = self.carpeta / nombre
                fichero.write_text("\n".join(lineas) + "\n", encoding="utf-8")
                conn.commit()
            except Exception:
                conn.rollback()
                if fichero is not None and fichero.exists():
                    fichero.unlink()
                raise
        datos["fichero"] = str(fichero)
        datos["mensaje"] = (f"Remesa de {datos['nombreMes']} emitida: {len(datos['recibos'])} "
                            f"recibo(s) por {describirImporte(datos['total'])}. "
                            f"Fichero generado: {fichero}")
        if datos["incidencias"]:
            datos["mensaje"] += ("\nNo incluidos:\n- " + "\n- ".join(datos["incidencias"]))
        return datos

    #Remesas emitidas, de la más reciente a la más antigua, con el estado de sus recibos
    def getRemesas(self):
        with conectar(self.db_path) as conn:
            filas = conn.execute(
                """select rm.mes, rm.fechaEmision, rm.fichero, count(r.id) as recibos,
                          coalesce(sum(r.importe), 0) as total,
                          sum(r.estado = 'COBRADO') as cobrados,
                          sum(r.estado = 'DEVUELTO') as devueltos,
                          sum(r.estado = 'EMITIDO') as pendientes
                   from Remesa rm left join Recibo r on r.mes = rm.mes
                   group by rm.mes order by rm.mes desc""").fetchall()
        return [dict(f) for f in filas]

    #Recibos de una remesa con el socio y la actividad
    def getRecibos(self, mes):
        with conectar(self.db_path) as conn:
            filas = conn.execute(
                """select r.id, r.mes, r.importe, r.estado, rm.fechaEmision, p.dni, p.nombre,
                          p.apellidos, p.cuentaBancaria, m.nombre as modalidad, n.nombre as nivel
                   from Recibo r
                   inner join Remesa rm on rm.mes = r.mes
                   inner join Inscripcion i on i.id = r.idInscripcion
                   inner join Persona p on p.id = i.idPersona
                   inner join Actividad a on a.id = i.idActividad
                   inner join Modalidad m on m.id = a.idModalidad
                   inner join Nivel n on n.id = a.idNivel
                   where r.mes = ? order by r.id""", (mes,)).fetchall()
        return [dict(f) for f in filas]
