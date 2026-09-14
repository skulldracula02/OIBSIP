"""Quick self-test for password_core. Run: python test_password_core.py"""
import string
from password_core import (
    PasswordError, PasswordOptions, evaluate_strength, generate_password, type_counts,
)

def check(condition, message):
    print(("PASS: " if condition else "FAIL: ") + message)
    assert condition, message

# 1. Basic generation honours length.
opts = PasswordOptions(length=20)
pw = generate_password(opts)
check(len(pw) == 20, f"length is exactly 20 (got {len(pw)})")

# 2. Every selected type is present (the security rule).
counts = type_counts(pw)
check(counts["lowercase"] >= 1 and counts["uppercase"] >= 1
      and counts["digits"] >= 1 and counts["symbols"] >= 1,
      "all four selected types present")

# 3. Run the guarantee many times (statistical check).
for i in range(500):
    p = generate_password(PasswordOptions(length=8))
    c = type_counts(p)
    assert c["lowercase"] >= 1 and c["uppercase"] >= 1 and c["digits"] >= 1 and c["symbols"] >= 1, p
check(True, "500 iterations always contain each selected type")

# 4. Only chosen types appear.
p2 = generate_password(PasswordOptions(length=30, use_symbols=False, use_uppercase=False))
check(all(ch in string.ascii_lowercase + string.digits for ch in p2),
      "only lowercase+digits when others unchecked")

# 5. Ambiguous exclusion.
p3 = generate_password(PasswordOptions(length=40, exclude_ambiguous=True))
check(not any(ch in "0OoIl1|" for ch in p3), "no ambiguous chars when excluded")

# 6. Validation errors.
for bad, label in [
    (PasswordOptions(length=5), "length < 8 rejected"),
    (PasswordOptions(length=20, use_lowercase=True, use_uppercase=False,
                     use_digits=False, use_symbols=False), "one type rejected"),
]:
    try:
        generate_password(bad)
        check(False, label)
    except PasswordError:
        check(True, label)

# 7. Strength indicator.
check(evaluate_strength("abc").label == "Weak", "short password is Weak")
check(evaluate_strength("aB3!kL9@qW2#zX7$mN4%pQ8&").label in ("Strong", "Very Strong"),
      "long diverse password is Strong/Very Strong")

# 8. Uniqueness (randomness sanity check).
batch = {generate_password(PasswordOptions(length=16)) for _ in range(200)}
check(len(batch) == 200, "200 generated passwords are all unique")

print("\nAll checks passed.")
