"""
prepare_data.py
---------------
Data layer for the fraud-detection pipeline.

Two modes:

1. REAL DATA (preferred) -- download "Credit Card Fraud Detection" (Credit Card
   Fraud Detection, 284,807 transactions / 492 frauds) from Kaggle:
       https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
   Drop `creditcard.csv` into  ./data/  and this module loads it as-is.

2. SYNTHETIC FALLBACK -- if no CSV is present, we generate a dataset that
   reproduces the *schema and statistics* of the benchmark dataset
   (Time, V1..V28 PCA components, Amount, Class) including the very rare
   positive class (~0.172%). This keeps the notebook runnable end-to-end
   without Kaggle credentials. The statistics are tuned to mirror the real
   data (fraud amounts skewed low, fraud concentrated in specific PCA
   directions, fraud clustered in low-traffic hours).

Public API
----------
load_raw_data(data_dir="data")   -> (DataFrame, source_label)
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd

RANDOM_STATE = 42
DATA_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CSV_NAME = "creditcard.csv"

# Real benchmark proportions (ULB / Worldline dataset).
N_ROWS = 284_807
FRAUD_RATE = 492 / 284_807  # ~0.001729 -> 0.172%

V_COLS = [f"V{i}" for i in range(1, 29)]


def _load_real_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected = set(["Time", "Amount", "Class"]) | set(V_COLS)
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(
            f"creditcard.csv is missing expected columns: {sorted(missing)}. "
            "Make sure you downloaded the Kaggle 'Credit Card Fraud Detection' dataset."
        )
    return df


def _generate_synthetic() -> pd.DataFrame:
    """Generate a dataset with the same schema/statistics as the Kaggle benchmark."""
    rng = np.random.default_rng(RANDOM_STATE)

    n_fraud = int(round(N_ROWS * FRAUD_RATE))  # ~492
    n_normal = N_ROWS - n_fraud

    # ---- V1..V28 : PCA components -------------------------------------------
    # Legitimate transactions ~ N(0,1) per component (PCA of scaled features).
    normal_v = rng.normal(loc=0.0, scale=1.0, size=(n_normal, 28))

    # Fraudulent transactions sit in a *shifted* region of PCA space, and only a
    # handful of components carry most of the signal. Two deliberate choices keep
    # the problem realistically hard (matching the real dataset, where fraud is
    # detectable but only ~99.9% AUC-ROC / ~0.80 AUC-PR is achievable):
    #   1. Modest shifts (~ +/-1.5 SD), so most frauds overlap the legitimate bulk.
    #   2. A HEAVY-tailed fraud spread, so a large share of frauds sits right
    #      inside the legitimate distribution and is genuinely near-undetectable.
    #      This is what produces the long, low-precision tail in the PR curve.
    fraud_shift = np.zeros(28)
    fraud_shift[[0, 1, 2, 3, 9, 10, 11, 12, 13, 16, 17, 18]] = [
        -1.6, 1.4, -1.9, 1.2, -1.0, -1.5, 1.3, -1.7, 0.6, -1.2, -2.0, -0.9,
    ]
    # Base fraud cloud only slightly wider than legitimate ...
    fraud_v = rng.normal(loc=fraud_shift, scale=1.5, size=(n_fraud, 28))
    # ... plus a heavy tail: ~35% of frauds get extra dispersion, pushing many
    # deep into the legitimate cloud where they cannot be separated.
    heavy = rng.random(n_fraud) < 0.35
    extra = rng.normal(loc=0.0, scale=np.where(heavy, 3.2, 0.0)[:, None], size=(n_fraud, 28))
    fraud_v = fraud_v + extra

    v = np.vstack([normal_v, fraud_v])
    labels = np.concatenate([np.zeros(n_normal, dtype=int), np.ones(n_fraud, dtype=int)])

    # ---- Amount --------------------------------------------------------------
    # Legitimate: log-normal, mean ~ 88 (mean of the real dataset).
    amount_normal = rng.lognormal(mean=3.4, sigma=1.35, size=n_normal)
    # Fraudulent: also skewed but lower on average, with a wide spread so the two
    # distributions overlap heavily (as they do in the real data).
    amount_fraud = rng.lognormal(mean=2.9, sigma=1.6, size=n_fraud)
    amount = np.concatenate([amount_normal, amount_fraud])
    amount = np.round(np.clip(amount, 0.0, 25_691.16), 2)

    # ---- Time ----------------------------------------------------------------
    # 48 hours of transactions (172,792 s window in the real data). Legitimate
    # traffic follows a day/night cycle; fraud is *over-represented at night*,
    # a pattern clearly visible in the real dataset.
    #
    # Implementation: sample hours via inverse-CDF (vectorised, O(n)) instead of
    # rejection sampling, which would be slow for 284k rows.
    seconds_in_day = 86_400
    def _sample_hours(size: int, weights_fn) -> np.ndarray:
        # Draw `size` hours-of-day from a piecewise-constant density.
        # (comment, not docstring, to keep this edit unambiguous)""
        grid = np.linspace(0.0, 24.0, 241)          # 6-minute resolution
        w = weights_fn((grid[:-1] + grid[1:]) / 2.0)
        cdf = np.cumsum(w * np.diff(grid))
        cdf /= cdf[-1]
        u = rng.random(size)
        hours = np.interp(u, cdf, grid[:-1])
        return hours
    # Legit: bimodal (peaks mid-morning / late evening).
    weights_norm = lambda h: (
        0.6 * np.exp(-0.5 * ((h - 11.0) / 4.0) ** 2)
        + 0.8 * np.exp(-0.5 * ((h - 20.0) / 3.0) ** 2)
        + 0.25
    )
    # Fraud: night-heavy (00:00-06:00 / 22:00-24:00 over-represented).
    weights_fraud = lambda h: np.where((h < 6) | (h >= 22), 2.2, 0.45)

    day_norm = rng.integers(0, 2, size=n_normal)
    hour_norm = _sample_hours(n_normal, weights_norm)
    normal_time = (day_norm * seconds_in_day + hour_norm * 3600).astype(int)

    day_fraud = rng.integers(0, 2, size=n_fraud)
    hour_fraud = _sample_hours(n_fraud, weights_fraud)
    fraud_time = (day_fraud * seconds_in_day + hour_fraud * 3600).astype(int)

    time = np.clip(np.concatenate([normal_time, fraud_time]), 0, 2 * seconds_in_day - 1).astype(int)

    df = pd.DataFrame(v, columns=V_COLS)
    df.insert(0, "Time", time)
    df["Amount"] = amount
    df["Class"] = labels

    # Shuffle so fraud is not all at the end.
    df = df.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)
    return df


def load_raw_data(data_dir: str = DATA_DIR_DEFAULT):
    """Return (dataframe, source_label). Uses the real CSV if available."""
    csv_path = os.path.join(data_dir, CSV_NAME)
    if os.path.exists(csv_path):
        return _load_real_csv(csv_path), f"REAL DATA: {csv_path}"

    os.makedirs(data_dir, exist_ok=True)
    df = _generate_synthetic()
    # Persist so repeat runs are identical & fast.
    out_path = os.path.join(data_dir, "creditcard_synthetic.csv")
    df.to_csv(out_path, index=False)
    return df, f"SYNTHETIC FALLBACK: {out_path}"


if __name__ == "__main__":
    frame, src = load_raw_data()
    print(src)
    print(frame.shape)
    print(frame["Class"].value_counts())
    print(f"Fraud rate: {frame['Class'].mean() * 100:.3f}%")
