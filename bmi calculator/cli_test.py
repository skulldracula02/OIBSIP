"""Drive bmi_cli.py with scripted input and assert on what it prints."""
import io
import sys
from contextlib import redirect_stdout

import bmi_cli


def run(answers):
    """Feed answers to the CLI as if typed, return everything it printed."""
    original_stdin = sys.stdin
    sys.stdin = io.StringIO("\n".join(answers) + "\n")
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            bmi_cli.main()
    except SystemExit:
        pass
    finally:
        sys.stdin = original_stdin
    return buffer.getvalue()


def check(label, answers, must_contain, must_not_contain=()):
    out = run(answers)
    for needle in must_contain:
        assert needle in out, f"{label}: missing {needle!r}\n{out}"
    for needle in must_not_contain:
        assert needle not in out, f"{label}: unexpected {needle!r}\n{out}"
    print(f"ok  {label}")


# The menu prompt consumes one line before the fields.
check(
    "normal weight",
    ["", "70.5", "1.75", "n"],
    ["BMI    : 23.02", "Normal weight"],
)
check(
    "underweight",
    ["", "45", "1.75", "n"],
    ["BMI    : 14.69", "Underweight"],
)
check(
    "overweight",
    ["", "85", "1.75", "n"],
    ["BMI    : 27.76", "Overweight"],
)
check(
    "obese",
    ["", "110", "1.75", "n"],
    ["BMI    : 35.92", "Obese"],
)
check(
    "non-numeric weight is rejected",
    ["", "abc", "70", "1.75", "n"],
    ["'abc' is not a valid number for Weight", "BMI    : 22.86"],
)
check(
    "negative weight is rejected",
    ["", "-70", "70", "1.75", "n"],
    ["must be greater than zero", "BMI    : 22.86"],
)
check(
    "empty input is rejected",
    ["", "", "70", "1.75", "n"],
    ["Weight is required", "BMI    : 22.86"],
)
check(
    "centimetres instead of metres is rejected, then asked again",
    ["", "70", "175", "1.75", "n"],
    ["Height of 175.0 is out of range", "Please try again", "BMI    : 22.86"],
)
check(
    "unit suffixes and comma decimals are accepted",
    ["", "70 kg", "1,75", "n"],
    ["BMI    : 22.86"],
)
check(
    "table option prints the reference ranges",
    ["t", "q"],
    ["Underweight     below 18.5", "Obese           30.0 and above"],
)
check(
    "quit exits cleanly",
    ["q"],
    ["Goodbye!"],
    must_not_contain=["Traceback"],
)
check(
    "round result is shown to 2 decimals",
    ["", "70", "1.7", "n"],
    ["BMI    : 24.22"],
)

print("\nALL CLI TESTS PASSED")
