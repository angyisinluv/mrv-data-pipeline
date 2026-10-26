import sqlite3

import pandas as pd
import pytest

from src import kpis


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
    with sqlite3.connect(path) as conn:
        plots.to_sql("plots", conn, index=False)
        conn.execute("CREATE VIEW usable_plots AS SELECT * FROM plots WHERE status IN ('clean','warning')")
    return path


def test_overall_survival_excludes_needs_review(db):
    result = kpis.overall_kpis(db)
    assert result["plots"] == 2                     # plot C is needs_review
    assert result["survival_pct"] == 80.0           # (90 + 70) / 200


def test_block_filter(db):
    assert kpis.overall_kpis(db, "Block A")["plots"] == 2


def test_invalid_irrigation_grouped_as_unknown(db):
    names = kpis.survival_by_irrigation(db)["irrigation_source"].tolist()
    assert "Unknown" in names and "More" not in names


def test_low_survival_list(db):
    result = kpis.low_survival_plots(db, threshold_pct=80)
    assert result["farmer_id"].tolist() == ["B"]
