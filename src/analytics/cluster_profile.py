import sqlite3
from pathlib import Path

import pandas as pd


CLUSTER_FILE = "output/cluster_labels.csv"
DB_PATH = Path("nifty100.db")

FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "operating_profit_margin_pct",
    "revenue_cagr",
    "fcf_cagr_5yr",
]

OUTLIER_FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "operating_profit_margin_pct",
    "revenue_cagr",
    "free_cash_flow_cr",
]

CLUSTER_NAMES = {
    0: "Balanced Compounders",
    1: "Extreme Growth Outlier",
    2: "Extreme ROE Leaders",
    3: "High-Leverage Growth",
    4: "High-Margin Quality",
}


def load_cluster_data():
    """Load company cluster assignments and financial features."""
    return pd.read_csv(CLUSTER_FILE)


def create_cluster_profile(df):
    """Calculate mean and median of five clustering features per cluster."""
    mean_profile = (
        df.groupby("cluster_id")[FEATURES]
        .mean()
        .round(2)
        .add_suffix("_mean")
    )

    median_profile = (
        df.groupby("cluster_id")[FEATURES]
        .median()
        .round(2)
        .add_suffix("_median")
    )

    profile = mean_profile.join(median_profile)

    profile["cluster_name"] = profile.index.map(CLUSTER_NAMES)

    return profile


def save_cluster_profile(profile):
    """Save cluster profiling statistics."""
    Path("output").mkdir(exist_ok=True)

    profile.to_csv(
        "output/cluster_profile.csv"
    )

    print("Saved: output/cluster_profile.csv")


def create_sector_outlier_report():
    """Flag companies with absolute sector Z-score greater than three."""

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        fr.company_id,
        fr.year,
        fr.return_on_equity_pct,
        fr.debt_to_equity,
        fr.operating_profit_margin_pct,
        fr.revenue_cagr,
        fr.free_cash_flow_cr,
        s.broad_sector
    FROM financial_ratios fr
    LEFT JOIN sectors s
        ON fr.company_id = s.company_id
    WHERE fr.year != 'TTM'
    """

    df = pd.read_sql_query(
        query,
        conn,
    )

    conn.close()

    if df.empty:
        print("No financial data available for outlier analysis.")
        return pd.DataFrame()

    # Convert year into sortable dates.
    df["date_order"] = pd.to_datetime(
        df["year"],
        errors="coerce",
    )

    # Keep latest available non-TTM record for each company.
    df = (
        df.sort_values(
            ["company_id", "date_order"]
        )
        .groupby("company_id")
        .tail(1)
        .copy()
    )

    outlier_rows = []

    for sector, sector_df in df.groupby(
        "broad_sector",
        dropna=False,
    ):
        for feature in OUTLIER_FEATURES:

            values = pd.to_numeric(
                sector_df[feature],
                errors="coerce",
            )

            mean = values.mean()
            std = values.std()

            # Cannot calculate a meaningful Z-score.
            if pd.isna(std) or std == 0:
                continue

            z_scores = (values - mean) / std

            for index, z_score in z_scores.items():

                if pd.isna(z_score):
                    continue

                if abs(z_score) > 3:

                    outlier_rows.append(
                        {
                            "company_id": sector_df.loc[
                                index,
                                "company_id",
                            ],
                            "broad_sector": sector,
                            "metric": feature,
                            "value": sector_df.loc[
                                index,
                                feature,
                            ],
                            "z_score": round(
                                float(z_score),
                                2,
                            ),
                        }
                    )

    outliers = pd.DataFrame(
        outlier_rows,
        columns=[
            "company_id",
            "broad_sector",
            "metric",
            "value",
            "z_score",
        ],
    )

    Path("output").mkdir(exist_ok=True)

    outliers.to_csv(
        "output/outlier_report.csv",
        index=False,
    )

    print("Saved: output/outlier_report.csv")
    print("Outlier rows:", len(outliers))

    return outliers


if __name__ == "__main__":

    df = load_cluster_data()

    profile = create_cluster_profile(df)

    print("Cluster Mean + Median Profile:")
    print(profile)

    save_cluster_profile(profile)

    create_sector_outlier_report()