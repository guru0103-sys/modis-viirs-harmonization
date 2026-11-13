# WEDNESDAY (tonight) - exact steps

Goal by end of night: repo shared, everyone can download, raw data in hand, mismatches written down.

## Everyone (20 min)
1. Create a free account at https://urs.earthdata.nasa.gov
2. Request your free MAP_KEY at https://firms.modaps.eosdis.nasa.gov/api/map_key/ (arrives by email)
3. Clone the repo, then:
   pip install -r requirements.txt
   export FIRMS_MAP_KEY=your_key        (Windows: set FIRMS_MAP_KEY=your_key)
4. Test: python src/make_synthetic.py && python src/clean.py && python src/match.py
   If the last command prints a summary, your setup works. Then delete data/raw/*.csv.

## Guru (30 min)
- Confirm the one-sentence claim (README.md) and region/dates in src/config.py
- Share the repo link with the team

## Storyteller (30 min)
- Create the GitHub repo, upload this folder, invite everyone
- Create a shared drive folder for large data files (data/ is not committed)

## Data engineer (60 min)
- python src/download_firms.py
- If it fails: check the key, then try one 10-day chunk by hand in the browser:
  https://firms.modaps.eosdis.nasa.gov/api/area/csv/<KEY>/MODIS_SP/73.8,27.6,77.6,32.6/10/2024-10-01
- Run python src/inspect_columns.py and paste output into docs/column_mismatches.md
- Upload the raw CSVs to the shared drive

## Pair person (30 min)
- Run all four scripts on synthetic data yourself, note anything confusing
- Read src/match.py so you can explain it to the team

## Validation analyst (45 min)
- Make Earthdata account, find MCD64A1 (MODIS burned area) and VNP64A1 (VIIRS burned area) in https://search.earthdata.nasa.gov
- Find the tile(s) covering Punjab/Haryana, write the tile names in docs/validation_notes.md
- Start the download (files are big)

## Frontend (45 min)
- pip install streamlit folium streamlit-folium
- Make app/app.py show a map with a few fake points and a sensor dropdown (MODIS / VIIRS / Harmonized)

## Done when
Raw MODIS and VIIRS CSVs exist for Oct-Nov 2024, mismatches are documented, burned-area tiles are identified.
