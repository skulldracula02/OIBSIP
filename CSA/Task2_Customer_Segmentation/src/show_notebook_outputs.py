"""Print the text output of selected notebook cells for visual verification."""
import json
import sys

with open("Task2_Customer_Segmentation.ipynb", encoding="utf-8") as fh:
    nb = json.load(fh)

code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]

which = [int(a) for a in sys.argv[1:]] or list(range(len(code_cells)))
for i in which:
    if i >= len(code_cells):
        continue
    src_first = code_cells[i]["source"][0].strip()[:70]
    print("=" * 100)
    print(f"CELL {i}  ->  {src_first}")
    print("=" * 100)
    for o in code_cells[i].get("outputs", []):
        if o.get("output_type") == "stream":
            print("".join(o["text"]))
        elif o.get("output_type") == "execute_result":
            data = o.get("data", {})
            if "text/plain" in data:
                print("".join(data["text/plain"]))
        elif o.get("output_type") == "error":
            print("ERROR:", o.get("ename"), o.get("evalue"))
    print()
