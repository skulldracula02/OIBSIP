"""
Build a deliberately messy, analysis-hostile dataset for the data-cleaning exercise.

Base data : Kaggle "Titanic - Machine Learning from Disaster" (train.csv, 891 rows x 12 cols),
            retrieved from the public mirror https://github.com/datasciencedojo/datasets.
Injected  : fake email / join_date / annual_spend columns + realistic data-quality defects
            (nulls, duplicates, inconsistent text casing, mixed date formats, currency
            strings, sentinel values, outliers, whitespace, wrong dtypes).

Run:  python src/build_messy_dataset.py
Out :  data/messy_dataset.csv   (the "before" file - the raw material for cleaning)
       data/titanic_clean_reference.csv (the base file, kept for provenance)
"""

from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_STATE = 42
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def main() -> None:
    rng = np.random.default_rng(RANDOM_STATE)

    raw = pd.read_csv(DATA / "titanic_raw.csv")
    # Keep a pristine copy so the pipeline is reproducible from a known-good base.
    raw.to_csv(DATA / "titanic_clean_reference.csv", index=False)

    df = raw.copy()

    # ------------------------------------------------------------------ #
    # 1. Add CRM-style columns that give us real dtype work to do
    # ------------------------------------------------------------------ #
    first = df["Name"].str.split(",").str[0].str.strip().str.lower()
    first = first.str.replace(r"[^a-z]", "", regex=True)
    df["Email"] = [
        f"{name}@{dom}" if pd.notna(name) and name else None
        for name, dom in zip(
            first,
            rng.choice(
                ["gmail.com", "yahoo.com", "outlook.com", "mail.com"], size=len(df)
            ),
        )
    ]

    # Genuine booking dates spread over 1910-1912, rendered in several formats later.
    join_dates = pd.to_datetime("1910-01-01") + pd.to_timedelta(
        rng.integers(0, 1095, size=len(df)), unit="D"
    )
    df["JoinDate"] = join_dates

    # Monetary column: fare in USD-ish terms, with a plausible long right tail.
    df["AnnualSpend"] = np.round(df["Fare"] * rng.uniform(8, 40, size=len(df)), 2)

    # ------------------------------------------------------------------ #
    # 2. Inconsistent categorical formatting (Sex)
    # ------------------------------------------------------------------ #
    sex_variants = {
        "male": ["male", "Male", "MALE", "M", "m", " male "],
        "female": ["female", "Female", "FEMALE", "F", "f", "female ", "FEMALE."],
    }
    new_sex = []
    for value in df["Sex"]:
        new_sex.append(rng.choice(sex_variants[value]))
    df["Sex"] = new_sex

    # Embarked: inconsistent casing + a stray blank-looking token
    embarked_map = {"S": ["S", "s", "Southampton"], "C": ["C", "c", "Cherbourg "], "Q": ["Q", "q", "Queenstown"]}
    new_embarked = []
    for value in df["Embarked"]:
        if pd.isna(value):
            new_embarked.append(rng.choice(["", " ", "Unknown", np.nan]))
        else:
            new_embarked.append(rng.choice(embarked_map[value]))
    df["Embarked"] = new_embarked

    # Pclass as text, mixed with a bogus label
    pclass_map = {1: ["First", "1st", "1"], 2: ["Second", "2nd", "2"], 3: ["Third", "3rd", "3"]}
    new_pclass = []
    for value in df["Pclass"]:
        token = rng.choice(pclass_map[value] + (["Unknown"] if rng.random() < 0.01 else []))
        new_pclass.append(token)
    df["Pclass"] = new_pclass

    # Whitespace / trailing junk inside free text
    df["Ticket"] = [
        f"  {t} " if rng.random() < 0.35 else t for t in df["Ticket"].astype(str)
    ]

    # ------------------------------------------------------------------ #
    # 3. Mixed date formats inside one column
    # ------------------------------------------------------------------ #
    def messy_date(ts: pd.Timestamp) -> str:
        style = rng.integers(0, 5)
        if style == 0:
            return ts.strftime("%Y-%m-%d")
        if style == 1:
            return ts.strftime("%d/%m/%Y")
        if style == 2:
            return ts.strftime("%b %d, %Y")
        if style == 3:
            return ts.strftime("%d-%b-%Y")
        return ts.strftime("%m/%d/%Y")

    df["JoinDate"] = [messy_date(ts) for ts in join_dates]

    # ------------------------------------------------------------------ #
    # 4. Currency as text, with symbols / commas / parentheses-negatives
    # ------------------------------------------------------------------ #
    def messy_money(value: float) -> str:
        style = rng.integers(0, 4)
        if style == 0:
            return f"${value:,.2f}"
        if style == 1:
            return f"USD {value:,.2f}"
        if style == 2:
            return f"{value:,.2f} USD"
        return f"{value:,.2f}"

    df["AnnualSpend"] = [messy_money(v) for v in df["AnnualSpend"]]

    # ------------------------------------------------------------------ #
    # 5. Missing-data injection
    # ------------------------------------------------------------------ #
    df["Cabin"] = df["Cabin"].where(rng.random(len(df)) > 0.08, np.nan)          # already ~77% null
    df["Age"] = df["Age"].mask(rng.random(len(df)) < 0.06, np.nan)               # push nulls up
    df["Fare"] = df["Fare"].mask(rng.random(len(df)) < 0.03, np.nan)
    df["Embarked"] = df["Embarked"].mask(rng.random(len(df)) < 0.02, np.nan)
    df["Email"] = df["Email"].mask(rng.random(len(df)) < 0.05, np.nan)
    df["AnnualSpend"] = df["AnnualSpend"].mask(rng.random(len(df)) < 0.04, np.nan)

    # Sentinel-style "fake" missing values that look like real data
    age_arr = np.array(df["Age"].to_numpy(dtype="float64"), copy=True)
    sentinel_idx = rng.choice(len(df), size=18, replace=False)
    age_arr[sentinel_idx] = -1.0
    df["Age"] = age_arr

    spend_arr = np.array(df["AnnualSpend"].astype("object").to_numpy(dtype="object"), copy=True)
    for i in rng.choice(len(df), size=12, replace=False):
        spend_arr[i] = rng.choice(["", "N/A", "n/a", "-", "NULL"])
    df["AnnualSpend"] = spend_arr

    # ------------------------------------------------------------------ #
    # 6. Outliers: extreme Age and AnnualSpend values (data-entry errors)
    # ------------------------------------------------------------------ #
    age_outliers = {int(i): float(rng.choice([180, 199, 250, 999]))
                    for i in rng.choice(len(df), size=6, replace=False)}
    for i, v in age_outliers.items():
        df.loc[i, "Age"] = v
    spend_outliers = {int(i): float(rng.choice([1_500_000, 2_750_000, 9_999_999]))
                      for i in rng.choice(len(df), size=5, replace=False)}
    spend_arr = np.array(df["AnnualSpend"].astype("object").to_numpy(dtype="object"), copy=True)
    for i, v in spend_outliers.items():
        spend_arr[i] = v
    df["AnnualSpend"] = spend_arr
    # Record the injected outliers so the notebook can prove it caught them.
    pd.DataFrame(
        [{"column": "Age", "row_index": i, "value": v} for i, v in age_outliers.items()]
        + [{"column": "AnnualSpend", "row_index": i, "value": v} for i, v in spend_outliers.items()]
    ).to_csv(DATA / "injected_outliers.csv", index=False)
    # NB: later steps shuffle the frame, so row_index above refers to PRE-shuffle
    # positions. The notebook identifies outliers statistically instead.

    # ------------------------------------------------------------------ #
    # 7. Duplicate rows (exact duplicates + near-duplicates)
    # ------------------------------------------------------------------ #
    exact_dupes = df.sample(14, random_state=1)
    df = pd.concat([df, exact_dupes], ignore_index=True)

    near = df.iloc[40:52].copy()
    near["PassengerId"] = near["PassengerId"] + 100000          # same person, new key
    near["Name"] = near["Name"].str.replace(r"\s+", " ", regex=True).str.strip()
    df = pd.concat([df, near], ignore_index=True)

    # ------------------------------------------------------------------ #
    # 8. Shuffle, reorder columns, corrupt the header, break dtypes
    # ------------------------------------------------------------------ #
    df = df.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)

    df = df[
        ["PassengerId", "Name", "Sex", "Age", "Pclass", "Survived", "SibSp", "Parch",
         "Ticket", "Fare", "Cabin", "Embarked", "Email", "JoinDate", "AnnualSpend"]
    ]
    # Human-style export header: spaces, inconsistent capitalisation.
    df.columns = [
        "Passenger Id", "Name", "Sex", "Age", "Pclass", "Survived", "SibSp", "Parch",
        "Ticket", "Fare", "Cabin", "Embarked", "Email", "Join Date", "Annual Spend",
    ]

    # Passenger Id -> string with a prefix (so it must be handled, not averaged)
    df["Passenger Id"] = ["P" + str(int(v)).zfill(5) for v in df["Passenger Id"]]

    # Survived / SibSp / Parch / Fare get string-ified the way real exports do
    df["Survived"] = [str(v) if rng.random() < 0.9 else ("Yes" if v == 1 else "No") for v in df["Survived"]]
    df["SibSp"] = [str(v) if rng.random() < 0.85 else float(v) for v in df["SibSp"]]
    df["Fare"] = [
        None if pd.isna(v) else (f"{v:.4f}" if rng.random() < 0.8 else v) for v in df["Fare"]
    ]

    df.to_csv(DATA / "messy_dataset.csv", index=False)

    print(f"Wrote {DATA / 'messy_dataset.csv'}  shape={df.shape}")
    print(f"Nulls total: {int(df.isna().sum().sum())}")
    print(f"Exact duplicate rows: {int(df.duplicated().sum())}")


if __name__ == "__main__":
    main()
