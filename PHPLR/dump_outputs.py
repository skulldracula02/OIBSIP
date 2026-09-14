"""Print the text outputs from the executed notebook, cell by cell, for verification."""
import nbformat

nb = nbformat.read("notebooks/house_price_linear_regression.ipynb", as_version=4)

for i, cell in enumerate(nb.cells):
    if cell.cell_type != "code":
        continue
    outs = []
    for o in cell.get("outputs", []):
        if o.get("output_type") == "stream":
            outs.append(o.get("text", ""))
        elif o.get("output_type") == "execute_result":
            data = o.get("data", {})
            if "text/plain" in data:
                outs.append(data["text/plain"])
    text = "".join(outs).strip()
    if text:
        print(f"\n===== CELL {i} =====")
        print(text[:1600])
