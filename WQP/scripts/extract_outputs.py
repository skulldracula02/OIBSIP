"""Extract key outputs (metrics, reports) from the executed notebook for reporting."""
import json
from pathlib import Path

nb = json.loads(Path("wine_quality_prediction.ipynb").read_text(encoding="utf-8"))
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    src = "".join(c["source"])
    outs = []
    for o in c.get("outputs", []):
        if o.get("output_type") == "stream":
            outs.append("".join(o.get("text", [])))
        elif o.get("output_type") in ("execute_result", "display_data"):
            data = o.get("data", {})
            if "text/plain" in data:
                outs.append("".join(data["text/plain"]))
    text = "".join(outs).strip()
    if not text:
        continue
    if any(k in src for k in [
        "accuracy_score", "classification_report", "comparison",
        "binary_df", "quality_counts", "importances", "Train size",
        "combined relationship", "df.shape", "quality_3class",
    ]):
        print("=" * 70)
        print(f"CELL {i}")
        print("=" * 70)
        print(text[:2000])
        print()
