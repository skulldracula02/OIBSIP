"""Headless smoke test: build the real GUI, drive it, assert on the widgets."""
import os
import sys
import tkinter as tk

import bmi_gui
import chart
import db

DB_PATH = "smoke_test.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

root = tk.Tk()
root.withdraw()

database = db.BMIDatabase(DB_PATH).connect()
app = bmi_gui.BMIApp(root, database)
root.update()
print("GUI built OK")

# --- 1. colour-coded result via the real calculate() path ------------------
app.user_var.set("TestUser")
app.weight_var.set("110")
app.height_var.set("1.75")
app.calculate()
root.update()
value = app.bmi_value_label.cget("text")
colour = app.bmi_value_label.cget("fg")
cat = app.bmi_category_label.cget("text")
assert value == "35.92", value
assert cat == "Obese", cat
assert colour == "#c0182a", colour
print(f"obese  -> BMI {value} '{cat}' colour {colour}")

app.weight_var.set("70")
app.calculate()
root.update()
assert app.bmi_value_label.cget("text") == "22.86"
assert app.bmi_category_label.cget("text") == "Normal weight"
assert app.bmi_value_label.cget("fg") == "#1a7f37"
print("normal -> BMI 22.86 'Normal weight' colour #1a7f37")

app.weight_var.set("50")
app.calculate()
root.update()
assert app.bmi_category_label.cget("text") == "Underweight"
print("under  -> BMI 16.33 'Underweight'")

app.weight_var.set("80")
app.calculate()
root.update()
assert app.bmi_category_label.cget("text") == "Overweight"
print("over   -> BMI 26.12 'Overweight'")

# --- 2. records persisted and table populated ------------------------------
rows = app.tree.get_children()
assert len(rows) == 4, rows
first = app.tree.item(rows[0])["values"]
print("table rows:", len(rows), "| first row:", first)
assert "T" not in str(first[0]), "date still contains the ISO 'T' separator"

stored = database.get_records("TestUser")
assert len(stored) == 4
bmis = [round(r["bmi"], 2) for r in stored]
assert bmis == [35.92, 22.86, 16.33, 26.12], bmis
print("db order (ascending):", bmis)

# --- 3. chart actually rendered onto the canvas ---------------------------
assert chart.build_figure(stored, "TestUser")[0] == chart.STATUS_OK
assert app.chart_canvas is not None, "chart canvas was not created"
print("chart canvas present, figure axes:",
      len(app.chart_canvas.figure.axes))

# --- 4. multi-user support ------------------------------------------------
app.user_var.set("Second")
app.weight_var.set("60")
app.height_var.set("1.60")
app.calculate()
root.update()
assert len(database.get_records("TestUser")) == 4, "records leaked across users"
assert len(database.get_records("Second")) == 1
users = [u["name"] for u in database.get_users()]
assert users == ["Second", "TestUser"], users
print("multi-user isolation OK, users:", users)

# switching users reloads their own history
app.user_var.set("TestUser")
app._on_user_selected()
root.update()
assert len(app.tree.get_children()) == 4
assert app.history_user_label.cget("text") == "TestUser"
print("user switch reloaded 4 rows for TestUser")

# --- 5. invalid input is rejected without crashing ------------------------
import tkinter.messagebox as mb
captured = []
mb.showwarning = lambda *a, **k: captured.append(a)
mb.showerror = lambda *a, **k: captured.append(a)

for bad_weight, bad_height, reason in [
    ("abc", "1.75", "non-numeric"),
    ("", "1.75", "empty"),
    ("-70", "1.75", "negative"),
    ("70", "-1.75", "negative height"),
    ("70", "175", "centimetres mistaken for metres"),
]:
    app.weight_var.set(bad_weight)
    app.height_var.set(bad_height)
    before = len(app.tree.get_children())
    app.calculate()
    root.update()
    after = len(app.tree.get_children())
    assert after == before, f"{reason} was saved: {before} -> {after}"
    assert captured, f"no message shown for {reason}"
    captured.clear()
    print(f"rejected {reason:<38} -> {app.status_var.get()[:58]}")

# --- 6. a failed write is reported, not raised ----------------------------
database.close()
app.weight_var.set("70")
app.height_var.set("1.75")
app.calculate()
root.update()
assert "Save failed" in app.status_var.get(), app.status_var.get()
print("closed-db write ->", app.status_var.get()[:70])
assert app.bmi_value_label.cget("text") == "22.86", "result vanished on save failure"
print("result still displayed after save failure")

# --- 7. graceful behaviour when the DB cannot be opened at all ------------
app._refresh_history()
root.update()
assert "Database error" in app.status_var.get()
print("history refresh with dead db ->", app.status_var.get()[:60])

root.destroy()
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

print("\nALL GUI SMOKE TESTS PASSED")
