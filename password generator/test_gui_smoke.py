"""Headless smoke test for the tkinter GUI (builds window, no mainloop)."""
import tkinter as tk
from password_generator_gui import PasswordGeneratorApp, CLIPBOARD_AVAILABLE

app = PasswordGeneratorApp()
app.update()  # force layout without blocking

print("Window title:", app.title())
print("pyperclip available:", CLIPBOARD_AVAILABLE)

# Generate via the app and inspect state + widgets
app.generate()
pw = app.password_var.get()
print("Generated:", pw)
print("Strength label:", app.strength_var.get())
print("Status:", app.status_var.get())
assert len(pw) == 16, "GUI length not honored"

# History should hold entries, capped at 5
for _ in range(7):
    app.generate()
assert app.history_list.size() == 5, f"history size {app.history_list.size()}"
print("History items:", app.history_list.size())

# Copy should succeed
copied = app.copy_to_clipboard(quiet=True)
print("Copy returned:", copied)

# Masking toggle
app.hide_var.set(True)
app._refresh_display()
assert app._result_entry.cget("show") == "*", "mask not applied"
app.hide_var.set(False)
app._refresh_display()
assert app._result_entry.cget("show") == "", "unmask failed"
print("Masking toggle OK")

# Invalid options should raise a controlled error, not crash
app.lower_var.set(False); app.upper_var.set(False)
app.digit_var.set(False); app.symbol_var.set(False)
app._on_length_change()
try:
    app._current_options().validate()
    raised = False
except Exception:
    raised = True
print("Zero types raises:", raised)

app.destroy()
app.quit()
print("\nGUI smoke test completed without errors.")
