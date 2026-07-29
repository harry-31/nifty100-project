import streamlit as st
import plotly.express as px

from utils.db import (
    get_companies,
    get_company,
    get_ratios,
    get_pl,
    get_pros_cons
)
st.set_page_config(
    page_title="Company Profile",
    layout="wide"
)

st.title(" Company Profile")

companies = get_companies()

company_name = st.selectbox(
    "Select Company",
    companies["company_name"]
)

company_id = companies.loc[
    companies["company_name"] == company_name,
    "id"
].iloc[0]
company = get_company(company_id)
ratios = get_ratios(company_id)
pl = get_pl(company_id)
pros = get_pros_cons(company_id)
st.subheader(company.iloc[0]["company_name"])
left, right = st.columns([2,1])

with left:
    st.write("**Website:**", company.iloc[0]["website"])
    st.write("**About Company:**")
    st.write(company.iloc[0]["about_company"])

with right:
    st.metric("ROE", company.iloc[0]["roe_percentage"])
    st.metric("ROCE", company.iloc[0]["roce_percentage"])
    st.metric("Face Value", company.iloc[0]["face_value"])


        
if not ratios.empty:
    latest = (
    ratios[ratios["year"] != "TTM"]   # TTM row hata do
    .sort_values("year")
    .iloc[-1]
)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("ROE (%)", round(latest["return_on_equity_pct"], 2))

    with c2:
        st.metric("Debt / Equity", round(latest["debt_to_equity"], 2))

    with c3:
        st.metric("Revenue CAGR", round(latest["revenue_cagr"], 2))

    with c4:
        st.metric("Free Cash Flow", round(latest["free_cash_flow_cr"], 2))
        
# Revenue Trend
if not pl.empty:
    pl = pl.sort_values("year")
    fig = px.line(
        pl,
        x="year",
        y="sales",
        markers=True,
        title="Revenue Trend"
    )
    st.plotly_chart(fig, use_container_width=True)

# Net Profit Trend
if not pl.empty:
    pl = pl.sort_values("year")
    fig = px.bar(
        pl,
        x="year",
        y="net_profit",
        title="Net Profit Trend"
    )
    st.plotly_chart(fig, use_container_width=True)
    
st.subheader("Pros & Cons")

if pros.empty:
    st.info("No Pros & Cons available.")
else:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ Pros")
        st.success(pros.iloc[0]["pros"])

    with col2:
        st.markdown("###  Cons")
        st.error(pros.iloc[0]["cons"])
        
