# Harmonization of MODIS and VIIRS Hot Spots
NASA Space Apps Challenge 2026 | Deadline: 15 Nov 2026, 11:59 PM (internal target: Sunday noon)

## One-sentence claim
We built a harmonized MODIS-VIIRS hot spot layer with a unified confidence score and calibrated FRP,
validated against burned area, to keep the fire record continuous as MODIS is decommissioned.

## Problem
MODIS (1 km pixels) and VIIRS (375 m pixels) report fires differently: different sensitivity, confidence
scales (MODIS 0-100, VIIRS low/nominal/high) and fire radiative power (FRP). Users who switch from MODIS to VIIRS
get a break in the record.

## Method (fill in as we go)
1. Matching: VIIRS hot spots to MODIS pixel footprints (space + time)
2. Unified confidence score
3. FRP calibration
4. Cross-sensor detection probability model
5. Validation against burned area

## Results
TBD

## Limits
- TBD (known: swath overlap not yet handled; scan/track box is an east-west / north-south approximation)

## How to run
```
pip install -r requirements.txt
export FIRMS_MAP_KEY=your_key        # Windows: set FIRMS_MAP_KEY=your_key
python src/download_firms.py         # real data (needs key)
python src/inspect_columns.py
python src/clean.py
python src/match.py
```
No key yet? `python src/make_synthetic.py` makes fake test data. Delete it before real runs.

## Layout
`src/` pipeline scripts | `data/` (not committed) | `outputs/` results | `app/` Streamlit app | `docs/` notes
