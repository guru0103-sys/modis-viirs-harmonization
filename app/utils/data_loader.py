from pathlib import Path
import pandas as pd

# Project root is the parent of the app folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

VIIRS_PATH = PROJECT_ROOT / "data" / "matched" / "viirs_coobserved.csv"
MODIS_PATH = PROJECT_ROOT / "data" / "clean" / "modis_clean.csv"
PAIRS_PATH = PROJECT_ROOT / "data" / "matched" / "matched_pairs.csv"


def _read_csv(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(
                f"Required dataset not found: {path}\n"
                "Place the project CSV in the path described in README.md."
            )
        return pd.DataFrame()
    return pd.read_csv(path)


def load_datasets():
    """Load the agreed source files without changing scientific results."""
    viirs = _read_csv(VIIRS_PATH)
    modis = _read_csv(MODIS_PATH)
    matched_pairs = _read_csv(PAIRS_PATH, required=False)

    for name, frame in [
        ("VIIRS", viirs),
        ("MODIS", modis),
    ]:
        missing = {"latitude", "longitude", "time_utc"} - set(frame.columns)
        if missing:
            raise ValueError(
                f"{name} CSV is missing expected columns: {', '.join(sorted(missing))}"
            )

    return viirs, modis, matched_pairs
