"""STEP 6 (Thursday morning): clean both files into the same shape.

Run:  python src/clean.py
Output: data/clean/modis_clean.csv, data/clean/viirs_clean.csv
"""
import pandas as pd

from config import RAW, CLEAN, REGION, MODIS_SOURCE, VIIRS_SOURCE, MODIS_SATELLITE

KEEP = ["sensor", "satellite", "time_utc", "latitude", "longitude", "scan", "track",
        "frp", "daynight", "conf_num", "conf_class"]


def load(path, sensor):
    df = pd.read_csv(path)
    df["acq_time"] = df["acq_time"].astype(int).astype(str).str.zfill(4)
    df["time_utc"] = pd.to_datetime(df["acq_date"].astype(str) + " " + df["acq_time"],
                                    format="%Y-%m-%d %H%M")
    df["sensor"] = sensor
    df["satellite"] = df["satellite"].astype(str)
    if sensor == "MODIS":
        df["conf_num"] = pd.to_numeric(df["confidence"], errors="coerce")
        df["conf_class"] = pd.NA
    else:
        df["conf_class"] = df["confidence"].astype(str).str.strip().str.lower().str[0]
        df["conf_num"] = pd.NA
    before = len(df)
    df = df.drop_duplicates(subset=["latitude", "longitude", "time_utc", "satellite"])
    df = df.dropna(subset=["latitude", "longitude", "frp", "scan", "track"])
    print(f"{sensor}: {before:,} rows -> {len(df):,} after cleaning")
    return df[KEEP].reset_index(drop=True)


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    modis = load(RAW / f"{MODIS_SOURCE}_{REGION}.csv", "MODIS")
    viirs = load(RAW / f"{VIIRS_SOURCE}_{REGION}.csv", "VIIRS")
    print("MODIS satellites present:", modis["satellite"].value_counts().to_dict())
    modis = modis[modis["satellite"].str.lower() == MODIS_SATELLITE.lower()].reset_index(drop=True)
    print(f"MODIS kept for matching ({MODIS_SATELLITE}): {len(modis):,}")
    modis.to_csv(CLEAN / "modis_clean.csv", index=False)
    viirs.to_csv(CLEAN / "viirs_clean.csv", index=False)
    print("Saved to data/clean/")


if __name__ == "__main__":
    main()
