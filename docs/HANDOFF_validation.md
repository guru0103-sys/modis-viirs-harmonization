# Validation handoff: MODIS–VIIRS Harmonization (NASA Space Apps 2026)

**For:** teammate 3 (validation)  **From:** Guru
**Hard deadline:** Sun 15 Nov 2026, 11:59 PM. **Team target:** submit by Sunday 12:00.
**Your check-ins:** Fri 9 PM (progress message) | Sat 12 PM (Test 1 done) | Sat 2 PM (decide on Test 2) | Sat 6 PM (final summary) | Sat 8 PM feature freeze.

---

## 1. The project in 60 seconds

Two satellite families detect fires from space:

- **MODIS** (Aqua satellite here): 1 km pixels. Older, being retired.
- **VIIRS** (Suomi NPP here): 375 m pixels. Newer and more sensitive, so it sees small fires MODIS misses.

They disagree on what counts as a fire, how confident the detection is, and how strong the fire is (**FRP** = fire radiative power, in megawatts). Our project builds a **harmonized layer** so a user switching from MODIS to VIIRS gets a continuous record: a unified confidence score, calibrated FRP, and a detection-probability curve.

Study area: **Punjab and Haryana, India. Period: October to November 2024.**

**Your job: prove the harmonized product can be trusted.** Judges will look for a number that says it works, so the quality of your result matters as much as mine.

## 2. What is already done (by Guru)

- Downloaded and cleaned the data: **5,202 MODIS Aqua fires** and **16,476 VIIRS Suomi-NPP fires.** MODIS Terra was excluded.
- Built a matching method: a VIIRS fire matches a MODIS fire if it lies inside the MODIS pixel box (scan x track in km, centred on the MODIS point) **and** the two detections are within a time window.
- Ran it on real data. With a 60-minute window: **492 VIIRS fires matched, 323 unique MODIS fires.** The primary window is now **30 minutes** (a provisional choice, not a proven optimum).
- Ran diagnostics showing the raw "97% of VIIRS fires missed by MODIS" is **not** a real miss rate, because of different overpass times, swath coverage and sensitivity.

**Important meaning of the data:** every match is a *candidate association*, not a confirmed same-fire event. Say so in any text you write.

## 3. What you get

Files from the shared drive (all produced by Guru's code). Unzip so the folders match:

| File | Location | What it is |
|---|---|---|
| `viirs_coobserved.csv` | `data/matched/` | One row per VIIRS fire (this is your main file) |
| `matched_pairs.csv` | `data/matched/` | One row per matched VIIRS–MODIS pair |
| `modis_clean.csv` | `data/clean/` | All MODIS Aqua fires |
| `viirs_clean.csv` | `data/clean/` | All VIIRS fires |

**Columns that matter:**

- `time_utc`, `latitude`, `longitude`, `frp`, `daynight`, `scan`, `track`
- `conf_class` (VIIRS: l / n / h = low / nominal / high) and `conf_num` (MODIS: 0 to 100)
- `modis_detected_box_30min` = 1 if a MODIS Aqua fire matched this VIIRS fire under the box rule and 30-minute window
- `modis_detected_distance_1p5km_30min` = same, but using a plain 1.5 km distance instead of the box
- `co_observed_proxy` = 1 if a MODIS fire exists within 150 km and 30 minutes (a rough proxy for "MODIS could have seen this"). **Use only co_observed_proxy = 1 rows for any detection statistic.**
- In `matched_pairs.csv`: VIIRS columns are unprefixed (`frp`), MODIS columns start with `modis_` (`modis_frp`, `modis_time_utc`), and `modis_idx` links to the row position in `modis_clean.csv`.

**Warning:** do not sort, re-index or deduplicate `modis_clean.csv`. `modis_idx` is the row position in that file and will break.

Set up your environment (do this tonight):

```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/friday_diagnostics.py # prints a table if setup + data are right
```

## 4. What you do

### TEST 1 (must finish by Saturday 12 PM): is the method stable?

**Rule for every sub-test: split by DAY, not by row.** Sort the unique dates, use the first 60% of days as **train** and the last 40% as **test**. Never let one day appear in both.

**1a. Detection-probability model**
- Data: VIIRS fires with `co_observed_proxy = 1`. Label = `modis_detected_box_30min`.
- Fit a logistic regression on the train days using `log(frp)` and day/night. (scikit-learn is already installed.)
- On the test days report: **AUC**, and a calibration table (predicted probability in 5 bins vs the observed detection rate).
- Also report detection rate by FRP bin on train vs test.

**1b. Does a confidence level mean the same thing in train and test?**
- VIIRS: for each `conf_class` (l / n / h), the share with `modis_detected_box_30min = 1`, train vs test.
- MODIS: a MODIS row is "confirmed" if its row position appears in the set of `modis_idx` values (>= 0) from the matched pairs. Bin `conf_num` into <30, 30 to 79, 80 or above, and report the confirmed share, train vs test.
- Report the train/test gap for each level. No pass or fail rule: just show it.

**1c. FRP calibration**
- Use `matched_pairs.csv`. For each `modis_idx`, **sum the VIIRS `frp`** of all its matched VIIRS fires, and pair that sum with `modis_frp`.
- Fit `modis_frp = a * summed_viirs_frp + b` on train days (use `modis_time_utc` for the split). On test days report slope, intercept, **R², RMSE**.
- The sample is small (about 260 MODIS pixels at 30 minutes, fewer after splitting). **Always print N** next to every number, and never claim more than N supports.

**Outputs of Test 1:**
1. `outputs/validation_results.csv` with columns: `test`, `metric`, `train`, `test_value`, `n_train`, `n_test`.
2. `outputs/validation_plots.png` with three panels: calibration plot, detection rate by FRP bin (train vs test), FRP scatter with the fitted line and a 1:1 line.
3. `docs/validation_summary.md`: **five plain-language lines** saying what the numbers mean, plus one line on limits.

**Done when:** Guru can run `python src/validate.py` (you write it) and the three outputs appear.

### TEST 2 (bonus, strict 2-hour limit): agreement with burned area

Only do this if Test 1 is done and the data is accessible.

- Product: **MCD64A1** (MODIS burned area, monthly, 500 m). Need Oct and Nov 2024 for the tiles that cover Punjab/Haryana (likely h24v05 and h24v06, but confirm on the MODIS tile map). Download needs an Earthdata login, which had a maintenance outage earlier.
- Useful layer: **Burn Date** (day of year).
- For each fire list (MODIS only, VIIRS only, matched), report the **share of detections inside a burned pixel whose burn date is within 3 days of the detection**.
- Files are HDF4, which can be painful to read (try `pyhdf` or GDAL). Convert lat/lon to the sinusoidal projection with `pyproj` before indexing pixels.
- **If you cannot read one file by Saturday 2 PM, drop Test 2 and tell Guru.** Do not let it eat your Saturday.
- Burned area measures agreement with an independent source, but it can miss small crop-residue fires. State that in your summary.

## 5. What not to do

- Do **not** change the matching rule or edit `match.py`. Guru owns it.
- Do **not** commit anything under `data/` to GitHub.
- Do **not** quote the raw "97% missed" figure anywhere.
- Do **not** report a number without its N.

## 6. If you get stuck

Ask in the group chat, not in DMs, so others see the answer. If you are blocked for more than 2 hours, say so immediately. Guru will pair you with whoever is free.

## 7. Limits to carry into your summary

- Matches are candidate associations, not confirmed same-fire events.
- `co_observed_proxy` is a proxy for swath overlap, not exact geometry.
- The pixel box assumes scan runs east-west and track north-south.
- One region and one season only.
- Small sample for FRP calibration.
