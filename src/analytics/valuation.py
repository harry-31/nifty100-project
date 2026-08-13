import os

import pandas as pd

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "..", "..", "data", "raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "..", "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# FILES
# ============================================================

COMPANY_FILE = os.path.join(DATA_DIR, "companies.xlsx")
MARKET_CAP_FILE = os.path.join(DATA_DIR, "market_cap.xlsx")
FINANCIAL_RATIO_FILE = os.path.join(DATA_DIR, "financial_ratios.xlsx")
SECTOR_FILE = os.path.join(DATA_DIR, "sectors.xlsx")


# ============================================================
# LOAD DATA
# ============================================================

companies = pd.read_excel(COMPANY_FILE, header=1)

companies.rename(columns={"id": "company_id"}, inplace=True)

market = pd.read_excel(MARKET_CAP_FILE)

ratios = pd.read_excel(FINANCIAL_RATIO_FILE)

sectors = pd.read_excel(SECTOR_FILE)


print("Companies :", len(companies))
print("Market :", len(market))
print("Ratios :", len(ratios))
print("Sectors :", len(sectors))


# ============================================================
# KEEP LATEST YEAR
# ============================================================

latest_year = market["year"].max()

market = market[market["year"] == latest_year].copy()


latest_ratio_year = ratios["year"].max()

ratios = ratios[ratios["year"] == latest_ratio_year].copy()


# ============================================================
# REQUIRED COLUMNS
# ============================================================

market = market[
    [
        "company_id",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]
]


ratios = ratios[
    [
        "company_id",
        "free_cash_flow_cr",
    ]
]


companies = companies[
    [
        "company_id",
        "company_name",
    ]
]


sectors = sectors[
    [
        "company_id",
        "broad_sector",
    ]
]


# ============================================================
# MERGE
# ============================================================

valuation = market.merge(
    companies,
    on="company_id",
    how="left",
)

valuation = valuation.merge(
    sectors,
    on="company_id",
    how="left",
)

valuation = valuation.merge(
    ratios,
    on="company_id",
    how="left",
)


# ============================================================
# CLEAN
# ============================================================

numeric_cols = [
    "market_cap_crore",
    "enterprise_value_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
    "free_cash_flow_cr",
]

for col in numeric_cols:
    valuation[col] = pd.to_numeric(
        valuation[col],
        errors="coerce",
    )


valuation.fillna(0, inplace=True)


# ============================================================
# FCF YIELD
# ============================================================

valuation["FCF_yield_pct"] = (
    valuation["free_cash_flow_cr"] / valuation["market_cap_crore"]
) * 100


valuation["FCF_yield_pct"] = valuation["FCF_yield_pct"].round(2)

# ============================================================
# SECTOR MEDIAN PE
# ============================================================

sector_median = valuation.groupby("broad_sector")["pe_ratio"].median().reset_index()

sector_median.rename(
    columns={"pe_ratio": "sector_median_pe"},
    inplace=True,
)

valuation = valuation.merge(
    sector_median,
    on="broad_sector",
    how="left",
)


# ============================================================
# PE VS SECTOR MEDIAN
# ============================================================

valuation["PE_vs_sector_median_pct"] = (
    (valuation["pe_ratio"] - valuation["sector_median_pe"])
    / valuation["sector_median_pe"]
) * 100

valuation["PE_vs_sector_median_pct"] = valuation["PE_vs_sector_median_pct"].round(2)


# ============================================================
# VALUATION FLAG
# ============================================================


def valuation_flag(row):

    pe = row["pe_ratio"]
    median = row["sector_median_pe"]

    if pd.isna(pe) or pd.isna(median):
        return "N/A"

    if pe > median * 1.5:
        return "Caution"

    if pe < median * 0.7:
        return "Discount"

    return "Fair"


valuation["flag"] = valuation.apply(
    valuation_flag,
    axis=1,
)


# ============================================================
# FINAL OUTPUT
# ============================================================

valuation_summary = valuation[
    [
        "company_id",
        "company_name",
        "broad_sector",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "FCF_yield_pct",
        "sector_median_pe",
        "PE_vs_sector_median_pct",
        "flag",
    ]
].copy()


valuation_summary.rename(
    columns={
        "broad_sector": "sector",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "ev_ebitda": "EV/EBITDA",
        "sector_median_pe": "5yr_median_PE",
    },
    inplace=True,
)


# ============================================================
# EXPORT EXCEL
# ============================================================

summary_path = os.path.join(
    OUTPUT_DIR,
    "valuation_summary.xlsx",
)

valuation_summary.to_excel(
    summary_path,
    index=False,
)


# ============================================================
# EXPORT FLAGS CSV
# ============================================================

valuation_flags = valuation_summary[
    valuation_summary["flag"].isin(
        [
            "Caution",
            "Discount",
        ]
    )
]

flags_path = os.path.join(
    OUTPUT_DIR,
    "valuation_flags.csv",
)

valuation_flags.to_csv(
    flags_path,
    index=False,
)


# ============================================================
# SUMMARY
# ============================================================

print("=" * 60)
print("VALUATION MODULE COMPLETED")
print("=" * 60)

print()

print("Latest Year :", latest_year)

print("Companies Processed :", len(valuation_summary))

print()

print(valuation_summary["flag"].value_counts())

print()

print(
    "Excel Saved :",
    summary_path,
)

print(
    "CSV Saved :",
    flags_path,
)

print("=" * 60)
