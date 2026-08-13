import sqlite3
from pathlib import Path

import pandas as pd

# ==================================================
# PART 1 — PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_FILE = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

OUTPUT_FILE = OUTPUT_DIR / "pros_cons_generated.csv"


# Make sure output directory exists
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==================================================
# PART 1 — DATABASE LOADER
# ==================================================


def load_data():

    connection = sqlite3.connect(DB_FILE)

    # ----------------------------------------------
    # Companies
    # ----------------------------------------------

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name,
            roce_percentage,
            roe_percentage
        FROM companies
        """,
        connection,
    )

    # ----------------------------------------------
    # Financial Ratios
    # ----------------------------------------------

    ratios = pd.read_sql_query(
        """
        SELECT *
        FROM financial_ratios
        """,
        connection,
    )

    # ----------------------------------------------
    # Profit & Loss
    # ----------------------------------------------

    pnl = pd.read_sql_query(
        """
        SELECT *
        FROM profitandloss
        """,
        connection,
    )

    # ----------------------------------------------
    # Balance Sheet
    # ----------------------------------------------

    balance = pd.read_sql_query(
        """
        SELECT *
        FROM balancesheet
        """,
        connection,
    )

    # ----------------------------------------------
    # Cash Flow
    # ----------------------------------------------

    cashflow = pd.read_sql_query(
        """
        SELECT *
        FROM cashflow
        """,
        connection,
    )

    # ----------------------------------------------
    # Sectors
    # ----------------------------------------------

    sectors = pd.read_sql_query(
        """
        SELECT *
        FROM sectors
        """,
        connection,
    )

    # ----------------------------------------------
    # Market Cap
    # ----------------------------------------------

    market_cap = pd.read_sql_query(
        """
        SELECT *
        FROM market_cap
        """,
        connection,
    )

    connection.close()

    return {
        "companies": companies,
        "ratios": ratios,
        "pnl": pnl,
        "balance": balance,
        "cashflow": cashflow,
        "sectors": sectors,
        "market_cap": market_cap,
    }


# ==================================================
# PART 2 — GENERAL HELPERS
# ==================================================


def sort_by_year(df):
    """
    Sort historical records from oldest to newest.
    """
    if df.empty:
        return df

    return df.sort_values("year").reset_index(drop=True)


def company_rows(df, company_id):
    """
    Return all records belonging to one company.
    """
    if "company_id" not in df.columns:
        return pd.DataFrame()

    result = df[df["company_id"] == company_id].copy()

    if "year" in result.columns:
        result = sort_by_year(result)

    return result


def latest_row(df, company_id):
    """
    Return latest available record for a company.
    """
    rows = company_rows(df, company_id)

    if rows.empty:
        return None

    return rows.iloc[-1]


def last_n_values(df, company_id, column, n):
    """
    Return last N non-null values for a metric.
    """
    rows = company_rows(df, company_id)

    if rows.empty or column not in rows.columns:
        return []

    return rows[column].dropna().tail(n).tolist()


def all_above(values, threshold):
    if not values:
        return False

    return all(value > threshold for value in values)


def all_positive(values):
    if not values:
        return False

    return all(value > 0 for value in values)


def all_negative(values):
    if not values:
        return False

    return all(value < 0 for value in values)


def strictly_increasing(values):
    if len(values) < 2:
        return False

    return all(values[i] > values[i - 1] for i in range(1, len(values)))


def strictly_decreasing(values):
    if len(values) < 2:
        return False

    return all(values[i] < values[i - 1] for i in range(1, len(values)))


# ==================================================
# PART 2 — CAGR
# ==================================================


def calculate_cagr(
    start_value,
    end_value,
    years,
):

    if years <= 0:
        return None

    if pd.isna(start_value) or pd.isna(end_value):
        return None

    if start_value == 0:
        return None

    if start_value > 0 and end_value > 0:

        cagr = ((end_value / start_value) ** (1 / years) - 1) * 100

        return round(cagr, 2)

    return None


def calculate_period_cagr(
    df,
    company_id,
    column,
    years=5,
):
    """
    Calculate CAGR using latest N+1 observations.
    """

    rows = company_rows(
        df,
        company_id,
    )

    if rows.empty or column not in rows.columns:
        return None

    rows = rows.dropna(subset=[column])

    required_rows = years + 1

    if len(rows) < required_rows:
        return None

    period = rows.tail(required_rows)

    start_value = period.iloc[0][column]
    end_value = period.iloc[-1][column]

    return calculate_cagr(
        start_value,
        end_value,
        years,
    )


# ==================================================
# PART 2 — CONFIDENCE SCORE
# ==================================================


def calculate_confidence(
    rule_strength,
    base=70,
):
    """
    Convert signal strength into a confidence score
    between 61 and 100.

    Only scores above 60 are eligible for output.
    """

    try:
        strength = abs(float(rule_strength))
    except (
        TypeError,
        ValueError,
    ):
        strength = 0

    confidence = base + min(
        30,
        strength,
    )

    return round(
        max(61, min(100, confidence)),
        2,
    )


# ==================================================
# PART 2 — FINANCIAL CLASSIFICATION
# ==================================================

FINANCIAL_SECTORS = {
    "Financial Services",
    "Financials",
    "Banking",
    "Insurance",
}


def is_financial_company(
    sectors_df,
    company_id,
):

    row = sectors_df[sectors_df["company_id"] == company_id]

    if row.empty:
        return False

    broad_sector = str(row.iloc[0]["broad_sector"]).strip()

    sub_sector = str(row.iloc[0]["sub_sector"]).strip()

    if broad_sector in FINANCIAL_SECTORS:
        return True

    financial_keywords = [
        "bank",
        "insurance",
        "finance",
        "financial",
        "nbfc",
    ]

    text = (broad_sector + " " + sub_sector).lower()

    return any(keyword in text for keyword in financial_keywords)


# ==================================================
# PART 3 — PRO RULES 01–06
# ==================================================


def generate_pro_rules_1_to_6(
    company_id,
    data,
):

    results = []

    ratios = data["ratios"]
    pnl = data["pnl"]

    # --------------------------------------------------
    # PRO_01
    # ROE > 20% sustained for 3+ years
    # --------------------------------------------------

    roe_values = last_n_values(
        ratios,
        company_id,
        "return_on_equity_pct",
        3,
    )

    if len(roe_values) == 3 and all_above(roe_values, 20):
        results.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_01",
                "text": (
                    "Consistently high return on equity "
                    "above 20% demonstrates exceptional "
                    "capital efficiency"
                ),
                "confidence_pct": calculate_confidence(min(roe_values) - 20),
            }
        )

    # --------------------------------------------------
    # PRO_02
    # FCF positive for 5+ consecutive years
    # --------------------------------------------------

    fcf_values = last_n_values(
        ratios,
        company_id,
        "free_cash_flow_cr",
        5,
    )

    if len(fcf_values) == 5 and all_positive(fcf_values):
        results.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_02",
                "text": (
                    "Strong free cash flow generation "
                    "over 5 years signals healthy "
                    "business fundamentals"
                ),
                "confidence_pct": calculate_confidence(
                    min(fcf_values)
                    / max(
                        abs(max(fcf_values)),
                        1,
                    )
                    * 30
                ),
            }
        )

    # --------------------------------------------------
    # PRO_03
    # D/E = 0 in latest year
    # --------------------------------------------------

    latest_ratio = latest_row(
        ratios,
        company_id,
    )

    if latest_ratio is not None:

        debt_to_equity = latest_ratio["debt_to_equity"]

        if pd.notna(debt_to_equity) and abs(float(debt_to_equity)) < 1e-9:
            results.append(
                {
                    "company_id": company_id,
                    "type": "pro",
                    "rule_id": "PRO_03",
                    "text": (
                        "Debt-free balance sheet provides "
                        "financial flexibility and "
                        "eliminates interest burden"
                    ),
                    "confidence_pct": 100,
                }
            )

    # --------------------------------------------------
    # PRO_04
    # Revenue CAGR > 15% over 5 years
    # --------------------------------------------------

    revenue_cagr_5y = calculate_period_cagr(
        pnl,
        company_id,
        "sales",
        5,
    )

    if revenue_cagr_5y is not None and revenue_cagr_5y > 15:
        results.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_04",
                "text": (
                    "Revenue growing at above 15% CAGR "
                    "over 5 years reflects strong "
                    "business momentum"
                ),
                "confidence_pct": calculate_confidence(revenue_cagr_5y - 15),
            }
        )

    # --------------------------------------------------
    # PRO_05
    # OPM > 25% in latest year
    # --------------------------------------------------

    if latest_ratio is not None:

        opm = latest_ratio["operating_profit_margin_pct"]

        if pd.notna(opm) and float(opm) > 25:
            results.append(
                {
                    "company_id": company_id,
                    "type": "pro",
                    "rule_id": "PRO_05",
                    "text": (
                        "Operating profit margin above "
                        "25% indicates strong pricing "
                        "power and cost discipline"
                    ),
                    "confidence_pct": calculate_confidence(float(opm) - 25),
                }
            )

    # --------------------------------------------------
    # PRO_06
    # PAT CAGR > 20% over 5 years
    # --------------------------------------------------

    pat_cagr_5y = calculate_period_cagr(
        pnl,
        company_id,
        "net_profit",
        5,
    )

    if pat_cagr_5y is not None and pat_cagr_5y > 20:
        results.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_06",
                "text": (
                    "Net profit compounding at above "
                    "20% over 5 years creates "
                    "significant shareholder value"
                ),
                "confidence_pct": calculate_confidence(pat_cagr_5y - 20),
            }
        )

    return results


# ==================================================
# PART 4 — PRO RULES 07–12
# ==================================================


def generate_pro_rules_7_to_12(
    company_id,
    data,
):

    results = []

    ratios = data["ratios"]
    pnl = data["pnl"]
    balance = data["balance"]
    market_cap = data["market_cap"]

    latest_ratio = latest_row(
        ratios,
        company_id,
    )

    # --------------------------------------------------
    # PRO_07
    # ICR > 10 OR Debt Free
    # --------------------------------------------------

    if latest_ratio is not None:

        icr = latest_ratio["interest_coverage"]
        de = latest_ratio["debt_to_equity"]

        debt_free = pd.notna(de) and abs(float(de)) < 1e-9

        high_coverage = pd.notna(icr) and float(icr) > 10

        if high_coverage or debt_free:

            strength = 30

            if high_coverage:
                strength = min(30, float(icr) - 10)

            results.append(
                {
                    "company_id": company_id,
                    "type": "pro",
                    "rule_id": "PRO_07",
                    "text": (
                        "Very high interest coverage ratio "
                        "reflects negligible financial stress "
                        "from debt servicing"
                    ),
                    "confidence_pct": calculate_confidence(strength),
                }
            )

    # --------------------------------------------------
    # PRO_08
    # Dividend Yield > 2% AND FCF positive
    # --------------------------------------------------

    latest_market = latest_row(
        market_cap,
        company_id,
    )

    fcf_values = last_n_values(
        ratios,
        company_id,
        "free_cash_flow_cr",
        1,
    )

    if latest_market is not None and fcf_values:

        dividend_yield = latest_market["dividend_yield_pct"]

        latest_fcf = fcf_values[-1]

        if pd.notna(dividend_yield) and float(dividend_yield) > 2 and latest_fcf > 0:

            results.append(
                {
                    "company_id": company_id,
                    "type": "pro",
                    "rule_id": "PRO_08",
                    "text": (
                        "Consistent dividend yield above 2% "
                        "backed by positive free cash flow"
                    ),
                    "confidence_pct": calculate_confidence(float(dividend_yield) - 2),
                }
            )

    # --------------------------------------------------
    # PRO_09
    # EPS CAGR > 15% over 5 years
    # --------------------------------------------------

    eps_cagr_5y = calculate_period_cagr(
        pnl,
        company_id,
        "eps",
        5,
    )

    if eps_cagr_5y is not None and eps_cagr_5y > 15:

        results.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_09",
                "text": (
                    "Earnings per share growing above "
                    "15% CAGR indicates strong earnings "
                    "quality and compounding"
                ),
                "confidence_pct": calculate_confidence(eps_cagr_5y - 15),
            }
        )

    # --------------------------------------------------
    # PRO_10
    # ROE improving for 3 consecutive years
    # --------------------------------------------------

    roe_values = last_n_values(
        ratios,
        company_id,
        "return_on_equity_pct",
        4,
    )

    if len(roe_values) == 4 and strictly_increasing(roe_values):

        results.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_10",
                "text": (
                    "Return on equity improving for "
                    "3 consecutive years shows "
                    "strengthening business quality"
                ),
                "confidence_pct": calculate_confidence(roe_values[-1] - roe_values[0]),
            }
        )

    # --------------------------------------------------
    # PRO_11
    # Revenue CAGR < PAT CAGR
    # --------------------------------------------------

    revenue_cagr = calculate_period_cagr(
        pnl,
        company_id,
        "sales",
        5,
    )

    pat_cagr = calculate_period_cagr(
        pnl,
        company_id,
        "net_profit",
        5,
    )

    if revenue_cagr is not None and pat_cagr is not None and revenue_cagr < pat_cagr:

        results.append(
            {
                "company_id": company_id,
                "type": "pro",
                "rule_id": "PRO_11",
                "text": (
                    "Revenue growing slower than profits "
                    "shows improving operating leverage "
                    "and scale benefits"
                ),
                "confidence_pct": calculate_confidence(pat_cagr - revenue_cagr),
            }
        )

    # --------------------------------------------------
    # PRO_12
    # Assets growing with declining debt
    # --------------------------------------------------

    balance_rows = company_rows(
        balance,
        company_id,
    )

    if not balance_rows.empty:

        balance_rows = balance_rows.dropna(
            subset=[
                "total_assets",
                "borrowings",
            ]
        )

        if len(balance_rows) >= 4:

            recent = balance_rows.tail(4)

            assets = recent["total_assets"].tolist()

            borrowings = recent["borrowings"].tolist()

            if strictly_increasing(assets) and strictly_decreasing(borrowings):

                results.append(
                    {
                        "company_id": company_id,
                        "type": "pro",
                        "rule_id": "PRO_12",
                        "text": (
                            "Growing asset base funded by "
                            "internal accruals reflects "
                            "self-sustaining growth"
                        ),
                        "confidence_pct": calculate_confidence(20),
                    }
                )

    return results


# ==================================================
# PART 5 — CON RULES 01–12
# ==================================================


def generate_con_rules_1_to_6(
    company_id,
    data,
):

    results = []

    ratios = data["ratios"]
    pnl = data["pnl"]
    sectors = data["sectors"]

    latest_ratio = latest_row(
        ratios,
        company_id,
    )

    # --------------------------------------------------
    # CON_01
    # D/E > 2.0 for non-financial companies
    # --------------------------------------------------

    if latest_ratio is not None:

        de = latest_ratio["debt_to_equity"]

        if (
            pd.notna(de)
            and float(de) > 2.0
            and not is_financial_company(
                sectors,
                company_id,
            )
        ):
            results.append(
                {
                    "company_id": company_id,
                    "type": "con",
                    "rule_id": "CON_01",
                    "text": (
                        f"Debt-to-equity ratio of "
                        f"{float(de):.2f} is elevated for "
                        "a non-financial company and "
                        "warrants monitoring"
                    ),
                    "confidence_pct": calculate_confidence((float(de) - 2) * 10),
                }
            )

    # --------------------------------------------------
    # CON_02
    # FCF negative for 3 consecutive years
    # --------------------------------------------------

    fcf_values = last_n_values(
        ratios,
        company_id,
        "free_cash_flow_cr",
        3,
    )

    if len(fcf_values) == 3 and all_negative(fcf_values):
        results.append(
            {
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON_02",
                "text": (
                    "Free cash flow negative for 3 "
                    "consecutive years raises concern "
                    "about cash generation quality"
                ),
                "confidence_pct": calculate_confidence(20),
            }
        )

    # --------------------------------------------------
    # CON_03
    # OPM declining for 3 consecutive years
    # --------------------------------------------------

    opm_values = last_n_values(
        ratios,
        company_id,
        "operating_profit_margin_pct",
        4,
    )

    if len(opm_values) == 4 and strictly_decreasing(opm_values):
        results.append(
            {
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON_03",
                "text": (
                    "Operating margins declining for "
                    "3 consecutive years suggest "
                    "pricing or cost pressure"
                ),
                "confidence_pct": calculate_confidence(
                    abs(opm_values[-1] - opm_values[0])
                ),
            }
        )

    # --------------------------------------------------
    # CON_04
    # Net profit negative in latest year
    # --------------------------------------------------

    latest_pnl = latest_row(
        pnl,
        company_id,
    )

    if latest_pnl is not None:

        net_profit = latest_pnl["net_profit"]

        if pd.notna(net_profit) and float(net_profit) < 0:
            results.append(
                {
                    "company_id": company_id,
                    "type": "con",
                    "rule_id": "CON_04",
                    "text": (
                        "Company reported a net loss "
                        "in the most recent financial year"
                    ),
                    "confidence_pct": calculate_confidence(
                        abs(float(net_profit))
                        / max(
                            abs(float(latest_pnl["sales"])),
                            1,
                        )
                        * 100
                    ),
                }
            )

    # --------------------------------------------------
    # CON_05
    # Revenue declining for 2+ years
    # --------------------------------------------------

    sales_values = last_n_values(
        pnl,
        company_id,
        "sales",
        3,
    )

    if len(sales_values) == 3 and strictly_decreasing(sales_values):
        results.append(
            {
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON_05",
                "text": (
                    "Revenue contraction over 2 "
                    "consecutive years indicates demand "
                    "weakness or market share loss"
                ),
                "confidence_pct": calculate_confidence(
                    (sales_values[0] - sales_values[-1])
                    / max(
                        abs(sales_values[0]),
                        1,
                    )
                    * 100
                ),
            }
        )

    # --------------------------------------------------
    # CON_06
    # ICR < 1.5
    # --------------------------------------------------

    if latest_ratio is not None:

        icr = latest_ratio["interest_coverage"]

        if pd.notna(icr) and float(icr) < 1.5:
            results.append(
                {
                    "company_id": company_id,
                    "type": "con",
                    "rule_id": "CON_06",
                    "text": (
                        "Interest coverage ratio below "
                        "1.5x indicates the company is at "
                        "risk of not meeting its debt "
                        "obligations"
                    ),
                    "confidence_pct": calculate_confidence((1.5 - float(icr)) * 20),
                }
            )

    return results


# ==================================================
# CON RULES 07–12
# ==================================================


def generate_con_rules_7_to_12(
    company_id,
    data,
):

    results = []

    ratios = data["ratios"]
    pnl = data["pnl"]
    balance = data["balance"]
    data["market_cap"]
    companies = data["companies"]

    latest_row(
        ratios,
        company_id,
    )

    # --------------------------------------------------
    # CON_07
    # Dividend payout > 100%
    # --------------------------------------------------

    latest_pnl = latest_row(
        pnl,
        company_id,
    )

    if latest_pnl is not None:

        payout = latest_pnl["dividend_payout"]

        if pd.notna(payout) and float(payout) > 100:
            results.append(
                {
                    "company_id": company_id,
                    "type": "con",
                    "rule_id": "CON_07",
                    "text": (
                        "Dividend payout ratio above 100% "
                        "means the company is paying "
                        "dividends from reserves, which "
                        "is unsustainable"
                    ),
                    "confidence_pct": calculate_confidence(float(payout) - 100),
                }
            )

    # --------------------------------------------------
    # CON_08
    # D/E rising for 3 consecutive years
    # --------------------------------------------------

    de_values = last_n_values(
        ratios,
        company_id,
        "debt_to_equity",
        4,
    )

    if len(de_values) == 4 and strictly_increasing(de_values):
        results.append(
            {
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON_08",
                "text": (
                    "Rising debt-to-equity ratio over "
                    "3 years suggests increasing "
                    "financial leverage risk"
                ),
                "confidence_pct": calculate_confidence(
                    (de_values[-1] - de_values[0]) * 20
                ),
            }
        )

    # --------------------------------------------------
    # CON_09
    # EPS declining for 3 consecutive years
    # --------------------------------------------------

    eps_values = last_n_values(
        pnl,
        company_id,
        "eps",
        4,
    )

    if len(eps_values) == 4 and strictly_decreasing(eps_values):
        results.append(
            {
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON_09",
                "text": (
                    "Earnings per share declining for "
                    "3 consecutive years reflects "
                    "deteriorating profitability"
                ),
                "confidence_pct": calculate_confidence(
                    abs(eps_values[-1] - eps_values[0])
                ),
            }
        )

    # --------------------------------------------------
    # CON_10
    # ROCE < 10%
    # --------------------------------------------------

    company_row = companies[companies["company_id"] == company_id]

    if not company_row.empty:

        roce = company_row.iloc[0]["roce_percentage"]

        if pd.notna(roce) and float(roce) < 10:
            results.append(
                {
                    "company_id": company_id,
                    "type": "con",
                    "rule_id": "CON_10",
                    "text": (
                        "Return on capital employed "
                        "below 10% suggests the business "
                        "is not generating sufficient "
                        "returns on invested capital"
                    ),
                    "confidence_pct": calculate_confidence((10 - float(roce)) * 5),
                }
            )

    # --------------------------------------------------
    # CON_11
    # Net Debt > 3x EBITDA
    # --------------------------------------------------
    #
    # EBITDA is approximated as:
    # Operating Profit + Depreciation
    #
    # Net Debt = Total Debt
    # because cash balance is not available
    # in the current database schema.
    # --------------------------------------------------

    balance_latest = latest_row(
        balance,
        company_id,
    )

    pnl_latest = latest_row(
        pnl,
        company_id,
    )

    if balance_latest is not None and pnl_latest is not None:

        borrowings = balance_latest["borrowings"]

        operating_profit = pnl_latest["operating_profit"]

        depreciation = pnl_latest["depreciation"]

        if (
            pd.notna(borrowings)
            and pd.notna(operating_profit)
            and pd.notna(depreciation)
        ):

            ebitda = float(operating_profit) + float(depreciation)

            if ebitda > 0:

                net_debt_to_ebitda = float(borrowings) / ebitda

                if net_debt_to_ebitda > 3:

                    results.append(
                        {
                            "company_id": company_id,
                            "type": "con",
                            "rule_id": "CON_11",
                            "text": (
                                "Net debt exceeding 3 times "
                                "EBITDA is a high leverage "
                                "ratio and limits financial "
                                "flexibility"
                            ),
                            "confidence_pct": calculate_confidence(
                                (net_debt_to_ebitda - 3) * 10
                            ),
                        }
                    )

    # --------------------------------------------------
    # CON_12
    # Revenue CAGR < 5% over 5 years
    # --------------------------------------------------

    revenue_cagr_5y = calculate_period_cagr(
        pnl,
        company_id,
        "sales",
        5,
    )

    if revenue_cagr_5y is not None and revenue_cagr_5y < 5:
        results.append(
            {
                "company_id": company_id,
                "type": "con",
                "rule_id": "CON_12",
                "text": (
                    "Revenue growing at below 5% "
                    "over 5 years lags inflation and "
                    "suggests limited business momentum"
                ),
                "confidence_pct": calculate_confidence(abs(5 - revenue_cagr_5y)),
            }
        )

    return results


# ==================================================
# PART 6 — VALIDATION + MAIN + OUTPUT
# ==================================================


def validate_loaded_data(data):

    print("\n------------------------------")
    print("Day 30 Data Validation")
    print("------------------------------")

    for name, df in data.items():

        if "company_id" in df.columns:
            company_count = df["company_id"].nunique()
        else:
            company_count = 0

        print(f"{name:<12} " f"rows={len(df):<5} " f"companies={company_count}")


# ==================================================
# FALLBACK HELPERS
# ==================================================


def create_fallback_pro(company_id):
    """
    Used only when none of the 12 primary Pro rules
    are triggered for a company.

    This ensures the Day 30 requirement that every
    company has at least one Pro.
    """

    return {
        "company_id": company_id,
        "type": "pro",
        "rule_id": "PRO_FALLBACK",
        "text": (
            "Company does not trigger any primary "
            "positive screening rule but remains "
            "included in the financial analysis universe"
        ),
        "confidence_pct": 61,
    }


def create_fallback_con(company_id):
    """
    Used only when none of the 12 primary Con rules
    are triggered for a company.

    This ensures every company has at least one Con
    in the final output as required by Day 30.
    """

    return {
        "company_id": company_id,
        "type": "con",
        "rule_id": "CON_FALLBACK",
        "text": (
            "No primary risk signal crossed the defined "
            "Con-rule thresholds in the available financial data"
        ),
        "confidence_pct": 61,
    }


# ==================================================
# OUTPUT VALIDATION
# ==================================================


def validate_output(
    companies,
    output_df,
):

    print("\n------------------------------")
    print("Final Day 30 Validation")
    print("------------------------------")

    expected_companies = set(companies["company_id"])

    output_companies = set(output_df["company_id"])

    pro_companies = set(output_df[output_df["type"] == "pro"]["company_id"])

    con_companies = set(output_df[output_df["type"] == "con"]["company_id"])

    missing_from_output = expected_companies - output_companies

    missing_pro = expected_companies - pro_companies

    missing_con = expected_companies - con_companies

    print(f"Generated rows : {len(output_df)}")

    print(
        f"Companies with Pro : " f"{len(pro_companies)} / " f"{len(expected_companies)}"
    )

    print(
        f"Companies with Con : " f"{len(con_companies)} / " f"{len(expected_companies)}"
    )

    if missing_from_output:
        print("\nMissing from output:")
        print(sorted(missing_from_output))

    if missing_pro:
        print("\nMissing Pro:")
        print(sorted(missing_pro))
    else:
        print("\nMissing Pro: NONE")

    if missing_con:
        print("\nMissing Con:")
        print(sorted(missing_con))
    else:
        print("\nMissing Con: NONE")

    # ----------------------------------------------
    # Confidence validation
    # ----------------------------------------------

    missing_confidence = output_df[output_df["confidence_pct"].isna()]

    low_confidence = output_df[output_df["confidence_pct"] <= 60]

    print("\nMissing confidence : " f"{len(missing_confidence)}")

    print("Confidence <= 60 : " f"{len(low_confidence)}")

    # ----------------------------------------------
    # Final status
    # ----------------------------------------------

    complete = (
        not missing_from_output
        and not missing_pro
        and not missing_con
        and len(missing_confidence) == 0
        and len(low_confidence) == 0
    )

    if complete:
        print("\nSTATUS: DAY 30 COMPLETE")
    else:
        print("\nSTATUS: DAY 30 NEEDS REVIEW")

    return complete


# ==================================================
# MAIN
# ==================================================


def main():

    print("Loading Day 30 financial data...")

    data = load_data()

    companies = data["companies"]

    total_companies = len(companies)

    print(f"\nProcessing " f"{total_companies} companies...")

    all_results = []

    # ==================================================
    # PROCESS EVERY COMPANY
    # ==================================================

    for company_id in companies["company_id"].tolist():

        # ----------------------------------------------
        # PRO RULES 01–06
        # ----------------------------------------------

        pros = generate_pro_rules_1_to_6(
            company_id,
            data,
        )

        # ----------------------------------------------
        # PRO RULES 07–12
        # ----------------------------------------------

        pros.extend(
            generate_pro_rules_7_to_12(
                company_id,
                data,
            )
        )

        # ----------------------------------------------
        # CON RULES 01–06
        # ----------------------------------------------

        cons = generate_con_rules_1_to_6(
            company_id,
            data,
        )

        # ----------------------------------------------
        # CON RULES 07–12
        # ----------------------------------------------

        cons.extend(
            generate_con_rules_7_to_12(
                company_id,
                data,
            )
        )

        # ----------------------------------------------
        # FALLBACK PRO
        # ----------------------------------------------

        if not pros:
            pros.append(create_fallback_pro(company_id))

        # ----------------------------------------------
        # FALLBACK CON
        # ----------------------------------------------

        if not cons:
            cons.append(create_fallback_con(company_id))

        # ----------------------------------------------
        # Add results
        # ----------------------------------------------

        all_results.extend(pros)
        all_results.extend(cons)

    # ==================================================
    # CREATE DATAFRAME
    # ==================================================

    output_df = pd.DataFrame(
        all_results,
        columns=[
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ],
    )

    # ==================================================
    # CLEAN CONFIDENCE
    # ==================================================

    output_df["confidence_pct"] = pd.to_numeric(
        output_df["confidence_pct"],
        errors="coerce",
    )

    # Keep only confidence > 60
    output_df = output_df[output_df["confidence_pct"] > 60].copy()

    # ==================================================
    # SAVE OUTPUT
    # ==================================================

    output_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # ==================================================
    # VALIDATION
    # ==================================================

    validate_loaded_data(data)

    validate_output(
        companies,
        output_df,
    )

    print("\nOutput File:")

    print(OUTPUT_FILE)

    print("\nDay 30 processing completed.")


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":
    main()
