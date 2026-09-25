from src.config import DB_PATH
from src.util.database import Database


class EmployeeModel:
    '''
    Clase que representa los objetos de negocio (model) relativos a las funcionalidades de
    los empleados. Varios métodos de esta clase se invocarán desde la vista (EmployeeView), y los resultados
    se devolverán nuevamente a la vista para su visualización
    '''

    def __init__(self, db_path=None):
        self.db = Database(db_path if db_path else DB_PATH)

    #Obtiene la lista de empleados para una compañia especificada por su nombre
    def getAllEmployees(self, company_name):
        query = """select Company.name as Compania, Employee.id as IdEmpleado, Employee.name as NombreEmpleado, Employee.salary as Salario 
                   from Company inner join Employee on Company.id=Employee.idCompany
                   where Company.name = ? order by Employee.id asc
                """
        return self.db.executeQuery(query, company_name)

    #Obtiene la lista de empleados para una compañia especificada por su nombre con antiguedad superior a una año (incluyendo a no activos)
    #current_date es la fecha que se quiere indicar para la fecha actual (a efectos de pruebas)
    def getEmployeesByYears(self, current_date, company_name):
        query = """select Company.name as Compania, Employee.name as NombreEmpleado, 
	                    cast((julianday(coalesce(Employee.endDate, ?)) - julianday(Employee.startDate)) / 365 as int) as Years
	                from Company inner join Employee on Company.id=Employee.idCompany
                    where Compania = ? and (julianday(coalesce(Employee.endDate, ?)) - julianday(Employee.startDate)) / 365 >= 1
                """
        return self.db.executeQuery(query, current_date, company_name, current_date)

    #Obtiene resumen (total empleados y media de salario) para una compañia especificada por su nombre
    def getSummaryEmployees(self, company_name):
        query = """select count(Employee.id) as total, avg(Employee.salary) as average
                   from Company inner join Employee on Company.id=Employee.idCompany
                   where Company.name = ?
                   group by (Company.id)
                """
        return self.db.executeQuery(query, company_name)

    #Obtiene el salario medio de todos los empleados por compañia
    def getAvgSalary(self):
        query = """select Company.name, avg(Employee.salary) as avgSalary
                  from Company left join Employee on Company.id=Employee.idCompany
                  group by (Company.id)
                """
        return self.db.executeQuery(query)

    #Inserción de los datos de un empleado (name,salary,birthDate,startDate,endDate,idCompany) en una compañia
    #Notar que no es necesario indicar explícitamente el valor de la clave del empleado (id),
    #ya que cuando éste es null, sqlite lo genera de forma autoincremental
    def insertEmployee(self, name, salary, birth_date, start_date, end_date, id_company):
        query = """
                insert into Employee(id,name,salary,birthDate,startDate,endDate,idCompany) values (null,?,?,?,?,?,?)
                """
        self.db.executeUpdateQuery(query, name, salary, birth_date, start_date, end_date, id_company)

    #Obtiene el id de una compañia especificada por su nombre.
    def getIdCompany(self, company_name):
        query = """select id from Company
                   where Company.name = ?
                """
        res = self.db.executeQuery(query, company_name)
        if len(res) == 1:
            return res[0].get("id")
        else:
            return None