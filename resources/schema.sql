--Primero se deben borrar todas las tablas (de detalle a maestro) y lugo anyadirlas (de maestro a detalle)

drop table if exists Employee;
drop table if exists Company;

drop table if exists Persona;
drop table if exists Horario;
drop table if exists Actividad;
drop table if exists Instalacion;
drop table if exists Nivel;
drop table if exists Modalidad;

create table Company (id integer not null primary key, id2 integer, name varchar(32), startDate varchar(10));
create table Employee (id integer primary key,  name varchar(32),
                       salary integer, birthDate varchar(10) , startDate varchar(10), endDate varChar (10), idCompany integer not null,
                       foreign key (idCompany) references Company (id), check (birthDate<'2010-01-01')
                      );

--Centro Deportivo Inteligente
--Datos maestros fijos indicados por el cliente (modalidades y niveles)
create table Modalidad (id integer not null primary key, nombre varchar(40) not null unique);
create table Nivel (id integer not null primary key, nombre varchar(20) not null unique);

--HU3: instalaciones del centro (datos de prueba) con su capacidad maxima de personas
create table Instalacion (id integer not null primary key, nombre varchar(40) not null unique,
                          capacidad integer not null, check (capacidad > 0)
                         );

--Una actividad es una modalidad con un nivel, un periodo (fechas) y un numero de plazas.
--idInstalacion es null hasta que se asigna (HU3). Una actividad, una instalacion.
create table Actividad (id integer not null primary key, idOferta integer not null, idModalidad integer not null, idNivel integer not null,
                        fechaInicio varchar(10) not null, fechaFin varchar(10) not null,
                        plazas integer not null, idInstalacion integer,
                        foreign key (idOferta) references Oferta(id),
                        foreign key (idModalidad) references Modalidad (id),
                        foreign key (idNivel) references Nivel (id),
                        foreign key (idInstalacion) references Instalacion (id),
                        check (plazas > 0), check (fechaInicio <= fechaFin)
                       );

--Periodicidad semanal de cada actividad: dia de la semana (1=lunes ... 7=domingo) y franja horaria (HH:MM)
create table Horario (id integer not null primary key, idActividad integer not null,
                      diaSemana integer not null, horaInicio varchar(5) not null, horaFin varchar(5) not null,
                      foreign key (idActividad) references Actividad (id),
                      check (diaSemana between 1 and 7), check (horaInicio < horaFin)
                     );

--HU8: personas (socios y no socios). El DNI se guarda normalizado (mayúsculas, sin espacios ni guiones).
--Los socios tienen número de socio (secuencial por antigüedad) y fecha de alta como socio;
--los no socios los tienen a null.
create table Persona (id integer not null primary key, dni varchar(20) not null unique,
                      nombre varchar(40) not null, apellidos varchar(80) not null,
                      fechaNacimiento varchar(10), telefono varchar(20), correo varchar(80),
                      numSocio integer unique, fechaAltaSocio varchar(10),
                      check (numSocio is null or numSocio > 0),
                      check ((numSocio is null) = (fechaAltaSocio is null)),
                      check (telefono is not null or correo is not null)
                     );

-- HU: 
create table Oferta (
    id integer not null primary key,
    curso varchar(20) not null,
    fechaInicio varchar(10) not null,
    fechaFin varchar(10) not null,
    estado varchar(10) not null,
    check (estado in ('ACTIVA','INACTIVA')),
    check (fechaInicio < fechaFin)
);