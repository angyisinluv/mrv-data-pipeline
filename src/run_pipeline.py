"""Full pipeline: load -> validate -> clean -> re-validate -> label -> save files and database."""
import os

from src.clean import add_status, clean, load_cleaning_config
from src.ingest import load_survey
from src.load_db import write_db
from src.validate import load_rules, run_rules

DATA = "data/raw/plantation_monitoring_dummy.csv"
MAPPING = "config/column_mapping.yaml"
RULES = "config/rules.yaml"
CLEANING = "config/cleaning.yaml"
DB = "data/mrv.db"


def main():
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    raw = load_survey(DATA, MAPPING)
    rules = load_rules(RULES)

    issues_before = run_rules(raw, rules)
    cleaned, audit = clean(raw, load_cleaning_config(CLEANING))
    issues_after = run_rules(cleaned, rules)
    plots = add_status(cleaned, issues_after)

    plots.to_csv("data/processed/plantation_clean.csv", index=False)
    audit.to_csv("reports/audit_log.csv", index=False)
    issues_after.to_csv("reports/validation_issues.csv", index=False)
    write_db(DB, {"plots": plots, "issues": issues_after, "audit_log": audit})

    print(f"Rows in: {len(raw)} | rows out: {len(plots)}")
    print(f"Issues before cleaning: {len(issues_before)} | after: {len(issues_after)}")
    print(f"Changes recorded in audit log: {len(audit)}")
    print("\nRow status:")
    print(plots["status"].value_counts().to_string())
    print(f"\nDatabase written to {DB}")


if __name__ == "__main__":
    main()
