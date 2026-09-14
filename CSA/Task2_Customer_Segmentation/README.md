# TASK 2 · Customer Segmentation Analysis

Segmenting an e-commerce customer base into distinct purchasing-behaviour groups
using **RFM analysis + K-Means clustering**, so marketing spend can be targeted
at the segments that actually drive revenue.

**Tech stack:** Python · pandas · scikit-learn (KMeans) · matplotlib · seaborn · Jupyter

---

## The headline result

**8% of customers generate 62% of revenue.**

| Segment | Customers | Share of base | Share of revenue | Recency | Frequency | Monetary |
|---|---:|---:|---:|---:|---:|---:|
| Champions | 99 | 8.3% | **62.0%** | 12 days | 21.8 | $5,596 |
| Loyal Customers | 190 | 16.0% | 24.9% | 39 days | 11.5 | $1,170 |
| Loyal Customers (less frequent) | 92 | 7.8% | 3.9% | 12 days | 6.7 | $378 |
| At Risk – High Value | 306 | 25.8% | 7.6% | 124 days | 5.6 | $222 |
| Hibernating / Lost | 250 | 21.1% | 1.1% | 264 days | 2.3 | $39 |
| New / Promising | 249 | 21.0% | 0.5% | 22 days | 1.7 | $17 |

Any strategy that treats the base as one homogeneous group misallocates almost
its entire budget.

---

## Repository layout

```
Task2_Customer_Segmentation/
├── Task2_Customer_Segmentation.ipynb   # The deliverable notebook (executed, with outputs)
├── README.md                           # This file
├── requirements.txt
├── data/
│   └── online_retail.csv               # Transaction dataset (UCI Online Retail schema)
├── outputs/                            # Charts + CSV artefacts from the pipeline
│   ├── 01_elbow_method.png
│   ├── 02_scatter_Recency_vs_Frequency.png
│   ├── 03_scatter_Frequency_vs_Monetary.png
│   ├── 04_scatter_Recency_vs_Monetary.png
│   ├── 05_customers_per_cluster.png
│   ├── 06_cluster_profile_heatmap.png
│   ├── rfm_clustered.csv               # Per-customer RFM + assigned segment
│   ├── rfm_scored.csv                  # Per-customer classical 1-5 RFM scores
│   ├── cluster_profiles.csv            # Profile table
│   └── elbow_silhouette.csv            # Inertia + silhouette by K
└── src/
    ├── make_dataset.py                 # Generates the dataset (with realistic defects)
    ├── rfm_clustering.py               # The whole pipeline, as importable functions
    ├── build_notebook.py               # Regenerates the .ipynb from readable source
    ├── check_notebook.py               # Verifies the notebook ran with no errors
    └── show_notebook_outputs.py        # Prints selected notebook cell outputs
```

---

## How to run

```bash
pip install -r requirements.txt

# 1. (optional) regenerate the dataset
python src/make_dataset.py

# 2. run the pipeline as a script -> writes all charts + CSVs to outputs/
python src/rfm_clustering.py

# 3. or open the notebook
jupyter notebook Task2_Customer_Segmentation.ipynb
```

To regenerate the notebook from source and verify it executes cleanly:

```bash
python src/build_notebook.py
python -m nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=600 Task2_Customer_Segmentation.ipynb
python src/check_notebook.py
```

---

## Feature checklist

| Requirement | Where | Status |
|---|---|---|
| Load dataset, inspect structure | Notebook §1, `load_and_clean()` | ✅ |
| Handle missing / inconsistent data | Notebook §1b, `load_and_clean()` | ✅ |
| Descriptive stats: purchase value, frequency, CLV | Notebook §2, `descriptive_stats()` | ✅ |
| Feature selection (2–3 behavioural features) | Notebook §3, `build_rfm()` | ✅ R, F, M |
| Normalisation / standardisation | Notebook §4, `scale_features()` | ✅ log1p + StandardScaler |
| K-Means with Elbow Method for K | Notebook §5, `evaluate_k()` / `pick_k()` | ✅ K=6 |
| Scatter plots, ≥2 feature combinations | Notebook §7, `plot_scatter_combinations()` | ✅ 3 combinations |
| Profile each cluster + describe customer type | Notebook §6, `profile_clusters()` / `label_clusters()` | ✅ |
| Bar chart: customers per cluster | Notebook §8, `plot_cluster_sizes()` | ✅ |
| Insights: marketing action per segment | Notebook §9, `MARKETING_ACTIONS` | ✅ |

---

## Data quality handling

The dataset deliberately carries the defects found in the real UCI Online
Retail data, and all six are handled explicitly (reported in the notebook's
QA table):

| Defect | Count | Action |
|---|---:|---|
| Rows missing `CustomerID` | 332 | Dropped — unattributable to any customer |
| Exact duplicate rows | 106 | `drop_duplicates()` |
| Cancellation / return rows | 776 | Flagged, netted out of revenue |
| `UnitPrice <= 0` | 97 | Dropped |
| Missing `Description` | 226 | Filled `"UNKNOWN"` (not a model feature) |
| Inconsistent `Country` casing/whitespace | ~6% | Stripped + title-cased |
| Quantity outliers | > 99.9th pct | Winsorised to protect centroids |

Result: 21,212 raw rows → **20,677 clean line items across 1,198 customers**.

---

## Modelling notes

**Why log1p *and* StandardScaler, not just one.** All three RFM features are
heavily right-skewed — a few wholesale buyers spend ~100× the median. On the
raw scale those points dominate every Euclidean distance and drag the centroids
toward them. `log1p` compresses the tail; `StandardScaler` then puts the three
features on a common footing so Recency (0–720) is not drowned by Monetary
(0–20,000).

**Why K=6.** Inertia falls steeply to K≈5 then flattens. `pick_k()` requires the
elbow to have genuinely flattened (marginal drop < 25% of the first drop) and
then chooses the best silhouette among the surviving candidates. K=6 keeps
segments granular enough to be actionable (a distinct "New/Promising" group
separate from "Loyal") without fragmenting the base. Final silhouette ≈ 0.39 —
real but moderate structure, which is normal for behavioural data.

**Why the segment names are rule-based, not hand-typed.** `label_clusters()`
classifies each cluster against the *base customer distribution* (not the
cluster means), so a cluster spending $1,170 is never mislabelled "low value"
just because one Champion cluster spends $5,596. "Champions" is reserved for
the single top-spending cluster that also clears the recency and frequency
bars.

---

## Recommended actions (summary)

| Segment | Action | Success metric |
|---|---|---|
| **Champions** | **Reward, don't discount.** VIP tier, early access, free express shipping, referrals. Discounting trains them to wait for sales. | Retention; referrals; AOV held flat |
| **Loyal Customers** | **Grow frequency.** Replenishment/subscription, points loyalty, personalised cross-sell. | Orders per customer per year |
| **Loyal (less frequent)** | **Trade up.** Bundles, free-shipping threshold just above their AOV. | Average order value |
| **At Risk – High Value** | **Urgent win-back.** Personal offer + feedback survey + human outreach for top individuals. Biggest recoverable pool. | Reactivation within 90 days |
| **New / Promising** | **Onboard to order #2.** 30-day welcome series, time-limited second-purchase incentive. | % reaching 2nd/3rd order |
| **Hibernating / Lost** | **Minimise spend.** Exclude from paid campaigns; one cheap seasonal email, then suppress. | Cost per reactivation vs CLV |

**Prioritisation:** At Risk – High Value → Champions → New/Promising → Hibernating.
Revenue is so concentrated that a 1-point gain in Champions retention beats a
10-point gain in Hibernating reactivation.

---

## Limitations

- **K-Means assumes spherical, similar-sized clusters.** These segments are a
  useful approximation, not a discovered ground truth. DBSCAN / GMM would allow
  different shapes and are worth comparing.
- **Silhouette ≈ 0.39** means moderate separation — expected when behaviour is
  a continuum rather than discrete islands.
- **Recency depends on a fixed snapshot date.** `build_rfm()` defaults to one
  day after the last transaction; production runs must fix "today" consistently
  or segments shift for calendar rather than behavioural reasons.
- **RFM is behavioural, not attitudinal.** It cannot tell a churned customer
  from one who moved or simply had no need.
- **Monetary is gross revenue**, not margin. A segment of heavy returners can
  look valuable while destroying profit.
- **The dataset is synthetic**, generated with the UCI Online Retail schema so
  the code is drop-in compatible with the real CSV. Change `DATA_PATH` to point
  at the real file — the method is unchanged, only the absolute numbers differ.

---

## Dataset note

`data/online_retail.csv` is generated by `src/make_dataset.py` using the exact
column schema of the UCI *Online Retail* dataset (also available on Kaggle),
including its realistic defects.

The real data is published on the UCI ML Repository:

- [Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) — id 352, covers 01/12/2010 – 09/12/2011 ([dataset details](https://archive.ics.uci.edu/ml/datasets/online%20retail))
- [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) — id 502, covers 01/12/2009 – 09/12/2011 (the range this synthetic set mirrors)

To use the genuine data, download the Excel file, save it as
`data/online_retail.csv`, and update `DATA_PATH` if needed — no other code
changes are required. Both datasets share the column schema
(`InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`,
`UnitPrice`, `CustomerID`, `Country`) and the same real-world defects the
pipeline cleans.
