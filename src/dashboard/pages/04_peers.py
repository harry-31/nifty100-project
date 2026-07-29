import streamlit as st
import pandas as pd

from utils.db import (
    get_companies,
    get_ratios
)

st.set_page_config(
    page_title="Peer Comparison",
    layout="wide"
)

st.title("👥 Peer Comparison")

companies = get_companies()
ratios = get_ratios()

# Remove TTM
ratios = ratios[ratios["year"] != "TTM"]

# Latest record for every company
ratios = (
    ratios
    .sort_values("year")
    .groupby("company_id")
    .tail(1)
)

# Merge company names
df = ratios.merge(
    companies,
    left_on="company_id",
    right_on="id",
    how="left"
)

company = st.selectbox(
    "Select Company",
    df["company_name"].sort_values().unique()
)

selected = df[df["company_name"] == company]

st.divider()

st.subheader("Company Metrics")

st.dataframe(
    selected[
        [
            "company_name",
            "return_on_equity_pct",
            "debt_to_equity",
            "revenue_cagr",
            "pat_cagr",
            "eps_cagr"
        ]
    ].rename(
        columns={
            "company_name":"Company",
            "return_on_equity_pct":"ROE %",
            "debt_to_equity":"Debt/Equity",
            "revenue_cagr":"Revenue CAGR",
            "pat_cagr":"PAT CAGR",
            "eps_cagr":"EPS CAGR"
        }
    ),
    use_container_width=True,
    hide_index=True
)

st.divider()

st.subheader("Top 10 Companies by ROE")
# Remove unrealistic ROE values
df = df[
    (df["return_on_equity_pct"] >= 0) &
    (df["return_on_equity_pct"] <= 100)
]
top = df.sort_values(
    "return_on_equity_pct",
    ascending=False
).head(10)

st.dataframe(
    top[
        [
            "company_name",
            "return_on_equity_pct",
            "debt_to_equity",
            "revenue_cagr"
        ]
    ].rename(
        columns={
            "company_name":"Company",
            "return_on_equity_pct":"ROE %",
            "debt_to_equity":"Debt/Equity",
            "revenue_cagr":"Revenue CAGR"
        }
    ),
    use_container_width=True,
    hide_index=True
)