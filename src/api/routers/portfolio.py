import math
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import APIRouter

router = APIRouter(tags=["Portfolio"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


FEATURES = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "capex_cr",
    "earnings_per_share",
    "dividend_payout_ratio_pct",
]


def safe_value(value):
    if value is None:
        return None

    value = float(value)

    if not math.isfinite(value):
        return None

    return round(value, 2)


@router.get("/portfolio/stats")
def portfolio_stats():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            net_profit_margin_pct,
            operating_profit_margin_pct,
            return_on_equity_pct,
            debt_to_equity,
            interest_coverage,
            asset_turnover,
            free_cash_flow_cr,
            capex_cr,
            earnings_per_share,
            dividend_payout_ratio_pct
        FROM financial_ratios
        """,
        conn,
    )

    conn.close()

    if df.empty:
        return {}

    # Convert all KPI columns to numeric
    for column in FEATURES:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # TTM should be considered the newest period.
    # Historical years are ordered newest -> oldest.
    df["date_order"] = pd.to_datetime(
        df["year"].replace({"TTM": None}), errors="coerce"
    )

    df["ttm_order"] = df["year"].eq("TTM").astype(int)

    df = df.sort_values(
        ["company_id", "ttm_order", "date_order"], ascending=[True, False, False]
    )

    # For every company and every KPI:
    # take the newest non-null value available.
    latest_values = {}

    for company_id, group in df.groupby("company_id"):

        company_values = {}

        for column in FEATURES:

            values = group[column].dropna()

            if values.empty:
                company_values[column] = None
            else:
                company_values[column] = values.iloc[0]

        latest_values[company_id] = company_values

    latest_df = pd.DataFrame.from_dict(latest_values, orient="index")

    result = {}

    for column in FEATURES:

        values = pd.to_numeric(latest_df[column], errors="coerce").dropna()

        if values.empty:
            result[column] = {
                "P10": None,
                "P25": None,
                "P50": None,
                "P75": None,
                "P90": None,
                "Mean": None,
                "Std": None,
            }

            continue

        result[column] = {
            "P10": safe_value(values.quantile(0.10)),
            "P25": safe_value(values.quantile(0.25)),
            "P50": safe_value(values.quantile(0.50)),
            "P75": safe_value(values.quantile(0.75)),
            "P90": safe_value(values.quantile(0.90)),
            "Mean": safe_value(values.mean()),
            "Std": safe_value(values.std()),
        }
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    stats_rows = []

    for metric, stats in result.items():
        stats_rows.append(
            {
                "metric": metric,
                "P10": stats["P10"],
                "P25": stats["P25"],
                "P50": stats["P50"],
                "P75": stats["P75"],
                "P90": stats["P90"],
                "Mean": stats["Mean"],
                "Std": stats["Std"],
            }
        )

    pd.DataFrame(stats_rows).to_csv(output_dir / "portfolio_stats.csv", index=False)

    return result
