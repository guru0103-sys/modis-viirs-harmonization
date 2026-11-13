"""STEP 4 (Wednesday): download raw MODIS and VIIRS hot spots from NASA FIRMS.

Run:  python src/download_firms.py
Needs: FIRMS_MAP_KEY environment variable.
Output: data/raw/MODIS_SP_<region>.csv and data/raw/VIIRS_SNPP_SP_<region>.csv
"""
import io
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests

from config import MAP_KEY, REGIONS, REGION, START, END, MODIS_SOURCE, VIIRS_SOURCE, RAW

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def fetch_chunk(source, bbox, start, days):
    area = ",".join(str(x) for x in bbox)
    url = f"{BASE}/{MAP_KEY}/{source}/{area}/{days}/{start:%Y-%m-%d}"
    for attempt in range(1, 4):
        try:
            r = requests.get(url, timeout=120)
        except requests.RequestException as e:
            print(f"  network error ({e}), retry {attempt}/3")
            time.sleep(5 * attempt)
            continue
        text = r.text.strip()
        if r.status_code == 200 and text.startswith("latitude"):
            return pd.read_csv(io.StringIO(text))
        if r.status_code == 200 and text == "":
            return pd.DataFrame()
        print(f"  unexpected reply (HTTP {r.status_code}): {text[:150]!r}, retry {attempt}/3")
        time.sleep(5 * attempt)
    raise RuntimeError(f"Failed: {source} from {start} ({days} days). Check key / dataset name / dates.")


def download(source, bbox, start, end):
    frames = []
    d = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while d <= last:
        days = min(5, (last - d).days + 1)  # API allows at most 10 days per request
        print(f"{source}: {d} (+{days} days)")
        df = fetch_chunk(source, bbox, d, days)
        if len(df):
            frames.append(df)
        d += timedelta(days=days)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main():
    if not MAP_KEY:
        sys.exit("Set FIRMS_MAP_KEY first (see src/config.py).")
    RAW.mkdir(parents=True, exist_ok=True)
    bbox = REGIONS[REGION]
    for source in (MODIS_SOURCE, VIIRS_SOURCE):
        df = download(source, bbox, START, END)
        out = RAW / f"{source}_{REGION}.csv"
        df.to_csv(out, index=False)
        print(f"Saved {len(df):,} rows -> {out}\n")


if __name__ == "__main__":
    main()
