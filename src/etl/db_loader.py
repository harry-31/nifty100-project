import sqlite3

import pandas as pd

from src.etl.loader import load_excel

conn = sqlite3.connect("nifty100.db")

# ---------------- Companies ----------------
companies = load_excel("data/raw/companies.xlsx")
companies.to_sql("companies", conn, if_exists="append", index=False)

# Valid company IDs
valid_ids = set(companies["id"])

# ---------------- Profit & Loss ----------------
pl = load_excel("data/raw/profitandloss.xlsx")
pl = pl[pl["company_id"].isin(valid_ids)]
pl.to_sql("profitandloss", conn, if_exists="append", index=False)

# ---------------- Balance Sheet ----------------
bs = load_excel("data/raw/balancesheet.xlsx")
bs = bs[bs["company_id"].isin(valid_ids)]
bs.to_sql("balancesheet", conn, if_exists="append", index=False)

# ---------------- Cash Flow ----------------
cf = load_excel("data/raw/cashflow.xlsx")
cf = cf[cf["company_id"].isin(valid_ids)]
cf.to_sql("cashflow", conn, if_exists="append", index=False)

# ---------------- Remaining Core Files ----------------
for table, file in {
    "analysis": "analysis.xlsx",
    "documents": "documents.xlsx",
    "prosandcons": "prosandcons.xlsx",
}.items():
    print(f"Loading {table}...")
    df = load_excel(f"data/raw/{file}")
    df = df[df["company_id"].isin(valid_ids)]
    df.to_sql(table, conn, if_exists="append", index=False)

# ---------------- Supporting Files ----------------
support_files = {
    "market_cap": "market_cap.xlsx",
    "financial_ratios": "financial_ratios.xlsx",
    "peer_groups": "peer_groups.xlsx",
    "sectors": "sectors.xlsx",
    "stock_prices": "stock_prices.xlsx",
}

for table, file in support_files.items():
    print(f"Loading {table}...")
    df = pd.read_excel(f"data/raw/{file}")
    if "company_id" in df.columns:
        df = df[df["company_id"].isin(valid_ids)]
    df.to_sql(table, conn, if_exists="append", index=False)

conn.commit()
conn.close()

print("✅ ALL DATASETS LOADED")
