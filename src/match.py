"""STEPS 7-8 (Thursday): match VIIRS hot spots to MODIS footprints and count the groups.

Run:  python src/match.py
Output:
  data/matched/viirs_flagged.csv   every VIIRS fire + modis_detected (1/0)  <- Friday's model uses this
  data/matched/matched_pairs.csv   one row per VIIRS-MODIS pair with both sensors' values
  outputs/match_summary.json       the counts and percentages

Rule: a VIIRS point matches a MODIS pixel if
  1. it lies inside the MODIS pixel box (scan x track in km, centred on the MODIS point), AND
  2. the detections are within MATCH_MINUTES of each other.
If several MODIS pixels qualify, the nearest wins.
"""
import json

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from config import CLEAN, MATCHED, OUT, MATCH_MINUTES, SEARCH_RADIUS_KM

EARTH_KM = 6371.0
KM_PER_DEG = 111.32


def match(viirs: pd.DataFrame, modis: pd.DataFrame) -> pd.DataFrame:
    """Return one row per VIIRS point: modis_idx (-1 if none) and distance in km."""
    tree = BallTree(np.radians(modis[["latitude", "longitude"]].to_numpy()), metric="haversine")
    v_xy = np.radians(viirs[["latitude", "longitude"]].to_numpy())
    cand = tree.query_radius(v_xy, r=SEARCH_RADIUS_KM / EARTH_KM)

    m_lat = modis["latitude"].to_numpy()
    m_lon = modis["longitude"].to_numpy()
    m_scan = modis["scan"].to_numpy()
    m_track = modis["track"].to_numpy()
    m_time = modis["time_utc"].to_numpy().astype("datetime64[s]").astype("int64")
    v_lat = viirs["latitude"].to_numpy()
    v_lon = viirs["longitude"].to_numpy()
    v_time = viirs["time_utc"].to_numpy().astype("datetime64[s]").astype("int64")

    best = np.full(len(viirs), -1, dtype=int)
    best_d = np.full(len(viirs), np.nan)
    for i, idx in enumerate(cand):
        if len(idx) == 0:
            continue
        dy = (v_lat[i] - m_lat[idx]) * KM_PER_DEG
        dx = (v_lon[i] - m_lon[idx]) * KM_PER_DEG * np.cos(np.radians(v_lat[i]))
        dt_min = np.abs(v_time[i] - m_time[idx]) / 60.0
        # scan runs roughly east-west, track roughly north-south (polar orbit approximation)
        ok = (np.abs(dx) <= m_scan[idx] / 2) & (np.abs(dy) <= m_track[idx] / 2) & (dt_min <= MATCH_MINUTES)
        if ok.any():
            dist = np.hypot(dx, dy)
            j = np.argmin(np.where(ok, dist, np.inf))
            best[i] = idx[j]
            best_d[i] = dist[j]
    return pd.DataFrame({"modis_idx": best, "dist_km": best_d}, index=viirs.index)


def main():
    MATCHED.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    modis = pd.read_csv(CLEAN / "modis_clean.csv", parse_dates=["time_utc"])
    viirs = pd.read_csv(CLEAN / "viirs_clean.csv", parse_dates=["time_utc"])

    res = match(viirs, modis)
    flagged = pd.concat([viirs, res], axis=1)
    flagged["modis_detected"] = (flagged["modis_idx"] >= 0).astype(int)
    flagged.to_csv(MATCHED / "viirs_flagged.csv", index=False)

    pairs = flagged[flagged["modis_detected"] == 1].copy()
    m = modis.add_prefix("modis_").reset_index().rename(columns={"index": "modis_idx"})
    pairs = pairs.merge(m, on="modis_idx", how="left")
    pairs.to_csv(MATCHED / "matched_pairs.csv", index=False)

    n_v, n_m = len(viirs), len(modis)
    n_v_match = int(flagged["modis_detected"].sum())
    matched_modis = set(flagged.loc[flagged["modis_detected"] == 1, "modis_idx"])
    summary = {
        "viirs_total": n_v,
        "viirs_matched_to_modis": n_v_match,
        "viirs_only_modis_missed": n_v - n_v_match,
        "pct_viirs_missed_by_modis": round(100 * (n_v - n_v_match) / max(n_v, 1), 1),
        "modis_total": n_m,
        "modis_confirmed_by_viirs": len(matched_modis),
        "modis_only_not_confirmed": n_m - len(matched_modis),
        "pct_modis_not_confirmed": round(100 * (n_m - len(matched_modis)) / max(n_m, 1), 1),
        "median_match_distance_km": round(float(np.nanmedian(flagged["dist_km"])), 2) if n_v_match else None,
        "match_minutes": MATCH_MINUTES,
    }
    (OUT / "match_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nCAVEAT: VIIRS points outside the Aqua swath count as 'missed by MODIS'.")
    print("Friday: restrict to the swath overlap before quoting the headline percentage.")


if __name__ == "__main__":
    main()
