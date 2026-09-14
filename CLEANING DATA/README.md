# Data Cleaning — From a Messy CRM Export to an Analysis-Ready Dataset

A professional-level data-cleaning deliverable: a deliberately dirty dataset is taken through
a documented, reproducible pipeline that produces a clean, typed, analysis-ready table.

**Stack:** Python 3.14 · pandas 3.0 · numpy 2.5 · matplotlib · Jupyter Notebook

---

## Headline results

| Metric | Before | After | Change |
|---|---|
| Rows | 917 | 891 | −26 (duplicates removed) |
| Columns | 15 | 17 | +2 engineered features |
| Null cells (incl. sentinels) | 1,097 (7.98%) | 760 (5.02%) | −337 |
| Exact duplicate rows | 7 | 0 | eliminated |
| Duplicate `Passenger Id`s | 14 | 0 | eliminated |
| Columns with correct dtype | 0 | 17 | **dtype accuracy 0% → 100%** |

All 49 notebook cells execute with **zero errors**, and the notebook ends with hard
assertions validating every cleaned column.

---

## Repository layout

```
CLEANING DATA/
├── data/
│   ├── titanic_raw.csv                 # base Kaggle Titanic train file (891 x 12)
│   ├── titanic_clean_reference.csv     # pristine base copy (provenance)
│   ├── messy_dataset.csv               # ← the INPUT: deliberately dirty (917 x 15)
│   ├── injected_outliers.csv           # record of injected extreme values
│   └── titanic_cleaned.csv             # ← the OUTPUT: analysis-ready (891 x 17)
├── notebooks/
│   └── data_cleaning_pipeline.ipynb    # the main deliverable (executed, with outputs)
├── outputs/
│   ├── 01_missingness_before.png       # missingness profile, pre-cleaning
│   ├── 02_outliers_before.png          # box-plots showing pre-cleaning outliers
│   ├── 03_outlier_methods.png          # IQR vs Z-score comparison
│   ├── 04_outliers_after.png           # distributions post-treatment
│   ├── 05_before_vs_after.png          # visual scorecard
│   ├── before_after_scorecard.csv      # the before/after summary table
│   ├── per_column_before_after.csv     # per-column null/dtype deltas
│   └── data_dictionary.csv             # self-describing schema of the clean file
└── src/
    ├── build_messy_dataset.py          # generates the dirty dataset (seeded, reproducible)
    └── build_notebook.py               # builds the notebook programmatically
```

---

## How to run

Everything is already executed and committed — you can simply open the notebook. To
regenerate from scratch:

```powershell
# 1. Regenerate the dirty dataset (deterministic: random_state=42)
python src/build_messy_dataset.py

# 2. Rebuild the notebook source (only needed if you edit build_notebook.py)
python src/build_notebook.py

# 3. Execute the notebook end-to-end
python -m nbconvert --to notebook --execute --inplace `
    --ExecutePreprocessor.timeout=300 notebooks/data_cleaning_pipeline.ipynb
```

> **Note:** `python` was not on `PATH` on this machine; the interpreter used throughout is
> `C:\Python314\python.exe`.

---

## The dataset

The base is the standard practice dataset from the Kaggle **"Titanic — Machine Learning from
Disaster"** competition (891 rows × 12 columns), retrieved from the public mirror
[`datasciencedojo/datasets`](https://github.com/datasciencedojo/datasets). On top of that
real data, `build_messy_dataset.py` injects a realistic catalogue of the defects that
actually occur in CRM and warehouse exports:

| Defect class | What was injected |
|---|---|
| Missing data | `Age` blank + sentinel `-1`; `Cabin` ~79% null; `Fare`, `Embarked`, `Email`, `Annual Spend` blanks; text sentinels `N/A`, `NULL`, `-` |
| Duplicates | 14 exact duplicate rows + 12 near-duplicates re-keyed under a new `Passenger Id` |
| Inconsistent categories | 6 spellings of `Sex`; 9 of `Embarked`; `1`/`1st`/`First`/`Unknown` for `Pclass`; `Yes`/`No`/`0`/`1` for `Survived` |
| Mixed date formats | 5 formats in one column: `1911-09-01`, `19/09/1911`, `Sep 19, 1911`, `19-Sep-1911`, `09/19/1911` |
| Money as text | `$972.04`, `USD 972.04`, `972.04 USD`, `972.04` |
| Outliers | `Age` = 180 / 199 / 250 / 999; `Annual Spend` up to 9,999,999 |
| Wrong dtypes | `Passenger Id` as text; `Survived` as text; `SibSp` mixing `0`/`0.0`; `Fare` as text |
| Dirty text | leading/trailing whitespace in `Ticket`; inconsistent header capitalisation |

> `Annual Spend` is **synthesised** for this exercise so that a currency-string defect could
> be demonstrated on a realistic monetary column. `Fare` is the genuine Titanic money field.

---

## Requirements checklist

| # | Requirement | Where it is satisfied |
|---|---|---|
| 1 | Data quality report (nulls, duplicates, dtype issues, range anomalies) | §4.2–4.6 |
| 2 | Missing-data strategy per column, justified in markdown | §5.4 + decision log §12 |
| 3 | Duplicate detection & removal, with counts documented | §6 (7 exact + 12 near-duplicates removed) |
| 4 | Standardisation (categories + date formats → datetime) | §7.1–7.3 |
| 5 | Outlier detection via **IQR and Z-score**, with cap/remove/retain decisions | §8, §8.1 |
| 6 | Data-type correction | §9 |
| 7 | Before vs. after summary table | §10 |
| 8 | Cleaned dataset saved to CSV | §11 → `data/titanic_cleaned.csv` |

---

## Key decisions and their justification

The full 25-row decision log is in **§12 of the notebook**. The most consequential choices:

**Order of operations.** Text hygiene → coercion → sentinel handling → duplicates →
standardisation → outliers → final dtypes. Duplicates are removed *before* imputation so that
statistics driving the fill are not computed from rows about to be deleted.

**`Cabin` (79% missing) was NOT imputed.** Fabricating four of every five values is
indefensible. Instead the *presence* signal was preserved as a `HasCabin` flag plus a `Deck`
category, and the residual `NaN` is treated as a legitimate "unknown" level.

**Forward-fill was explicitly rejected.** The brief lists it as an option; this dataset is an
unordered cross-section, so "the previous row" is an unrelated passenger. Forward-filling
would inject one person's age into another's record — fabricating data with no basis.
Choosing *not* to use a technique is itself a documented decision.

**Impossible vs. merely unusual.** We repair what is **impossible** (`Age = -1` sentinel,
`Age = 999`) and cap what is **merely extreme** (`Annual Spend` up to 9,999,999, winsorised at
the 99th percentile). A `Fare` of `0.00` is *retained* because complimentary tickets really
existed — it is unusual, not impossible.

**Duplicates were detected on a business key, not the surrogate ID.** Keying only on
`Passenger Id` always "succeeds" because the ID is unique by construction — which is exactly
how duplicate customers survive in production warehouses. Using the natural key
(`Name`, `Sex`, `Age`, `Ticket`, `Fare`) caught the 12 re-keyed copies.

**Dates are resolved per row, not with a single global `dayfirst=` flag.** See below — this
was a genuine bug found and fixed during development.

---

## A real bug found and fixed during development

The first implementation of the date resolver chose one global `dayfirst=` value for the whole
column. Because **both** `dd/mm/yyyy` and `mm/dd/yyyy` rows are present, no single flag can be
correct — and the result was that **122 of 891 dates silently disappeared** while the cell
still reported success.

The fix resolves the convention **per row** on evidence:

* first component > 12 → must be a day → `dd/mm/yyyy`
* second component > 12 → must be a day → `mm/dd/yyyy`
* neither > 12 → genuinely ambiguous → fall back to the column-wide dominant convention
  inferred from the unambiguous rows

A hard `assert date_nulls == 0` now guards the step, so a silent parse failure can never pass
again. This is documented in §7.3 of the notebook, because the *detection* of a silent
data-integrity bug is as much a part of professional data cleaning as the fix.

---

## Verification performed

* All 49 code cells compile and execute with **0 error outputs**.
* Final assertions confirm: binary `Survived`; `Pclass ∈ {1,2,3}`; canonical `Sex` and
  `Embarked` levels; `Age ∈ [0, 120]`; non-negative `Fare`; positive `Annual Spend`; unique
  `Passenger Id`; `Join Date` is a true `datetime64`.
* CSV round-trip re-loaded and checked for shape, duplicates and dtype fidelity.
* A previously-impossible query (`survival rate by Pclass × Sex`) is shown to work on the
  cleaned data — the concrete business value of the pipeline.

## Known limitations (stated honestly)

* **`Age` and `Fare` were imputed**, not measured. Imputation is an informed estimate, not
  truth. For predictive modelling, add a missing-indicator column so the model can
  distinguish imputed from observed values.
* **Residual nulls remain in `Cabin` (703) and `Email` (57)** by deliberate choice — these
  are honest nulls, not oversights.
* **Outlier handling is a judgement call**, not a fact. The winsorisation cap on
  `Annual Spend` should be reviewed by a domain expert before the data is used for decisions.
* **`Join Date` and `Annual Spend` are synthetic** columns added for the exercise; only the
  original 12 Titanic fields are real.
