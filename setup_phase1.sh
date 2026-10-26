mkdir -p config src tests reports data/raw
touch src/__init__.py tests/__init__.py

cat > requirements.txt << 'EOF'
pandas
pyyaml
pytest
EOF

cat > .gitignore << 'EOF'
venv/
.venv/
__pycache__/
.pytest_cache/
.ipynb_checkpoints/
reports/*.csv
EOF

cat > config/column_mapping.yaml << 'EOF'
# Maps standard column names (left) to the column names in the survey export (right).
# For a new project or survey version, only this file needs to change.
project: demo_plantation
columns:
  timestamp: timestamp
  farmer_id: farmer_id
  block: block
  village: village
  gender: gender
  parcel_area_ha: parcel_area_ha
  planted_area_ha: planted_area_ha
  trees_planted: trees_planted
  trees_surviving: trees_surviving
  cashew_surviving: cashew_surviving
  mango_surviving: mango_surviving
  amla_surviving: amla_surviving
  neem_surviving: neem_surviving
  irrigation_source: irrigation_source
  irrigation_frequency: irrigation_frequency
  weeding_frequency: weeding_frequency
  fencing_complete: fencing_complete
  grazing_present: grazing_present
  ground_cover: ground_cover
EOF

cat > config/rules.yaml << 'EOF'
# Each rule has an id, a type, a severity (fail or warning) and a message.
# Rule types: compare, sum_equals, allowed_values, not_null, ratio_range, duplicate
rules:
  - id: planted_area_exceeds_parcel_area
    type: compare
    left: planted_area_ha
    operator: "<="
    right: parcel_area_ha
    severity: fail
    message: Planted area is larger than the land parcel area

  - id: surviving_exceeds_planted
    type: compare
    left: trees_surviving
    operator: "<="
    right: trees_planted
    severity: fail
    message: Surviving trees are more than trees originally planted

  - id: species_sum_mismatch
    type: sum_equals
    columns: [cashew_surviving, mango_surviving, amla_surviving, neem_surviving]
    total: trees_surviving
    severity: fail
    message: Species counts do not add up to total surviving trees

  - id: invalid_irrigation_category
    type: allowed_values
    column: irrigation_source
    values: [Pond, Water Tanker, Lift Irrigation from River, Canal, Stream, "Pond , Water Tanker"]
    severity: warning
    message: Irrigation source is not a valid category

  - id: missing_irrigation_source
    type: not_null
    columns: [irrigation_source]
    severity: warning
    message: Irrigation source is blank

  - id: incomplete_survey_row
    type: not_null
    columns: [irrigation_frequency, weeding_frequency, fencing_complete, grazing_present, ground_cover]
    severity: warning
    message: Survey row has blank answers (survey may have stopped partway)

  - id: implausible_tree_density
    type: ratio_range
    numerator: trees_planted
    denominator: planted_area_ha
    min: 300
    max: 500
    severity: warning
    message: Trees per hectare is outside the expected 300-500 range

  - id: inconsistent_gender_text
    type: allowed_values
    column: gender
    values: [Male, Female]
    severity: warning
    message: Gender text is not in the standard format (Male or Female)

  - id: duplicate_farmer_id
    type: duplicate
    column: farmer_id
    severity: fail
    message: Farmer ID appears more than once
EOF

cat > src/ingest.py << 'EOF'
"""Load a raw survey export and rename its columns to the standard names."""
import pandas as pd
import yaml


def load_mapping(mapping_path):
    with open(mapping_path) as f:
        return yaml.safe_load(f)


def load_survey(csv_path, mapping_path):
    """Read the CSV and return a DataFrame that uses the standard column names."""
    mapping = load_mapping(mapping_path)["columns"]       # standard -> source
    raw = pd.read_csv(csv_path)

    missing = [src for src in mapping.values() if src not in raw.columns]
    if missing:
        raise ValueError(f"Columns missing from the file: {missing}")

    reverse = {src: std for std, src in mapping.items()}  # source -> standard
    df = raw[list(reverse)].rename(columns=reverse)
    df.insert(0, "row_number", range(2, len(df) + 2))     # row number as seen in Excel (header is row 1)
    return df
EOF

cat > src/validate.py << 'EOF'
"""A small rule engine. Rules come from config/rules.yaml; this file knows how to run each type."""
import operator

import pandas as pd
import yaml

OPERATORS = {"<=": operator.le, "<": operator.lt, ">=": operator.ge, ">": operator.gt, "==": operator.eq}


def load_rules(rules_path):
    with open(rules_path) as f:
        return yaml.safe_load(f)["rules"]


# Each check returns a boolean Series: True means that row BREAKS the rule.

def check_compare(df, rule):
    ok = OPERATORS[rule["operator"]](df[rule["left"]], df[rule["right"]])
    return ~ok & df[rule["left"]].notna() & df[rule["right"]].notna()


def check_sum_equals(df, rule):
    return df[rule["columns"]].sum(axis=1) != df[rule["total"]]


def check_allowed_values(df, rule):
    col = df[rule["column"]]
    return col.notna() & ~col.isin(rule["values"])          # blanks are handled by not_null rules


def check_not_null(df, rule):
    return df[rule["columns"]].isna().any(axis=1)


def check_ratio_range(df, rule):
    ratio = df[rule["numerator"]] / df[rule["denominator"]]
    return (ratio < rule["min"]) | (ratio > rule["max"])


def check_duplicate(df, rule):
    return df.duplicated(subset=rule["column"], keep="first")   # the first submission is kept, later ones flagged


CHECKS = {
    "compare": check_compare,
    "sum_equals": check_sum_equals,
    "allowed_values": check_allowed_values,
    "not_null": check_not_null,
    "ratio_range": check_ratio_range,
    "duplicate": check_duplicate,
}


def run_rules(df, rules):
    """Apply every rule and return one row per problem found."""
    found = []
    for rule in rules:
        broken = CHECKS[rule["type"]](df, rule)
        hits = df.loc[broken, ["row_number", "farmer_id"]].copy()
        hits["rule_id"] = rule["id"]
        hits["severity"] = rule["severity"]
        hits["message"] = rule["message"]
        found.append(hits)
    return pd.concat(found, ignore_index=True)
EOF

cat > src/run_validation.py << 'EOF'
"""Run all rules on the dummy data, save the issue list, and compare with the answer key."""
import pandas as pd

from src.ingest import load_survey
from src.validate import load_rules, run_rules

DATA = "data/raw/plantation_monitoring_dummy.csv"
KEY = "data/raw/injected_issues_answer_key.csv"
MAPPING = "config/column_mapping.yaml"
RULES = "config/rules.yaml"
OUT = "reports/validation_issues.csv"


def main():
    df = load_survey(DATA, MAPPING)
    issues = run_rules(df, load_rules(RULES))
    issues.to_csv(OUT, index=False)

    print(f"Rows checked: {len(df)}")
    print(f"Issues found: {len(issues)}\n")
    print(issues["rule_id"].value_counts().to_string(), "\n")

    # Compare with the answer key (a pair is farmer_id + issue name)
    key = pd.read_csv(KEY)
    expected = set(zip(key["farmer_id"], key["issue"]))
    found = set(zip(issues["farmer_id"], issues["rule_id"]))

    caught = expected & found
    missed = expected - found
    extra = found - expected
    print(f"Planted problems caught: {len(caught)} of {len(expected)}")
    print(f"Planted problems missed: {len(missed)}")
    print(f"Extra flags (not in answer key): {len(extra)}")
    if extra:
        print(pd.Series([r for _, r in extra]).value_counts().to_string())


if __name__ == "__main__":
    main()
EOF

cat > tests/test_validate.py << 'EOF'
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
EOF
