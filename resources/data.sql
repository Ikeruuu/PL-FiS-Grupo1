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


