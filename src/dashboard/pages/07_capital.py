import streamlit as st
import plotly.express as px

from utils.db import (
    get_market_cap,
    get_companies
)

st.set_page_config(
    page_title="Capital Allocation",
    layout="wide"
)

st.title("💰 Capital Allocation")

market = get_market_cap("2024")
companies = get_companies()

df = market.merge(
    companies,
    left_on="company_id",
    right_on="id",
    how="left"
)

st.metric(
    "Total Companies",
    len(df)
)

st.metric(
    "Total Market Cap",
    f"{df['market_cap_crore'].sum():,.0f} Cr"
)

st.divider()

st.subheader("Top 20 Companies by Market Cap")

top = (
    df.sort_values(
        "market_cap_crore",
        ascending=False
    )
    .head(20)
)

fig = px.bar(
    top,
    x="company_name",
    y="market_cap_crore",
    text_auto=".2s",
    title="Top Companies by Market Cap"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.divider()

st.subheader("Market Capitalisation Table")

st.dataframe(
    top[
        [
            "company_name",
            "market_cap_crore",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield_pct"
        ]
    ].rename(
        columns={
            "company_name":"Company",
            "market_cap_crore":"Market Cap",
            "pe_ratio":"P/E",
            "pb_ratio":"P/B",
            "dividend_yield_pct":"Dividend Yield"
        }
    ),
    use_container_width=True,
    hide_index=True
)