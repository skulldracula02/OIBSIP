"""Execute the notebook end-to-end and save it in place with outputs."""
import sys
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

path = "notebooks/house_price_linear_regression.ipynb"
nb = nbformat.read(path, as_version=4)

client = NotebookClient(
    nb,
    timeout=600,
    kernel_name="python3",
    resources={"metadata": {"path": "notebooks"}},
)

try:
    client.execute()
    print("NOTEBOOK EXECUTED SUCCESSFULLY")
except CellExecutionError as e:
    print("CELL EXECUTION ERROR:")
    print(e)
    nbformat.write(nb, path)
    sys.exit(1)

nbformat.write(nb, path)
print(f"Saved executed notebook to {path}")
