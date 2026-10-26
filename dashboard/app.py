"""Streamlit dashboard. Run from the project folder:  streamlit run dashboard/app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from src import kpis

DB = str(ROOT / "data" / "mrv.db")

st.set_page_config(page_title="Plantation Monitoring KPIs", layout="wide")
st.title("Plantation Monitoring: Survival and Data Quality")
st.caption("Synthetic demo data. Survival KPIs use only plots that passed validation (not marked needs_review).")

if not Path(DB).exists():
       import subprocess
       with st.spinner("Building the database from the synthetic data..."):
           result = subprocess.run(
               [sys.executable, "-m", "src.run_pipeline"],
               cwd=ROOT, capture_output=True, text=True,
           )
       if result.returncode != 0 or not Path(DB).exists():
           st.error("Could not build the database.")
           st.code(result.stderr or result.stdout)
           st.stop()
# ---- sidebar filters ----
st.sidebar.header("Filters")
block = st.sidebar.selectbox("Block", ["All"] + kpis.list_blocks(DB))
threshold = st.sidebar.slider("Low survival threshold (%)", 50, 100, 80)

# ---- headline numbers ----
overall = kpis.overall_kpis(DB, block)
status = kpis.status_counts(DB, block).set_index("status")["plots"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Usable plots", f"{int(overall['plots']):,}")
c2.metric("Trees planted", f"{int(overall['trees_planted']):,}")
c3.metric("Survival rate", f"{overall['survival_pct']}%")
c4.metric("Plots needing review", int(status.get("needs_review", 0)))

# ---- charts ----
left, right = st.columns(2)
with left:
    st.subheader("Survival by block")
    st.bar_chart(kpis.survival_by_block(DB).set_index("block")["survival_pct"])
with right:
    st.subheader("Survival by irrigation source")
    st.bar_chart(kpis.survival_by_irrigation(DB, block).set_index("irrigation_source")["survival_pct"])

left, right = st.columns(2)
with left:
    st.subheader("Surviving trees by species (share %)")
    st.bar_chart(kpis.species_mix(DB, block).set_index("species")["share_pct"])
with right:
    st.subheader("Data quality: plots by status")
    st.bar_chart(kpis.status_counts(DB, block).set_index("status")["plots"])

# ---- tables ----
st.subheader(f"Plots below {threshold}% survival (follow-up list)")
st.dataframe(kpis.low_survival_plots(DB, threshold, block), hide_index=True)

st.subheader("Validation issues by rule")
st.dataframe(kpis.issues_by_rule(DB), hide_index=True)
