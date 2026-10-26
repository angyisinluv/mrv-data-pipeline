# MRV Data Pipeline

A configurable Python pipeline that validates plantation monitoring survey data before it is used for Measurement, Reporting and Verification (MRV) work.

> **Data note:** all data in this repository is synthetic. It is generated randomly to imitate the structure of a tree-plantation monitoring survey. It contains no real farmers, villages, projects or coordinates.

## Problem

Monitoring survey exports usually arrive with errors: planted area larger than the land parcel, more surviving trees than planted, species counts that do not add up, duplicate farmers, incomplete rows. Checking these by hand each monitoring round is slow, and different people check different things.

## What this does (Phase 1)

- Loads a survey export and maps its column names to a standard format (`config/column_mapping.yaml`)
- Runs a set of validation rules defined in plain text (`config/rules.yaml`), so a rule can be added or changed without touching the code
- Produces a list of every problem found, with row number, farmer ID, rule, severity (fail or warning) and message
- Checks itself against an answer key of problems planted in the dummy data

## Results on the dummy dataset

| Measure | Result |
|---|---|
| Rows checked | 506 |
| Rules | 9 (6 rule types) |
| Problems planted on purpose | 107 |
| Planted problems caught | 107 of 107 |
| Planted problems missed | 0 |
| Extra flags | 18 |
| Unit tests | 6 passing |

The 18 extra flags are all `implausible_tree_density`. They are rows where the planted area was inflated, so trees per hectare looks too low. One data error legitimately triggers two checks.

## Rule types

| Type | Checks |
|---|---|
| `compare` | One column against another (planted area must not exceed parcel area) |
| `sum_equals` | Columns must add up to a total (species counts equal total surviving) |
| `allowed_values` | Values must come from a list (irrigation source, gender format) |
| `not_null` | Required answers must not be blank |
| `ratio_range` | A ratio must fall in a range (trees per hectare) |
| `duplicate` | A value must not repeat (farmer ID) |

Example rule:

```yaml
- id: surviving_exceeds_planted
  type: compare
  left: trees_surviving
  operator: "<="
  right: trees_planted
  severity: fail
  message: Surviving trees are more than trees originally planted
```

## Project structure

```
mrv-data-pipeline/
├── config/
│   ├── column_mapping.yaml    standard column names for each survey export
│   └── rules.yaml             validation rules
├── src/
│   ├── ingest.py              load CSV and rename columns
│   ├── validate.py            rule engine
│   └── run_validation.py      run all rules and compare with the answer key
├── tests/
│   └── test_validate.py
├── data/raw/                  synthetic data and answer key
└── reports/                   generated issue list
```

## How to run

```bash
git clone https://github.com/angyisinluv/mrv-data-pipeline.git
cd mrv-data-pipeline
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python -m src.run_validation
python -m pytest -q
```

The issue list is saved to `reports/validation_issues.csv`.

## Roadmap

- [x] Phase 1: configurable rule engine with tests
- [x] Phase 2: cleaning with an audit trail, and loading into a SQLite database
- [ ] Phase 3: survival KPIs by block, species and irrigation, plus a dashboard
- [ ] Phase 4: automated QA report for each monitoring round
- [ ] Phase 5 (optional): model to flag plots at risk of low survival

## Tech stack

Python, pandas, PyYAML, pytest

## Author

Angyllyn Gurung
