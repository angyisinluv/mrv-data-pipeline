import pandas as pd

from src.clean import add_status, remove_duplicates, standardize_text


def make_df():
    return pd.DataFrame({
        "row_number": [2, 3, 4],
        "farmer_id": ["A", "A", "B"],
        "gender": ["MALE", "Male", None],
    })


def test_standardize_text_fixes_case_and_logs_change():
    rules = [{"column": "gender", "mapping": {"male": "Male", "female": "Female"}}]
    df, log = standardize_text(make_df(), rules)
    assert df["gender"].tolist()[:2] == ["Male", "Male"]
    assert pd.isna(df["gender"].iloc[2])          # blanks stay blank
    assert len(log) == 1 and log[0]["old_value"] == "MALE" and log[0]["new_value"] == "Male"


def test_remove_duplicates_keeps_first_and_logs_removed_row():
    df, log = remove_duplicates(make_df(), {"column": "farmer_id", "keep": "first"})
    assert df["row_number"].tolist() == [2, 4]
    assert log[0]["row_number"] == 3 and log[0]["action"] == "row_removed"


def test_add_status():
    df = pd.DataFrame({"farmer_id": ["A", "B", "C"]})
    issues = pd.DataFrame({"farmer_id": ["A", "B"], "severity": ["fail", "warning"]})
    assert add_status(df, issues)["status"].tolist() == ["needs_review", "warning", "clean"]
