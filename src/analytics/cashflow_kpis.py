from pathlib import Path
import sqlite3
import re
import numpy as np
import pandas as pd

DB = Path("nifty100.db")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

INTELLIGENCE_FILE = OUTPUT / "cashflow_intelligence.xlsx"
DISTRESS_FILE = OUTPUT / "distress_alerts.csv"


# ============================================================
# PUBLIC TESTED HELPERS
# ============================================================

def free_cash_flow(cfo, cfi):
    if cfo is None or cfi is None:
        return None
    return cfo + cfi


def cfo_quality_score(cfo, pat):
    if pat is None or pat == 0:
        return None

    ratio = cfo / pat

    if ratio > 1.0:
        return "High Quality"
    elif ratio >= 0.5:
        return "Moderate"
    else:
        return "Accrual Risk"


def capex_intensity(investing_activity, sales):
    if sales is None or sales == 0:
        return None, None

    value = abs(investing_activity) / abs(sales) * 100

    if value < 3:
        label = "Asset Light"
    elif value <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return value, label


def fcf_conversion_rate(fcf, pat):
    if pat is None or pat == 0:
        return None

    return fcf / pat * 100


def capital_allocation_pattern(
    cfo,
    cfi,
    cff,
    cfo_pat_ratio=None,
):
    if cfo < 0 and cfi > 0 and cff > 0:
        return "Distress Signal"

    if cfo < 0 and cfi < 0 and cff > 0:
        return "Growth Funded by Debt"

    if cfo > 0 and cfi > 0 and cff < 0:
        return "Liquidating Assets"

    if cfo > 0 and cfi > 0 and cff > 0:
        return "Cash Accumulator"

    if cfo < 0 and cfi < 0 and cff < 0:
        return "Pre-Revenue"

    if cfo > 0 and cfi < 0 and cff < 0:
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            return "Shareholder Returns"
        return "Reinvestor"

    return "Mixed"


# ============================================================
# HELPERS
# ============================================================

def normalize_year(value):
    if pd.isna(value):
        return np.nan

    match = re.search(r"(20\d{2})", str(value))

    if match:
        return int(match.group(1))

    return np.nan


def safe_float(value):
    try:
        if pd.isna(value):
            return np.nan
        return float(value)
    except Exception:
        return np.nan


def calculate_cagr(start, end, years=5):
    if pd.isna(start) or pd.isna(end):
        return np.nan

    if years <= 0 or start <= 0 or end <= 0:
        return np.nan

    try:
        return ((end / start) ** (1 / years) - 1) * 100
    except Exception:
        return np.nan


def get_sector_mapping(conn):

    info = pd.read_sql(
        "PRAGMA table_info(sectors)",
        conn,
    )

    columns = info["name"].tolist()

    id_col = next(
        (
            c for c in
            ["company_id", "id", "ticker", "symbol"]
            if c in columns
        ),
        None,
    )

    sector_col = next(
        (
            c for c in
            ["sector", "sector_name", "sector_label",
             "industry", "sector_type"]
            if c in columns
        ),
        None,
    )

    if not id_col or not sector_col:
        return pd.DataFrame(
            columns=["company_id", "sector"]
        )

    return pd.read_sql(
        f'''
        SELECT
            "{id_col}" AS company_id,
            "{sector_col}" AS sector
        FROM sectors
        ''',
        conn,
    ).drop_duplicates("company_id")


def load_data():

    conn = sqlite3.connect(DB)

    companies = pd.read_sql(
        "SELECT * FROM companies",
        conn,
    )

    cashflow = pd.read_sql(
        "SELECT * FROM cashflow",
        conn,
    )

    pnl = pd.read_sql(
        "SELECT * FROM profitandloss",
        conn,
    )

    balance = pd.read_sql(
        "SELECT * FROM balancesheet",
        conn,
    )

    ratios = pd.read_sql(
        "SELECT * FROM financial_ratios",
        conn,
    )

    sectors = get_sector_mapping(conn)

    conn.close()

    companies = companies.rename(
        columns={"id": "company_id"}
    )

    for df in [
        cashflow,
        pnl,
        balance,
        ratios,
    ]:
        if "year" in df.columns:
            df["year_num"] = df["year"].apply(
                normalize_year
            )

    sectors["company_id"] = (
        sectors["company_id"].astype(str)
    )

    return (
        companies,
        cashflow,
        pnl,
        balance,
        ratios,
        sectors,
    )


# ============================================================
# COMPANY CALCULATION
# ============================================================

def calculate_company_metrics(
    company_id,
    cashflow,
    pnl,
    balance,
    ratios,
):

    cf = cashflow[
        cashflow["company_id"].astype(str)
        == str(company_id)
    ].copy()

    pl = pnl[
        pnl["company_id"].astype(str)
        == str(company_id)
    ].copy()

    bs = balance[
        balance["company_id"].astype(str)
        == str(company_id)
    ].copy()

    rr = ratios[
        ratios["company_id"].astype(str)
        == str(company_id)
    ].copy()

    # --------------------------------------------------------
    # No cashflow data
    # --------------------------------------------------------

    if cf.empty:

        return {
            "company_id": str(company_id),
            "latest_year": np.nan,
            "cfo_quality_score": np.nan,
            "cfo_quality_label": "Insufficient Data",
            "capex_intensity_pct": np.nan,
            "capex_label": "Insufficient Data",
            "fcf_cagr_5yr": np.nan,
            "fcf_conversion_pct": np.nan,
            "distress_flag": False,
            "deleveraging_flag": False,
            "capital_allocation_label": "Insufficient Data",
            "latest_cfo": np.nan,
            "latest_cff": np.nan,
            "latest_net_profit": (
                safe_float(
                    pl.iloc[-1]["net_profit"]
                )
                if not pl.empty
                else np.nan
            ),
        }

    cf = (
        cf.dropna(subset=["year_num"])
        .sort_values("year_num")
    )

    pl = (
        pl.dropna(subset=["year_num"])
        .sort_values("year_num")
    )

    bs = (
        bs.dropna(subset=["year_num"])
        .sort_values("year_num")
    )

    yearly = cf[
        [
            "year_num",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ]
    ].copy()

    yearly = yearly.rename(
        columns={
            "operating_activity": "cfo",
            "investing_activity": "cfi",
            "financing_activity": "cff",
        }
    )

    pl_small = (
        pl[
            [
                "year_num",
                "sales",
                "net_profit",
            ]
        ]
        .drop_duplicates("year_num")
    )

    yearly = yearly.merge(
        pl_small,
        on="year_num",
        how="left",
    )

    if not bs.empty:

        bs_small = (
            bs[
                [
                    "year_num",
                    "borrowings",
                ]
            ]
            .drop_duplicates("year_num")
        )

        yearly = yearly.merge(
            bs_small,
            on="year_num",
            how="left",
        )

    else:
        yearly["borrowings"] = np.nan

    yearly["fcf"] = (
        yearly["cfo"]
        + yearly["cfi"]
    )

    # --------------------------------------------------------
    # CFO Quality
    # --------------------------------------------------------

    quality = yearly[
        yearly["net_profit"].notna()
        & (yearly["net_profit"] != 0)
    ].copy()

    quality["cfo_pat_ratio"] = (
        quality["cfo"]
        / quality["net_profit"]
    )

    quality = (
        quality
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna(
            subset=["cfo_pat_ratio"]
        )
    )

    quality_5 = quality.tail(5)

    if quality_5.empty:

        quality_average = np.nan
        quality_label = "Insufficient Data"

    else:

        quality_average = quality_5[
            "cfo_pat_ratio"
        ].mean()

        if quality_average > 1:
            quality_label = "High Quality"
        elif quality_average >= 0.5:
            quality_label = "Moderate"
        else:
            quality_label = "Accrual Risk"

    # --------------------------------------------------------
    # Latest year
    # --------------------------------------------------------

    latest = yearly.iloc[-1]

    latest_year = int(
        latest["year_num"]
    )

    latest_cfo = safe_float(
        latest["cfo"]
    )

    latest_cfi = safe_float(
        latest["cfi"]
    )

    latest_cff = safe_float(
        latest["cff"]
    )

    latest_sales = safe_float(
        latest["sales"]
    )

    latest_profit = safe_float(
        latest["net_profit"]
    )

    latest_fcf = safe_float(
        latest["fcf"]
    )

    # --------------------------------------------------------
    # CapEx
    # --------------------------------------------------------

    capex_value, capex_label = (
        capex_intensity(
            latest_cfi,
            latest_sales,
        )
    )

    # --------------------------------------------------------
    # FCF CAGR
    # --------------------------------------------------------

    history = (
        yearly[
            ["year_num", "fcf"]
        ]
        .dropna()
        .sort_values("year_num")
    )

    fcf_cagr_5yr = np.nan

    if len(history) >= 6:

        fcf_cagr_5yr = calculate_cagr(
            history.iloc[-6]["fcf"],
            history.iloc[-1]["fcf"],
            5,
        )

    # --------------------------------------------------------
    # FCF Conversion
    # --------------------------------------------------------

    fcf_conversion = (
        fcf_conversion_rate(
            latest_fcf,
            latest_profit,
        )
    )

    # --------------------------------------------------------
    # Distress
    # --------------------------------------------------------

    distress = bool(
        latest_cfo < 0
        and latest_cff > 0
    )

    # --------------------------------------------------------
    # Deleveraging
    # --------------------------------------------------------

    deleveraging = False

    if len(yearly) >= 2:

        latest_borrowings = safe_float(
            latest["borrowings"]
        )

        previous_borrowings = safe_float(
            yearly.iloc[-2]["borrowings"]
        )

        if (
            not pd.isna(latest_borrowings)
            and not pd.isna(previous_borrowings)
            and latest_borrowings < previous_borrowings
            and latest_cff < 0
        ):
            deleveraging = True

    # --------------------------------------------------------
    # Capital Allocation
    # --------------------------------------------------------

    ratio = None

    if (
        not pd.isna(latest_cfo)
        and not pd.isna(latest_profit)
        and latest_profit != 0
    ):
        ratio = latest_cfo / latest_profit

    pattern = capital_allocation_pattern(
        latest_cfo,
        latest_cfi,
        latest_cff,
        cfo_pat_ratio=ratio,
    )

    return {
        "company_id": str(company_id),
        "latest_year": latest_year,
        "cfo_quality_score": quality_average,
        "cfo_quality_label": quality_label,
        "capex_intensity_pct": capex_value,
        "capex_label": capex_label,
        "fcf_cagr_5yr": fcf_cagr_5yr,
        "fcf_conversion_pct": fcf_conversion,
        "distress_flag": distress,
        "deleveraging_flag": deleveraging,
        "capital_allocation_label": pattern,
        "latest_cfo": latest_cfo,
        "latest_cff": latest_cff,
        "latest_net_profit": latest_profit,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading Day 31 data...")

    (
        companies,
        cashflow,
        pnl,
        balance,
        ratios,
        sectors,
    ) = load_data()

    print(
        f"Companies in master table: {len(companies)}"
    )

    print(
        f"Cashflow companies: "
        f"{cashflow.company_id.nunique()}"
    )

    print(
        f"P&L companies: "
        f"{pnl.company_id.nunique()}"
    )

    print(
        f"Balance sheet companies: "
        f"{balance.company_id.nunique()}"
    )

    results = []

    for company_id in companies[
        "company_id"
    ].astype(str):

        result = calculate_company_metrics(
            company_id,
            cashflow,
            pnl,
            balance,
            ratios,
        )

        results.append(result)

    output = pd.DataFrame(results)

    # Add sectors
    output = output.merge(
        sectors[
            [
                "company_id",
                "sector",
            ]
        ],
        on="company_id",
        how="left",
    )

    output["sector"] = (
        output["sector"]
        .fillna("Unknown")
        .astype(str)
    )

    columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]

    output = output[
        columns
    ].sort_values("company_id")

    output[
        [
            "cfo_quality_score",
            "capex_intensity_pct",
            "fcf_cagr_5yr",
            "fcf_conversion_pct",
        ]
    ] = output[
        [
            "cfo_quality_score",
            "capex_intensity_pct",
            "fcf_cagr_5yr",
            "fcf_conversion_pct",
        ]
    ].round(2)

    output.to_excel(
        INTELLIGENCE_FILE,
        index=False,
    )

    # Distress alerts
    distress = pd.DataFrame(results)

    distress = distress[
        distress["distress_flag"] == True
    ].copy()

    distress = distress.merge(
        output[
            [
                "company_id",
                "sector",
            ]
        ],
        on="company_id",
        how="left",
    )

    distress = distress[
        [
            "company_id",
            "sector",
            "latest_year",
            "latest_cfo",
            "latest_cff",
            "latest_net_profit",
        ]
    ]

    distress = distress.rename(
        columns={
            "latest_cfo": "cfo_value",
            "latest_cff": "cff_value",
        }
    )

    distress.to_csv(
        DISTRESS_FILE,
        index=False,
    )

    # Validation
    print("\n" + "=" * 60)
    print("DAY 31 VALIDATION")
    print("=" * 60)

    print("Output rows:", len(output))
    print(
        "Unique companies:",
        output["company_id"].nunique(),
    )

    print(
        "Required columns present:",
        all(
            c in output.columns
            for c in columns
        ),
    )

    print(
        "\nInsufficient Data companies:"
    )

    print(
        output[
            output["cfo_quality_label"]
            == "Insufficient Data"
        ][
            ["company_id", "sector"]
        ].to_string(index=False)
    )

    print(
        "\nCFO Quality:"
    )

    print(
        output[
            "cfo_quality_label"
        ].value_counts().to_string()
    )

    print(
        "\nCapEx:"
    )

    print(
        output[
            "capex_label"
        ].value_counts().to_string()
    )

    print(
        "\nDistress signals:",
        int(
            output["distress_flag"].sum()
        ),
    )

    print(
        "Deleveraging:",
        int(
            output["deleveraging_flag"].sum()
        ),
    )

    print(
        "\nExcel:",
        INTELLIGENCE_FILE,
    )

    print(
        "Distress CSV:",
        DISTRESS_FILE,
    )

    if (
        len(output) == 92
        and output["company_id"].nunique() == 92
    ):
        print(
            "\nSTATUS: DAY 31 COMPLETE"
        )
    else:
        print(
            "\nSTATUS: DAY 31 INCOMPLETE"
        )


if __name__ == "__main__":
    main()
