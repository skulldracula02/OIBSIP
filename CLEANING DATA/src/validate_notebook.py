"""Validate every code cell in the notebook compiles before we execute it."""
import ast

import nbformat

nb = nbformat.read("notebooks/data_cleaning_pipeline.ipynb", as_version=4)
bad = 0
for i, cell in enumerate(nb.cells):
    if cell.cell_type != "code":
        continue
    try:
        ast.parse(cell.source)
    except SyntaxError as e:
        bad += 1
        print(f"--- CELL {i}: {e.msg} (line {e.lineno}) ---")
        print(repr(e.text))
        print(cell.source[:600])
        print()

print(f"Checked {sum(c.cell_type == 'code' for c in nb.cells)} code cells; {bad} with syntax errors")
