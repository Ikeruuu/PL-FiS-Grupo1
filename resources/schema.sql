--Primero se deben borrar todas las tablas (de detalle a maestro) y lugo anyadirlas (de maestro a detalle)

drop table if exists Employee;
drop table if exists Company;

create table Company (id integer not null primary key, id2 integer, name varchar(32), startDate varchar(10));
create table Employee (id integer primary key,  name varchar(32), 
                       salary integer, birthDate varchar(10) , startDate varchar(10), endDate varChar (10), idCompany integer not null,
                       foreign key (idCompany) references Company (id), check (birthDate<'2010-01-01')
                      );

