# 🍷 Wine Quality Prediction

Train and compare three classification models — **Random Forest**, **Stochastic Gradient
Descent (SGD)** and a **Support Vector Classifier (SVC)** — to predict the quality score of
wine (scale 3–9) from its physicochemical properties (acidity, density, alcohol, sulphates…).

This project is an end-to-end notebook covering data loading, EDA, class-imbalance analysis,
target engineering, stratified splitting, model training, evaluation and a deployment
recommendation.

---

## 📊 Results at a glance

Primary task: **3-class classification** — `low (≤5)` / `medium (6–7)` / `high (≥8)`,
on a combined red + white dataset of **6,497 wines** (80/20 stratified split → 5,197 train / 1,300 test).

| Model | Accuracy | Macro F1 | Weighted F1 |
|-------|---------:|---------:|------------:|
| **Random Forest** | **0.7908** | **0.7181** | **0.7906** |
| SGD | 0.6485 | 0.4775 | 0.6732 |
| SVC | 0.6323 | 0.5310 | 0.6586 |

*(Majority-class baseline ≈ 44% — every model beats it comfortably.)*

Bonus **binary** task (`good = quality ≥ 7`):

| Model | Accuracy | Macro F1 |
|-------|---------:|---------:|
| **Random Forest** | **0.8669** | **0.7975** |
| SVC | 0.7408 | 0.6874 |
| SGD | 0.7077 | 0.6499 |

### 🏆 Deployment recommendation: **Random Forest**

It gives the best accuracy and macro-F1, needs **no feature scaling** (fewer production moving
parts), handles the dataset's multicollinearity, compensates for class imbalance via
`class_weight="balanced"`, and — most importantly — provides **feature importances** that
explain *why* a wine is rated highly.

Use **SGD** instead only if you must serve predictions at very large scale on minimal hardware.
Use **SVC** for a strong margin model on small/medium data if training cost is affordable.

---

## 📁 Project structure

```
WQP/
├── wine_quality_prediction.ipynb   # main notebook (executed, with outputs + figures)
├── data/
│   ├── winequality-red.csv         # 1,599 red wines  (UCI)
│   └── winequality-white.csv       # 4,898 white wines (UCI)
├── figures/                        # 9 exported PNG charts
├── scripts/
│   ├── download_data.py            # fetches the dataset from UCI
│   ├── build_notebook.py           # regenerates the notebook source
│   └── extract_outputs.py          # pulls metrics out of the executed notebook
├── requirements.txt
└── README.md
```

---

## 📦 Dataset

The **Wine Quality** dataset from the UCI Machine Learning Repository
([archive.ics.uci.edu/dataset/186/wine+quality](https://archive.ics.uci.edu/dataset/186/wine+quality)),
originally published by Cortez et al. (2009). It contains two variants:

| File | Rows | Description |
|------|-----:|-------------|
| `winequality-red.csv` | 1,599 | red *Vinho Verde* wines |
| `winequality-white.csv` | 4,898 | white *Vinho Verde* wines |

**11 input features:** fixed acidity, volatile acidity, citric acid, residual sugar, chlorides,
free sulfur dioxide, total sulfur dioxide, density, pH, sulphates, alcohol.
**Target:** `quality` (integer score). No missing values.

The dataset is fetched automatically — see `scripts/download_data.py`, which pulls the official
UCI zip bundle (`https://archive.ics.uci.edu/static/public/186/wine+quality.zip`).
It is also on Kaggle if you prefer:
[kaggle.com/datasets/uciml/red-wine-quality-cortez-et-al-2009](https://www.kaggle.com/datasets/uciml/red-wine-quality-cortez-et-al-2009).

---

## 🚀 Setup & run

### 1. Install dependencies
```powershell
pip install -r requirements.txt
```

### 2. Download the data
```powershell
python scripts/download_data.py
```

### 3. Run the notebook
```powershell
jupyter notebook wine_quality_prediction.ipynb
```
Or execute it headless (produces the `figures/` PNGs):
```powershell
jupyter nbconvert --to notebook --execute --inplace wine_quality_prediction.ipynb
```

> This project was built and verified with **Python 3.12**, pandas 3.0, numpy 2.5,
> scikit-learn 1.9, seaborn 0.13, matplotlib 3.11.

---

## 🔍 What the notebook covers (feature checklist)

- [x] **Load & inspect** dataset structure, class distribution of quality scores
- [x] **EDA** — distribution plots for all chemical features + correlation heatmap
- [x] **Class-imbalance discussion** — which scores are underrepresented and how it affects modelling
- [x] **Feature engineering** — binary (good/bad) and 3-class (low/medium/high) targets, with justification
- [x] **Stratified train/test split** to preserve class ratios
- [x] **Three classifiers** — Random Forest, SGD, SVC (scikit-learn Pipelines, no data leakage)
- [x] **Evaluation** — accuracy, classification report, confusion matrix for each
- [x] **Random-Forest feature importance** chart
- [x] **Comparison table** of all three models
- [x] **Conclusion** — most suitable model for deployment, and why

---

## 💡 Key findings

1. **The raw target is severely imbalanced.** Scores 5 and 6 make up ~77% of the data;
   scores 3, 4, 9 are near-empty (score 9 has only 5 samples). Accuracy alone is therefore
   misleading — we report **macro F1** (equal weight per class) as the primary metric.

2. **Grouping the target is essential.** We bin into `low / medium / high`, which removes the
   5-sample-class problem and yields learnable classes (37% / 60% / 3%) while preserving ordinality.

3. **Alcohol is the dominant predictor** (+0.44 correlation, top Random-Forest importance),
   followed by **volatile acidity** and **density** — matching wine-chemistry domain knowledge.

4. **Errors are between adjacent tiers.** Confusion matrices show mistakes concentrate on
   low↔medium and medium↔high boundaries, rarely low↔high — exactly the graceful behaviour
   you want for a fuzzy ordinal target.

5. **Random Forest wins on every metric** and is the recommended deployment model.

### Possible next steps
- Hyperparameter tuning with `GridSearchCV` / `RandomizedSearchCV`
- Ordinal-aware models (e.g. ordinal logistic regression) since quality is ordered
- Resampling (SMOTE) or cost-sensitive thresholds for the rare "high" class
- Try gradient boosting (XGBoost / LightGBM), which often edges out plain Random Forest
