#!/usr/bin/env python3
"""
bmi_gui.py - Advanced tier: a tkinter BMI calculator with multi-user
history stored in SQLite and a matplotlib trend chart.

Run it with:
    python bmi_gui.py

Nothing is printed to the command line; every message appears in the window.
Database problems are reported in the status bar instead of crashing.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import chart
import db
from bmi_core import ValidationError, assess, parse_number

# Colour palette
BG = "#f4f6f8"
CARD = "#ffffff"
INK = "#1f2933"
MUTED = "#6b7280"
ACCENT = "#2f6fd0"

CATEGORY_COLOURS = {
    "Underweight": "#c8860d",
    "Normal weight": "#1a7f37",
    "Overweight": "#c8860d",
    "Obese": "#c0182a",
}


class BMIApp:
    def __init__(self, root, database):
        self.root = root
        self.database = database
        self.chart_canvas = None
        self.current_user = None

        self.weight_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready.")

        self.root.title("BMI Calculator")
        self.root.geometry("980x660")
        self.root.minsize(880, 600)
        self.root.configure(bg=BG)

        self._configure_styles()
        self._build_layout()
        self._refresh_users()
        self._refresh_history()

    # ------------------------------------------------------------- styling

    def _configure_styles(self):
        style = ttk.Style()
        # 'clam' honours custom colours on every platform, unlike the default.
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 10))
        style.configure("Heading.TLabel", background=BG, foreground=INK,
                        font=("Segoe UI", 15, "bold"))
        style.configure("Field.TLabel", background=CARD, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(14, 7))

    def _card(self, parent):
        """A white rounded-ish panel with a subtle border."""
        outer = tk.Frame(parent, bg=CARD, highlightbackground="#d8dee5",
                         highlightthickness=1, bd=0)
        return outer

    # -------------------------------------------------------------- layout

    def _build_layout(self):
        header = ttk.Frame(self.root, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        ttk.Label(header, text="BMI Calculator", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Track body mass index over time for multiple people.",
            foreground=MUTED,
        ).pack(anchor="w")

        body = ttk.Frame(self.root, padding=(18, 6, 18, 6))
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 14))

        self._build_input_card(left)
        self._build_result_card(left)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self._build_history_card(right)

        status = tk.Label(self.root, textvariable=self.status_var, anchor="w",
                          bg="#e8ecf1", fg=INK, padx=14, pady=6, font=("Segoe UI", 9))
        status.pack(fill="x", side="bottom")

    def _build_input_card(self, parent):
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 12))
        inner = ttk.Frame(card, style="Card.TFrame", padding=16)
        inner.pack(fill="x")

        ttk.Label(inner, text="Enter measurements", style="Card.TLabel",
                  font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2,
                                                      sticky="w", pady=(0, 12))

        ttk.Label(inner, text="USER", style="Field.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w")
        self.user_combo = ttk.Combobox(inner, textvariable=self.user_var,
                                       state="normal", width=26)
        self.user_combo.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 12))
        self.user_combo.bind("<<ComboboxSelected>>", self._on_user_selected)

        ttk.Label(inner, text="WEIGHT (kg)", style="Field.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w")
        weight_entry = ttk.Entry(inner, textvariable=self.weight_var, width=26,
                                 font=("Segoe UI", 11))
        weight_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(2, 12))

        ttk.Label(inner, text="HEIGHT (m)", style="Field.TLabel").grid(
            row=5, column=0, columnspan=2, sticky="w")
        height_entry = ttk.Entry(inner, textvariable=self.height_var, width=26,
                                 font=("Segoe UI", 11))
        height_entry.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(2, 14))

        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)

        calculate = ttk.Button(inner, text="Calculate & Save", style="Accent.TButton",
                               command=self.calculate)
        calculate.grid(row=7, column=0, columnspan=2, sticky="ew")

        ttk.Button(inner, text="Show history only", command=self.show_only).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        ttk.Button(inner, text="Clear fields", command=self.clear_fields).grid(
            row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # Enter in either entry runs the calculation.
        weight_entry.bind("<Return>", lambda _event: self.calculate())
        height_entry.bind("<Return>", lambda _event: self.calculate())
        weight_entry.focus_set()

    def _build_result_card(self, parent):
        card = self._card(parent)
        card.pack(fill="both", expand=True)
        inner = ttk.Frame(card, style="Card.TFrame", padding=16)
        inner.pack(fill="both", expand=True)

        ttk.Label(inner, text="Result", style="Card.TLabel",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.bmi_value_label = tk.Label(inner, text="--", bg=CARD, fg=INK,
                                        font=("Segoe UI", 30, "bold"))
        self.bmi_value_label.pack(anchor="w", pady=(6, 0))

        self.bmi_category_label = tk.Label(inner, text="No calculation yet",
                                           bg=CARD, fg=MUTED,
                                           font=("Segoe UI", 11, "bold"))
        self.bmi_category_label.pack(anchor="w")

        self.bmi_detail_label = tk.Label(inner, text="", bg=CARD, fg=MUTED,
                                         font=("Segoe UI", 9), justify="left",
                                         wraplength=230)
        self.bmi_detail_label.pack(anchor="w", pady=(10, 0))

    def _build_history_card(self, parent):
        card = self._card(parent)
        card.pack(fill="both", expand=True)
        inner = ttk.Frame(card, style="Card.TFrame", padding=12)
        inner.pack(fill="both", expand=True)

        bar = ttk.Frame(inner, style="Card.TFrame")
        bar.pack(fill="x", pady=(0, 8))

        ttk.Label(bar, text="History for", style="Card.TLabel").pack(side="left")
        self.history_user_label = ttk.Label(bar, text="(no user)", style="Card.TLabel",
                                            font=("Segoe UI", 10, "bold"))
        self.history_user_label.pack(side="left", padx=(6, 12))

        ttk.Button(bar, text="Add user", command=self.add_user).pack(side="right")
        ttk.Button(bar, text="Delete user", command=self.delete_user).pack(side="right",
                                                                           padx=(0, 6))

        notebook = ttk.Notebook(inner)
        notebook.pack(fill="both", expand=True)

        graph_tab = ttk.Frame(notebook, style="Card.TFrame")
        table_tab = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(graph_tab, text="Trend graph")
        notebook.add(table_tab, text="Records")

        self.chart_holder = ttk.Frame(graph_tab, style="Card.TFrame")
        self.chart_holder.pack(fill="both", expand=True)
        self.chart_message = ttk.Label(graph_tab, text="", style="Card.TLabel",
                                       foreground=MUTED, justify="center")
        self.chart_message.pack(fill="both", expand=True)

        columns = ("when", "weight", "height", "bmi", "category")
        self.tree = ttk.Treeview(table_tab, columns=columns, show="headings", height=12)
        for key, title, width in (
            ("when", "Date", 150),
            ("weight", "Weight (kg)", 95),
            ("height", "Height (m)", 90),
            ("bmi", "BMI", 70),
            ("category", "Category", 120),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")

        scrollbar = ttk.Scrollbar(table_tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for category, colour in CATEGORY_COLOURS.items():
            self.tree.tag_configure(category, foreground=colour)

        actions = ttk.Frame(table_tab, style="Card.TFrame")
        actions.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(actions, text="Delete selected record",
                   command=self.delete_selected_record).pack(side="left")

    # -------------------------------------------------------------- helpers

    def set_status(self, message):
        self.status_var.set(message)

    def _refresh_users(self, select=None):
        """Reload the user dropdown from the database."""
        try:
            users = [row["name"] for row in self.database.get_users()]
        except db.StorageError as error:
            # Requirement: report database read failures without crashing.
            self.set_status(f"Database error: {error}")
            messagebox.showerror("Database error", str(error))
            return

        self.user_combo["values"] = users
        if select and select in users:
            self.user_var.set(select)
            self.current_user = select
        elif users and not self.user_var.get():
            self.user_var.set(users[0])
            self.current_user = users[0]

        label = self.user_var.get().strip() or "(no user)"
        self.history_user_label.configure(text=label)

    def _on_user_selected(self, _event=None):
        self.current_user = self.user_var.get().strip() or None
        self.history_user_label.configure(text=self.current_user or "(no user)")
        self._refresh_history()

    def add_user(self):
        name = simpledialog.askstring("New user", "Name of the new user:", parent=self.root)
        if not name or not name.strip():
            return
        try:
            self.database.add_user(name)
        except db.StorageError as error:
            self.set_status(f"Database error: {error}")
            messagebox.showerror("Database error", str(error))
            return
        self._refresh_users(select=name.strip())
        self._refresh_history()
        self.set_status(f"Added user '{name.strip()}'.")

    def delete_user(self):
        name = self.user_var.get().strip()
        if not name:
            messagebox.showinfo("No user selected", "Pick a user first.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Delete user",
            f"Delete '{name}' and every BMI record belonging to them?",
            parent=self.root,
        ):
            return
        try:
            self.database.delete_user(name)
        except db.StorageError as error:
            self.set_status(f"Database error: {error}")
            messagebox.showerror("Database error", str(error))
            return

        self.user_var.set("")
        self.current_user = None
        self._refresh_users()
        self._refresh_history()
        self.set_status(f"Deleted user '{name}'.")

    def clear_fields(self):
        self.weight_var.set("")
        self.height_var.set("")
        self.bmi_value_label.configure(text="--", fg=INK)
        self.bmi_category_label.configure(text="No calculation yet", fg=MUTED)
        self.bmi_detail_label.configure(text="")
        self.set_status("Fields cleared.")

    # ---------------------------------------------------------- calculation

    def _read_inputs(self):
        """Parse both fields, showing a message box on the first problem."""
        try:
            weight = parse_number(self.weight_var.get(), "Weight")
            height = parse_number(self.height_var.get(), "Height")
        except ValidationError as error:
            self.set_status(f"Input error: {error}")
            messagebox.showwarning("Check your input", str(error), parent=self.root)
            return None

        return weight, height

    def calculate(self):
        user = self.user_var.get().strip()
        if not user:
            messagebox.showwarning(
                "Name required",
                "Enter a user name so the record can be saved to their history.",
                parent=self.root,
            )
            return

        values = self._read_inputs()
        if values is None:
            return
        weight, height = values

        try:
            bmi, category, colour = assess(weight, height)
        except ValidationError as error:
            self.set_status(f"Input error: {error}")
            messagebox.showwarning("Unrealistic result", str(error), parent=self.root)
            return

        self._show_result(bmi, category, colour, weight, height)

        try:
            self.database.add_record(user, weight, height, bmi, category)
        except db.StorageError as error:
            # Requirement: report database write failures without crashing.
            self.set_status(f"Save failed: {error}")
            messagebox.showerror(
                "Could not save",
                f"The result is shown, but it could not be saved.\n\n{error}",
                parent=self.root,
            )
            return

        self.current_user = user
        self._refresh_users(select=user)
        self._refresh_history()
        self.set_status(f"Saved BMI {bmi:.2f} ({category}) for '{user}'.")

    def show_only(self):
        """Show the result without writing a record to the database."""
        values = self._read_inputs()
        if values is None:
            return
        weight, height = values
        try:
            bmi, category, colour = assess(weight, height)
        except ValidationError as error:
            self.set_status(f"Input error: {error}")
            messagebox.showwarning("Unrealistic result", str(error), parent=self.root)
            return
        self._show_result(bmi, category, colour, weight, height)
        self.set_status("Calculated without saving.")

    def _show_result(self, bmi, category, colour, weight, height):
        self.bmi_value_label.configure(text=f"{bmi:.2f}", fg=colour)
        self.bmi_category_label.configure(text=category, fg=colour)

        healthy_low = 18.5 * (height ** 2)
        healthy_high = 24.9 * (height ** 2)

        detail = f"Weight {weight:g} kg  |  Height {height:g} m\n"
        if category == "Normal weight":
            detail += "Your BMI is in the healthy range."
        elif bmi < 18.5:
            detail += (f"To reach a BMI of 18.5 at this height, "
                       f"aim for about {healthy_low:.1f} kg.")
        else:
            detail += (f"To reach a BMI of 24.9 at this height, "
                       f"aim for about {healthy_high:.1f} kg.")
        detail += "\nBMI is a screening tool, not a medical diagnosis."
        self.bmi_detail_label.configure(text=detail)

    # ------------------------------------------------------------ history

    def _refresh_history(self):
        user = self.user_var.get().strip()
        if not user:
            self._render_chart([], None)
            self._fill_table([])
            self.history_user_label.configure(text="(no user)")
            return

        try:
            records = self.database.get_records(user)
        except db.StorageError as error:
            self.set_status(f"Database error: {error}")
            messagebox.showerror("Database error", str(error), parent=self.root)
            records = []

        self.history_user_label.configure(text=user)
        self._fill_table(records)
        self._render_chart(records, user)

    def _fill_table(self, records):
        self.tree.delete(*self.tree.get_children())
        for record in records:
            self.tree.insert(
                "", "end", iid=str(record["id"]),
                values=(
                    record["recorded_at"].replace("T", " "),
                    f"{record['weight_kg']:.1f}",
                    f"{record['height_m']:.2f}",
                    f"{record['bmi']:.2f}",
                    record["category"],
                ),
                tags=(record["category"],),
            )

    def _render_chart(self, records, user):
        """Draw the matplotlib figure, or show a message when it cannot be drawn."""
        status, figure, message = chart.build_figure(records, user or "")

        if status != chart.STATUS_OK or figure is None:
            if self.chart_canvas is not None:
                self.chart_canvas.get_tk_widget().destroy()
                self.chart_canvas = None
            self.chart_message.configure(text=message)
            self.chart_message.pack(fill="both", expand=True)
            return

        self.chart_message.pack_forget()

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            self.chart_message.configure(
                text="matplotlib's tkinter backend is unavailable."
            )
            self.chart_message.pack(fill="both", expand=True)
            return

        if self.chart_canvas is None:
            self.chart_canvas = FigureCanvasTkAgg(figure, master=self.chart_holder)
            self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            self.chart_canvas.figure = figure
        self.chart_canvas.draw()

    def delete_selected_record(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Nothing selected",
                                "Select a row in the Records tab first.",
                                parent=self.root)
            return
        try:
            self.database.delete_record(int(selection[0]))
        except db.StorageError as error:
            self.set_status(f"Database error: {error}")
            messagebox.showerror("Database error", str(error), parent=self.root)
            return
        self._refresh_history()
        self.set_status("Record deleted.")


def main():
    root = tk.Tk()

    database = db.BMIDatabase()
    try:
        database.connect()
    except db.StorageError as error:
        # The window must exist before a message box can be attached to it.
        root.withdraw()
        messagebox.showerror(
            "Database error",
            f"The BMI database could not be opened, so history cannot be "
            f"saved or loaded.\n\n{error}\n\nYou can still use the calculator, "
            f"but records will not persist.",
        )
        root.deiconify()

    app = BMIApp(root, database)
    if database.conn is None:
        root.withdraw()
        messagebox.showerror(
            "Database unavailable",
            "The database could not be opened. Restart the app after fixing "
            "the problem to save history.",
        )
        root.deiconify()
        app.set_status("Database unavailable - records will not be saved.")

    def on_close():
        database.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
