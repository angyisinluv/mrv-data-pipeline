"""Data-quality action centre: filter flagged records and export a correction list."""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from src import kpis

DB = str(ROOT / "data" / "mrv.db")

st.set_page_config(page_title="Data quality action centre", layout="wide")
st.title("Data quality action centre")
st.caption("Flagged records to correct. Synthetic demo data.")

if not Path(DB).exists():
    st.info("The database is not built yet. Open the main page first, then come back here.")
    st.stop()

issues = kpis.issue_records(DB)

# ---- filters ----
st.sidebar.header("Filters")
rules = st.sidebar.multiselect("Validation rule", sorted(issues["rule_id"].unique()))
severities = st.sidebar.multiselect("Severity", sorted(issues["severity"].unique()))
blocks = st.sidebar.multiselect("Block", sorted(issues["block"].unique()))

filtered = issues
if rules:
    filtered = filtered[filtered["rule_id"].isin(rules)]
if severities:
    filtered = filtered[filtered["severity"].isin(severities)]
if blocks:
    filtered = filtered[filtered["block"].isin(blocks)]

# ---- summary ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Issues shown", f"{len(filtered):,}")
c2.metric("Records affected", f"{filtered['row_number'].nunique():,}")
c3.metric("Fail", int((filtered["severity"] == "fail").sum()))
c4.metric("Warning", int((filtered["severity"] == "warning").sum()))

if filtered.empty:
    st.success("No issues match these filters.")
    st.stop()

st.subheader("Issues by rule")
st.bar_chart(filtered.groupby("rule_id").size().sort_values(ascending=False))

st.subheader("Records to correct")
st.dataframe(filtered, hide_index=True, use_container_width=True)

# ---- downloads ----
export = filtered.assign(correction_status="open", corrected_value="", notes="")

d1, d2, _ = st.columns([1, 1, 4])
d1.download_button(
    "Download CSV",
    export.to_csv(index=False).encode("utf-8"),
    file_name="flagged_records.csv",
    mime="text/csv",
)
try:
    buffer = io.BytesIO()
    export.to_excel(buffer, index=False, sheet_name="Flagged records")
    d2.download_button(
        "Download Excel",
        buffer.getvalue(),
        file_name="flagged_records.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
except ImportError:
    d2.caption("Install openpyxl for Excel export.")

st.caption("The download adds correction_status, corrected_value and notes columns for the field team to fill in.")
