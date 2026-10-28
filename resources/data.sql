--Carga inicial de datos. Se cargan de maestro a detalle

--Company
insert into Company(id,id2,name,startDate) values(1,null,'Company 1','2020-05-03');
insert into Company(id,id2,name,startDate) values(2,3333,'Company 2','1999-12-24');
insert into Company(id,id2,name,startDate) values(3, 2222,'Company 3','2013-01-23');
--Employee
insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E1',2000,'2000-01-01','2020-01-01',null,3);
insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E2',3000,'1998-01-01','2020-01-01','2021-01-01', 2);
insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E3',1500,'2001-01-01','2020-01-01', null, 2);
insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E4',1000,'2004-01-01','2023-01-01', null, 3);
insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E5',4000,'1990-01-01','2013-01-01', null, 3 );
insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E6',1000,'2000-01-01','2021-01-01', '2023-01-01',3);


--Centro Deportivo Inteligente

--Modalidad (datos fijos del cliente)
insert into Modalidad(id,nombre) values(1,'Natación');
insert into Modalidad(id,nombre) values(2,'Pilates');
insert into Modalidad(id,nombre) values(3,'Acondicionamiento físico general');
insert into Modalidad(id,nombre) values(4,'Pádel');
insert into Modalidad(id,nombre) values(5,'Tenis');
--Nivel (datos fijos del cliente)
insert into Nivel(id,nombre) values(1,'Iniciación');
insert into Nivel(id,nombre) values(2,'Medio');
insert into Nivel(id,nombre) values(3,'Avanzado');
--Instalacion (datos de prueba, HU3)
insert into Instalacion(id,nombre,capacidad) values(1,'Piscina',25);
insert into Instalacion(id,nombre,capacidad) values(2,'Sala polivalente',15);
insert into Instalacion(id,nombre,capacidad) values(3,'Gimnasio',20);
insert into Instalacion(id,nombre,capacidad) values(4,'Pista de pádel 1',4);
insert into Instalacion(id,nombre,capacidad) values(5,'Pista de pádel 2',4);
insert into Instalacion(id,nombre,capacidad) values(6,'Pista de tenis',4);
-- Oferta 
insert into Oferta (id,curso,fechaInicio,fechaFin,estado)
values(1,'2026-2027','2026-10-01','2027-06-30','ACTIVA');
--Actividad (datos de prueba). Las tres primeras ya tienen instalación asignada
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(1,1,4,2,'2026-10-01','2027-06-30',4,4);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(2,1,1,1,'2026-10-01','2027-06-30',20,1);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(3,1,2,1,'2026-10-01','2026-12-31',12,2);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(4,1,4,1,'2026-10-01','2027-06-30',4,null);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(5,1,4,3,'2026-10-01','2027-06-30',4,null);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(6,1,2,2,'2027-01-01','2027-06-30',15,null);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(7,1,3,2,'2026-10-01','2027-06-30',20,null);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(8,1,5,1,'2026-10-01','2027-06-30',4,null);
--Actividades de la Piscina para la consulta de ocupación
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(9,1,1,3,'2026-10-01','2027-06-30',15,1);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(10,1,1,2,'2027-01-01','2027-06-30',20,1);
--Cuota mensual de cada actividad en euros (HU Consultar la oferta de actividades disponibles)
update Actividad set cuota = 30 where id in (1, 4, 5);
update Actividad set cuota = 25 where id in (2, 9, 10);
update Actividad set cuota = 20 where id in (3, 6);
update Actividad set cuota = 18 where id = 7;
update Actividad set cuota = 35 where id = 8;
--Horario (1=lunes ... 7=domingo)
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,1,1,'18:00','19:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,1,3,'18:00','19:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,2,2,'10:00','11:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,2,4,'10:00','11:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,3,1,'09:00','10:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,4,1,'18:30','19:30');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,5,1,'19:00','20:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,5,3,'19:00','20:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,6,1,'09:00','10:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,7,5,'17:00','18:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,8,6,'10:00','11:30');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,9,1,'08:00','09:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,9,1,'21:00','22:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,10,2,'11:00','12:00');
--Persona (datos maestros de prueba, HU8). Los socios ya están en el sistema y su número
--de socio es secuencial por orden de antigüedad (fecha de alta como socio).
insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values(null,'10000001A','Marta','García López','1975-03-12','600111001','marta.garcia@example.com',1,'2005-09-01');
insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values(null,'10000002B','Luis','Fernández Díaz','1982-07-25','600111002',null,2,'2009-01-15');
insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values(null,'10000003C','Ana','Suárez Menéndez','1990-11-03',null,'ana.suarez@example.com',3,'2014-06-20');
insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values(null,'10000004D','Pablo','Álvarez Rodríguez','2001-02-17','600111004','pablo.alvarez@example.com',4,'2019-10-02');
insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values(null,'10000005E','Lucía','Martínez Pérez','1998-05-30','600111005','lucia.martinez@example.com',5,'2023-03-11');
--No socios
insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values(null,'20000001F','Jorge','Sánchez Vega','1995-08-08','611222001',null,null,null);
insert into Persona(id,dni,nombre,apellidos,fechaNacimiento,telefono,correo,numSocio,fechaAltaSocio) values(null,'20000002G','Elena','Iglesias Prieto',null,null,'elena.iglesias@example.com',null,null);
