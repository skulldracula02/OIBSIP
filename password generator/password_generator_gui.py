#!/usr/bin/env python3
"""
password_generator_gui.py
=========================
ADVANCED TIER - Random Password Generator (tkinter GUI).

Feature checklist for this file (on top of all beginner features):
  [x] GUI window with a slider/spinbox for length and checkboxes for types
  [x] Cryptographically secure generation via the secrets module
  [x] Password strength indicator (colored bar + Weak/Medium/Strong label)
  [x] Security rule enforced: at least one char from each selected type
  [x] "Copy to Clipboard" button (pyperclip) + auto-copy on generation
  [x] Checkbox to exclude ambiguous characters (0, O, l, 1)
  [x] Session history showing the last 5 generated passwords (in memory only)

Run with:  python password_generator_gui.py
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from password_core import (
    CHAR_TYPE_LABELS,
    MIN_LENGTH,
    PasswordError,
    PasswordOptions,
    evaluate_strength,
    generate_password,
    type_counts,
)

# Optional clipboard dependency -------------------------------------------
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:          # pragma: no cover - depends on environment
    CLIPBOARD_AVAILABLE = False

HISTORY_LIMIT = 5

# Colours for the strength indicator
STRENGTH_COLORS = {
    "Weak": "#d9534f",        # red
    "Medium": "#f0ad4e",      # orange
    "Strong": "#5cb85c",      # green
    "Very Strong": "#2e8b57", # darker green
}


class PasswordGeneratorApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Advanced Password Generator")
        self.geometry("620x680")
        self.minsize(560, 620)
        self.configure(padx=16, pady=14)

        # ---- Tk variables -------------------------------------------------
        self.length_var = tk.IntVar(value=16)
        self.lower_var = tk.BooleanVar(value=True)
        self.upper_var = tk.BooleanVar(value=True)
        self.digit_var = tk.BooleanVar(value=True)
        self.symbol_var = tk.BooleanVar(value=True)
        self.ambiguous_var = tk.BooleanVar(value=False)   # exclude ambiguous
        self.hide_var = tk.BooleanVar(value=False)
        self.password_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready.")
        self.strength_var = tk.StringVar(value="")
        self.history_var = tk.StringVar(value="(none yet)")

        self._history: list[str] = []          # in-memory only, never persisted
        self._result_entry: ttk.Entry | None = None

        self._build_ui()

        # Start with the password visible.
        self._refresh_display()

        self.bind("<Return>", lambda _event: self.generate())
        self.bind("<Control-c>", self._on_ctrl_c)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:                     # pragma: no cover
            pass
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

        # ---- Length control ---------------------------------------------
        length_frame = ttk.LabelFrame(self, text="Password length")
        length_frame.pack(fill="x", pady=(0, 10))

        self.length_spin = ttk.Spinbox(
            length_frame, from_=MIN_LENGTH, to=128,
            textvariable=self.length_var, width=6,
            command=self._on_length_change,
        )
        self.length_spin.pack(side="left", padx=(10, 12), pady=10)

        self.length_scale = ttk.Scale(
            length_frame, from_=MIN_LENGTH, to=128, orient="horizontal",
            command=self._on_scale_move,
        )
        self.length_scale.set(self.length_var.get())
        self.length_scale.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=10)

        self.length_hint = ttk.Label(length_frame, text="16", width=4, anchor="e")
        self.length_hint.pack(side="right", padx=(0, 12))

        # ---- Character types --------------------------------------------
        types_frame = ttk.LabelFrame(self, text="Character types (pick at least 2)")
        types_frame.pack(fill="x", pady=(0, 10))

        grid_opts = {"sticky": "w", "padx": 12, "pady": 4}
        ttk.Checkbutton(
            types_frame, text=CHAR_TYPE_LABELS["lowercase"], variable=self.lower_var
        ).grid(row=0, column=0, **grid_opts)
        ttk.Checkbutton(
            types_frame, text=CHAR_TYPE_LABELS["uppercase"], variable=self.upper_var
        ).grid(row=1, column=0, **grid_opts)
        ttk.Checkbutton(
            types_frame, text=CHAR_TYPE_LABELS["digits"], variable=self.digit_var
        ).grid(row=0, column=1, **grid_opts)
        ttk.Checkbutton(
            types_frame, text=CHAR_TYPE_LABELS["symbols"], variable=self.symbol_var
        ).grid(row=1, column=1, **grid_opts)

        ttk.Separator(types_frame, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 2)
        )
        ttk.Checkbutton(
            types_frame,
            text="Exclude ambiguous characters  (0  O  o  l  1  |  ` ' \" )",
            variable=self.ambiguous_var,
        ).grid(row=3, column=0, columnspan=2, **grid_opts)

        # ---- Generate button --------------------------------------------
        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(0, 10))
        self.generate_btn = ttk.Button(
            btns, text="Generate Password", command=self.generate
        )
        self.generate_btn.pack(side="left")
        ttk.Button(btns, text="Clear history", command=self.clear_history).pack(
            side="right"
        )

        # ---- Result ------------------------------------------------------
        result_frame = ttk.LabelFrame(self, text="Your password")
        result_frame.pack(fill="x", pady=(0, 10))

        self._result_entry = ttk.Entry(
            result_frame, textvariable=self.password_var,
            font=("Consolas", 15), justify="center",
        )
        self._result_entry.pack(fill="x", padx=12, pady=(10, 6))

        btn_row = ttk.Frame(result_frame)
        btn_row.pack(fill="x", padx=12, pady=(0, 6))
        self.copy_btn = ttk.Button(
            btn_row, text="Copy to Clipboard", command=self.copy_to_clipboard
        )
        self.copy_btn.pack(side="left")
        ttk.Checkbutton(
            btn_row, text="Hide password", variable=self.hide_var,
            command=self._refresh_display,
        ).pack(side="left", padx=12)
        ttk.Button(btn_row, text="Show types", command=self.show_type_breakdown).pack(
            side="right"
        )

        # ---- Strength indicator -----------------------------------------
        strength_frame = ttk.LabelFrame(self, text="Password strength")
        strength_frame.pack(fill="x", pady=(0, 10))

        self.strength_canvas = tk.Canvas(
            strength_frame, height=22, highlightthickness=0
        )
        self.strength_canvas.pack(fill="x", padx=12, pady=(10, 4))
        self._draw_strength_bar(0, "#cccccc")

        self.strength_label = ttk.Label(
            strength_frame, textvariable=self.strength_var, font=("Segoe UI", 10, "bold")
        )
        self.strength_label.pack(anchor="w", padx=12, pady=(0, 10))

        # ---- History -----------------------------------------------------
        history_frame = ttk.LabelFrame(self, text=f"Session history (last {HISTORY_LIMIT})")
        history_frame.pack(fill="both", expand=True)

        self.history_list = tk.Listbox(
            history_frame, height=HISTORY_LIMIT, font=("Consolas", 11),
            activestyle="none",
        )
        self.history_list.pack(fill="both", expand=True, padx=12, pady=(10, 10))

        # ---- Status bar --------------------------------------------------
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(
            fill="x", pady=(8, 0)
        )

        if not CLIPBOARD_AVAILABLE:
            self.status_var.set(
                "pyperclip not found - install it with: pip install pyperclip"
            )

    # ------------------------------------------------------------------
    # Length slider / spinbox sync
    # ------------------------------------------------------------------
    def _on_scale_move(self, value: str) -> None:
        length = int(float(value))
        self.length_var.set(length)
        # Guard: the Scale fires during construction before the hint exists.
        hint = getattr(self, "length_hint", None)
        if hint is not None:
            hint.config(text=str(length))

    def _on_length_change(self) -> None:
        try:
            length = int(self.length_var.get())
        except (tk.TclError, ValueError):
            length = MIN_LENGTH
        self.length_scale.set(length)
        self.length_hint.config(text=str(length))

    # ------------------------------------------------------------------
    # Options / generation
    # ------------------------------------------------------------------
    def _current_options(self) -> PasswordOptions:
        try:
            length = int(self.length_var.get())
        except (tk.TclError, ValueError):
            raise PasswordError("Password length must be a whole number.")
        return PasswordOptions(
            length=length,
            use_lowercase=self.lower_var.get(),
            use_uppercase=self.upper_var.get(),
            use_digits=self.digit_var.get(),
            use_symbols=self.symbol_var.get(),
            exclude_ambiguous=self.ambiguous_var.get(),
        )

    def generate(self) -> None:
        """Generate a password from the current controls and auto-copy it."""
        try:
            options = self._current_options()
            password = generate_password(options)
        except PasswordError as exc:
            messagebox.showerror("Invalid options", str(exc), parent=self)
            self.status_var.set(f"Error: {exc}")
            return

        self.password_var.set(password)
        self._update_strength(password)
        self._push_history(password)
        self._refresh_display()

        # Auto-copy on generation (required by the advanced checklist).
        if self.copy_to_clipboard(quiet=True):
            self.status_var.set("Password generated and copied to clipboard.")
        else:
            self.status_var.set("Password generated. Clipboard unavailable.")

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------
    def copy_to_clipboard(self, quiet: bool = False) -> bool:
        password = self.password_var.get()
        if not password:
            if not quiet:
                messagebox.showinfo(
                    "Nothing to copy", "Generate a password first.", parent=self
                )
            return False
        try:
            if CLIPBOARD_AVAILABLE:
                pyperclip.copy(password)
            else:
                self.clipboard_clear()
                self.clipboard_append(password)
                self.update()          # keep the clipboard alive on some platforms
        except Exception as exc:       # pragma: no cover - platform specific
            if not quiet:
                messagebox.showwarning(
                    "Clipboard error",
                    f"Could not copy to clipboard:\n{exc}",
                    parent=self,
                )
            return False
        if not quiet:
            self.status_var.set("Copied to clipboard.")
        return True

    def _on_ctrl_c(self, _event) -> None:
        self.copy_to_clipboard()

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    def _refresh_display(self) -> None:
        """Show either the real password or a masked version."""
        password = self.password_var.get()
        if self._result_entry is None:
            return
        if self.hide_var.get() and password:
            # Keep the StringVar intact: only change what the widget shows.
            self._result_entry.config(show="*")
        else:
            self._result_entry.config(show="")

    def _draw_strength_bar(self, score: int, color: str) -> None:
        """Redraw the segmented strength bar for *score* (0-100)."""
        canvas = self.strength_canvas
        canvas.delete("all")
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 200)
        height = 22
        segments = 10
        gap = 4
        seg_width = (width - gap * (segments - 1)) / segments
        filled = round(score / 100 * segments)
        for i in range(segments):
            x0 = i * (seg_width + gap)
            x1 = x0 + seg_width
            fill = color if i < filled else "#e0e0e0"
            canvas.create_rectangle(x0, 0, x1, height, fill=fill, outline="")

    def _update_strength(self, password: str) -> None:
        report = evaluate_strength(password)
        color = STRENGTH_COLORS.get(report.label, "#888")
        self._draw_strength_bar(report.score, color)
        self.strength_var.set(
            f"{report.label}  -  score {report.score}/100  ({report.details})"
        )
        self.strength_label.config(foreground=color)

    def show_type_breakdown(self) -> None:
        password = self.password_var.get()
        if not password:
            messagebox.showinfo(
                "No password", "Generate a password first.", parent=self
            )
            return
        counts = type_counts(password)
        report = evaluate_strength(password)
        message = "\n".join(f"  {name.title():<10}: {count}" for name, count in counts.items())
        message += f"\n\nStrength: {report.label} ({report.score}/100)"
        message += "\n\nTips:\n" + "\n".join(f"  - {s}" for s in report.suggestions)
        messagebox.showinfo("Password breakdown", message, parent=self)

    # ------------------------------------------------------------------
    # History (memory only)
    # ------------------------------------------------------------------
    def _push_history(self, password: str) -> None:
        """Add to the in-session history, keeping only the latest entries."""
        self._history.insert(0, password)
        self._history = self._history[:HISTORY_LIMIT]
        self._render_history()

    def _render_history(self) -> None:
        self.history_list.delete(0, tk.END)
        for index, password in enumerate(self._history, start=1):
            shown = password if not self.hide_var.get() else "*" * len(password)
            self.history_list.insert(tk.END, f"{index:>2}. {shown}")

    def clear_history(self) -> None:
        self._history.clear()
        self._render_history()
        self.status_var.set("History cleared.")


def main() -> None:
    app = PasswordGeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
