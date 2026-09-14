import json

path = "car_price_prediction.ipynb"
with open(path, encoding="utf-8") as f:
    nb = json.load(f)

nb["cells"][0]["source"] = [
    "# Car Price Prediction with Machine Learning\n",
    "\n",
    "This notebook predicts used-car selling prices from age, mileage, fuel type, transmission, brand, and vehicle specifications.\n",
    "\n",
    "**Dataset:** [Vehicle dataset from CarDekho (Kaggle)](https://www.kaggle.com/datasets/nehalbirla/vehicle-dataset-from-cardekho), using \`Car details v3.csv\` (8,128 listings). The downloaded source is stored in \`data/cardekho_source/\`. Prices are in INR.\n",
]
nb["cells"][2]["source"] = [
    "DATA_PATH = 'data/cardekho_source/Car details v3.csv'\n",
    "df = pd.read_csv(DATA_PATH)\n",
    "print('Raw dataset shape:', df.shape)\n",
    "df.head()"
]
nb["cells"][3]["source"] = '''# Data cleaning: inspect, remove duplicates, standardize categories, and parse units
print("Duplicates before removal:", df.duplicated().sum())
display(df.isna().sum().to_frame("missing before cleaning"))
df = df.drop_duplicates().copy()

categorical_columns = ['fuel', 'seller_type', 'transmission', 'owner']
for column in categorical_columns:
    df[column] = df[column].astype('string').str.strip().str.title()
df['fuel'] = df['fuel'].replace({'Cng': 'CNG', 'Lpg': 'LPG'})

def first_number(value):
    match = re.search(r'\\d+(?:\\.\\d+)?', str(value))
    return float(match.group()) if match else np.nan

for column in ['mileage', 'engine', 'max_power']:
    df[column] = df[column].map(first_number)
for column in ['year', 'selling_price', 'km_driven', 'seats']:
    df[column] = pd.to_numeric(df[column], errors='coerce')

required = ['name', 'year', 'selling_price', 'km_driven', 'fuel', 'transmission']
df = df.dropna(subset=required)
df = df[df['selling_price'] > 0].reset_index(drop=True)
print('Cleaned shape:', df.shape)
display(df.isna().sum().to_frame("missing after cleaning"))
df.head()
'''.splitlines(True)
nb["cells"][4]["source"] = '''# Feature engineering: calculate car age and extract brand from name
CURRENT_YEAR = 2026
df['car_age'] = CURRENT_YEAR - df['year']
df = df[df['car_age'].between(0, 50)].copy()
df['brand'] = df['name'].str.split().str[0].str.strip().str.title()

print('Reference year:', CURRENT_YEAR)
display(df[['name', 'year', 'car_age', 'brand']].head())
display(df['brand'].value_counts().head(15).to_frame('listings'))
'''.splitlines(True)
nb["cells"][7]["source"] = '''# Select features, split data, and prepare one-hot encoding
target = 'selling_price'
feature_columns = ['km_driven', 'fuel', 'seller_type', 'transmission', 'owner',
                   'mileage', 'engine', 'max_power', 'seats', 'brand', 'car_age']
X, y = df[feature_columns], df[target]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print('Training rows:', len(X_train), '| Test rows:', len(X_test))

numeric_features = ['km_driven', 'mileage', 'engine', 'max_power', 'seats', 'car_age']
categorical_features = ['fuel', 'seller_type', 'transmission', 'owner', 'brand']
preprocess = ColumnTransformer([
    ('num', Pipeline([('imputer', SimpleImputer(strategy='median')),
                      ('scale', StandardScaler())]), numeric_features),
    ('cat', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')),
                      ('onehot', OneHotEncoder(handle_unknown='ignore'))]), categorical_features)
])
'''.splitlines(True)
nb["cells"][10]["source"] = '''# Feature importance chart for the best-performing model
# Permutation importance works for any selected model and keeps original feature labels.
from sklearn.inspection import permutation_importance

best_pipe = Pipeline([('preprocess', preprocess), ('model', models[best_model_name])])
best_pipe.fit(X_train, y_train)
permutation = permutation_importance(
    best_pipe, X_test, y_test, n_repeats=8, random_state=42, scoring='r2', n_jobs=-1
)
importance_df = pd.DataFrame({
    'Feature': feature_columns,
    'Importance': permutation.importances_mean
}).sort_values('Importance', ascending=False)

plt.figure(figsize=(11, 6))
sns.barplot(data=importance_df, x='Importance', y='Feature', hue='Feature',
            legend=False, palette='viridis')
plt.title(f'Permutation Feature Importance - {best_model_name}')
plt.xlabel('Mean decrease in test R2 after shuffling')
plt.ylabel('')
plt.tight_layout()
plt.show()
importance_df
'''.splitlines(True)

# Present the metrics in ranked order and avoid an encoding-dependent R-squared glyph.
model_source = ''.join(nb["cells"][8]["source"])
model_source = model_source.replace("R�", "R2")
model_source = model_source.replace("results_df = pd.DataFrame(results)\nresults_df", "results_df = pd.DataFrame(results).sort_values('R2', ascending=False).reset_index(drop=True)\nresults_df")
nb["cells"][8]["source"] = model_source.splitlines(True)
nb["cells"][9]["source"] = '''# Select the best model using the highest held-out test R2 score
best_model_name = results_df.iloc[0]['Model']
print('Best model:', best_model_name)
'''.splitlines(True)

# Required support imports used by the revised cleaning and preprocessing cells.
imports = ''.join(nb["cells"][1]["source"])
imports = imports.replace("import numpy as np\n", "import numpy as np\nimport re\n")
imports = imports.replace("from sklearn.preprocessing import OneHotEncoder, StandardScaler\n",
                          "from sklearn.preprocessing import OneHotEncoder, StandardScaler\nfrom sklearn.impute import SimpleImputer\n")
nb["cells"][1]["source"] = imports.splitlines(True)

with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print("Notebook updated for the downloaded CarDekho dataset.")

# Execute every cell so the delivered notebook includes reproducible results and charts.
from nbclient import NotebookClient
from nbformat import read, write

with open(path, encoding="utf-8") as f:
    executable_notebook = read(f, as_version=4)
NotebookClient(executable_notebook, timeout=180, kernel_name="python3").execute()
with open(path, "w", encoding="utf-8") as f:
    write(executable_notebook, f)
print("Notebook executed successfully.")
