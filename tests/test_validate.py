import pandas as pd

from src.validate import run_rules


def make_df(**cols):
    df = pd.DataFrame(cols)
    df.insert(0, "row_number", range(2, len(df) + 2))
    df["farmer_id"] = [f"F{i}" for i in range(len(df))] if "farmer_id" not in df else df["farmer_id"]
    return df


def test_planted_area_exceeds_parcel_area():
    df = make_df(planted_area_ha=[1.0, 2.0], parcel_area_ha=[1.5, 1.0])
    rule = {"id": "r", "type": "compare", "left": "planted_area_ha", "operator": "<=",
            "right": "parcel_area_ha", "severity": "fail", "message": "m"}
    result = run_rules(df, [rule])
    assert result["farmer_id"].tolist() == ["F1"]          # only the second row breaks the rule


def test_species_sum_mismatch():
    df = make_df(a=[5, 5], b=[5, 4], total=[10, 10])
    rule = {"id": "r", "type": "sum_equals", "columns": ["a", "b"], "total": "total",
            "severity": "fail", "message": "m"}
    assert run_rules(df, [rule])["farmer_id"].tolist() == ["F1"]


def test_allowed_values_ignores_blanks():
    df = make_df(src=["Pond", "More", None])
    rule = {"id": "r", "type": "allowed_values", "column": "src", "values": ["Pond"],
            "severity": "warning", "message": "m"}
    assert run_rules(df, [rule])["farmer_id"].tolist() == ["F1"]   # None is not flagged here


def test_not_null_flags_blank_rows():
    df = make_df(a=[1, None], b=[1, 1])
    rule = {"id": "r", "type": "not_null", "columns": ["a", "b"], "severity": "warning", "message": "m"}
    assert run_rules(df, [rule])["farmer_id"].tolist() == ["F1"]


def test_density_range():
    df = make_df(trees=[400, 100, 900], area=[1.0, 1.0, 1.0])
    rule = {"id": "r", "type": "ratio_range", "numerator": "trees", "denominator": "area",
            "min": 300, "max": 500, "severity": "warning", "message": "m"}
    assert run_rules(df, [rule])["farmer_id"].tolist() == ["F1", "F2"]


def test_duplicate_keeps_first_submission():
    df = make_df(farmer_id=["A", "A", "B"])
    rule = {"id": "r", "type": "duplicate", "column": "farmer_id", "severity": "fail", "message": "m"}
    result = run_rules(df, [rule])
    assert result["row_number"].tolist() == [3]            # second "A" row only
