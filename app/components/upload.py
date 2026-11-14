
"""Upload and process fresh MODIS–VIIRS FIRMS datasets."""

from pathlib import Path
import sys
import tempfile
import uuid

import pandas as pd
import streamlit as st


# Ensure the project root is importable when Streamlit runs app/main.py.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _get_upload_workspace():
    """Create a stable temporary workspace for this browser session."""

    if "upload_workspace_id" not in st.session_state:
        st.session_state["upload_workspace_id"] = uuid.uuid4().hex

    return (
        Path(tempfile.gettempdir())
        / "modis_viirs_uploads"
        / st.session_state["upload_workspace_id"]
    )


def render_upload_page():
    """Render upload controls and process uploaded FIRMS CSV files."""

    st.markdown("## Upload & process datasets")

    st.caption(
        "UPLOAD RAW FIRMS CSV FILES  /  CLEAN  /  MATCH  /  RELOAD DASHBOARD"
    )

    st.info(
        "Upload the original raw MODIS and VIIRS FIRMS CSV files. "
        "The pipeline uses the project's existing Aqua filtering, "
        "cleaning, matching, and diagnostic rules."
    )

    modis_file = st.file_uploader(
        "MODIS Aqua CSV",
        type=["csv"],
        key="upload_modis_csv",
        help="Upload a raw MODIS FIRMS CSV containing acq_date, acq_time, confidence, and sensor fields.",
    )

    viirs_file = st.file_uploader(
        "VIIRS Suomi-NPP CSV",
        type=["csv"],
        key="upload_viirs_csv",
        help="Upload a raw VIIRS FIRMS CSV containing acq_date, acq_time, confidence, and sensor fields.",
    )

    st.divider()

    if modis_file is None or viirs_file is None:
        st.warning(
            "Select both CSV files before starting processing."
        )
        return

    st.write("**Selected files**")
    st.write(f"MODIS: `{modis_file.name}`")
    st.write(f"VIIRS: `{viirs_file.name}`")

    if st.button(
        "Process datasets",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner(
                "Cleaning, matching, and generating diagnostics..."
            ):
                # Import only when processing is requested.
                from src.pipeline import run_pipeline

                modis_raw = pd.read_csv(modis_file)
                viirs_raw = pd.read_csv(viirs_file)

                workspace = _get_upload_workspace()

                result = run_pipeline(
                    modis_raw=modis_raw,
                    viirs_raw=viirs_raw,
                    output_dir=workspace,
                )

                # Load the newly generated dashboard datasets.
                viirs = pd.read_csv(
                    workspace / "matched" / "viirs_coobserved.csv"
                )

                modis = pd.read_csv(
                    workspace / "clean" / "modis_clean.csv"
                )

                matched_pairs = pd.read_csv(
                    workspace / "matched" / "matched_pairs.csv"
                )

                # Store in this Streamlit browser session.
                st.session_state["active_datasets"] = {
                    "viirs": viirs,
                    "modis": modis,
                    "matched_pairs": matched_pairs,
                    "source": "uploaded",
                    "workspace": str(workspace),
                    "summary": result["match_summary"],
                }

            st.success("Processing completed successfully.")

            st.write("**Generated dataset summary**")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Clean MODIS",
                f"{result['modis_count']:,}",
            )

            col2.metric(
                "Clean VIIRS",
                f"{result['viirs_count']:,}",
            )

            col3.metric(
                "Candidate pairs",
                f"{result['matched_pair_count']:,}",
            )

            st.caption(
                "The dashboard will now use these uploaded datasets. "
                "Your original project CSV files remain unchanged."
            )

            st.rerun()

        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            st.info(
                "Check that both uploads are raw FIRMS CSV files "
                "with the expected columns. Your previous dashboard "
                "dataset has not been replaced."
            )

    st.divider()

    active = st.session_state.get("active_datasets")

    if active and active.get("source") == "uploaded":
        st.success("An uploaded dataset is currently active.")

        if st.button(
            "Return to original project datasets",
            use_container_width=True,
        ):
            del st.session_state["active_datasets"]
            st.rerun()

    else:
        st.caption(
            "The dashboard is currently using the original project datasets."
        )
