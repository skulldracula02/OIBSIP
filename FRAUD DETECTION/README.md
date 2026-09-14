# Fraud Detection on Heavily Imbalanced Financial Transactions

An end-to-end machine-learning pipeline that detects fraudulent credit-card
transactions, treating **class imbalance** as the central engineering challenge.

The project is delivered as a single, fully-executed Jupyter notebook:
**[`01_fraud_detection.ipynb`](01_fraud_detection.ipynb)** — all 42 code cells
run with saved outputs, so you can read the results without executing anything.

---

## The problem in one line

Fraud is **0.172%** of transactions (492 out of 284,807) — a **580:1** imbalance.
A model that predicts "legitimate" for every transaction scores **99.83%
accuracy** while catching zero fraud. Every design decision below follows from
that fact.

---

## Dataset

The benchmark **Credit Card Fraud Detection** dataset (ULB / Worldline):
284,807 transactions, 492 fraudulent, features `V1..V28` (PCA-transformed and
anonymised) plus `Time` and `Amount`.

**To use the real data:** download `creditcard.csv` from
[Kaggle — Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
and drop it into `data/`. The notebook picks it up automatically.

**Without the CSV:** the pipeline falls back to `src/prepare_data.py`, which
generates a synthetic dataset with the **same schema and same 0.172% fraud rate**,
so the notebook runs end-to-end out of the box. The synthetic data is deliberately
built to be *hard* — most frauds overlap the legitimate distribution and ~35% sit
in a heavy tail that is genuinely near-undetectable — so the metrics land in a
realistic band (AUC-PR ≈ 0.78–0.90) rather than the degenerate 1.0 you get from
trivially separable toy data. The real CSV reproduces the benchmark exactly.

---

## Results

Test set (56,962 transactions / 98 frauds), decision threshold = 0.5:

| Strategy | Accuracy | Precision | Recall | F1 | AUC-ROC | AUC-PR |
|---|---|---|
| LR (none) | 0.9995 | 0.986 | 0.714 | 0.828 | 0.945 | 0.831 |
| LR (`class_weight='balanced'`) | 0.9631 | 0.040 | **0.898** | 0.077 | 0.945 | 0.792 |
| LR (SMOTE) | 0.9778 | 0.065 | 0.888 | 0.121 | 0.945 | 0.815 |
| LR (undersampled) | 0.9623 | 0.040 | 0.898 | 0.076 | 0.944 | 0.783 |
| **Random Forest (balanced)** | 0.9947 | 0.235 | 0.929 | **0.375** | **0.996** | **0.902** |
| XGBoost (`scale_pos_weight`) | 0.9688 | 0.049 | **0.939** | 0.094 | 0.993 | 0.872 |

**Read the first column against the fourth.** Accuracy spans 0.963–0.9995 — an
essentially useless range — while Recall and AUC-PR cleanly separate the models.
That is the whole argument for abandoning accuracy on this problem.

---

## Feature checklist — where each item is answered

| # | Requirement | Location in `01_fraud_detection.ipynb` |
|---|---|---|
| 1 | Load data; analyse class imbalance (% fraudulent) | §1 — **0.172%**, 580:1 |
| 2 | EDA: amount distribution (fraud vs. non-fraud), time-of-day | §2 — fraud skews to *low* amounts; fraud *rate* peaks overnight |
| 3 | Why accuracy misleads on imbalanced data (markdown) | §3 — the do-nothing baseline scores 99.83% |
| 4 | Class imbalance handling (SMOTE / undersampling / `class_weight`) | §6 — all three compared head-to-head |
| 5 | Stratified train/test split | §4 — `stratify=y` pins the fraud ratio in both splits |
| 6 | ≥2 models (Logistic Regression + ensemble) | §7 — LR, Random Forest, and XGBoost |
| 7 | Evaluate with Precision, Recall, F1, AUC-ROC | §8 — plus AUC-PR and confusion matrices |
| 8 | Which metric matters most and why (Recall vs Precision) | §9 — Recall first; threshold as the trade-off dial (F2) |
| 9 | Feature importance / coefficient analysis | §10 — LogReg coefficients + RF importances, with rank correlation |
| 10 | Scalability to 1M transactions/hour | §12 — measured latency, throughput projection, architecture |

**§11** adds 3-fold stratified cross-validation as a stability check, and **§13**
concludes.

---

## Key findings

**1. Accuracy is worse than useless here — it is misleading.** The do-nothing
classifier scores 99.83%. Accuracy's denominator (>284k legitimate transactions)
so completely dominates the minority class that the metric has almost no dynamic
range, and optimising it actively pushes a model toward predicting the majority
class.

**2. `class_weight='balanced'` beat SMOTE as an engineering choice.** Both lift
recall dramatically, but SMOTE synthesises ~227,000 fake frauds from only 394 real
ones — so the resampled training set becomes ~99.8% synthetic points sitting on
the convex hull of those 394 originals, and the model partly learns SMOTE's
interpolation geometry rather than real fraud behaviour. Class weighting changes
the *loss* instead of the *dataset*: same benefit, no synthetic rows, no memory
cost, and it is the only one of the three that scales cleanly.

**3. Recall is the primary business metric.** A missed fraud is a direct,
unbounded financial loss; a false positive is bounded analyst time. Recall answers
"what fraction of the money we lost did this stop?" — so it is held at a
business-mandated floor, and Precision is chosen to be as high as possible subject
to that floor. §9 computes this frontier and picks the F2-optimal threshold (F2
weights recall twice as heavily as precision).

**4. Accuracy at the 0.5 default hides a bad model.** `LR (none)` scores 99.95%
accuracy while missing 28 of 98 frauds. The threshold — not the model — is where
the recall/precision trade-off actually gets decided, and it should be set from a
cost model, never left at the library default.

**5. Both model families agree on *what* matters.** Logistic-regression
coefficients and Random Forest importances converge on the same PCA components
(`V14`, `V17`, `V12`, `V10`, `V4`), which is strong evidence the signal is real
rather than an artefact of one algorithm. Neither `Amount` nor `hour_of_day` ranks
in the top 10 — they are weak individually, exactly as the EDA predicted.

**6. Compute is not the scalability bottleneck.** Measured inference is
microseconds per transaction, so 1M/hour (278 tps) needs only a few cores. The
real challenges are **stateful streaming features** (which this dataset cannot
express — there is no card ID), **adversarial drift** requiring windowed
retraining and delayed-ground-truth monitoring, and **end-to-end latency**
dominated by feature retrieval rather than the model itself.

---

## Project structure

```
FRAUD DETECTION/
├── 01_fraud_detection.ipynb    # The deliverable — 69 cells, fully executed
├── README.md                   # This file
├── requirements.txt
├── data/
│   ├── creditcard.csv          # (optional) drop the real Kaggle file here
│   └── creditcard_synthetic.csv# generated fallback, same schema + fraud rate
├── outputs/                    # Generated figures and metric tables
│   ├── 01_class_imbalance.png
│   ├── 02_amount_distribution.png
│   ├── 03_time_of_day.png
│   ├── 04_resampling.png
│   ├── 05_metrics_comparison.png
│   ├── 06_roc_pr_curves.png
│   ├── 07_confusion_matrices.png
│   ├── 08_threshold_tradeoff.png
│   ├── 09_feature_importance.png
│   ├── metrics_summary.csv
│   ├── cv_results.csv
│   └── logreg_coefficients.csv
└── src/
    ├── prepare_data.py         # Data loading + synthetic fallback generator
    └── build_notebook.py       # Regenerates the notebook from source
```

---

## Running it

```bash
pip install -r requirements.txt

# Open and run all cells:
jupyter notebook 01_fraud_detection.ipynb
```

The notebook is already executed with saved outputs. To re-run it from scratch
(takes ~90s):

```bash
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=fraud-detection \
  01_fraud_detection.ipynb
```

> If the kernel is missing, register it first:
> `python -m ipykernel install --user --name fraud-detection --display-name "Python 3 (fraud-detection)"`

To regenerate the notebook after editing `src/build_notebook.py`:

```bash
python src/build_notebook.py
```

---

## Honest limitations

- **Synthetic fallback data.** Without `data/creditcard.csv` the notebook uses
  generated data. It matches the real schema, fraud rate and qualitative patterns
  (fraud skews to low amounts and to overnight hours, most frauds overlap the
  legitimate distribution), but the absolute metric values are *not* the Kaggle
  benchmark's. Drop in the real CSV for published numbers.
- **No card identifier.** The highest-value production features — per-card
  velocity (transactions in the last 5 min / 1 h / 24 h) and deviation from the
  cardholder's usual behaviour — require a card ID that the PCA anonymisation
  removed. They are noted as a production improvement, not faked.
- **Single train/test split.** §11's cross-validation is a stability check, not a
  substitute for time-based validation. Fraud detection should ultimately validate
  on a *later* time window than it trains on, since the real deployment is
  predicting the future.
- **The cost model is illustrative.** The dollar figures in §8.2 use a simple
  per-fraud loss and per-alert review cost to make the point that FN and FP cost
  *different* amounts. Real thresholds need real economics.
