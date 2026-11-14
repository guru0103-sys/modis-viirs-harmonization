"""One place for every setting. Change here, nowhere else."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
MATCHED = ROOT / "data" / "matched"
OUT = ROOT / "outputs"

# Free key from https://firms.modaps.eosdis.nasa.gov/api/map_key/
# Set it in your terminal:  export FIRMS_MAP_KEY=yourkey   (Windows: set FIRMS_MAP_KEY=yourkey)
MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")

# Bounding box = west, south, east, north (degrees)
REGIONS = {
    "punjab_haryana": (73.8, 27.6, 77.6, 32.6),
}
REGION = "punjab_haryana"

# Crop-burning peak. Use a past season: SP (standard processing) archive lags by months.
START = "2024-10-01"
END = "2024-11-30"

# FIRMS dataset names
MODIS_SOURCE = "MODIS_SP"        # Terra + Aqua together
VIIRS_SOURCE = "VIIRS_SNPP_SP"   # Suomi NPP (flies close in time to Aqua)

# Compare Aqua (MODIS) with Suomi NPP (VIIRS) first: their overpasses are minutes apart.
MODIS_SATELLITE = "Aqua"

# Matching rules
MATCH_MINUTES = 30     # max time gap between the two detections
SEARCH_RADIUS_KM = 3.5 # candidate search radius (covers the biggest MODIS pixel at scan edge)
