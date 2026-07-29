import streamlit as st
import plotly.express as px

from utils.db import (
    get_companies,
    get_ratios,
    get_market_cap,
    get_sectors
)

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide"
)

st.title("📈 Nifty 100 Analytics Dashboard")

# Sidebar
year = st.sidebar.selectbox(
    "Select Financial Year",
    [
        "2019-03",
        "2020-03",
        "2021-03",
        "2022-03",
        "2023-03",
        "2024-03"
    ],
    index=5
)

#load data
companies = get_companies()
ratios = get_ratios(year=year)
market_year = year[:4]
market = get_market_cap(market_year)
sectors = get_sectors()


# KPI Calculations
total_companies = len(companies)

avg_roe = (
    round(ratios["return_on_equity_pct"].mean(), 2)
    if not ratios.empty else 0
)

median_de = (
    round(ratios["debt_to_equity"].median(), 2)
    if not ratios.empty else 0
)

median_rev = (
    round(ratios["revenue_cagr"].median(), 2)
    if not ratios.empty else 0
)

debt_free = (
    len(ratios[ratios["debt_to_equity"] <= 0])
    if not ratios.empty else 0
)

if not market.empty:
    median_pe = float(market["pe_ratio"].median())
else:
    median_pe = 0

# KPI Cards
c1, c2, c3 = st.columns(3)
c4, c5, c6 = st.columns(3)

c1.metric("Total Companies", total_companies)
c2.metric("Average ROE", avg_roe)
c3.metric(
    "Median P/E",
    f"{median_pe:.2f}"
)

c4.metric("Median D/E", median_de)
c5.metric("Median Revenue CAGR", median_rev)
c6.metric("Debt-Free Companies", debt_free)

st.divider()

# Sector Distribution
st.subheader("📊 Sector Distribution")

if not sectors.empty:

    sector_count = (
        sectors.groupby("broad_sector")
        .size()
        .reset_index(name="Companies")
    )

    fig = px.pie(
        sector_count,
        names="broad_sector",
        values="Companies",
        hole=0.45,
        title="Companies by Broad Sector"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No sector data available.")

st.divider()

# Top 5 Companies by ROE
st.subheader("🏆 Top 5 Companies by ROE")

if not ratios.empty:

    top5 = (
        ratios.sort_values(
            by="return_on_equity_pct",
            ascending=False
        )
        .head(5)
    )

    top5 = top5.merge(
        companies,
        left_on="company_id",
        right_on="id"
    )

    st.dataframe(
        top5[
            [
                "company_name",
                "return_on_equity_pct",
                "debt_to_equity",
                "revenue_cagr"
            ]
        ],
        use_container_width=True
    )

else:
    st.warning("No financial ratio data available.")

st.success("✅ Home Screen Loaded Successfully")