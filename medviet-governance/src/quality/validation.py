from pathlib import Path

import pandas as pd

try:
    from great_expectations.dataset import PandasDataset
except ImportError:
    PandasDataset = None  # type: ignore[misc, assignment]

from great_expectations.core.expectation_suite import ExpectationSuite


def build_patient_expectation_suite() -> ExpectationSuite:
    if PandasDataset is None:
        raise ImportError(
            "Great Expectations PandasDataset is unavailable in this version."
        )

    df = pd.read_csv("data/raw/patients_raw.csv")
    dataset = PandasDataset(df)

    dataset.expect_column_values_to_not_be_null("patient_id")

    dataset.expect_column_value_lengths_to_equal(column="cccd", value=12)

    dataset.expect_column_values_to_be_between(
        column="ket_qua_xet_nghiem",
        min_value=0,
        max_value=50,
    )

    valid_conditions = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
    dataset.expect_column_values_to_be_in_set(
        column="benh",
        value_set=valid_conditions,
    )

    dataset.expect_column_values_to_match_regex(
        column="email",
        regex=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )

    dataset.expect_column_values_to_be_unique(column="patient_id")

    return dataset.get_expectation_suite()


def validate_anonymized_data(filepath: str, raw_filepath: str | None = None) -> dict:
    df = pd.read_csv(filepath)
    raw_path = Path(raw_filepath or "data/raw/patients_raw.csv")
    raw_df = pd.read_csv(raw_path) if raw_path.is_file() else None

    results: dict = {
        "success": True,
        "failed_checks": [],
        "stats": {"total_rows": len(df), "columns": list(df.columns)},
    }

    if raw_df is not None and "patient_id" in df.columns and "cccd" in df.columns:
        merged = df[["patient_id", "cccd"]].merge(
            raw_df[["patient_id", "cccd"]],
            on="patient_id",
            suffixes=("_anon", "_raw"),
        )
        leaked = merged[merged["cccd_anon"] == merged["cccd_raw"]]
        if not leaked.empty:
            results["success"] = False
            results["failed_checks"].append(
                "cccd values unchanged from raw for at least one patient_id"
            )

    important = [
        c
        for c in ("patient_id", "ho_ten", "cccd", "email")
        if c in df.columns
    ]
    for col in important:
        if df[col].isna().any():
            results["success"] = False
            results["failed_checks"].append(f"null values found in {col}")

    if raw_df is not None:
        if len(df) != len(raw_df):
            results["success"] = False
            results["failed_checks"].append("row count mismatch vs raw dataset")

    return results
