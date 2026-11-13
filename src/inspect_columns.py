"""STEP 4b (Wednesday): look at what you downloaded and write down the mismatches.

Run:  python src/inspect_columns.py
"""
import pandas as pd

from config import RAW, REGION, MODIS_SOURCE, VIIRS_SOURCE

files = {
    "MODIS": RAW / f"{MODIS_SOURCE}_{REGION}.csv",
    "VIIRS": RAW / f"{VIIRS_SOURCE}_{REGION}.csv",
}
dfs = {}
for name, path in files.items():
    df = pd.read_csv(path)
    dfs[name] = df
    print("=" * 70)
    print(name, path.name, f"{len(df):,} rows")
    print("columns:", list(df.columns))
    print(df.head(3).to_string())
    for col in ("satellite", "instrument", "daynight", "confidence"):
        if col in df:
            print(f"\n{col} values:")
            print(df[col].value_counts().head(10).to_string())
    for col in ("frp", "scan", "track"):
        if col in df:
            print(f"\n{col}:", df[col].describe()[["min", "50%", "max"]].round(2).to_dict())

print("=" * 70)
print("Only in MODIS :", sorted(set(dfs["MODIS"].columns) - set(dfs["VIIRS"].columns)))
print("Only in VIIRS :", sorted(set(dfs["VIIRS"].columns) - set(dfs["MODIS"].columns)))
print("Shared        :", sorted(set(dfs["MODIS"].columns) & set(dfs["VIIRS"].columns)))
print("\nCopy this output into docs/column_mismatches.md")
