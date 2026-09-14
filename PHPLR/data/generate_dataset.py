"""
Generate a realistic Ames-Housing-style dataset for the linear regression project.

Why synthetic? The Kaggle "House Prices: Advanced Regression Techniques" (Ames) dataset
requires a Kaggle API key. This generator reproduces the *structure* and *statistical
behaviour* of that dataset (including missing values and a categorical location column)
so the whole pipeline can run reproducibly offline.

The generated file is written to data/house_prices.csv.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RNG_SEED = 42
N_ROWS = 2930  # close to the real Ames dataset size


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)

    # ------------------------------------------------------------------
    # Core features requested by the task: area, location, rooms, age
    # ------------------------------------------------------------------
    # Living area in square feet (log-normal -> realistic right skew).
    area = np.round(rng.lognormal(mean=7.20, sigma=0.32, size=N_ROWS))

    # Age of the house at sale (years).
    age = np.clip(np.round(rng.gamma(shape=2.2, scale=15.0, size=N_ROWS)), 0, 130)

    # Rooms (above ground).
    rooms = np.clip(np.round(area / 320 + rng.normal(0, 0.7, N_ROWS)), 1, 12)

    # Number of bathrooms (a strong real-world predictor).
    bathrooms = np.clip(np.round(area / 900 + rng.normal(0, 0.35, N_ROWS), 1), 1, 5)

    # Garage capacity (cars).
    garage = np.clip(np.round(rng.normal(2.0, 0.8, size=N_ROWS)), 0, 4)

    # Overall quality (1-10). Drives price strongly, correlated with area.
    quality = np.clip(np.round(rng.normal(6, 1.4, N_ROWS) + (area - 1200) / 1500), 1, 10)

    # Location category (categorical -> needs One-Hot Encoding).
    locations = ["Downtown", "Suburb", "Rural", "Waterfront"]
    location = rng.choice(locations, size=N_ROWS, p=[0.28, 0.42, 0.22, 0.08])

    # Location price multipliers and baseline premiums.
    loc_mult = {"Downtown": 1.10, "Suburb": 1.00, "Rural": 0.82, "Waterfront": 1.55}
    loc_base = {"Downtown": 45000, "Suburb": 30000, "Rural": 12000, "Waterfront": 120000}

    # Binary flag: recently renovated (example of a boolean feature).
    renovated = rng.choice([0, 1], size=N_ROWS, p=[0.62, 0.38])

    # ------------------------------------------------------------------
    # Generate the target: sale price.
    # True data-generating process (what the model tries to recover):
    #   price = base + area*120 - age*900 + rooms*4500 + bathrooms*8000
    #           + garage*6000 + quality*11000 + location effect
    #           - renovated discount... + noise
    # ------------------------------------------------------------------
    base = 60000
    price = (
        base
        + loc_base_effect(location, loc_base)
        + area * 118.0
        - age * 850.0
        + rooms * 4200.0
        + bathrooms * 8500.0
        + garage * 5500.0
        + quality * 10500.0
        + renovated * 7000.0
        + rng.normal(0, 18000, N_ROWS)          # irreducible noise / unobserved factors
    )
    price = price * np.array([loc_mult[l] for l in location])
    price = np.clip(price, 45000, None).round(-2)  # round to nearest $100

    df = pd.DataFrame(
        {
            "area": area.astype(int),
            "location": location,
            "rooms": rooms.astype(int),
            "bathrooms": bathrooms,
            "garage": garage.astype(int),
            "age": age.astype(int),
            "quality": quality.astype(int),
            "renovated": renovated.astype(int),
            "price": price.astype(int),
        }
    )

    # ------------------------------------------------------------------
    # Inject realistic missingness (so cleaning is a genuine step).
    # ------------------------------------------------------------------
    for col, frac in [("area", 0.02), ("bathrooms", 0.04), ("garage", 0.03), ("age", 0.015)]:
        idx = rng.choice(df.index, size=int(len(df) * frac), replace=False)
        df.loc[idx, col] = np.nan

    # A few SalePrice outliers / data-entry noise, and a handful of duplicate rows.
    dup_idx = rng.choice(df.index, size=15, replace=False)
    df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)

    out = "data/house_prices.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out}: shape={df.shape}")
    print(df.head().to_string())
    print("\nMissing values:\n", df.isnull().sum().to_string())
    print("\nPrice describe:\n", df["price"].describe().to_string())


def loc_base_effect(location: np.ndarray, loc_base: dict[str, int]) -> np.ndarray:
    return np.array([loc_base[l] for l in location])


if __name__ == "__main__":
    main()
