import sqlite3

import pandas as pd
import pytest

from src import kpis


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    plots = pd.DataFrame({
        "row_number": [1, 2],
        "farmer_id": ["A", "B"],
        "block": ["Block A", "Block B"],
        "village": ["V1", "V2"],
        "status": ["needs_review", "warning"],
    })
    issues = pd.DataFrame({
        "row_number": [1, 2, 9],
        "farmer_id": ["A", "B", "Z"],
        "rule_id": ["surviving_exceeds_planted", "bad_irrigation", "duplicate_farmer"],
        "severity": ["fail", "warning", "fail"],
        "message": ["m1", "m2", "m3"],
    })
    with sqlite3.connect(path) as conn:
        plots.to_sql("plots", conn, index=False)
        issues.to_sql("issues", conn, index=False)
    return path


def test_issue_records_joins_block_and_village(db):
    df = kpis.issue_records(db)
    row = df[df["farmer_id"] == "A"].iloc[0]
    assert row["block"] == "Block A" and row["village"] == "V1"


def test_issue_for_removed_row_is_kept(db):
    df = kpis.issue_records(db)
    assert df[df["farmer_id"] == "Z"].iloc[0]["block"] == "n/a"


def test_fail_issues_listed_first(db):
    assert kpis.issue_records(db)["severity"].iloc[0] == "fail"
