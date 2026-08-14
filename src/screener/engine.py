import sqlite3
from pathlib import Path

import pandas as pd
import yaml

DB_PATH = Path(__file__).resolve().parents[2] / "nifty100.db"
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "screener_config.yaml"


def get_connection():
    """Get a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def load_financial_ratios():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
    conn.close()
    return df


def load_config():
    """Load screener configuration from YAML."""
    with open(CONFIG_PATH, "r") as file:
        return yaml.safe_load(file)


def apply_filters(filters):
    """
    Apply dynamic filters to the latest non-TTM financial ratios for each company.
    """
    df = load_complete_data()

    # Exclude TTM and keep the latest annual record for each company
    df = df[df["year"].astype(str).str.upper() != "TTM"].copy()
    df["sort_year"] = pd.to_numeric(
        df["year"].astype(str).str[:4],
        errors="coerce",
    )

    df = (
        df.sort_values("sort_year")
        .groupby("company_id", as_index=False)
        .last()
        .drop(columns="sort_year")
    )

    if "roe_min" in filters:
        df = df[df["return_on_equity_pct"] >= filters["roe_min"]]

    if "debt_to_equity_max" in filters:
        df = df[df["debt_to_equity"] <= filters["debt_to_equity_max"]]

    if "free_cash_flow_min" in filters:
        df = df[df["free_cash_flow_cr"] >= filters["free_cash_flow_min"]]

    if "revenue_cagr_min" in filters:
        df = df[df["revenue_cagr"] >= filters["revenue_cagr_min"]]

    if "pat_cagr_min" in filters:
        df = df[df["pat_cagr"] >= filters["pat_cagr_min"]]

    if "eps_cagr_min" in filters:
        df = df[df["eps_cagr"] >= filters["eps_cagr_min"]]

    if "asset_turnover_min" in filters:
        df = df[df["asset_turnover"] >= filters["asset_turnover_min"]]

    if "interest_coverage_min" in filters:
        df = df[df["interest_coverage"] >= filters["interest_coverage_min"]]

    if "operating_profit_margin_min" in filters:
        df = df[
            df["operating_profit_margin_pct"] >= filters["operating_profit_margin_min"]
        ]

    if "net_profit_margin_min" in filters:
        df = df[df["net_profit_margin_pct"] >= filters["net_profit_margin_min"]]

    if "pe_max" in filters:
        df = df[df["pe_ratio"] <= filters["pe_max"]]

    if "pb_max" in filters:
        df = df[df["pb_ratio"] <= filters["pb_max"]]

    if "dividend_yield_min" in filters:
        df = df[df["dividend_yield_pct"] >= filters["dividend_yield_min"]]

    return df

    return df


def quality_compounder():
    filters = load_config()["quality_compounder"]
    return apply_filters(filters)


def growth_accelerator():
    """
    Filter companies matching the Growth Accelerator criteria.
    """
    filters = load_config()["growth_accelerator"]
    return apply_filters(filters)


def debt_free_bluechip():
    """
    Filter companies with no debt and strong profitability.
    """
    filters = load_config()["debt_free_bluechip"]
    return apply_filters(filters)


def value_pick():
    """
    Filter companies matching the Value Pick criteria.
    """
    filters = load_config()["value_pick"]
    return apply_filters(filters)


def dividend_champion():
    """
    Filter companies with high dividend yield,
    healthy ROE and positive free cash flow.
    """
    filters = load_config()["dividend_champion"]
    return apply_filters(filters)


def turnaround_watch():
    """
    Companies showing improving growth with positive cash flow.
    """
    filters = load_config()["turnaround_watch"]
    return apply_filters(filters)


def composite_quality_score():
    """
    Calculate a composite quality score for each company-year.
    """
    df = load_financial_ratios().copy()

    df["quality_score"] = (
        df["return_on_equity_pct"] * 0.30
        + df["operating_profit_margin_pct"] * 0.20
        + df["revenue_cagr"] * 0.20
        + df["pat_cagr"] * 0.20
        + df["interest_coverage"] * 0.10
    )

    return df.sort_values("quality_score", ascending=False)


def export_quality_scores(filename="output/screener_output.xlsx"):
    """
    Export composite quality scores to an Excel file.
    """
    from pathlib import Path

    df = composite_quality_score()

    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(output_path, index=False)


def load_complete_data():
    """
    Load all metrics required for the screener by joining
    financial_ratios, companies and market_cap.
    """
    import sqlite3

    import pandas as pd

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        fr.*,

        c.company_name,
        c.roce_percentage,

        mc.market_cap_crore,
        mc.pe_ratio,
        mc.pb_ratio,
        mc.dividend_yield_pct

    FROM financial_ratios fr

    LEFT JOIN companies c
        ON fr.company_id = c.id

    LEFT JOIN market_cap mc
        ON fr.company_id = mc.company_id
       AND CAST(SUBSTR(fr.year, 1, 4) AS INTEGER) = mc.year
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


def normalize(series, reverse=False):
    """
    Normalize a pandas Series to a 0â€“100 score using
    10th and 90th percentile winsorization.
    """
    s = series.fillna(series.median())

    p10 = s.quantile(0.10)
    p90 = s.quantile(0.90)

    s = s.clip(lower=p10, upper=p90)

    score = (s - p10) / (p90 - p10) * 100

    if reverse:
        score = 100 - score

    return score.clip(0, 100)


def calculate_composite_score():
    """
    Calculate composite quality score (0â€“100).
    """
    df = load_complete_data().copy()

    # Profitability (35%)
    df["roe_score"] = normalize(df["return_on_equity_pct"])
    df["roce_score"] = normalize(df["roce_percentage"])
    df["npm_score"] = normalize(df["net_profit_margin_pct"])

    # Cash Quality (30%)
    df["fcf_score"] = normalize(df["free_cash_flow_cr"])

    cfo_pat = df["cash_from_operations_cr"] / df["free_cash_flow_cr"].replace(0, pd.NA)

    df["cfo_pat_score"] = normalize(cfo_pat)

    df["fcf_positive"] = (df["free_cash_flow_cr"] > 0).astype(int) * 100

    # Growth (20%)
    df["revenue_score"] = normalize(df["revenue_cagr"])
    df["pat_score"] = normalize(df["pat_cagr"])

    # Leverage (15%)
    df["de_score"] = normalize(df["debt_to_equity"], reverse=True)

    df["icr_score"] = normalize(df["interest_coverage"])

    df["composite_quality_score"] = (
        df["roe_score"] * 0.15
        + df["roce_score"] * 0.10
        + df["npm_score"] * 0.10
        + df["fcf_score"] * 0.15
        + df["cfo_pat_score"] * 0.10
        + df["fcf_positive"] * 0.05
        + df["revenue_score"] * 0.10
        + df["pat_score"] * 0.10
        + df["de_score"] * 0.10
        + df["icr_score"] * 0.05
    )

    return df.sort_values("composite_quality_score", ascending=False)


def export_screener_report(filename="output/screener_output.xlsx"):
    """
    Export all preset screeners into separate Excel sheets.
    """
    output = Path(filename)
    output.parent.mkdir(parents=True, exist_ok=True)

    presets = {
        "Quality Compounder": quality_compounder(),
        "Growth Accelerator": growth_accelerator(),
        "Debt Free Bluechip": debt_free_bluechip(),
        "Value Pick": value_pick(),
        "Dividend Champion": dividend_champion(),
        "Turnaround Watch": turnaround_watch(),
    }
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet, df in presets.items():
            df.to_excel(writer, sheet_name=sheet[:31], index=False)

    return output
