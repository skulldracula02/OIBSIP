"""Report any error output captured in the executed notebook."""
import nbformat

nb = nbformat.read("notebooks/data_cleaning_pipeline.ipynb", as_version=4)
errors = 0
executed = 0
for i, cell in enumerate(nb.cells):
    if cell.cell_type != "code":
        continue
    executed += 1
    for out in cell.get("outputs", []):
        if out.get("output_type") == "error":
            errors += 1
            print(f"=== CELL {i}: {out.get('ename')}: {out.get('evalue')} ===")
            tb = out.get("traceback", [])
            for line in tb[-8:]:
                print("   ", line)
            print()

print(f"Executed code cells: {executed}   error outputs: {errors}")
