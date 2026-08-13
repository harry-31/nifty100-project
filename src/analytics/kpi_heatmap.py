import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DB_PATH = Path("nifty100.db")

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


def create_kpi_correlation_heatmap():
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

    for column in FEATURES:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # Use newest available non-null value for each company.
    df["date_order"] = pd.to_datetime(
        df["year"].replace({"TTM": None}),
        errors="coerce",
    )

    df["ttm_order"] = df["year"].eq("TTM").astype(int)

    df = df.sort_values(
        ["company_id", "ttm_order", "date_order"],
        ascending=[True, False, False],
    )

    latest = df.groupby("company_id").first()

    correlation = latest[FEATURES].corr(method="pearson")

    print("10-KPI Pearson Correlation Matrix:")
    print(correlation.round(2).to_string())

    Path("reports").mkdir(exist_ok=True)

    plt.figure(figsize=(12, 10))

    plt.imshow(
        correlation,
        aspect="auto",
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
    )

    plt.colorbar(label="Pearson Correlation")

    plt.xticks(
        range(len(FEATURES)),
        FEATURES,
        rotation=45,
        ha="right",
    )

    plt.yticks(
        range(len(FEATURES)),
        FEATURES,
    )

    plt.title("Nifty100 Financial KPI Pearson Correlation Heatmap")

    plt.tight_layout()

    output = "reports/kpi_correlation_heatmap.png"

    plt.savefig(
        output,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    print(f"Saved: {output}")


if __name__ == "__main__":
    create_kpi_correlation_heatmap()
