# Random Password Generator

A Python tool that generates strong, random passwords from user-defined
criteria. Two tiers are included:

* **Beginner tier** - a command-line tool.
* **Advanced tier** - a tkinter GUI with complexity controls, a strength
  indicator and clipboard integration.

Both tiers share one security-focused core module that uses Python's
`secrets` module (never `random`) for every random choice.

---

## Files

| File | Purpose |
| --- | --- |
| `password_core.py` | Shared generation + strength logic (uses `secrets`) |
| `password_generator.py` | **Beginner** command-line tool |
| `password_generator_gui.py` | **Advanced** tkinter GUI |
| `test_password_core.py` | Self-tests for the core logic |
| `test_gui_smoke.py` | Headless smoke test for the GUI |

---

## Requirements

* Python 3.8+ (developed and verified on **Python 3.14**).
* `tkinter` - ships with most Python installs (verified 8.6 here).
* `pyperclip` - only needed for the GUI clipboard button.

```powershell
pip install pyperclip
```

If `pyperclip` is missing, the GUI still runs: it falls back to tkinter's
built-in clipboard and the status bar tells you how to install it.

---

## Running the beginner (CLI) version

```powershell
python password_generator.py
```

You are prompted for:

1. **Length** - a whole number, minimum **8** enforced (max 256).
2. **Character types** - lowercase, uppercase, numbers, symbols.
   At least **2** must be selected, or you are re-prompted.
3. **Ambiguous characters** - optionally excluded.
4. Whether to generate another password (no restart needed).

Invalid input is rejected with a clear message and re-prompted. Results are
shown with a strength bar:

```
      Kx0@*YL4FsJ4;[9l
  Strength: [##########] Very Strong  (16 chars, 4 character type(s), ~104 bits of entropy)
```

---

## Running the advanced (GUI) version

```powershell
python password_generator_gui.py
```

Controls:

* **Length** - synced spinbox + slider (8-128).
* **Character types** - four checkboxes (at least 2 required).
* **Exclude ambiguous characters** - removes `0 O o l 1 |` and similar.
* **Generate Password** button (or press **Enter**). The password is copied
  to the clipboard automatically.
* **Copy to Clipboard** button (or press **Ctrl+C** in the window).
* **Show types** - a breakdown of how many of each character class the
  password contains, plus strength tips.
* **Hide password** - masks the entry and history with asterisks.
* **Session history** - the last 5 passwords, held **in memory only**. They
  are never written to disk for security; closing the window clears them.

The strength bar is colour-coded: red (Weak) -> orange (Medium) -> green
(Strong / Very Strong).

---

## Security notes

* **`secrets`, not `random`.** `random` is a predictable Mersenne-Twister
  PRNG. `secrets` draws from the OS cryptographic random source
  ([docs.python.org/3/library/secrets.html](https://docs.python.org/3/library/secrets.html)).
* **Every selected type is guaranteed.** One character from each selected
  class is placed first, then the rest are drawn from the combined pool, and
  the whole result is shuffled. So "contains a symbol" is a guarantee, not a
  probability.
* **Uniform selection.** All choices use `secrets.choice`.
* **Nothing is persisted.** History is session-only; no files are written.

---

## Tests

```powershell
python test_password_core.py    # core logic: 10 checks incl. 500-iteration guarantee
python test_gui_smoke.py        # builds the GUI headlessly and exercises every control
```

`test_password_core.py` verifies length, the per-type guarantee over 500
iterations, type filtering, ambiguous-character exclusion, validation
errors, uniqueness, and the strength classifier.

---

## Strength scoring

Entropy is estimated as `length * log2(pool_size)` bits and mapped to a
0-100 score, adjusted for character diversity and hard-capped for very short
passwords. Rough bands: **Weak** (<45), **Medium** (<70), **Strong** (<90),
**Very Strong** (>=90).
