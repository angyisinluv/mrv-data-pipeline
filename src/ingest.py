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
