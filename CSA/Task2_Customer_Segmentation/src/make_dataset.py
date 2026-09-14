"""
Generate a synthetic e-commerce transaction dataset.

The schema intentionally mirrors the classic UCI "Online Retail" dataset
(InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice,
CustomerID, Country) so that the exact same analysis code can be pointed at
the real CSV from Kaggle/UCI with no changes.

It deliberately also injects the data-quality problems the real dataset has:
    * missing CustomerID
    * missing Description
    * cancelled / returned orders (negative Quantity)
    * duplicate rows
    * inconsistent text casing and whitespace in Country
    * a few zero / negative UnitPrice rows (data entry errors)

Run:
    python src/make_dataset.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RANDOM_STATE = 42
N_CUSTOMERS = 1200
OUT_PATH = "data/online_retail.csv"

rng = np.random.default_rng(RANDOM_STATE)

COUNTRIES = [
    "United Kingdom",
    "Germany",
    "France",
    "EIRE",
    "Spain",
    "Netherlands",
    "Belgium",
    "Switzerland",
    "Portugal",
    "Australia",
]

PRODUCTS = [
    ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
    ("71053", "WHITE METAL LANTERN", 3.39),
    ("84406B", "CREAM CUPID HEARTS COAT HANGER", 2.75),
    ("84029G", "KNITTED UNION FLAG HOT WATER BOTTLE", 3.39),
    ("84029E", "RED WOOLLY HOTTIE WHITE HEART", 3.39),
    ("22752", "SET 7 BABUSHKA NESTING BOXES", 7.65),
    ("21730", "GLASS STAR FROSTED T-LIGHT HOLDER", 4.25),
    ("22633", "HAND WARMER UNION JACK", 1.85),
    ("22632", "HAND WARMER RED POLKA DOT", 1.85),
    ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69),
    ("47566", "PARTY BUNTING", 4.95),
    ("20725", "LUNCH BAG RED RETROSPOT", 1.65),
    ("22383", "LUNCH BAG SUKI DESIGN", 1.65),
    ("20727", "LUNCH BAG BLACK SKULL", 1.65),
    ("21232", "STRAWBERRY CERAMIC TRINKET BOX", 2.10),
    ("22086", "PAPER CHAIN KIT 50'S CHRISTMAS", 2.95),
    ("37410", "TWO DOOR CURTAIN", 11.95),
    ("21871", "SAVE THE PLANET MUG", 2.10),
    ("22423", "REGENCY CAKESTAND 3 TIER", 12.75),
    ("22803", "PINK SPOTTY CUP", 1.95),
]

# ---------------------------------------------------------------------------
# 1. Build latent customer "types" so the clusters we discover are real, not
#    noise. Each archetype gets its own recency / frequency / monetary range.
#    This gives the K-Means step something genuine to find, exactly like a
#    real retail base splits into VIPs, loyal regulars and one-time buyers.
# ---------------------------------------------------------------------------
ARCHETYPES = {
    # name: (share, max_recency_days, freq_lo, freq_hi, avg_unit_lo, avg_unit_hi, qty_lo, qty_hi)
    "champions":      (0.06, 25,  14, 32, 22, 65, 6, 22),
    "loyal":          (0.14, 60,   7, 16, 14, 38, 4, 14),
    "potential":      (0.20, 120,  3,  9,  9, 24, 3, 10),
    "at_risk":        (0.22, 260,  2,  7,  7, 20, 2,  8),
    "hibernating":    (0.20, 500,  1,  3,  5, 14, 1,  5),
    "new_one_time":   (0.18, 40,   1,  2,  4, 12, 1,  4),
}

archetype_names = list(ARCHETYPES.keys())
archetype_shares = np.array([v[0] for v in ARCHETYPES.values()])
archetype_shares = archetype_shares / archetype_shares.sum()

customer_archetype = rng.choice(
    archetype_names, size=N_CUSTOMERS, p=archetype_shares
)

# Reference "today" for recency = day after the last transaction in the data.
SNAPSHOT = pd.Timestamp("2011-12-10")

rows = []
invoice_counter = 536_000

for idx, archetype in enumerate(customer_archetype):
    customer_id = 12346 + idx
    _, max_recency, freq_lo, freq_hi, price_lo, price_hi, qty_lo, qty_hi = (
        ARCHETYPES[archetype]
    )

    n_orders = int(rng.integers(freq_lo, freq_hi + 1))

    # Recency: most recent order within max_recency days of the snapshot,
    # earlier orders spread further back in time.
    last_order_days_ago = int(rng.integers(1, max_recency + 1))

    country = (
        "United Kingdom"
        if rng.random() < 0.72
        else COUNTRIES[int(rng.integers(1, len(COUNTRIES)))]
    )

    for order_no in range(n_orders):
        # Space orders out going backwards in time from the last order.
        gap = int(rng.integers(5, 45)) * order_no
        days_ago = last_order_days_ago + gap
        if days_ago > 720:
            continue  # outside the 2-year window
        invoice_date = SNAPSHOT - pd.Timedelta(days=days_ago)
        invoice_date = invoice_date + pd.Timedelta(
            hours=int(rng.integers(8, 20)), minutes=int(rng.integers(0, 60))
        )

        invoice_no = str(invoice_counter)
        invoice_counter += 1

        # 1-5 distinct products per order
        n_lines = int(rng.integers(1, 6))
        chosen = rng.choice(len(PRODUCTS), size=n_lines, replace=False)

        for p in chosen:
            stock_code, description, base_price = PRODUCTS[p]
            unit_price = np.round(
                base_price * rng.uniform(price_lo / 20.0, price_hi / 20.0), 2
            )
            quantity = int(rng.integers(qty_lo, qty_hi + 1))

            # ~4% of lines are returns / cancellations
            if rng.random() < 0.04:
                invoice_no_line = "C" + invoice_no
                quantity = -quantity
            else:
                invoice_no_line = invoice_no

            rows.append(
                {
                    "InvoiceNo": invoice_no_line,
                    "StockCode": stock_code,
                    "Description": description,
                    "Quantity": quantity,
                    "InvoiceDate": invoice_date,
                    "UnitPrice": unit_price,
                    "CustomerID": customer_id,
                    "Country": country,
                }
            )

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# 2. Inject the messy real-world defects
# ---------------------------------------------------------------------------
n = len(df)

# Missing CustomerID (~1.5%) - guest checkouts
guest_mask = rng.random(n) < 0.015
df.loc[guest_mask, "CustomerID"] = np.nan

# Missing Description (~1%)
df.loc[rng.random(n) < 0.01, "Description"] = np.nan

# Zero / negative UnitPrice data-entry errors (~0.4%)
df.loc[rng.random(n) < 0.004, "UnitPrice"] = 0.0

# Inconsistent casing / stray whitespace in Country
messy_mask = rng.random(n) < 0.06
df.loc[messy_mask, "Country"] = (
    df.loc[messy_mask, "Country"].str.upper().radd("  ").str.strip().str.title()
    .apply(lambda c: "  " + str(c) + "  " if isinstance(c, str) else c)
)

# Exact duplicate rows (~0.5%)
dupes = df.sample(frac=0.005, random_state=RANDOM_STATE)
df = pd.concat([df, dupes], ignore_index=True)

# Shuffle so it does not look generated in order
df = df.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)

df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["CustomerID"] = df["CustomerID"].astype("Float64")

df.to_csv(OUT_PATH, index=False)

print(f"Wrote {len(df):,} rows to {OUT_PATH}")
print(f"Unique customers (raw): {df['CustomerID'].nunique():,}")
print(f"Missing CustomerID rows: {df['CustomerID'].isna().sum():,}")
print(f"Date range: {df['InvoiceDate'].min()} -> {df['InvoiceDate'].max()}")
print(df.head(8).to_string())
