-- Datos históricos importados, vinculados al catálogo y a la temporada del CSV.
BEGIN;
create table if not exists ActividadHistorica (
    id integer primary key,
    temporada text not null,
    idModalidad integer not null references Modalidad(id),
    idNivel integer not null references Nivel(id),
    plazas integer not null check (plazas > 0),
    unique (temporada, idModalidad, idNivel)
);
create table if not exists InscripcionHistorica (
    id integer primary key,
    idActividad integer not null references ActividadHistorica(id),
    tipo text not null check (tipo in ('SOCIO', 'NO_SOCIO')),
    identificador text not null,
    estado text not null check (estado in ('CONFIRMADA', 'EN_ESPERA', 'PENDIENTE_ACEPTACION', 'CANCELADA')),
    fecha text not null,
    unique (idActividad, tipo, identificador)
);
COMMIT;
