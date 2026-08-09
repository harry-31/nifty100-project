import re
import sqlite3
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "analysis.xlsx"
DB_FILE = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

PARSED_FILE = OUTPUT_DIR / "analysis_parsed.csv"
FAILURE_FILE = OUTPUT_DIR / "parse_failures.csv"
DIVERGENCE_FILE = OUTPUT_DIR / "cagr_divergence_review.csv"


# --------------------------------------------------
# Configuration
# --------------------------------------------------

TARGET_FIELDS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]

PATTERN = re.compile(
    r"(\d+)\s*Years?:?\s*(-?[\d.]+)%",
    re.IGNORECASE,
)

CAGR_METRIC_MAP = {
    "compounded_sales_growth": "sales",
    "compounded_profit_growth": "net_profit",
}


# --------------------------------------------------
# Parser
# --------------------------------------------------

def parse_metric(text):
    """
    Parse values such as:

        10 Years: 21%
        5 Years: 24%
        3 Years 14%
        1 Year: -2%

    Returns:
        (period_years, value_pct)

    Returns None when text does not match.
    """

    if pd.isna(text):
        return None

    text = str(text).strip()

    match = PATTERN.search(text)

    if not match:
        return None

    period_years = int(match.group(1))
    value_pct = float(match.group(2))

    return period_years, value_pct


# --------------------------------------------------
# CAGR calculation
# Same rules as src/analytics/cagr.py
# --------------------------------------------------

def calculate_cagr(start_value, end_value, years):

    if years <= 0:
        return None

    if start_value == 0:
        return None

    if start_value > 0 and end_value > 0:
        cagr = (
            (end_value / start_value) ** (1 / years) - 1
        ) * 100

        return round(cagr, 2)

    # Same invalid cases handled by Ratio Engine:
    # decline to loss, turnaround, both negative, etc.
    return None


# --------------------------------------------------
# Ratio Engine cross-validation
# --------------------------------------------------

def load_financial_history():

    connection = sqlite3.connect(DB_FILE)

    query = """
        SELECT
            company_id,
            year,
            sales,
            net_profit
        FROM profitandloss
        ORDER BY company_id, year
    """

    financial_df = pd.read_sql_query(
        query,
        connection,
    )

    connection.close()

    return financial_df


def compute_period_cagr(
    financial_df,
    company_id,
    metric_column,
    period_years,
):
    """
    Recompute CAGR for the same period requested by
    analysis.xlsx using the Ratio Engine CAGR formula.

    Example:
        period_years = 5

    Uses the latest observation and the observation
    5 periods before it.
    """

    company_data = financial_df[
        financial_df["company_id"] == company_id
    ].copy()

    company_data = company_data.sort_values("year")

    company_data = company_data.dropna(
        subset=[metric_column]
    )

    required_rows = period_years + 1

    if len(company_data) < required_rows:
        return None

    # Latest N+1 observations
    period_data = company_data.tail(required_rows)

    start_value = period_data.iloc[0][metric_column]
    end_value = period_data.iloc[-1][metric_column]

    return calculate_cagr(
        start_value,
        end_value,
        period_years,
    )


def cross_validate_cagr(parsed_df):

    financial_df = load_financial_history()

    review_rows = []

    # Validation columns
    parsed_df["computed_cagr_pct"] = pd.NA
    parsed_df["divergence_pct"] = pd.NA
    parsed_df["manual_review"] = False

    for index, row in parsed_df.iterrows():

        metric_type = row["metric_type"]

        # Only CAGR fields are cross-validated
        if metric_type not in CAGR_METRIC_MAP:
            continue

        metric_column = CAGR_METRIC_MAP[metric_type]

        computed_cagr = compute_period_cagr(
            financial_df=financial_df,
            company_id=row["company_id"],
            metric_column=metric_column,
            period_years=int(row["period_years"]),
        )

        if computed_cagr is None:
            continue

        parsed_value = float(row["value_pct"])

        divergence = abs(
            parsed_value - computed_cagr
        )

        parsed_df.at[
            index,
            "computed_cagr_pct"
        ] = computed_cagr

        parsed_df.at[
            index,
            "divergence_pct"
        ] = round(divergence, 2)

        # Requirement:
        # flag divergence greater than 5%
        if divergence > 5:

            parsed_df.at[
                index,
                "manual_review"
            ] = True

            review_rows.append(
                {
                    "company_id": row["company_id"],
                    "metric_type": metric_type,
                    "period_years": row["period_years"],
                    "parsed_value_pct": parsed_value,
                    "computed_cagr_pct": computed_cagr,
                    "divergence_pct": round(
                        divergence,
                        2,
                    ),
                }
            )

    review_df = pd.DataFrame(
        review_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "parsed_value_pct",
            "computed_cagr_pct",
            "divergence_pct",
        ],
    )

    return parsed_df, review_df


# --------------------------------------------------
# Main processing
# --------------------------------------------------

def main():

    print("Reading analysis.xlsx...")

    # First row is banner/title.
    # Actual headers are on second row.
    df = pd.read_excel(
        INPUT_FILE,
        header=1,
    )

    print(f"Rows loaded: {len(df)}")

    required_columns = [
        "company_id",
        *TARGET_FIELDS,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    parsed_rows = []
    failure_rows = []

    # --------------------------------------------------
    # Parse analysis text
    # --------------------------------------------------

    for _, row in df.iterrows():

        company_id = row["company_id"]

        for metric_type in TARGET_FIELDS:

            raw_text = row[metric_type]

            result = parse_metric(raw_text)

            if result is None:

                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "raw_text": raw_text,
                    }
                )

                continue

            period_years, value_pct = result

            parsed_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ],
    )

    failures_df = pd.DataFrame(
        failure_rows,
        columns=[
            "company_id",
            "metric_type",
            "raw_text",
        ],
    )

    # --------------------------------------------------
    # Cross-validation
    # --------------------------------------------------

    print("Cross-validating CAGR values...")

    parsed_df, divergence_df = (
        cross_validate_cagr(parsed_df)
    )

    # --------------------------------------------------
    # Save outputs
    # --------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    parsed_df[
    [
        "company_id",
        "metric_type",
        "period_years",
        "value_pct",
    ]
].to_csv(
    PARSED_FILE,
    index=False,
)

    failures_df.to_csv(
        FAILURE_FILE,
        index=False,
    )

    divergence_df.to_csv(
        DIVERGENCE_FILE,
        index=False,
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    total_entries = (
        len(df) * len(TARGET_FIELDS)
    )

    parsed_count = len(parsed_df)
    failure_count = len(failures_df)

    validated_count = (
        parsed_df["computed_cagr_pct"]
        .notna()
        .sum()
    )

    review_count = len(divergence_df)

    print("\n--------------------------------")
    print("NLP Analysis Parser Complete")
    print("--------------------------------")

    print(f"Total entries       : {total_entries}")
    print(f"Parsed              : {parsed_count}")
    print(f"Failures            : {failure_count}")
    print(f"CAGR validated      : {validated_count}")
    print(f"Manual review flags : {review_count}")

    print(f"\nParsed output : {PARSED_FILE}")
    print(f"Failure log   : {FAILURE_FILE}")
    print(f"Review file   : {DIVERGENCE_FILE}")


if __name__ == "__main__":
    main()