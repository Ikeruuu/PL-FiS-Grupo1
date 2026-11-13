--Datos de ejemplo del Sprint 2 (bloque de ocupación de instalaciones y asistencia).
--HU16, HU17 y HU18. Se cargan DESPUÉS de data.sql, solo en la aplicación (main.py y demo_local.py).
--Están en un fichero aparte para no cambiar los datos que usan las pruebas de las demás historias.

--HU16: oferta de la temporada anterior (inactiva) con actividades e inscripciones,
--para poder añadir actividades a la oferta actual viendo la demanda que tuvieron
insert into Oferta (id,curso,fechaInicio,fechaFin,estado) values(2,'2025-2026','2025-10-01','2026-06-30','INACTIVA');
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(11,2,4,2,'2025-10-01','2026-06-30',4,4);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(12,2,1,1,'2025-10-01','2026-06-30',20,1);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(13,2,2,2,'2025-10-01','2026-06-30',15,2);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(14,2,5,1,'2025-10-01','2026-06-30',4,6);
insert into Actividad(id,idOferta,idModalidad,idNivel,fechaInicio,fechaFin,plazas,idInstalacion) values(15,2,3,3,'2025-10-01','2026-06-30',20,3);
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,11,1,'18:00','19:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,11,3,'18:00','19:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,12,2,'10:00','11:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,12,4,'10:00','11:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,13,5,'09:00','10:00');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,14,6,'10:00','11:30');
insert into Horario(id,idActividad,diaSemana,horaInicio,horaFin) values(null,15,2,'19:00','20:00');
--Inscripciones de la temporada anterior: pádel medio lleno con lista de espera, tenis lleno,
--natación con pocas inscripciones y acondicionamiento físico avanzado sin inscripciones
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(1,11,'2025-09-02 10:00:00','2025-09-02 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(2,11,'2025-09-02 11:00:00','2025-09-02 11:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(3,11,'2025-09-03 09:00:00','2025-09-03 09:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(4,11,'2025-09-03 12:00:00','2025-09-03 12:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(5,11,'2025-09-04 09:00:00',null,'EN_ESPERA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(6,11,'2025-09-05 09:00:00',null,'EN_ESPERA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(1,12,'2025-09-02 10:30:00','2025-09-02 10:30:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(7,12,'2025-09-10 10:30:00','2025-09-10 10:30:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(2,13,'2025-09-02 12:00:00','2025-09-02 12:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(3,13,'2025-09-02 12:30:00','2025-09-02 12:30:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(4,13,'2025-09-02 13:00:00','2025-09-02 13:00:00','CANCELADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(5,14,'2025-09-06 10:00:00','2025-09-06 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(6,14,'2025-09-06 10:30:00','2025-09-06 10:30:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(7,14,'2025-09-06 11:00:00','2025-09-06 11:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(1,14,'2025-09-06 11:30:00','2025-09-06 11:30:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(2,14,'2025-09-07 11:30:00',null,'EN_ESPERA');

--HU17 y HU18: inscripciones en la oferta actual y asistencia de algunas sesiones de octubre
--Pádel medio (act. 1, 4 plazas): personas 1-4 inscritas y la 6 en espera
--Natación iniciación (act. 2, 20 plazas): personas 1, 5, 6, 7 inscritas y la 4 cancelada
--Pilates iniciación (act. 3, 12 plazas): personas 2, 3, 5, 6, 7 inscritas (asiste poca gente)
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(1,1,'2026-09-10 10:00:00','2026-09-10 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(2,1,'2026-09-11 10:00:00','2026-09-11 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(3,1,'2026-09-12 10:00:00','2026-09-12 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(4,1,'2026-09-13 10:00:00','2026-09-13 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(1,2,'2026-09-10 10:00:00','2026-09-10 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(5,2,'2026-09-11 10:00:00','2026-09-11 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(6,2,'2026-09-12 10:00:00','2026-09-12 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(7,2,'2026-09-13 10:00:00','2026-09-13 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(2,3,'2026-09-10 10:00:00','2026-09-10 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(3,3,'2026-09-11 10:00:00','2026-09-11 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(5,3,'2026-09-12 10:00:00','2026-09-12 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(6,3,'2026-09-13 10:00:00','2026-09-13 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(7,3,'2026-09-14 10:00:00','2026-09-14 10:00:00','CONFIRMADA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(6,1,'2026-09-15 10:00:00',null,'EN_ESPERA');
insert into Inscripcion(idPersona,idActividad,fechaSolicitud,fechaInscripcion,estado) values(4,2,'2026-09-14 10:00:00','2026-09-14 10:00:00','CANCELADA');
--Asistencia registrada (1 = asistió). La sesión de pádel del 14/10 se canceló por fuerza mayor.
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=1 and idActividad=1),'2026-10-05','18:00',1,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=2 and idActividad=1),'2026-10-05','18:00',1,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=3 and idActividad=1),'2026-10-05','18:00',1,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=4 and idActividad=1),'2026-10-05','18:00',1,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=1 and idActividad=1),'2026-10-07','18:00',1,'2026-10-07 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=2 and idActividad=1),'2026-10-07','18:00',1,'2026-10-07 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=3 and idActividad=1),'2026-10-07','18:00',1,'2026-10-07 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=4 and idActividad=1),'2026-10-07','18:00',0,'2026-10-07 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=1 and idActividad=1),'2026-10-12','18:00',1,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=2 and idActividad=1),'2026-10-12','18:00',1,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=3 and idActividad=1),'2026-10-12','18:00',1,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=4 and idActividad=1),'2026-10-12','18:00',1,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=1 and idActividad=1),'2026-10-19','18:00',1,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=2 and idActividad=1),'2026-10-19','18:00',0,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=3 and idActividad=1),'2026-10-19','18:00',1,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=4 and idActividad=1),'2026-10-19','18:00',1,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=1 and idActividad=2),'2026-10-06','10:00',1,'2026-10-06 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=5 and idActividad=2),'2026-10-06','10:00',1,'2026-10-06 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=6 and idActividad=2),'2026-10-06','10:00',1,'2026-10-06 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=7 and idActividad=2),'2026-10-06','10:00',1,'2026-10-06 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=1 and idActividad=2),'2026-10-08','10:00',1,'2026-10-08 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=5 and idActividad=2),'2026-10-08','10:00',1,'2026-10-08 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=6 and idActividad=2),'2026-10-08','10:00',0,'2026-10-08 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=7 and idActividad=2),'2026-10-08','10:00',1,'2026-10-08 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=1 and idActividad=2),'2026-10-13','10:00',1,'2026-10-13 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=5 and idActividad=2),'2026-10-13','10:00',1,'2026-10-13 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=6 and idActividad=2),'2026-10-13','10:00',1,'2026-10-13 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=7 and idActividad=2),'2026-10-13','10:00',1,'2026-10-13 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=2 and idActividad=3),'2026-10-05','09:00',0,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=3 and idActividad=3),'2026-10-05','09:00',0,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=5 and idActividad=3),'2026-10-05','09:00',0,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=6 and idActividad=3),'2026-10-05','09:00',1,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=7 and idActividad=3),'2026-10-05','09:00',1,'2026-10-05 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=2 and idActividad=3),'2026-10-12','09:00',1,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=3 and idActividad=3),'2026-10-12','09:00',0,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=5 and idActividad=3),'2026-10-12','09:00',0,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=6 and idActividad=3),'2026-10-12','09:00',1,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=7 and idActividad=3),'2026-10-12','09:00',0,'2026-10-12 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=2 and idActividad=3),'2026-10-19','09:00',0,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=3 and idActividad=3),'2026-10-19','09:00',0,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=5 and idActividad=3),'2026-10-19','09:00',0,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=6 and idActividad=3),'2026-10-19','09:00',0,'2026-10-19 20:00:00');
insert into Asistencia(idInscripcion,fecha,horaInicio,asistio,fechaRegistro) values((select id from Inscripcion where idPersona=7 and idActividad=3),'2026-10-19','09:00',1,'2026-10-19 20:00:00');
insert into SesionCancelada(idActividad,fecha,horaInicio,fechaCancelacion) values(1,'2026-10-14','18:00','2026-10-14 12:00:00');
