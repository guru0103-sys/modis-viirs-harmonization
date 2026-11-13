# THURSDAY - exact steps

Goal by end of day: matched table + the three counts + a second person who can re-run everything.

## Morning (9:00-12:00)
Data engineer: python src/clean.py. Read the printed row counts. Check:
- MODIS satellites present: should include Aqua and Terra
- Rows dropped by cleaning: should be small. If it is more than 5%, find out why
- Write the counts into docs/data_quality.md

Guru: read src/match.py with the REAL data in mind. Decide the settings in src/config.py:
- MATCH_MINUTES: start at 60. Plot the time gap of matched pairs; if most are under 10 minutes, tighten to 30
- MODIS_SATELLITE: keep Aqua first

## Midday (12:00-15:00) - the matching run
python src/match.py
Read outputs/match_summary.json. Sanity checks:
1. Median match distance should be below about 1 km. Larger means a geometry bug
2. pct_viirs_missed_by_modis is plausibly 40-80 percent for small agricultural fires (my guess, not a fact: check against your data)
3. Unconfirmed MODIS share should be small. If it is large, your time window or box is wrong

If matching is slow, reduce the date range in config.py to one month and rerun.

## Afternoon (15:00-19:00)
Pair person: fresh clone, run clean.py and match.py from scratch. Write down every error, fix the README steps. This is the reproducibility check.

Validation analyst: finish the burned area download, open one file, confirm you can read it (rasterio or pyhdf, pick one and note it in docs/validation_notes.md).

Frontend: load outputs from data/matched/viirs_flagged.csv into the app map: color points by modis_detected.

Storyteller: write the first draft of the 2-minute script (problem, the bridge idea, one chart, result).

## Evening (19:00-21:00) - Guru and the pair
Write the first finding in README Results, for example:
"In Punjab/Haryana, Oct-Nov 2024, X percent of VIIRS fires had no MODIS match; the share rises as FRP falls."
Chart idea for Friday: detection rate by FRP bin (this is the detection probability curve).

## Decision gate (Thursday 21:00)
- Match rate looks sane, distance below 1 km: keep region 2 on the plan
- Otherwise: drop region 2, spend Friday morning fixing matching

## Done when
outputs/match_summary.json exists on real data, data/matched/viirs_flagged.csv exists, and the pair person has reproduced it.
