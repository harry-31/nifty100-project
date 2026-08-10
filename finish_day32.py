from pathlib import Path
import sqlite3
import re
import pandas as pd

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "output" / "capital_allocation.csv"
OUTPUT = ROOT / "output"

def normalize_year(value):
    if pd.isna(value):
        return None

    s = str(value).strip()

    # Four-digit year anywhere in the string
    m = re.search(r"(19|20)\d{2}", s)
    if m:
        return int(m.group())

    # Two-digit year such as Mar-13
    m = re.search(r"[-/ ](\d{2})$", s)
    if m:
        yy = int(m.group(1))
        return 2000 + yy if yy <= 30 else 1900 + yy

    return None


print("=" * 70)
print("DAY 32 — CAPITAL ALLOCATION REPORT")
print("=" * 70)

df = pd.read_csv(INPUT)

print("Source rows:", len(df))
print("Source companies:", df["company_id"].nunique())

required = [
    "company_id",
    "year",
    "cfo_sign",
    "cfi_sign",
    "cff_sign",
    "pattern_label",
]

missing = [
    c for c in required
    if c not in df.columns
]

if missing:
    raise SystemExit(
        f"ERROR: Missing columns: {missing}"
    )

# ------------------------------------------------------------
# NORMALIZE YEARS
# ------------------------------------------------------------

df["year_num"] = df["year"].apply(
    normalize_year
)

bad_years = df[
    df["year_num"].isna()
]

print(
    "Unparseable year rows:",
    len(bad_years)
)

if len(bad_years):
    print(
        bad_years[
            ["company_id", "year"]
        ].head(20).to_string(index=False)
    )

# Remove rows where year cannot be determined
df = df.dropna(
    subset=["year_num"]
).copy()

df["year_num"] = (
    df["year_num"]
    .astype(int)
)

# ------------------------------------------------------------
# MASTER COMPANIES
# ------------------------------------------------------------

conn = sqlite3.connect(
    ROOT / "nifty100.db"
)

master = pd.read_sql(
    "SELECT id FROM companies",
    conn
)

conn.close()

master_ids = set(
    master["id"]
    .astype(str)
)

df["company_id"] = (
    df["company_id"]
    .astype(str)
    .str.strip()
)

source_ids = set(
    df["company_id"]
)

extra_ids = sorted(
    source_ids - master_ids
)

missing_ids = sorted(
    master_ids - source_ids
)

print()
print("Master companies:", len(master_ids))
print("Source companies:", len(source_ids))
print("Extra source IDs:", extra_ids)
print("Missing master IDs:", missing_ids)

# Keep only the actual 92 Nifty100 companies
df = df[
    df["company_id"].isin(master_ids)
].copy()

print()
print(
    "After filtering to master:",
    df["company_id"].nunique(),
    "companies"
)

print(
    "Rows after filtering:",
    len(df)
)

# ------------------------------------------------------------
# DUPLICATE COMPANY-YEAR CHECK
# ------------------------------------------------------------

duplicates = df[
    df.duplicated(
        subset=[
            "company_id",
            "year_num",
        ],
        keep=False,
    )
].sort_values(
    [
        "company_id",
        "year_num",
    ]
)

print()
print(
    "Duplicate company-year rows:",
    len(duplicates)
)

# Keep one row per company/year
df = (
    df.sort_values(
        [
            "company_id",
            "year_num",
        ]
    )
    .drop_duplicates(
        subset=[
            "company_id",
            "year_num",
        ],
        keep="last",
    )
)

# ------------------------------------------------------------
# YEAR COVERAGE
# ------------------------------------------------------------

print()
print("Year range:")
print(
    df["year_num"].min(),
    "to",
    df["year_num"].max()
)

print()
print("Companies by year:")

print(
    df.groupby("year_num")[
        "company_id"
    ]
    .nunique()
    .to_string()
)

# ------------------------------------------------------------
# LATEST YEAR
# ------------------------------------------------------------

latest_year = df["year_num"].max()

latest = df[
    df["year_num"] == latest_year
].copy()

# Ensure one company/year
latest = (
    latest
    .drop_duplicates(
        subset=[
            "company_id",
            "year_num",
        ]
    )
)

print()
print(
    "Latest year:",
    latest_year
)

print(
    "Latest-year companies:",
    latest["company_id"].nunique()
)

# ------------------------------------------------------------
# DISTRIBUTION
# ------------------------------------------------------------

distribution = (
    latest["pattern_label"]
    .fillna("Unknown")
    .value_counts()
    .rename_axis(
        "capital_allocation_pattern"
    )
    .reset_index(
        name="company_count"
    )
)

distribution["percentage"] = (
    distribution["company_count"]
    / len(latest)
    * 100
).round(2)

distribution_path = (
    OUTPUT
    / "capital_allocation_distribution.csv"
)

distribution.to_csv(
    distribution_path,
    index=False
)

print()
print("=" * 70)
print("LATEST YEAR DISTRIBUTION")
print("=" * 70)

print(
    distribution.to_string(
        index=False
    )
)

# ------------------------------------------------------------
# YEAR-OVER-YEAR CHANGES
# ------------------------------------------------------------

work = df[
    [
        "company_id",
        "year_num",
        "pattern_label",
    ]
].copy()

work = work.sort_values(
    [
        "company_id",
        "year_num",
    ]
)

work["previous_pattern"] = (
    work
    .groupby("company_id")[
        "pattern_label"
    ]
    .shift(1)
)

work["previous_year"] = (
    work
    .groupby("company_id")[
        "year_num"
    ]
    .shift(1)
)

changes = work[
    work["previous_pattern"].notna()
    &
    (
        work["pattern_label"]
        != work["previous_pattern"]
    )
].copy()

changes = changes.rename(
    columns={
        "pattern_label":
            "current_pattern"
    }
)

changes = changes[
    [
        "company_id",
        "previous_year",
        "year_num",
        "previous_pattern",
        "current_pattern",
    ]
]

changes = changes.rename(
    columns={
        "year_num": "current_year"
    }
)

changes_path = (
    OUTPUT / "pattern_changes.csv"
)

changes.to_csv(
    changes_path,
    index=False
)

print()
print("=" * 70)
print("YEAR-OVER-YEAR PATTERN CHANGES")
print("=" * 70)

print(
    "Total pattern changes:",
    len(changes)
)

if not changes.empty:
    print(
        changes.head(30)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# FINAL VALIDATION
# ------------------------------------------------------------

print()
print("=" * 70)
print("DAY 32 FINAL VALIDATION")
print("=" * 70)

print(
    "Master companies:",
    len(master_ids)
)

print(
    "Filtered companies:",
    df["company_id"].nunique()
)

print(
    "Latest-year companies:",
    latest["company_id"].nunique()
)

print(
    "Latest-year rows:",
    len(latest)
)

print(
    "Distribution total:",
    distribution[
        "company_count"
    ].sum()
)

print(
    "Distribution file:",
    distribution_path.exists()
)

print(
    "Pattern changes file:",
    changes_path.exists()
)

if (
    df["company_id"].nunique() == 92
    and latest["company_id"].nunique() == 92
    and len(latest) == 92
    and distribution[
        "company_count"
    ].sum() == 92
):

    print()
    print("STATUS: DAY 32 COMPLETE")

else:

    print()
    print("STATUS: DAY 32 NEEDS REVIEW")
# ============================================================
# FINAL VALIDATION
# ============================================================

print()
print("=" * 70)
print("DAY 32 FINAL VALIDATION")
print("=" * 70)

print("Master companies:", len(master_ids))
print("Filtered analyzable companies:", df["company_id"].nunique())
print("Latest-year companies:", latest["company_id"].nunique())
print("Latest-year rows:", len(latest))
print(
    "Distribution total:",
    distribution["company_count"].sum()
)
print(
    "Distribution file:",
    distribution_path.exists()
)
print(
    "Pattern changes file:",
    changes_path.exists()
)

missing_from_analysis = sorted(
    master_ids - set(df["company_id"])
)

print(
    "Companies without capital-allocation data:",
    missing_from_analysis
)

# ATGL is expected to be missing because it has
# no cashflow source data.
expected_missing = {"ATGL"}

if (
    len(master_ids) == 92
    and df["company_id"].nunique() == 91
    and latest["company_id"].nunique() == 91
    and len(latest) == 91
    and distribution["company_count"].sum() == 91
    and set(missing_from_analysis) == expected_missing
    and distribution_path.exists()
    and changes_path.exists()
):

    print()
    print(
        "STATUS: DAY 32 COMPLETE "
        "(91 analyzable + ATGL insufficient data)"
    )

else:

    print()
    print("STATUS: DAY 32 NEEDS REVIEW")
