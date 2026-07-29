import streamlit as st
import plotly.express as px

from utils.db import (
    get_companies,
    get_pl
)

st.set_page_config(
    page_title="Financial Trends",
    layout="wide"
)

st.title("📈 Financial Trends")

companies = get_companies()

company = st.selectbox(
    "Select Company",
    companies["company_name"]
)

company_id = companies.loc[
    companies["company_name"] == company,
    "id"
].iloc[0]

pl = get_pl(company_id)

if not pl.empty:

    pl = (
        pl
        .sort_values("year")
    )

    st.subheader("Revenue Trend")

    fig = px.line(
        pl,
        x="year",
        y="sales",
        markers=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Net Profit Trend")

    fig = px.bar(
        pl,
        x="year",
        y="net_profit"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Operating Profit")

    fig = px.line(
        pl,
        x="year",
        y="operating_profit",
        markers=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:
    st.warning("No financial data found.")