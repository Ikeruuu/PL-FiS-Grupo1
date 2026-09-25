import os
import tempfile
import unittest
from unittest.mock import patch

from src.config import SCHEMA_PATH
from src.employees.employeeModel import EmployeeModel
from src.employees.employeeView import EmployeeView
from src.util.database import Database
from src.util.unexpectedException import UnexpectedException

TEST_DATA = """
    insert into Company(id,id2,name,startDate) values(1,null,'Company 1','2020-05-03');
    insert into Company(id,id2,name,startDate) values(2,3333,'Company 2','1999-12-24');
    insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E1',2000,'2000-01-01','2020-01-01',null,2);
    insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E1',2000,'2000-01-01','2020-01-01','2021-01-01',2);
    insert into Employee (id,name,salary,birthDate,startDate,endDate,idCompany) values (null,'E1',2000,'2000-01-01','2020-01-01','2020-10-01',2);
"""


class TestEmployee(unittest.TestCase):

    def setUp(self):
        #Crea una base de datos temporal e independiente para cada test
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name

        self.db = Database(self.db_path)
        self.db.executeScript(SCHEMA_PATH) #Genera el esquema ejecutando el script SCHEMA
        self.db.executeScriptBatch(TEST_DATA) #Carga de datos de prueba

        self.empleado = EmployeeModel(db_path=self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def testGetAllEmployeesEmptyCompany(self):
        listEmployeesC1 = self.empleado.getAllEmployees('Company 1')
        self.assertEqual(len(listEmployeesC1), 0)

    def testGetAllEmployees(self):
        listEmployeesC2 = self.empleado.getAllEmployees('Company 2')
        expectedOutput = [
            {"Compania": 'Company 2', "IdEmpleado": 1, "NombreEmpleado": 'E1', "Salario": 2000},
            {"Compania": 'Company 2', "IdEmpleado": 2, "NombreEmpleado": 'E1', "Salario": 2000},
            {"Compania": 'Company 2', "IdEmpleado": 3, "NombreEmpleado": 'E1', "Salario": 2000},
        ]
        self.assertEqual(listEmployeesC2, expectedOutput)

    def testGetEmployeesByYears(self):
        #Con fecha actual 2024-06-01, E1 (alta 2020-01-01 sin baja) lleva >4 años,
        #y E1 (alta 2020-01-01, baja 2021-01-01) lleva 1 año; el tercero no llega al año.
        listEmployees = self.empleado.getEmployeesByYears('2024-06-01', 'Company 2')
        self.assertEqual(len(listEmployees), 2)
        self.assertTrue(all(row["Years"] >= 1 for row in listEmployees))

    def testInsertEmployee(self):
        self.empleado.insertEmployee('E7', 5000, '2000-05-01', '2019-01-01', None, 2)
        listEmployees = self.empleado.getAllEmployees('Company 2')
        self.assertEqual(len(listEmployees), 4)
        row = self.empleado.db.executeQuery(
            "select endDate, idCompany from Employee where name = ?", 'E7')
        self.assertEqual(len(row), 1)
        self.assertIsNone(row[0].get("endDate"))
        self.assertEqual(row[0].get("idCompany"), 2)

    def testGetSummaryEmployees(self):
        summary = self.empleado.getSummaryEmployees('Company 2')
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0].get("total"), 3)
        self.assertEqual(summary[0].get("average"), 2000.0)

    def testGetAvgSalary(self):
        result = self.empleado.getAvgSalary()
        self.assertEqual(len(result), 2)
        byCompany = {row["name"]: row["avgSalary"] for row in result}
        self.assertEqual(byCompany["Company 1"], None)
        self.assertEqual(byCompany["Company 2"], 2000.0)

    def testGetIdCompany(self):
        self.assertEqual(self.empleado.getIdCompany('Company 1'), 1)
        self.assertEqual(self.empleado.getIdCompany('Company 2'), 2)
        self.assertIsNone(self.empleado.getIdCompany('No existe'))

    def testForeignKeysAreEnabled(self):
        with self.assertRaises(UnexpectedException):
            self.db.executeUpdateQuery(
                "insert into Employee(name, idCompany) values (?, ?)",
                'Invalid employee',
                999,
            )

    def testViewValidatesSalary(self):
        view = EmployeeView()
        with patch("builtins.input", side_effect=["not-a-number", "-1", "1000"]):
            self.assertEqual(view._read_salary(), 1000)

    def testViewValidatesDates(self):
        view = EmployeeView()
        with patch("builtins.input", side_effect=["2024-01-01", "2000-01-01"]):
            self.assertEqual(
                view._read_date("Fecha nacimiento (aaaa-mm-dd): ", birth_date=True),
                "2000-01-01",
            )


if __name__ == '__main__':
    unittest.main()