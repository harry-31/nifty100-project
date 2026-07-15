import pandas as pd


# ---------------- DQ-01 ----------------
# Primary Key Uniqueness
def validate_primary_key(df, key):
    return df[df.duplicated(subset=[key], keep=False)]


# ---------------- DQ-02 ----------------
# (company_id, year) uniqueness
def validate_company_year(df):
    return (
        df.groupby(["company_id", "year"])
        .size()
        .reset_index(name="count")
        .query("count > 1")
    )


# ---------------- DQ-03 ----------------
# Foreign Key Integrity
def validate_foreign_key(child_df, parent_df):
    valid_ids = set(parent_df["id"])
    return child_df[~child_df["company_id"].isin(valid_ids)]


# ---------------- DQ-04 ----------------
# Balance Sheet Check
def validate_balance_sheet(df):
    required = [
        "total_liabilities",
        "total_assets"
    ]

    if not all(col in df.columns for col in required):
        return pd.DataFrame()

    return df[
        (df["total_assets"] - df["total_liabilities"]).abs()
        > (0.01 * df["total_assets"])
    ]


# ---------------- DQ-05 ----------------
# OPM Cross Check
def validate_opm(df):
    required = [
        "sales",
        "operating_profit",
        "opm_percentage"
    ]

    if not all(col in df.columns for col in required):
        return pd.DataFrame()

    calc = (df["operating_profit"] / df["sales"]) * 100

    return df[
        (calc - df["opm_percentage"]).abs() > 1
    ]


# ---------------- DQ-06 ----------------
# Positive Sales
def validate_positive_sales(df):
    if "sales" not in df.columns:
        return pd.DataFrame()

    return df[df["sales"] <= 0]