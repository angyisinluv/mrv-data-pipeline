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
