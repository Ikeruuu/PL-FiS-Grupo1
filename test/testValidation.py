import unittest

from src.util.validation import (
    ValidationError,
    validate_date,
    validate_date_range,
    validate_non_empty,
    validate_salary,
)


class TestValidation(unittest.TestCase):

    def testValidateNonEmpty(self):
        self.assertEqual(validate_non_empty("  Employee  "), "Employee")

    def testValidateNonEmptyRejectsBlankValue(self):
        with self.assertRaises(ValidationError):
            validate_non_empty("  ")

    def testValidateSalary(self):
        self.assertEqual(validate_salary(" 1000 "), 1000)

    def testValidateSalaryRejectsInvalidValues(self):
        for value in ("not-a-number", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_salary(value)

    def testValidateDate(self):
        self.assertEqual(validate_date("2000-01-02"), "2000-01-02")
        self.assertIsNone(validate_date("", allow_empty=True))

    def testValidateBirthDateRejectsRecentDate(self):
        with self.assertRaises(ValidationError):
            validate_date("2024-01-01", birth_date=True)

    def testValidateDateRange(self):
        validate_date_range("2020-01-01", "2021-01-01")
        validate_date_range("2020-01-01", None)
        with self.assertRaises(ValidationError):
            validate_date_range("2021-01-01", "2020-01-01")


if __name__ == "__main__":
    unittest.main()
