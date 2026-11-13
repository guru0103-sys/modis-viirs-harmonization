
import pandas as pd

df = pd.read_csv("data/matched/matched_pairs.csv")

df["viirs_time"] = pd.to_datetime(df["time_utc"])
df["modis_time"] = pd.to_datetime(df["modis_time_utc"])

df["time_gap_min"] = (
    (df["viirs_time"] - df["modis_time"])
    .dt.total_seconds()
    .abs() / 60
)

print("TIME GAP DISTRIBUTION")
print(df["time_gap_min"].describe())

print("\nTIME GAP BINS")
bins = [0, 5, 10, 15, 30, 45, 60, 90, 120]
labels = [
    "0-5", "5-10", "10-15", "15-30",
    "30-45", "45-60", "60-90", "90-120"
]

df["gap_bin"] = pd.cut(
    df["time_gap_min"],
    bins=bins,
    labels=labels,
    include_lowest=True
)

print(df["gap_bin"].value_counts(sort=False))

print("\nSIGNED TIME DIFFERENCE")
signed_gap = (
    (df["viirs_time"] - df["modis_time"])
    .dt.total_seconds() / 60
)

print(signed_gap.describe())

print("\nVIIRS EARLIER THAN MODIS:", (signed_gap < 0).sum())
print("VIIRS LATER THAN MODIS:", (signed_gap > 0).sum())
