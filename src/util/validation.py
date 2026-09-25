from datetime import date, datetime


class ValidationError(ValueError):
    """Indica que un valor de entrada no cumple una regla de validación."""


def validate_non_empty(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError("El valor no puede estar vacío.")
    return normalized


def validate_salary(value: str) -> int:
    try:
        salary = int(value.strip())
    except ValueError as error:
        raise ValidationError("El salario debe ser un número entero.") from error

    if salary < 0:
        raise ValidationError("El salario no puede ser negativo.")
    return salary


def validate_date(value: str, allow_empty: bool = False, birth_date: bool = False) -> str | None:
    normalized = value.strip()
    if allow_empty and not normalized:
        return None

    try:
        parsed = datetime.strptime(normalized, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValidationError("La fecha debe tener el formato AAAA-MM-DD.") from error

    if birth_date and parsed >= date(2010, 1, 1):
        raise ValidationError("La fecha de nacimiento debe ser anterior a 2010-01-01.")
    return parsed.isoformat()


def validate_date_range(start_date: str, end_date: str | None) -> None:
    if end_date is not None and end_date < start_date:
        raise ValidationError("La fecha de baja no puede ser anterior a la fecha de alta.")
