"""Independent verification that the cleaned CSV really is analysis-ready."""
import pandas as pd

clean = pd.read_csv("data/titanic_cleaned.csv")
messy = pd.read_csv("data/messy_dataset.csv", dtype=str, keep_default_na=False)

print("=" * 68)
print("CLEANED DATASET VERIFICATION")
print("=" * 68)
print(f"Shape            : {clean.shape[0]:,} rows x {clean.shape[1]} columns")
print(f"Messy shape      : {messy.shape[0]:,} rows x {messy.shape[1]} columns")
print(f"Duplicate rows   : {int(clean.duplicated().sum())}")
print(f"Duplicate IDs    : {int(clean['Passenger Id'].duplicated().sum())}")
print()

print("Null counts per column:")
print(clean.isna().sum().to_string())
print()

print("Dtypes:")
print(clean.dtypes.to_string())
print()

print("Value integrity spot-checks:")
print(f"  Sex values          : {sorted(clean['Sex'].dropna().unique())}")
print(f"  Pclass values       : {sorted(clean['Pclass'].unique())}")
print(f"  Embarked values     : {sorted(clean['Embarked'].dropna().unique())}")
print(f"  Survived values     : {sorted(clean['Survived'].unique())}")
print(f"  Deck values         : {sorted(clean['Deck'].dropna().unique())}")
print(f"  Age range           : {clean['Age'].min():.1f} .. {clean['Age'].max():.1f}")
print(f"  Fare range          : {clean['Fare'].min():,.2f} .. {clean['Fare'].max():,.2f}")
print(f"  Annual Spend range  : {clean['Annual Spend'].min():,.2f} .. {clean['Annual Spend'].max():,.2f}")
print(f"  Join Date range     : {clean['Join Date'].min()} .. {clean['Join Date'].max()}")
print()

print("Analysis that was impossible before cleaning:")
agg = (clean.groupby(["Pclass", "Sex"], observed=True)
       .agg(n=("Survived", "size"), survival_rate=("Survived", "mean"))
       .round(3))
print(agg.to_string())
print("=" * 68)
