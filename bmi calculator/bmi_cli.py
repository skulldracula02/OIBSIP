#!/usr/bin/env python3
"""
bmi_cli.py - Beginner tier: a command-line BMI calculator.

Run it with:
    python bmi_cli.py

It asks for weight in kilograms and height in metres, prints the BMI rounded
to two decimal places together with the health category, and keeps asking
until the numbers make sense.
"""

import sys

from bmi_core import (
    MAX_HEIGHT_M,
    MAX_WEIGHT_KG,
    MIN_HEIGHT_M,
    MIN_WEIGHT_KG,
    ValidationError,
    assess,
    check_range,
    parse_number,
)

# ANSI colour codes so the category stands out in the terminal.
COLOURS = {
    "#1a7f37": "\033[92m",  # green  - normal
    "#c8860d": "\033[93m",  # yellow - under/overweight
    "#c0182a": "\033[91m",  # red    - obese
}
RESET = "\033[0m"


def colourise(text, hex_colour, enabled):
    """Wrap text in an ANSI colour unless the stream is not a terminal."""
    if not enabled:
        return text
    return f"{COLOURS.get(hex_colour, '')}{text}{RESET}"


def prompt_for_number(prompt, field_name, low, high):
    """Keep asking until the user supplies a usable measurement.

    The number format and the allowed range are both checked here, so the
    user is asked again for this one field only, instead of being sent back
    to the start and losing the other measurement.

    Returns the parsed float. Raises EOFError if input ends (Ctrl+D / Ctrl+Z).
    """
    while True:
        try:
            raw = input(prompt)
        except EOFError:
            print()
            raise

        try:
            value = parse_number(raw, field_name)
            check_range(value, field_name, low, high)
            return value
        except ValidationError as error:
            print(f"  ! {error}")
            print("  Please try again.\n")


def calculate_once(use_colour):
    """Ask for both measurements, then print the result. Returns (bmi, category)."""
    try:
        weight = prompt_for_number(
            "Enter your weight in kg (e.g. 70.5): ", "Weight", MIN_WEIGHT_KG, MAX_WEIGHT_KG
        )
        height = prompt_for_number(
            "Enter your height in m (e.g. 1.75): ", "Height", MIN_HEIGHT_M, MAX_HEIGHT_M
        )
    except EOFError:
        return None

    try:
        bmi, category, hex_colour = assess(weight, height)
    except ValidationError as error:
        # Weight and height were individually plausible but the result is
        # absurd (normally centimetres entered where metres were expected).
        # Ask again rather than silently returning to the menu.
        print(f"  ! {error}")
        print("  Please try again.\n")
        return calculate_once(use_colour)

    rounded = round(bmi, 2)
    print()
    print(f"  Weight : {weight} kg")
    print(f"  Height : {height} m")
    print(f"  BMI    : {rounded:.2f}")
    print(f"  Result : {colourise(category, hex_colour, use_colour)}")
    print()

    if category == "Underweight":
        print("  Tip: a balanced, calorie-rich diet may help you reach a healthy range.")
    elif category == "Normal weight":
        print("  Tip: you are in the healthy range - keep up your current habits.")
    else:
        print("  Tip: regular activity and a balanced diet can help lower your BMI.")
    print("\n  Note: BMI is a rough screening tool, not a medical diagnosis.")

    return rounded, category


def show_table():
    """Print the reference categories."""
    print()
    print("  Category        BMI range")
    print("  --------------  ----------------")
    print("  Underweight     below 18.5")
    print("  Normal weight   18.5 - 24.9")
    print("  Overweight      25.0 - 29.9")
    print("  Obese           30.0 and above")
    print()


def main():
    use_colour = sys.stdout.isatty()

    print("=" * 46)
    print("  BMI CALCULATOR")
    print("=" * 46)
    show_table()

    while True:
        try:
            answer = input("Press Enter to calculate a BMI, 't' for the table, or 'q' to quit: ")
        except EOFError:
            print()
            break

        choice = answer.strip().lower()

        if choice == "q":
            print("Goodbye!")
            break
        if choice == "t":
            show_table()
            continue

        calculate_once(use_colour)

        try:
            again = input("Calculate another? (y/n): ").strip().lower()
        except EOFError:
            print()
            break
        if again not in ("y", "yes", ""):
            print("Goodbye!")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")
