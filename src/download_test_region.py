
from pathlib import Path
import pandas as pd

from config import MAP_KEY

if not MAP_KEY:
    raise RuntimeError(
        "FIRMS_MAP_KEY is missing. Add it to src/config.py."
    )

# Sri Lanka bounding box
BBOX = "79.5,5.8,82.0,10.1"

START_DATE = "2024-10-01"
DAYS = 5

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "test_region"
OUTPUT.mkdir(parents=True, exist_ok=True)

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

SOURCES = {
    "MODIS_SP": "modis_sri_lanka.csv",
    "VIIRS_SNPP_SP": "viirs_sri_lanka.csv",
}

for source, filename in SOURCES.items():
    url = (
        f"{BASE}/{MAP_KEY}/{source}/"
        f"{BBOX}/{DAYS}/{START_DATE}"
    )

    print(f"\nDownloading {source}...")

    df = pd.read_csv(url, dtype={"acq_time": str})

    if df.empty:
        print("No observations found.")
        continue

    path = OUTPUT / filename
    df.to_csv(path, index=False)

    print(f"Saved: {path}")
    print(f"Rows: {len(df):,}")
    print(f"Size: {path.stat().st_size / 1024:.1f} KB")

print("\nDownload complete.")
