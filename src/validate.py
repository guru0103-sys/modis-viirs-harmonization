
"""
Test 1 validation for MODIS–VIIRS fire harmonization.
Run from project root: python src/validate.py

This script does not modify match.py, config.py, or any input data.

It uses the supplied 30-minute VIIRS co-observation labels and
validates MODIS–VIIRS candidate associations using matched_pairs.csv.

The matching provenance is checked directly from the timestamps:
pairs with a time gap <=30 minutes are used for the MODIS confidence
and FRP analyses. The script reports the actual pair count, maximum
time gap, and number of pairs outside the 30-minute window.
"""

from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import roc_auc_score, r2_score, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline


ROOT = Path(__file__).resolve().parents[1]
MATCHED = ROOT / "data" / "matched"
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"

OUT.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

MATCH_WINDOW_MINUTES = 30


def read_csv(path, required):
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")

    df = pd.read_csv(path)
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"{path.name}: missing columns {missing}; "
            f"actual columns: {df.columns.tolist()}"
        )

    return df


def add_day(df, col):
    out = df.copy()
    out["_time"] = pd.to_datetime(
        out[col], utc=True, errors="coerce"
    )
    out = out[out["_time"].notna()].copy()
    out["_day"] = out["_time"].dt.strftime("%Y-%m-%d")
    return out


def split_by_day(df):
    days = sorted(df["_day"].dropna().unique())

    if len(days) < 2:
        raise ValueError(
            f"Need at least 2 unique days; found {len(days)}"
        )

    cut = int(np.floor(0.60 * len(days)))
    cut = min(max(cut, 1), len(days) - 1)

    train_days = set(days[:cut])
    test_days = set(days[cut:])

    train = df[df["_day"].isin(train_days)].copy()
    test = df[df["_day"].isin(test_days)].copy()

    assert not (set(train["_day"]) & set(test["_day"]))

    return train, test, len(train_days), len(test_days)


def rate(y):
    return float(np.mean(y)) if len(y) else np.nan


def add_result(
    rows, test, metric, train_value,
    test_value, n_train, n_test
):
    rows.append({
        "test": test,
        "metric": metric,
        "train": train_value,
        "test_value": test_value,
        "n_train": int(n_train),
        "n_test": int(n_test)
    })


# ---------------------------------------------------------
# Load input files and inspect schemas
# ---------------------------------------------------------

co_path = MATCHED / "viirs_coobserved.csv"
pair_path = MATCHED / "matched_pairs.csv"
modis_path = CLEAN / "modis_clean.csv"
viirs_path = CLEAN / "viirs_clean.csv"

co = read_csv(
    co_path,
    [
        "time_utc", "frp", "daynight", "conf_class",
        "co_observed_proxy", "modis_detected_box_30min"
    ]
)

pairs = read_csv(
    pair_path,
    [
        "time_utc", "frp", "modis_idx",
        "modis_time_utc", "modis_frp"
    ]
)

modis = read_csv(modis_path, ["time_utc", "conf_num"])
viirs = read_csv(viirs_path, ["time_utc"])

print("INPUT FILES — actual row counts and columns")

for name, df in [
    ("viirs_coobserved.csv", co),
    ("matched_pairs.csv", pairs),
    ("modis_clean.csv", modis),
    ("viirs_clean.csv", viirs)
]:
    print(f"\n{name}: {len(df):,} rows")
    print(", ".join(df.columns))


# ---------------------------------------------------------
# Matching provenance verification
# ---------------------------------------------------------

pairs["time_viirs"] = pd.to_datetime(
    pairs["time_utc"], utc=True, errors="coerce"
)

pairs["time_modis"] = pd.to_datetime(
    pairs["modis_time_utc"], utc=True, errors="coerce"
)

pairs["gap_min"] = (
    pairs["time_viirs"] - pairs["time_modis"]
).abs().dt.total_seconds() / 60

valid_gaps = pairs["gap_min"].dropna()

if len(valid_gaps):
    max_gap = float(valid_gaps.max())
    pairs_over_window = int(
        (valid_gaps > MATCH_WINDOW_MINUTES).sum()
    )
else:
    max_gap = np.nan
    pairs_over_window = 0

p30 = pairs[
    pairs["gap_min"].le(MATCH_WINDOW_MINUTES)
].copy()

confirmed_idx = set(
    pd.to_numeric(
        p30["modis_idx"], errors="coerce"
    ).dropna().astype(int)
)

print("\n========== MATCHING PROVENANCE ==========")
print(f"Matching window: {MATCH_WINDOW_MINUTES} minutes")
print(f"Total pairs: {len(pairs)}")
print(f"Pairs within 30 minutes: {len(p30)}")
print(f"Pairs exceeding 30 minutes: {pairs_over_window}")
print(f"Maximum time gap: {max_gap:.1f} minutes")
print(f"Unique MODIS detections: {len(confirmed_idx)}")


# ---------------------------------------------------------
# 1a — Logistic model and detection rates
# ---------------------------------------------------------

# Use only co_observed_proxy == 1.
a = co[
    pd.to_numeric(
        co["co_observed_proxy"], errors="coerce"
    ).eq(1)
].copy()

a["frp"] = pd.to_numeric(a["frp"], errors="coerce")
a["label"] = pd.to_numeric(
    a["modis_detected_box_30min"], errors="coerce"
)

a["daynight"] = (
    a["daynight"].astype(str).str.upper().str.strip()
)

a = a[
    (a["frp"] > 0)
    & a["label"].isin([0, 1])
    & a["daynight"].isin(["D", "N"])
].copy()

a["log_frp"] = np.log(a["frp"])
a["is_night"] = (a["daynight"] == "N").astype(int)

a = add_day(a, "time_utc")

atr, ate, a_train_days, a_test_days = split_by_day(a)

Xtr = atr[["log_frp", "is_night"]].to_numpy()
Xte = ate[["log_frp", "is_night"]].to_numpy()

ytr = atr["label"].astype(int).to_numpy()
yte = ate["label"].astype(int).to_numpy()

model = None
pred = np.full(len(ate), np.nan)

if len(np.unique(ytr)) == 2 and len(atr) >= 10:
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            max_iter=2000,
            class_weight=None
        )
    )

    model.fit(Xtr, ytr)
    pred = model.predict_proba(Xte)[:, 1]

    auc = (
        roc_auc_score(yte, pred)
        if len(np.unique(yte)) == 2
        else np.nan
    )
else:
    auc = np.nan
    warnings.warn(
        "1a: training split lacks both classes "
        "or has too few rows; logistic model not fitted."
    )

add_result(
    results := [],
    "1a",
    "test_AUC",
    np.nan,
    auc,
    len(atr),
    len(ate)
)


# ---------------------------------------------------------
# 1a — Calibration
# ---------------------------------------------------------

cal_rows = []

if model is not None:
    bins = np.linspace(0, 1, 6)

    bin_id = np.clip(
        np.digitize(pred, bins[1:-1], right=False),
        0,
        4
    )

    for i in range(5):
        mask = bin_id == i
        n = int(mask.sum())

        pmean = (
            float(np.mean(pred[mask]))
            if n else np.nan
        )

        observed = rate(yte[mask]) if n else np.nan

        add_result(
            results,
            "1a",
            f"calibration_bin_{i+1}_predicted_vs_observed",
            pmean,
            observed,
            len(atr),
            n
        )

        cal_rows.append((
            pmean,
            observed,
            n,
            f"{bins[i]:.1f}-{bins[i+1]:.1f}"
        ))

else:
    cal_rows = [
        (np.nan, np.nan, 0, f"{i}")
        for i in range(5)
    ]


# ---------------------------------------------------------
# 1a — Co-detection rate by FRP bins
# ---------------------------------------------------------

frp_edges = [0, 1, 2, 5, 10, 20, np.inf]

frp_labels = [
    "<1", "1–2", "2–5",
    "5–10", "10–20", ">20"
]

atr_bins = pd.cut(
    atr["frp"],
    bins=frp_edges,
    labels=frp_labels,
    right=False
)

ate_bins = pd.cut(
    ate["frp"],
    bins=frp_edges,
    labels=frp_labels,
    right=False
)

for b in frp_labels:
    gtr = atr[atr_bins.astype(str) == b]
    gte = ate[ate_bins.astype(str) == b]

    add_result(
        results,
        "1a",
        f"co_detection_rate_FRP_{b}",
        rate(gtr["label"]) if len(gtr) else np.nan,
        rate(gte["label"]) if len(gte) else np.nan,
        len(gtr),
        len(gte)
    )


# ---------------------------------------------------------
# 1b — VIIRS confidence reliability
# ---------------------------------------------------------

for cls in ["l", "n", "h"]:
    gtr = atr[
        atr["conf_class"].astype(str).str.lower() == cls
    ]

    gte = ate[
        ate["conf_class"].astype(str).str.lower() == cls
    ]

    rtr = rate(gtr["label"])
    rte = rate(gte["label"])

    add_result(
        results,
        "1b",
        f"VIIRS_conf_{cls}_co_detection_share",
        rtr,
        rte,
        len(gtr),
        len(gte)
    )

    add_result(
        results,
        "1b",
        f"VIIRS_conf_{cls}_train_test_gap_pp",
        rtr,
        (rte - rtr) * 100
        if np.isfinite(rtr) and np.isfinite(rte)
        else np.nan,
        len(gtr),
        len(gte)
    )


# ---------------------------------------------------------
# 1b — MODIS confidence reliability
# Use the confirmed 30-minute candidate associations.
# ---------------------------------------------------------

m = modis.copy()

# Preserve original row order because modis_idx refers
# to the original positional index in modis_clean.csv.
m["_rowpos"] = np.arange(len(m))

m["confirmed"] = (
    m["_rowpos"].isin(confirmed_idx).astype(int)
)

m["conf_num"] = pd.to_numeric(
    m["conf_num"], errors="coerce"
)

m["conf_bin"] = pd.cut(
    m["conf_num"],
    bins=[-np.inf, 30, 80, np.inf],
    labels=["<30", "30–79", "80+"],
    right=False
)

m = add_day(m, "time_utc")

mtr, mte, m_train_days, m_test_days = split_by_day(m)

for b in ["<30", "30–79", "80+"]:
    gtr = mtr[mtr["conf_bin"].astype(str) == b]
    gte = mte[mte["conf_bin"].astype(str) == b]

    rtr = rate(gtr["confirmed"])
    rte = rate(gte["confirmed"])

    add_result(
        results,
        "1b",
        f"MODIS_conf_{b}_confirmed_share",
        rtr,
        rte,
        len(gtr),
        len(gte)
    )

    add_result(
        results,
        "1b",
        f"MODIS_conf_{b}_train_test_gap_pp",
        rtr,
        (rte - rtr) * 100
        if np.isfinite(rtr) and np.isfinite(rte)
        else np.nan,
        len(gtr),
        len(gte)
    )


# ---------------------------------------------------------
# 1c — FRP calibration
# Aggregate candidate associations by MODIS row.
# Only pairs within the 30-minute window are included.
# ---------------------------------------------------------

p30["modis_idx"] = pd.to_numeric(
    p30["modis_idx"], errors="coerce"
)

p30["frp"] = pd.to_numeric(
    p30["frp"], errors="coerce"
)

p30["modis_frp"] = pd.to_numeric(
    p30["modis_frp"], errors="coerce"
)

agg = (
    p30.dropna(
        subset=[
            "modis_idx",
            "frp",
            "modis_frp",
            "time_modis"
        ]
    )
    .groupby("modis_idx", as_index=False)
    .agg(
        summed_viirs_frp=("frp", "sum"),
        modis_frp=("modis_frp", "first"),
        modis_time=("time_modis", "first"),
        n_viirs=("frp", "size")
    )
)

agg["_day"] = agg["modis_time"].dt.strftime("%Y-%m-%d")

rtr, rte, r_train_days, r_test_days = split_by_day(agg)

X_train = rtr[["summed_viirs_frp"]].to_numpy()
y_train = rtr["modis_frp"].to_numpy()

X_test = rte[["summed_viirs_frp"]].to_numpy()
y_test = rte["modis_frp"].to_numpy()

reg = None

if (
    len(rtr) >= 3
    and len(rte) >= 2
    and np.isfinite(X_train).all()
    and np.isfinite(y_train).all()
):
    reg = LinearRegression().fit(X_train, y_train)

    test_pred = reg.predict(X_test)

    slope = float(reg.coef_[0])
    intercept = float(reg.intercept_)

    r2 = (
        r2_score(y_test, test_pred)
        if len(y_test) >= 2
        else np.nan
    )

    rmse = float(
        np.sqrt(mean_squared_error(y_test, test_pred))
    )

else:
    slope = intercept = r2 = rmse = np.nan
    test_pred = np.array([])

    warnings.warn(
        "1c: insufficient train/test MODIS groups "
        "for reliable linear calibration."
    )

add_result(
    results, "1c", "slope_modis_vs_summed_viirs",
    slope, np.nan, len(rtr), len(rte)
)

add_result(
    results, "1c", "intercept_MW",
    intercept, np.nan, len(rtr), len(rte)
)

add_result(
    results, "1c", "test_R2",
    np.nan, r2, len(rtr), len(rte)
)

add_result(
    results, "1c", "test_RMSE_MW",
    np.nan, rmse, len(rtr), len(rte)
)


# ---------------------------------------------------------
# Save validation results
# ---------------------------------------------------------

res = pd.DataFrame(
    results,
    columns=[
        "test",
        "metric",
        "train",
        "test_value",
        "n_train",
        "n_test"
    ]
)

res.to_csv(
    OUT / "validation_results.csv",
    index=False
)


# ---------------------------------------------------------
# Three-panel validation plot
# ---------------------------------------------------------

fig, axes = plt.subplots(1, 3, figsize=(17, 5))


# Calibration plot
ax = axes[0]

ax.plot(
    [0, 1], [0, 1],
    linestyle="--",
    label="Ideal"
)

if cal_rows and any(
    np.isfinite(x[0]) and np.isfinite(x[1])
    for x in cal_rows
):
    xs = [
        x[0] for x in cal_rows
        if np.isfinite(x[0]) and np.isfinite(x[1])
    ]

    ys = [
        x[1] for x in cal_rows
        if np.isfinite(x[0]) and np.isfinite(x[1])
    ]

    ax.plot(
        xs, ys,
        marker="o",
        label="Test data"
    )

ax.set(
    xlabel="Mean predicted probability",
    ylabel="Observed co-detection rate",
    title=f"1a Calibration (test N={len(ate)})",
    xlim=(0, 1),
    ylim=(0, 1)
)

ax.legend(fontsize=8)


# FRP bins train/test
ax = axes[1]

centres = np.arange(len(frp_labels))
width = 0.38

rates_train = []
rates_test = []

for b in frp_labels:
    rates_train.append(
        rate(atr.loc[atr_bins == b, "label"])
    )

    rates_test.append(
        rate(ate.loc[ate_bins == b, "label"])
    )

ax.bar(
    centres - width / 2,
    rates_train,
    width,
    label="Train"
)

ax.bar(
    centres + width / 2,
    rates_test,
    width,
    label="Test"
)

ax.set_xticks(centres, frp_labels)

ax.set(
    xlabel="VIIRS FRP (MW)",
    ylabel="Co-detection agreement",
    title="1a Co-detection by FRP"
)

ax.legend(fontsize=8)


# FRP scatter and fitted line
ax = axes[2]

if len(rte):
    ax.scatter(
        rte["summed_viirs_frp"],
        rte["modis_frp"],
        alpha=.7,
        label=f"Test pixels (N={len(rte)})"
    )

maxv = max(
    float(np.nanmax(agg["summed_viirs_frp"]))
    if len(agg) else 1,

    float(np.nanmax(agg["modis_frp"]))
    if len(agg) else 1,

    1
)

ax.plot(
    [0, maxv],
    [0, maxv],
    linestyle=":",
    label="1:1"
)

if reg is not None:
    xx = np.linspace(0, maxv, 100)

    ax.plot(
        xx,
        reg.predict(xx.reshape(-1, 1)),
        label="Train fit"
    )

ax.set(
    xlabel="Summed matched VIIRS FRP (MW)",
    ylabel="MODIS FRP (MW)",
    title=(
        f"1c FRP calibration "
        f"(train N={len(rtr)}, test N={len(rte)})"
    )
)

ax.legend(fontsize=8)

fig.tight_layout()

fig.savefig(
    OUT / "validation_plots.png",
    dpi=180
)

plt.close(fig)


# ---------------------------------------------------------
# Six-line validation summary
# ---------------------------------------------------------

def fmt(v, digits=3):
    return (
        "not estimable"
        if not np.isfinite(v)
        else f"{v:.{digits}f}"
    )


auc_row = res[res.metric == "test_AUC"]

auc_val = (
    float(auc_row.iloc[0].test_value)
    if len(auc_row)
    else np.nan
)

frp_1_2_rate = rate(
    ate.loc[ate_bins == "1–2", "label"]
)

frp_above_20_rate = rate(
    ate.loc[ate_bins == ">20", "label"]
)

high_train = atr[
    atr["conf_class"].astype(str).str.lower() == "h"
]

high_test = ate[
    ate["conf_class"].astype(str).str.lower() == "h"
]

if pairs_over_window == 0 and len(valid_gaps) == len(pairs):
    provenance_text = (
        f"matched_pairs.csv contains {len(pairs)} candidate pairs, "
        f"all within the {MATCH_WINDOW_MINUTES}-minute window; "
        f"the maximum observed gap is {max_gap:.1f} minutes."
    )
else:
    provenance_text = (
        f"matched_pairs.csv contains {len(pairs)} candidate pairs; "
        f"{len(p30)} are within {MATCH_WINDOW_MINUTES} minutes "
        f"and {pairs_over_window} exceed that window. "
        f"The 1b MODIS and 1c analyses use only the qualifying subset."
    )


summary = [
    (
        f"1a: The held-out-day logistic model AUC was "
        f"{fmt(auc_val)} (train N={len(atr)}, test N={len(ate)}); "
        f"0.5 is chance ranking and 1.0 is perfect ranking."
    ),

    (
        f"1a: The five-bin calibration plot compares predicted "
        f"probabilities with observed co-detection agreement on "
        f"{len(ate)} held-out VIIRS fires; small/empty bins are unstable."
    ),

    (
        f"1a: On test days, co-detection agreement ranged from "
        f"{frp_1_2_rate:.1%} for 1–2 MW "
        f"(N={int((ate_bins == '1–2').sum())}) to "
        f"{frp_above_20_rate:.1%} above 20 MW "
        f"(N={int((ate_bins == '>20').sum())}); "
        f"these are not true detection probabilities."
    ),

    (
        f"1b: VIIRS high-confidence co-detection was "
        f"{rate(high_train['label']):.1%} in train "
        f"(N={len(high_train)}) versus "
        f"{rate(high_test['label']):.1%} in test "
        f"(N={len(high_test)}); the small test group makes this unstable."
    ),

    (
        f"1c: FRP calibration used {len(rtr)} train and "
        f"{len(rte)} test MODIS groups; test R²={fmt(r2)} "
        f"and RMSE={fmt(rmse)} MW, so interpret cautiously."
    ),

    (
        "Limits: matches are candidate associations; "
        "co_observed_proxy is only a proxy for swath overlap; "
        "the pixel box assumes scan east-west and track north-south; "
        "this is one region and one season; the FRP sample is small. "
        + provenance_text
    )
]

(DOCS / "validation_summary.md").write_text(
    "\n".join(summary) + "\n",
    encoding="utf-8"
)


# ---------------------------------------------------------
# Final report
# ---------------------------------------------------------

print("\n========== VALIDATION COMPLETE ==========")

print("\nMatching provenance:")
print(f"Matching window: {MATCH_WINDOW_MINUTES} minutes")
print(f"Total pairs: {len(pairs)}")
print(f"Pairs within 30 minutes: {len(p30)}")
print(f"Pairs exceeding 30 minutes: {pairs_over_window}")
print(f"Maximum time gap: {max_gap:.1f} minutes")
print(f"Unique MODIS detections: {len(confirmed_idx)}")

print("\nSaved:")
print(OUT / "validation_results.csv")
print(OUT / "validation_plots.png")
print(DOCS / "validation_summary.md")

print("\nValidation summary:")
for line in summary:
    print(line)
