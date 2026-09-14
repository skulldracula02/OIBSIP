"""
password_core.py
================
Shared, security-focused password generation logic used by both the
beginner command-line tool and the advanced GUI.

Security note
-------------
This module uses the ``secrets`` module (not ``random``) for every
random choice.  ``random`` is a Mersenne-Twister PRNG that is perfectly
predictable once you know a few outputs, so it must never be used to
create passwords, tokens or keys.  ``secrets`` draws from the operating
system's cryptographically secure random source.

Reference: https://docs.python.org/3/library/secrets.html
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Character sets
# --------------------------------------------------------------------------

LOWERCASE = string.ascii_lowercase           # abcdefghijklmnopqrstuvwxyz
UPPERCASE = string.ascii_uppercase           # ABCDEFGHIJKLMNOPQRSTUVWXYZ
DIGITS = string.digits                       # 0123456789
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?/|~"     # common, shell-friendly-ish set

# Characters that look alike in many fonts and cause transcription errors.
AMBIGUOUS = "0OoIl1|`'\";:,.()[]{}"

MIN_LENGTH = 8

#: Human readable names for each character class.
CHAR_TYPE_LABELS = {
    "lowercase": "Lowercase letters (a-z)",
    "uppercase": "Uppercase letters (A-Z)",
    "digits": "Numbers (0-9)",
    "symbols": "Symbols (!@#$%...)",
}


class PasswordError(ValueError):
    """Raised when the requested options cannot produce a valid password."""


# --------------------------------------------------------------------------
# Options container
# --------------------------------------------------------------------------

@dataclass
class PasswordOptions:
    """Everything that can be configured about a generated password."""

    length: int = 16
    use_lowercase: bool = True
    use_uppercase: bool = True
    use_digits: bool = True
    use_symbols: bool = True
    exclude_ambiguous: bool = False

    # ----------------------------------------------------------------
    def selected_types(self) -> list[str]:
        """Return the list of enabled character classes."""
        selected = []
        if self.use_lowercase:
            selected.append("lowercase")
        if self.use_uppercase:
            selected.append("uppercase")
        if self.use_digits:
            selected.append("digits")
        if self.use_symbols:
            selected.append("symbols")
        return selected

    def character_pool(self) -> dict[str, str]:
        """Return the (possibly filtered) character pool per selected type."""
        pools = {
            "lowercase": LOWERCASE,
            "uppercase": UPPERCASE,
            "digits": DIGITS,
            "symbols": SYMBOLS,
        }
        result: dict[str, str] = {}
        for type_name in self.selected_types():
            chars = pools[type_name]
            if self.exclude_ambiguous:
                chars = "".join(c for c in chars if c not in AMBIGUOUS)
            if not chars:
                raise PasswordError(
                    f"All characters of type '{CHAR_TYPE_LABELS[type_name]}' "
                    "were removed by the ambiguous-character filter. "
                    "Enable another character type or disable the filter."
                )
            result[type_name] = chars
        return result

    # ----------------------------------------------------------------
    def validate(self) -> None:
        """Raise :class:`PasswordError` if the options are invalid."""
        if not isinstance(self.length, int):
            raise PasswordError("Password length must be a whole number.")
        if self.length < MIN_LENGTH:
            raise PasswordError(
                f"Password length must be at least {MIN_LENGTH} characters."
            )
        selected = self.selected_types()
        if len(selected) < 2:
            raise PasswordError(
                "Select at least 2 character types "
                "(uppercase, lowercase, numbers, symbols)."
            )
        # Guarantees the "one char per selected type" rule is satisfiable.
        if self.length < len(selected):
            raise PasswordError(
                f"Length {self.length} is too short to include one character "
                f"from each of the {len(selected)} selected types."
            )


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def generate_password(options: PasswordOptions) -> str:
    """
    Build a cryptographically secure password that satisfies *options*.

    Guarantees:
      * exactly ``options.length`` characters;
      * at least one character from **every** selected character type;
      * every character drawn uniformly from the selected (and possibly
        ambiguity-filtered) pool.

    The result is shuffled with :func:`secrets.SystemRandom.shuffle` so the
    guaranteed characters do not always sit at the start of the password.
    """
    options.validate()
    pools = options.character_pool()

    # 1. Seed the password with one character from each selected type so the
    #    "must contain each selected type" rule is guaranteed, not just likely.
    password: list[str] = [secrets.choice(pool) for pool in pools.values()]

    # 2. Fill the remaining positions from the combined pool.
    combined = "".join(pools.values())
    remaining = options.length - len(password)
    password.extend(secrets.choice(combined) for _ in range(remaining))

    # 3. Shuffle so the seeded characters are not stuck at the front.
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


# --------------------------------------------------------------------------
# Strength estimation
# --------------------------------------------------------------------------

@dataclass
class StrengthReport:
    """Result of :func:`evaluate_strength`."""

    label: str                     # "Weak" | "Medium" | "Strong" | "Very Strong"
    score: int                     # 0-100
    entropy_bits: float = 0.0
    details: str = ""
    suggestions: list[str] = field(default_factory=list)


def evaluate_strength(password: str, options: PasswordOptions | None = None) -> StrengthReport:
    """
    Estimate password strength from length + character diversity + entropy.

    Entropy is ``length * log2(pool_size)`` bits.  As a rough guide:
    < 45 bits  -> Weak, < 70 -> Medium, < 100 -> Strong, else Very Strong.
    The score blends the entropy with a diversity bonus so a 40-character
    all-lowercase password does not outrank a balanced 20-character one.
    """
    if not password:
        return StrengthReport("Weak", 0, 0.0, "Empty password", ["Generate a password first."])

    length = len(password)
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    diversity = sum([has_lower, has_upper, has_digit, has_symbol])

    # Estimate the effective pool size from what the password actually uses.
    pool_size = 0
    if has_lower:
        pool_size += 26
    if has_upper:
        pool_size += 26
    if has_digit:
        pool_size += 10
    if has_symbol:
        pool_size += len(SYMBOLS)
    pool_size = max(pool_size, 1)

    import math
    entropy = length * math.log2(pool_size)

    # Map entropy to a 0-100 score, then reward diversity.
    score = min(100, int(entropy / 1.2))
    score += (diversity - 1) * 4
    # Penalise very short passwords hard.
    if length < MIN_LENGTH:
        score = min(score, 25)
    elif length < 12:
        score = min(score, 60)
    if has_symbol and has_digit and has_upper and has_lower and length >= 16:
        score += 5
    score = max(0, min(100, score))

    if score < 45:
        label = "Weak"
    elif score < 70:
        label = "Medium"
    elif score < 90:
        label = "Strong"
    else:
        label = "Very Strong"

    suggestions: list[str] = []
    if length < 12:
        suggestions.append("Use at least 12-16 characters.")
    if diversity < 3:
        suggestions.append("Mix more character types (upper, lower, digits, symbols).")
    if not has_symbol:
        suggestions.append("Add symbols to widen the character pool.")
    if not suggestions:
        suggestions.append("Looks good. Store it in a password manager.")

    details = (
        f"{length} chars, {diversity} character type(s), "
        f"~{entropy:.0f} bits of entropy"
    )
    return StrengthReport(label, score, entropy, details, suggestions)


def type_counts(password: str) -> dict[str, int]:
    """Count how many characters of each type a password contains."""
    return {
        "lowercase": sum(c.islower() for c in password),
        "uppercase": sum(c.isupper() for c in password),
        "digits": sum(c.isdigit() for c in password),
        "symbols": sum((not c.isalnum()) for c in password),
    }
