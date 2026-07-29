import streamlit as st
import pandas as pd

from utils.db import (
    get_ratios,
    get_companies,
    get_market_cap
)

st.set_page_config(
    page_title="Stock Screener",
    layout="wide"
)

st.title("Nifty 100 Stock Screener")

# -----------------------------
# Load Data
# -----------------------------
ratios = get_ratios()
companies = get_companies()
market = get_market_cap("2024")

# Remove TTM
ratios = ratios[ratios["year"] != "TTM"]

# Latest year per company
ratios = (
    ratios
    .sort_values("year")
    .groupby("company_id")
    .tail(1)
)

# Merge
df = ratios.merge(
    companies,
    left_on="company_id",
    right_on="id",
    how="left"
)

df = df.merge(
    market,
    on="company_id",
    how="left"
)

# -----------------------------
# Sidebar Filters
# -----------------------------

st.sidebar.header("Filters")

roe = st.sidebar.slider(
    "Minimum ROE",
    0.0,
    50.0,
    15.0
)

de = st.sidebar.slider(
    "Maximum Debt/Equity",
    0.0,
    5.0,
    1.0
)

rev = st.sidebar.slider(
    "Minimum Revenue CAGR",
    0.0,
    30.0,
    10.0
)

pe = st.sidebar.slider(
    "Maximum P/E",
    0.0,
    150.0,
    40.0
)

# -----------------------------
# Apply Filters
# -----------------------------
# Remove unrealistic values
df = df[
    (df["return_on_equity_pct"] >= 0) &
    (df["return_on_equity_pct"] <= 100)
]
filtered = df[
    (df["return_on_equity_pct"] >= roe) &
    (df["debt_to_equity"] <= de) &
    (df["revenue_cagr"] >= rev) &
    (df["pe_ratio"] <= pe)
]

# -----------------------------
# KPIs
# -----------------------------

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Matching Companies", len(filtered))

with c2:
    st.metric(
        "Average ROE",
        round(filtered["return_on_equity_pct"].mean(),2)
        if len(filtered) else 0
    )

with c3:
    st.metric(
        "Average P/E",
        round(filtered["pe_ratio"].mean(),2)
        if len(filtered) else 0
    )

st.divider()

# -----------------------------
# Result Table
# -----------------------------

show = filtered[
    [
        "company_name",
        "return_on_equity_pct",
        "debt_to_equity",
        "revenue_cagr",
        "pe_ratio",
        "market_cap_crore"
    ]
]

show.columns = [
    "Company",
    "ROE %",
    "Debt/Equity",
    "Revenue CAGR",
    "P/E",
    "Market Cap"
]

st.dataframe(
    show.sort_values("ROE %", ascending=False),
    use_container_width=True,
    hide_index=True
)

# -----------------------------
# Download CSV
# -----------------------------

csv = show.to_csv(index=False)

st.download_button(
    "⬇ Download CSV",
    csv,
    "screened_companies.csv",
    "text/csv"
)