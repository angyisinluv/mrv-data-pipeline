"""Apply safe automatic fixes and record every change in an audit log."""
import pandas as pd
import yaml

AUDIT_COLUMNS = ["row_number", "farmer_id", "column", "old_value", "new_value", "action", "reason"]


def load_cleaning_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def standardize_text(df, rules):
    """Fix text such as 'MALE' or 'female' using the mapping in cleaning.yaml."""
    df = df.copy()
    log = []
    for rule in rules:
        col = rule["column"]
        for idx, value in df[col].items():
            if pd.isna(value):
                continue
            new_value = rule["mapping"].get(str(value).strip().lower(), value)
            if new_value != value:
                log.append({
                    "row_number": df.at[idx, "row_number"], "farmer_id": df.at[idx, "farmer_id"],
                    "column": col, "old_value": value, "new_value": new_value,
                    "action": "value_standardized", "reason": f"Standard format for {col}",
                })
                df.at[idx, col] = new_value
    return df, log


def remove_duplicates(df, rule):
    """Drop repeated submissions, keeping the first one, and log each removed row."""
    col = rule["column"]
    is_dup = df.duplicated(subset=col, keep=rule["keep"])
    log = [{
        "row_number": row["row_number"], "farmer_id": row["farmer_id"], "column": col,
        "old_value": row[col], "new_value": "", "action": "row_removed",
        "reason": f"Duplicate {col}; {rule['keep']} submission kept",
    } for _, row in df[is_dup].iterrows()]
    return df[~is_dup].copy(), log


def clean(df, config):
    """Run all cleaning steps. Returns the cleaned data and the audit log."""
    log = []
    df, steps = standardize_text(df, config.get("standardize_text", []))
    log += steps
    df, steps = remove_duplicates(df, config["remove_duplicates"])
    log += steps
    return df.reset_index(drop=True), pd.DataFrame(log, columns=AUDIT_COLUMNS)


def add_status(df, issues):
    """Label each row: clean, warning (only warnings) or needs_review (at least one fail)."""
    fail_ids = set(issues.loc[issues["severity"] == "fail", "farmer_id"])
    warn_ids = set(issues.loc[issues["severity"] == "warning", "farmer_id"])
    df = df.copy()
    df["status"] = "clean"
    df.loc[df["farmer_id"].isin(warn_ids), "status"] = "warning"
    df.loc[df["farmer_id"].isin(fail_ids), "status"] = "needs_review"
    return df
