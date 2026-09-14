"""
Download the Wine Quality dataset (red + white) from the UCI Machine Learning
Repository and save the raw CSV files into the data/ folder.

Source: https://archive.ics.uci.edu/dataset/186/wine+quality
The UCI zip bundle contains winequality-red.csv and winequality-white.csv,
both ';'-separated.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import requests

UCI_ZIP_URL = (
    "https://archive.ics.uci.edu/static/public/186/wine+quality.zip"
)
# Fallback: individual raw CSVs hosted in the UCI repo / mirrors
FALLBACK_URLS = {
    "winequality-red.csv": [
        "https://raw.githubusercontent.com/mlflow/mlflow/master/examples/sklearn_elasticnet_wine/winequality-red.csv",
        "https://raw.githubusercontent.com/plotly/datasets/master/winequality-red.csv",
    ],
    "winequality-white.csv": [
        "https://raw.githubusercontent.com/selva86/datasets/master/winequality-white.csv",
    ],
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def download_zip() -> bool:
    print(f"[zip] requesting {UCI_ZIP_URL}")
    headers = {"User-Agent": "Mozilla/5.0 (wine-quality-project)"}
    try:
        r = requests.get(UCI_ZIP_URL, headers=headers, timeout=60)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"[zip] failed: {exc}")
        return False

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        print(f"[zip] members: {names}")
        extracted = 0
        for name in names:
            base = Path(name).name
            if base in ("winequality-red.csv", "winequality-white.csv"):
                target = DATA_DIR / base
                with zf.open(name) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                print(f"[zip] wrote {target} ({target.stat().st_size} bytes)")
                extracted += 1
        return extracted >= 2


def download_fallback() -> bool:
    ok = 0
    for fname, urls in FALLBACK_URLS.items():
        target = DATA_DIR / fname
        if target.exists() and target.stat().st_size > 0:
            print(f"[fb] {fname} already present")
            ok += 1
            continue
        for url in urls:
            print(f"[fb] trying {url}")
            try:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                text = r.text
                # Normalise to ';' separated header format expected from UCI
                first_line = text.splitlines()[0]
                sep = ";" if ";" in first_line else ","
                # If the mirror used commas and no semicolons, convert header row
                if sep == ",":
                    lines = text.splitlines()
                    lines[0] = ";".join(lines[0].split(","))
                    text = "\n".join(lines)
                target.write_text(text, encoding="utf-8")
                print(f"[fb] wrote {target} ({target.stat().st_size} bytes)")
                ok += 1
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[fb] failed: {exc}")
    return ok >= 2


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if download_zip():
        print("Downloaded from UCI zip bundle.")
        return 0
    if download_fallback():
        print("Downloaded from fallback mirrors.")
        return 0
    print("ERROR: could not download the dataset.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
