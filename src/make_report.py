"""Build a standalone HTML QA report for one monitoring round.

Usage:  python -m src.make_report --round "2026 Q3"
"""
import argparse
import html
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from src import kpis

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "mrv.db"
OUT_DIR = ROOT / "reports"

CSS = """
body{font-family:Segoe UI,Arial,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#222}
h1{margin-bottom:0}
h2{margin-top:2rem;border-bottom:1px solid #ddd;padding-bottom:.3rem}
.sub{color:#666}
.tiles{display:flex;gap:1rem;flex-wrap:wrap}
.tile{flex:1;min-width:150px;background:#f4f6f8;border-radius:8px;padding:1rem}
.tile .n{font-size:1.8rem;font-weight:600}
.tile .l{color:#555;font-size:.9rem}
table.t{border-collapse:collapse;width:100%;font-size:.9rem}
.t th,.t td{border-bottom:1px solid #e3e3e3;padding:.4rem .6rem;text-align:left}
.t th{background:#f4f6f8}
.note{background:#fff8e1;border-left:4px solid #f0b400;padding:.6rem 1rem}
"""


def _columns(conn, table):
    """Column names of a table, or an empty list if the table does not exist."""
    return pd.read_sql(f"PRAGMA table_info({table})", conn)["name"].tolist()


def _table(df):
    if df is None or df.empty:
        return "<p>None.</p>"
    return df.to_html(index=False, classes="t", border=0, na_rep="")


def _tile(label, value):
    return f'<div class="tile"><div class="n">{html.escape(str(value))}</div><div class="l">{html.escape(label)}</div></div>'


def _review_plots(db_path):
    """Plots marked needs_review, with the rules that flagged them when available."""
    with sqlite3.connect(db_path) as conn:
        plots = pd.read_sql(
            "SELECT farmer_id, block, village, trees_planted, trees_surviving "
            "FROM plots WHERE status = 'needs_review' ORDER BY block, village, farmer_id",
            conn,
        )
        issue_cols = _columns(conn, "issues")
        if "farmer_id" in issue_cols and "rule_id" in issue_cols:
            reasons = pd.read_sql(
                "SELECT farmer_id, GROUP_CONCAT(DISTINCT rule_id) AS reasons "
                "FROM issues GROUP BY farmer_id",
                conn,
            )
            plots = plots.merge(reasons, on="farmer_id", how="left")
    return plots


def _audit(db_path, limit=25):
    with sqlite3.connect(db_path) as conn:
        if not _columns(conn, "audit_log"):
            return 0, pd.DataFrame()
        n = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        return n, pd.read_sql(f"SELECT * FROM audit_log LIMIT {int(limit)}", conn)


def build_report(db_path, label, threshold=80):
    """Return the report as an HTML string."""
    db_path = str(db_path)
    overall = kpis.overall_kpis(db_path)
    status = kpis.status_counts(db_path)
    counts = dict(zip(status["status"], status["plots"]))
    total = int(status["plots"].sum())
    review = _review_plots(db_path)
    n_changes, audit = _audit(db_path)

    tiles = "".join([
        _tile("Plots in database", f"{total:,}"),
        _tile("Clean", int(counts.get("clean", 0))),
        _tile("Warning", int(counts.get("warning", 0))),
        _tile("Needs review", int(counts.get("needs_review", 0))),
        _tile("Survival rate", f"{overall['survival_pct']}%"),
    ])

    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>QA report {html.escape(label)}</title><style>{CSS}</style></head><body>",
        "<h1>Data quality and survival report</h1>",
        f"<p class='sub'>Monitoring round: {html.escape(label)} &middot; generated {date.today().isoformat()} &middot; synthetic demo data</p>",
        f"<div class='tiles'>{tiles}</div>",
        "<p class='note'>Survival rate = total surviving trees / total planted trees, "
        f"based on {int(overall['plots']):,} usable plots. Plots marked needs_review are excluded.</p>",
        "<h2>Issues by rule</h2>", _table(kpis.issues_by_rule(db_path)),
        "<h2>Plots needing review (send to field team)</h2>", _table(review),
        "<h2>Survival by block</h2>", _table(kpis.survival_by_block(db_path)),
        "<h2>Survival by irrigation source</h2>", _table(kpis.survival_by_irrigation(db_path)),
        f"<h2>Plots below {threshold}% survival</h2>",
        _table(kpis.low_survival_plots(db_path, threshold, limit=25)),
        f"<h2>Changes made by cleaning ({n_changes} recorded)</h2>",
        "<p>First 25 shown. The full list is in reports/audit_log.csv.</p>" if n_changes > 25 else "",
        _table(audit),
        "</body></html>",
    ]
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Generate an HTML QA report.")
    parser.add_argument("--round", default=date.today().isoformat(), help="label for the monitoring round")
    parser.add_argument("--threshold", type=float, default=80, help="low survival threshold (%%)")
    args = parser.parse_args()

    if not DB.exists():
        raise SystemExit("Database not found. Run  python -m src.run_pipeline  first.")

    OUT_DIR.mkdir(exist_ok=True)
    safe = args.round.replace(" ", "_").replace("/", "-")
    out = OUT_DIR / f"qa_report_{safe}.html"
    out.write_text(build_report(DB, args.round, args.threshold), encoding="utf-8")
    print(f"Report written to {out}")


if __name__ == "__main__":
    main()
