#!/usr/bin/env python3
"""
password_generator.py
=====================
BEGINNER TIER - Random Password Generator (command line).

Feature checklist for this file:
  [x] Prompt for desired password length (minimum 8 enforced)
  [x] Prompt for which character types to include
      (uppercase / lowercase / numbers / symbols, at least 2 required)
  [x] Generate and display a password matching all criteria
  [x] Input validation: reject invalid lengths or too few character types
  [x] Option to generate another password without restarting the program

Run with:  python password_generator.py
"""

from __future__ import annotations

import sys

from password_core import (
    CHAR_TYPE_LABELS,
    MIN_LENGTH,
    PasswordError,
    PasswordOptions,
    evaluate_strength,
    generate_password,
)

# --------------------------------------------------------------------------
# Input helpers (validation lives here)
# --------------------------------------------------------------------------

def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question and keep asking until the answer is clear."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = input(prompt + suffix).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  ! Please answer 'y' or 'n'.")


def ask_length() -> int:
    """Prompt for the password length, rejecting anything below MIN_LENGTH."""
    while True:
        raw = input(
            f"Desired password length (minimum {MIN_LENGTH}, recommended 16): "
        ).strip().lstrip("\ufeff")   # tolerate a stray BOM from pasted input
        if not raw:
            print("  ! Please enter a number.")
            continue
        try:
            length = int(raw)
        except ValueError:
            print(f"  ! '{raw}' is not a whole number. Try again.")
            continue
        if length < MIN_LENGTH:
            print(f"  ! Too short. The minimum allowed length is {MIN_LENGTH}.")
            continue
        if length > 256:
            print("  ! That is longer than you will ever need (max 256). Clamping.")
            return 256
        return length


def ask_character_types() -> dict[str, bool]:
    """Ask which character types to include; enforce the 'at least 2' rule."""
    print("\nCharacter types to include:")
    for key, label in CHAR_TYPE_LABELS.items():
        print(f"  - {key}: {label}")
    print()

    while True:
        choices = {
            "lowercase": ask_yes_no("Include lowercase letters (a-z)?", True),
            "uppercase": ask_yes_no("Include uppercase letters (A-Z)?", True),
            "digits": ask_yes_no("Include numbers (0-9)?", True),
            "symbols": ask_yes_no("Include symbols (!@#$%...)?", True),
        }
        selected = [name for name, enabled in choices.items() if enabled]
        if len(selected) < 2:
            print(
                "  ! You must pick at least 2 character types "
                f"(you picked {len(selected)}). Let's try again.\n"
            )
            continue
        return choices


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------

def render_strength_bar(report) -> str:
    """Return a small text bar plus a label for the strength report."""
    filled = round(report.score / 10)          # 0-10 blocks
    bar = "#" * filled + "-" * (10 - filled)
    return f"[{bar}] {report.label}  ({report.details})"


def show_password(password: str) -> None:
    print("\n" + "=" * 58)
    print("  Your generated password:")
    print(f"\n      {password}\n")
    report = evaluate_strength(password)
    print(f"  Strength: {render_strength_bar(report)}")
    print("=" * 58)


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------

def build_options() -> PasswordOptions:
    """Interactively collect every option for one password."""
    print("\n--- New password ---")
    length = ask_length()
    types = ask_character_types()
    exclude_ambiguous = False
    if types["digits"] or types["uppercase"] or types["lowercase"]:
        exclude_ambiguous = ask_yes_no(
            "\nExclude ambiguous characters (0 O o l 1 |)?", False
        )
    return PasswordOptions(
        length=length,
        use_lowercase=types["lowercase"],
        use_uppercase=types["uppercase"],
        use_digits=types["digits"],
        use_symbols=types["symbols"],
        exclude_ambiguous=exclude_ambiguous,
    )


def main() -> int:
    print("=" * 58)
    print("  RANDOM PASSWORD GENERATOR  (beginner command-line version)")
    print("=" * 58)
    print("Generates strong passwords using the secure 'secrets' module.")

    while True:
        try:
            options = build_options()
            password = generate_password(options)
        except PasswordError as exc:
            print(f"\n  ! {exc}\n  Starting over.\n")
            continue
        except (KeyboardInterrupt, EOFError):
            print("\n\nCancelled. Goodbye!")
            return 0

        show_password(password)

        try:
            again = ask_yes_no("\nGenerate another password?", True)
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            return 0
        if not again:
            print("\nThanks for using the password generator. Stay safe!")
            return 0


if __name__ == "__main__":
    sys.exit(main())
