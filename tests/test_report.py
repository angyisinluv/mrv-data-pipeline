import sqlite3

import pandas as pd
import pytest

from src import make_report


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    plots = pd.DataFrame({
        "farmer_id": ["A", "B", "C"],
        "block": ["Block A", "Block A", "Block B"],
        "village": ["V1", "V2", "V3"],
        "planted_area_ha": [1.0, 1.0, 1.0],
        "trees_planted": [100, 100, 100],
        "trees_surviving": [90, 70, 100],
        "cashew_surviving": [50, 40, 60], "mango_surviving": [20, 10, 20],
        "amla_surviving": [10, 10, 10], "neem_surviving": [10, 10, 10],
        "irrigation_source": ["Pond", "More", "Pond"],
        "status": ["clean", "warning", "needs_review"],
    })
    issues = pd.DataFrame({
        "farmer_id": ["C"], "rule_id": ["surviving_exceeds_planted"], "severity": ["fail"],
    })
    with sqlite3.connect(path) as conn:
        plots.to_sql("plots", conn, index=False)
        issues.to_sql("issues", conn, index=False)
        conn.execute("CREATE VIEW usable_plots AS SELECT * FROM plots WHERE status IN ('clean','warning')")
    return path


def test_report_contains_headline_numbers(db):
    report = make_report.build_report(db, "Test round")
    assert "Test round" in report
    assert "80.0%" in report            # (90 + 70) / 200


def test_review_plot_listed_with_reason(db):
    report = make_report.build_report(db, "Test round")
    assert "surviving_exceeds_planted" in report
    assert ">C<" in report              # farmer C appears in the review table


def test_report_works_without_audit_log(db):
    assert "recorded" in make_report.build_report(db, "Test round")
