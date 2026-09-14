# BMI Calculator

A Python BMI calculator built in two tiers: a beginner command-line tool and an
advanced tkinter desktop app with multi-user history and trend charts.

## Requirements

- Python 3.8+ (developed and tested on Python 3.14.3)
- `tkinter` — bundled with standard Python on Windows
- `matplotlib` — only needed for the advanced GUI's trend graph
- `sqlite3` — bundled with standard Python

```powershell
pip install matplotlib
```

On this machine Python lives at `C:\Python314\python.exe` and is not on PATH,
so the examples below use the full path.

## Beginner tier — command line

```powershell
C:\Python314\python.exe bmi_cli.py
```

Prompts for weight in kilograms and height in metres, then prints the BMI
rounded to two decimal places with its health category.

Sample run:

```
  Weight : 70.5 kg
  Height : 1.75 m
  BMI    : 23.02
  Result : Normal weight
```

Features:

- BMI = weight / height² with the result rounded to 2 decimals
- Categories: Underweight (< 18.5), Normal weight (18.5–24.9),
  Overweight (25.0–29.9), Obese (≥ 30)
- Rejects non-numeric input, blanks, negative values and out-of-range values,
  re-asking for **only the field that was wrong** so the other entry is kept
- Accepts small conveniences: `70 kg`, `1,75` (comma decimal), `1.75m`
- `t` at the menu prints the reference table, `q` quits

## Advanced tier — GUI

```powershell
C:\Python314\python.exe bmi_gui.py
```

A tkinter window with everything from the beginner tier plus history and charts.

- **No command line** — all feedback appears in the window and its status bar
- Weight and height entry fields with labels, a **Calculate & Save** button,
  and Enter-to-calculate in either field
- **Colour-coded result**: green for normal weight, amber for under/overweight,
  red for obese
- **Multi-user support** — type a new name or add one with the *Add user*
  button; each person keeps a separate history
- **SQLite storage** in `bmi_records.db`, created automatically next to the
  scripts on first run
- **Trend graph** — a matplotlib line chart of BMI over time, with dashed
  category guide lines and a value label on each point
- **Records tab** — full history table, with delete for a selected record
- **Error handling** — database read/write failures are reported in the status
  bar and a message box instead of crashing; a failed save still shows the
  calculated result

### A note on the trend chart

The chart plots BMI against the recorded date. If one record carries a
timestamp far away from the rest (for example a record saved with today's date
while back-filling older ones), a date axis would squash the real trend into a
sliver. In that case the chart automatically switches to plotting by record
number and says so in the status line.

## Files

| File | Purpose |
| --- | --- |
| `bmi_core.py` | Shared BMI maths, categories, limits and input validation |
| `bmi_cli.py` | Beginner tier command-line calculator |
| `bmi_gui.py` | Advanced tier tkinter application |
| `db.py` | SQLite user and record storage, raising `StorageError` on failure |
| `chart.py` | matplotlib trend chart, embedded into the GUI canvas |
| `cli_test.py` | Automated CLI tests (scripted input and output assertions) |
| `smoke_test.py` | Automated GUI tests (builds the real window and drives it) |

## Database

Created automatically on first run as `bmi_records.db` in the project folder.

```sql
users   (id, name UNIQUE, created_at)
records (id, user_id -> users.id, weight_kg, height_m, bmi, category, recorded_at)
```

Foreign keys are enabled per connection, so deleting a user cascades to their
records. Delete `bmi_records.db` to start fresh.

## Tests

```powershell
C:\Python314\python.exe cli_test.py     # 12 CLI tests
C:\Python314\python.exe smoke_test.py   # GUI: colours, persistence, errors
```

Both suites build the real objects and assert on real behaviour, including the
rejection of bad input, per-user isolation of history, and behaviour when the
database cannot be written.

## Health note

BMI is a rough screening tool based only on height and weight. It does not
distinguish muscle from fat and is not a medical diagnosis.
