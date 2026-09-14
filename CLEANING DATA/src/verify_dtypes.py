"""Confirm the in-notebook dtype of Join Date is datetime64 (CSV round-trip re-infers to str)."""
import sys
import nbformat
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. In-notebook dtype: read straight from the executed notebook's dtype audit output.
nb = nbformat.read("notebooks/data_cleaning_pipeline.ipynb", as_version=4)
for cell in nb.cells:
    if cell.cell_type == "code" and "assert pd.api.types.is_datetime64_any_dtype" in cell.source:
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream":
                print("Notebook assertion cell output:")
                print("".join(out.get("text", [])))

# 2. Prove the CSV is re-loadable as a real datetime when the schema is declared.
clean = pd.read_csv("data/titanic_cleaned.csv", parse_dates=["Join Date"])
print("\nReloaded with parse_dates:")
print(clean.dtypes[["Join Date", "Age", "Pclass", "Survived", "Annual Spend"]].to_string())
print(f"\nJoin Date dtype: {clean['Join Date'].dtype}")
print(f"Join Date nulls: {clean['Join Date'].isna().sum()}")
print(f"Date range     : {clean['Join Date'].min().date()} .. {clean['Join Date'].max().date()}")
print(f"Unique dates   : {clean['Join Date'].nunique()}")
