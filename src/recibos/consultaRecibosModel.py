'''
HU15 "Consultar los recibos y los ingresos por actividad".

Para una temporada (por defecto, la de la oferta vigente) se listan los recibos, con filtros por
actividad y por estado, y un resumen por actividad con los ingresos (solo recibos cobrados), el
importe pendiente (emitidos) y el importe devuelto, ordenado de más a menos ingresos y con una fila
de totales. La rentabilidad se mide solo con los ingresos (no hay análisis de costes) y no hace
falta exportar la consulta.

Un recibo pertenece a la temporada en la que se emitió, que es la de la oferta de su actividad:
solo se emiten recibos de los meses en los que la actividad está en curso.
'''
from src.config import DB_PATH
from src.recibos.comun import (
    COBRADO,
    DEVUELTO,
    EMITIDO,
    ESTADOS_RECIBO,
    ReciboError,
    conectar,
    describirActividad,
)


class ConsultaRecibosModel:

    def __init__(self, db_path=None):
        self.db_path = db_path if db_path else DB_PATH

    #Temporadas (ofertas), la vigente primero y después de la más reciente a la más antigua
    def getTemporadas(self):
        with conectar(self.db_path) as conn:
            filas = conn.execute("""select id, curso, estado from Oferta
                                    order by estado = 'ACTIVA' desc, fechaInicio desc""").fetchall()
        return [dict(f) for f in filas]

    def getTemporadaVigente(self):
        with conectar(self.db_path) as conn:
            fila = conn.execute("select id, curso, estado from Oferta where estado = 'ACTIVA' "
                                "order by fechaInicio desc").fetchone()
        if fila is None:
            raise ReciboError("No hay una temporada vigente: elige una temporada")
        return dict(fila)

    #Actividades de una temporada para el filtro
    def getActividades(self, idOferta):
        with conectar(self.db_path) as conn:
            filas = conn.execute("""select a.id, m.nombre as modalidad, n.nombre as nivel
                                    from Actividad a
                                    inner join Modalidad m on m.id = a.idModalidad
                                    inner join Nivel n on n.id = a.idNivel
                                    where a.idOferta = ? order by m.nombre, a.idNivel, a.id""",
                                 (idOferta,)).fetchall()
        return [dict(f, nombre=describirActividad(f["modalidad"], f["nivel"])) for f in filas]

    def consultar(self, idOferta=None, idActividad=None, estado=None):
        '''
        Devuelve la temporada, la lista de recibos que cumplen los filtros, el resumen por
        actividad (que no depende del filtro de estado) y los totales.
        idActividad=None es «Todas» y estado=None es «Todos».
        '''
        if estado is not None and estado not in ESTADOS_RECIBO:
            raise ReciboError("El estado debe ser emitido, cobrado o devuelto")
        with conectar(self.db_path) as conn:
            if idOferta is None:
                temporada = self.getTemporadaVigente()
            else:
                fila = conn.execute("select id, curso, estado from Oferta where id = ?", (idOferta,)).fetchone()
                if fila is None:
                    raise ReciboError("La temporada no existe")
                temporada = dict(fila)
            actividades = conn.execute(
                """select a.id, m.nombre as modalidad, n.nombre as nivel from Actividad a
                   inner join Modalidad m on m.id = a.idModalidad
                   inner join Nivel n on n.id = a.idNivel
                   where a.idOferta = ? and (? is null or a.id = ?)""",
                (temporada["id"], idActividad, idActividad)).fetchall()
            if idActividad is not None and not actividades:
                raise ReciboError("La actividad no es de la temporada elegida")
            recibos = conn.execute(
                """select r.id, r.mes, r.importe, r.estado, rm.fechaEmision, a.id as idActividad,
                          m.nombre as modalidad, n.nombre as nivel, p.dni, p.nombre, p.apellidos
                   from Recibo r
                   inner join Remesa rm on rm.mes = r.mes
                   inner join Inscripcion i on i.id = r.idInscripcion
                   inner join Persona p on p.id = i.idPersona
                   inner join Actividad a on a.id = i.idActividad
                   inner join Modalidad m on m.id = a.idModalidad
                   inner join Nivel n on n.id = a.idNivel
                   where a.idOferta = ? and (? is null or a.id = ?)
                   order by r.mes desc, r.id""",
                (temporada["id"], idActividad, idActividad)).fetchall()

        resumen = {a["id"]: {"idActividad": a["id"],
                             "actividad": describirActividad(a["modalidad"], a["nivel"]),
                             "ingresos": 0.0, "pendiente": 0.0, "devuelto": 0.0, "recibos": 0}
                   for a in actividades}
        clave = {COBRADO: "ingresos", EMITIDO: "pendiente", DEVUELTO: "devuelto"}
        listado = []
        for r in recibos:
            fila = resumen[r["idActividad"]]
            fila[clave[r["estado"]]] += r["importe"]
            fila["recibos"] += 1
            if estado is None or r["estado"] == estado:
                listado.append(dict(r, actividad=describirActividad(r["modalidad"], r["nivel"]),
                                    socio=f"{r['nombre']} {r['apellidos']} ({r['dni']})"))
        filas = sorted(resumen.values(), key=lambda f: (-f["ingresos"], f["actividad"], f["idActividad"]))
        for f in filas:
            for c in ("ingresos", "pendiente", "devuelto"):
                f[c] = round(f[c], 2)
        totales = {c: round(sum(f[c] for f in filas), 2) for c in ("ingresos", "pendiente", "devuelto")}
        totales["recibos"] = sum(f["recibos"] for f in filas)
        return {"temporada": temporada, "recibos": listado, "resumen": filas, "totales": totales,
                "mensaje": None if listado else "No hay recibos para los filtros seleccionados"}
