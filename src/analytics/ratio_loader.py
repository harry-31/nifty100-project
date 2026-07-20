import sqlite3
import pandas as pd
import os

from ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    debt_to_equity,
    interest_coverage_ratio,
    asset_turnover,
)

from cashflow_kpis import (
    free_cash_flow,
)

from cagr import (
    revenue_cagr,
    pat_cagr,
    eps_cagr,
)

DB_PATH = "nifty100.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def load_table(table_name):
    conn = get_connection()

    df = pd.read_sql_query(
        f"SELECT * FROM {table_name}",
        conn
    )

    conn.close()

    return df


def remove_duplicates(df):
    return df.drop_duplicates(
        subset=["company_id", "year"],
        keep="first"
    )


def load_clean_data():

    pnl = remove_duplicates(
        load_table("profitandloss")
    )

    bs = remove_duplicates(
        load_table("balancesheet")
    )

    cf = remove_duplicates(
        load_table("cashflow")
    )

    return pnl, bs, cf


def merge_data():

    pnl, bs, cf = load_clean_data()

    merged = pnl.merge(
        bs,
        on=["company_id", "year"],
        how="left"
    )

    merged = merged.merge(
        cf,
        on=["company_id", "year"],
        how="left"
    )

    return merged


def build_ratio_dataframe():

    merged = merge_data()
    merged = merged.sort_values(["company_id", "year"])

    records = []

    for _, row in merged.iterrows():

        record = {

            "company_id": row["company_id"],

            "year": row["year"],

            "net_profit_margin_pct":
                net_profit_margin(
                    row["net_profit"],
                    row["sales"],
                ),

            "operating_profit_margin_pct":
                operating_profit_margin(
                    row["operating_profit"],
                    row["sales"],
                ),

            "return_on_equity_pct":
                return_on_equity(
                    row["net_profit"],
                    row["equity_capital"],
                    row["reserves"],
                ),

            "debt_to_equity":
                debt_to_equity(
                    row["borrowings"],
                    row["equity_capital"],
                    row["reserves"],
                ),

            "interest_coverage":
                interest_coverage_ratio(
                    row["operating_profit"],
                    row["other_income"],
                    row["interest"],
                ),

            "asset_turnover":
                asset_turnover(
                    row["sales"],
                    row["total_assets"],
                ),

            "free_cash_flow_cr":
                free_cash_flow(
                    row["operating_activity"],
                    abs(row["investing_activity"]),
                ),
                "capex_cr":
    abs(row["investing_activity"]),

"earnings_per_share":
    row["eps"],

"dividend_payout_ratio_pct":
    row["dividend_payout"],

"total_debt_cr":
    row["borrowings"],

"cash_from_operations_cr":
    row["operating_activity"],
        }

        records.append(record)

    ratio_df = pd.DataFrame(records)

    ratio_df["revenue_cagr"] = None
    ratio_df["pat_cagr"] = None
    ratio_df["eps_cagr"] = None

    for company, group in merged.groupby("company_id"):

        group = group.sort_values("year")

        if len(group) < 2:
            continue

        start = group.iloc[0]
        end = group.iloc[-1]

        years = len(group) - 1

        rev, _ = revenue_cagr(
            start["sales"],
            end["sales"],
            years,
        )

        pat, _ = pat_cagr(
            start["net_profit"],
            end["net_profit"],
            years,
        )

        eps, _ = eps_cagr(
            start["eps"],
            end["eps"],
            years,
        )

        ratio_df.loc[
            ratio_df.company_id == company,
            "revenue_cagr"
        ] = rev

        ratio_df.loc[
            ratio_df.company_id == company,
            "pat_cagr"
        ] = pat

        ratio_df.loc[
            ratio_df.company_id == company,
            "eps_cagr"
        ] = eps

    return ratio_df


def save_to_database(df):

    conn = get_connection()

    df.to_sql(
        "financial_ratios",
        conn,
        if_exists="replace",
        index=False,
    )

    conn.close()
def generate_edge_case_log(df):

    os.makedirs("output", exist_ok=True)

    with open("output/ratio_edge_cases.log", "w") as f:

        f.write("========== RATIO EDGE CASE REPORT ==========\n\n")

        # Negative / Zero Equity
        neg_equity = df[df["return_on_equity_pct"].isna()]
        f.write(f"ROE not computed (negative/zero equity): {len(neg_equity)} rows\n")

        # Interest = 0
        no_interest = df[df["interest_coverage"].isna()]
        f.write(f"Interest Coverage unavailable (interest = 0): {len(no_interest)} rows\n")

        # Debt Free
        debt_free = df[df["debt_to_equity"] == 0]
        f.write(f"Debt Free companies: {len(debt_free)} rows\n")

        # Missing Asset Turnover
        asset_missing = df[df["asset_turnover"].isna()]
        f.write(f"Asset Turnover unavailable: {len(asset_missing)} rows\n")

        # Missing CAGR
        rev_missing = df[df["revenue_cagr"].isna()]
        pat_missing = df[df["pat_cagr"].isna()]
        eps_missing = df[df["eps_cagr"].isna()]

        f.write(f"Revenue CAGR unavailable: {len(rev_missing)} rows\n")
        f.write(f"PAT CAGR unavailable: {len(pat_missing)} rows\n")
        f.write(f"EPS CAGR unavailable: {len(eps_missing)} rows\n")

        f.write("\nReview Category:\n")
        f.write("- Data source issue\n")
        f.write("- Version difference\n")
        f.write("- Formula discrepancy\n")

    print("ratio_edge_cases.log generated.")
    print("financial_ratios table updated successfully.")


if __name__ == "__main__":

    ratio_df = build_ratio_dataframe()

    print(ratio_df.head())

    print()

    print(ratio_df.info())

    save_to_database(ratio_df)
    
    generate_edge_case_log(ratio_df)
    
    
