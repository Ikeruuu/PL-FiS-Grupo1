from src.config import DB_PATH
from src.util.database import Database


class ModalidadInstalacionError(Exception):
    '''Error de la HU19. El mensaje se muestra tal cual al usuario.'''


class ConfirmacionRequerida(ModalidadInstalacionError):
    '''
    HU19: al quitar modalidades, alguna actividad ya asignada quedaría incoherente.
    afectadas contiene esas actividades para mostrarlas antes de confirmar.
    '''

    def __init__(self, mensaje, afectadas):
        super().__init__(mensaje)
        self.afectadas = afectadas


class ModalidadInstalacionModel:
    '''
    Objetos de negocio de la HU19 "Indicar las modalidades que admite cada instalación".
    La comprobación al asignar está en InstalacionModel.asignarInstalacion.
    '''

    def __init__(self, db_path=None):
        self.db = Database(db_path if db_path else DB_PATH)

    def getModalidades(self):
        return self.db.executeQuery("select id, nombre from Modalidad order by id")

    #Ids de las modalidades que admite una instalación
    def getModalidadesAdmitidas(self, id_instalacion):
        res = self.db.executeQuery("""select idModalidad from InstalacionModalidad
                                      where idInstalacion = ? order by idModalidad""", id_instalacion)
        return [r["idModalidad"] for r in res]

    #Resumen de cada instalación con los nombres de las modalidades que admite
    def getConfiguracion(self):
        filas = self.db.executeQuery("""select i.id, i.nombre, m.nombre as modalidad
                                        from Instalacion i
                                        left join InstalacionModalidad im on im.idInstalacion = i.id
                                        left join Modalidad m on m.id = im.idModalidad
                                        order by i.id, m.id""")
        config = {}
        for f in filas:
            entrada = config.setdefault(f["id"], {"id": f["id"], "nombre": f["nombre"], "modalidades": []})
            if f["modalidad"] is not None:
                entrada["modalidades"].append(f["modalidad"])
        return list(config.values())

    #Actividades asignadas a la instalación cuya modalidad no está entre las indicadas
    def getActividadesAfectadas(self, id_instalacion, ids_modalidades):
        actividades = self.db.executeQuery("""select a.id, a.idModalidad, m.nombre as modalidad, n.nombre as nivel
                                              from Actividad a
                                              inner join Modalidad m on m.id = a.idModalidad
                                              inner join Nivel n on n.id = a.idNivel
                                              where a.idInstalacion = ? order by a.id""", id_instalacion)
        return [a for a in actividades if a["idModalidad"] not in set(ids_modalidades)]

    #Guarda las modalidades que admite la instalación. Si alguna actividad ya asignada quedaría
    #incoherente, lanza ConfirmacionRequerida salvo que se confirme (confirmar=True).
    def guardarModalidades(self, id_instalacion, ids_modalidades, confirmar=False):
        instalacion = self.db.executeQuery("select id, nombre from Instalacion where id = ?", id_instalacion)
        if not instalacion:
            raise ModalidadInstalacionError(f"No existe la instalación {id_instalacion}")
        existentes = {m["id"] for m in self.getModalidades()}
        ids = sorted(set(ids_modalidades))
        for idModalidad in ids:
            if idModalidad not in existentes:
                raise ModalidadInstalacionError(f"No existe la modalidad {idModalidad}")

        afectadas = self.getActividadesAfectadas(id_instalacion, ids)
        if afectadas and not confirmar:
            lista = ", ".join(f"{a['modalidad']} {a['nivel'].lower()} (actividad {a['id']})" for a in afectadas)
            raise ConfirmacionRequerida(
                f"Estas actividades asignadas a {instalacion[0]['nombre']} quedarían incoherentes: "
                f"{lista}. ¿Guardar igualmente?", afectadas)

        #Borrar e insertar en una misma transacción para no dejar la configuración a medias
        with self.db._connect() as (conn, curs):
            curs.execute("delete from InstalacionModalidad where idInstalacion = ?", (id_instalacion,))
            curs.executemany("insert into InstalacionModalidad(idInstalacion, idModalidad) values (?, ?)",
                             [(id_instalacion, m) for m in ids])
            conn.commit()
        return f"Modalidades de {instalacion[0]['nombre']} guardadas"

    #Informe (solo consulta): asignaciones existentes cuya instalación no admite la modalidad
    def getIncoherencias(self):
        return self.db.executeQuery("""select a.id, m.nombre as modalidad, n.nombre as nivel,
                                              i.nombre as instalacion
                                       from Actividad a
                                       inner join Instalacion i on i.id = a.idInstalacion
                                       inner join Modalidad m on m.id = a.idModalidad
                                       inner join Nivel n on n.id = a.idNivel
                                       where not exists (select 1 from InstalacionModalidad im
                                                         where im.idInstalacion = a.idInstalacion
                                                           and im.idModalidad = a.idModalidad)
                                       order by i.nombre, a.id""")
