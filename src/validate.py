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
