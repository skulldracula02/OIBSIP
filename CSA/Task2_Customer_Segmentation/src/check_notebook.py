"""Verify the executed notebook: no errored cells, all code cells ran."""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "Task2_Customer_Segmentation.ipynb"
with open(path, encoding="utf-8") as fh:
    nb = json.load(fh)

code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
errors = []
images = 0
for i, c in enumerate(code_cells):
    for o in c.get("outputs", []):
        if o.get("output_type") == "error":
            errors.append((i, o.get("ename"), o.get("evalue")))
        if "image/png" in o.get("data", {}):
            images += 1

unrun = [i for i, c in enumerate(code_cells) if c.get("execution_count") is None]

print(f"File:              {path}")
print(f"Total cells:       {len(nb['cells'])}")
print(f"Code cells:        {len(code_cells)}")
print(f"Executed cells:    {len(code_cells) - len(unrun)}/{len(code_cells)}")
print(f"Inline images:     {images}")
print(f"Errored cells:     {len(errors)}")
for i, ename, evalue in errors:
    print(f"   cell {i}: {ename}: {evalue}")
if unrun:
    print(f"Un-run code cells: {unrun}")

sys.exit(1 if errors else 0)
