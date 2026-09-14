"""
bmi_core.py - Shared BMI calculation and validation logic.

Both the command-line tool (bmi_cli.py) and the GUI application (bmi_gui.py)
use this module so the maths, categories and error handling stay identical.
"""

# (upper bound exclusive, category label, hex colour for the GUI)
CATEGORIES = [
    (18.5, "Underweight", "#c8860d"),
    (25.0, "Normal weight", "#1a7f37"),
    (30.0, "Overweight", "#c8860d"),
    (float("inf"), "Obese", "#c0182a"),
]

# Accepted measurement ranges, shared by the CLI and the GUI.
MIN_WEIGHT_KG = 1.0
MAX_WEIGHT_KG = 500.0
MIN_HEIGHT_M = 0.5
MAX_HEIGHT_M = 2.5
# BMI value falls outside this range -> almost certainly a typo
MIN_REASONABLE_BMI = 5.0
MAX_REASONABLE_BMI = 150.0


class ValidationError(ValueError):
    """Raised when user input cannot be turned into a valid measurement."""


def classify(bmi):
    """Return (category_label, colour_hex) for a BMI value."""
    for upper, label, colour in CATEGORIES:
        if bmi < upper:
            return label, colour
    # Unreachable: the last bucket ends at infinity.
    return "Obese", "#c0182a"


def calculate_bmi(weight_kg, height_m):
    # Returns BMI = weight / height squared, raising ValidationError on bad numbers.
    check_range(weight_kg, "Weight", MIN_WEIGHT_KG, MAX_WEIGHT_KG)
    check_range(height_m, "Height", MIN_HEIGHT_M, MAX_HEIGHT_M)

    bmi = weight_kg / (height_m ** 2)

    if not MIN_REASONABLE_BMI <= bmi <= MAX_REASONABLE_BMI:
        raise ValidationError(
            f"Result of {bmi:.1f} is not a realistic BMI. "
            "Check that height is in metres (e.g. 1.75) and weight in kilograms."
        )
    return bmi


def check_range(value, name, low, high):
    """Reject non-numeric, non-finite, negative or absurd values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number.")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValidationError(f"{name} must be a finite number.")
    if value <= 0:
        raise ValidationError(f"{name} must be greater than zero (got {value}).")
    if not low <= value <= high:
        raise ValidationError(
            f"{name} of {value} is out of range. Expected between {low} and {high}."
        )


def parse_number(text, field_name):
    """Convert raw text (from input() or a tkinter Entry) into a float.

    Accepts an optional trailing unit word such as '70 kg' or '1.75 m'
    and a comma decimal separator, since both are common typos.
    """
    if text is None:
        raise ValidationError(f"{field_name} is required.")

    cleaned = str(text).strip().lower()
    if not cleaned:
        raise ValidationError(f"{field_name} is required.")

    # Drop a trailing unit so "70 kg" and "1.75m" still work.
    # Longest suffixes come first: "cm" must be tried before "m".
    for unit in ("kilograms", "metres", "meters", "kgs", "cm", "kg", "m"):
        if cleaned.endswith(unit):
            cleaned = cleaned[: -len(unit)].strip()
            break

    cleaned = cleaned.replace(",", ".")

    try:
        value = float(cleaned)
    except ValueError:
        raise ValidationError(
            f"'{text}' is not a valid number for {field_name}. "
            "Please enter digits only, e.g. 70.5"
        ) from None

    if value != value or value in (float("inf"), float("-inf")):
        raise ValidationError(f"{field_name} must be a finite number.")

    return value


def assess(weight_kg, height_m):
    """Convenience: validate, calculate and classify in one call.

    Returns (bmi, category_label, colour_hex).
    """
    bmi = calculate_bmi(weight_kg, height_m)
    label, colour = classify(bmi)
    return bmi, label, colour
