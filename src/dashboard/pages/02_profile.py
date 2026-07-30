import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.db import (
    get_companies,
    get_company,
    get_ratios,
    get_pl,
    get_pros_cons,
    get_sectors
)
def safe(value):
    try:
        if value is None:
            return "N/A"

        if str(value) == "nan":
            return "N/A"

        return round(float(value), 2)

    except:
        return "N/A"
    
st.set_page_config(
    page_title="Company Profile",
    layout="wide"
)

st.title("🏢 Company Profile")

# -------------------------
# Load Data
# -------------------------

companies = get_companies()
sectors = get_sectors()

# -------------------------
# Company Search
# -------------------------

company_name = st.selectbox(
    "🔍 Search Company",
    companies["company_name"].tolist()
)

if not company_name:
    st.warning("Ticker not found — please try another.")
    st.stop()

company_id = companies.loc[
    companies["company_name"] == company_name,
    "id"
].iloc[0]

company = get_company(company_id)
ratios = get_ratios(company_id)
pl = get_pl(company_id)
pros = get_pros_cons(company_id)

if company.empty:
    st.warning("Ticker not found — please try another.")
    st.stop()

info = company.iloc[0]

# -------------------------
# Sector Information
# -------------------------

sector = "N/A"
sub_sector = "N/A"

if not sectors.empty:
    sec = sectors[sectors["company_id"] == company_id]

    if not sec.empty:
        sector = sec.iloc[0]["broad_sector"]
        sub_sector = sec.iloc[0]["sub_sector"]

# -------------------------
# Company Card
# -------------------------

st.subheader(info["company_name"])

left, right = st.columns([2, 1])

with left:

    st.write("### Company Information")

    st.write(f"**Sector:** {sector}")
    st.write(f"**Sub Sector:** {sub_sector}")

    website = str(info["website"])

    if website.startswith("http"):
        st.markdown(f"**Website:** [{website}]({website})")
    else:
        st.write(f"**Website:** {website}")

    if "nse_profile" in info.index:
        st.write(f"**NSE:** {info['nse_profile']}")

    st.write("### About Company")
    st.write(info["about_company"])

with right:

    st.metric("ROE", info["roe_percentage"])
    st.metric("ROCE", info["roce_percentage"])
    st.metric("Face Value", info["face_value"])
    st.metric("Book Value", info["book_value"])

st.divider()

# -------------------------
# Latest Financial KPIs
# -------------------------
if not ratios.empty:

    latest = (
        ratios[ratios["year"] != "TTM"]
        .sort_values("year")
        .iloc[-1]
    )

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    npm = latest.get("net_profit_margin_pct")

    if npm is None:
        npm = latest.get("operating_profit_margin_pct", 0)

    c1.metric("ROE (%)", safe(latest["return_on_equity_pct"]))
    c2.metric("Debt / Equity", safe(latest["debt_to_equity"]))
    c3.metric("Net Profit Margin", safe(npm))
    c4.metric("Revenue CAGR", safe(latest["revenue_cagr"]))
    c5.metric("Free Cash Flow", safe(latest["fcf"]))
    c6.metric("EPS", safe(latest["earnings_per_share"]))
st.divider()


# ==========================
# Revenue & Net Profit Trends
# ==========================

if not pl.empty:

    pl = pl[pl["year"] != "TTM"]
    pl = pl.sort_values("year")

    st.subheader("📈 Revenue & Net Profit Trend")

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(
            pl,
            x="year",
            y="sales",
            title="Revenue (10 Years)",
            text_auto=True
        )

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Revenue"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:

        fig = px.bar(
            pl,
            x="year",
            y="net_profit",
            title="Net Profit (10 Years)",
            text_auto=True
        )

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Net Profit"
        )

        st.plotly_chart(fig, use_container_width=True)

else:

    st.info("Revenue and Profit data not available.")

st.divider()

# ==========================
# ROE vs ROCE Trend
# ==========================

st.subheader("📊 ROE vs ROCE Trend")

if not ratios.empty:

    chart = (
        ratios[ratios["year"] != "TTM"]
        .sort_values("year")
    )

    fig = px.line(
        chart,
        x="year",
        y="return_on_equity_pct",
        markers=True,
        title="ROE Trend"
    )

    fig.add_scatter(
        x=chart["year"],
        y=[info["roce_percentage"]] * len(chart),
        mode="lines+markers",
        name="ROCE"
    )

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Percentage (%)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.info("Financial ratio data not available.")

st.divider()

# ==========================
# Pros & Cons
# ==========================

st.subheader("✅ Pros & ❌ Cons")

if pros.empty:

    st.info("No Pros & Cons available.")

else:

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### ✅ Pros")

        pros_list = str(pros.iloc[0]["pros"]).split("\n")

        for item in pros_list:
            if item.strip():
                st.success(item.strip())

    with col2:

        st.markdown("### ❌ Cons")

        cons_list = str(pros.iloc[0]["cons"]).split("\n")

        for item in cons_list:
            if item.strip():
                st.error(item.strip())

st.divider()

# ==========================
# Additional Information
# ==========================

with st.expander("📋 Additional Company Details"):

    c1, c2 = st.columns(2)

    with c1:

        website = str(info["website"])

        if website.startswith("http"):
            st.markdown(f"**Website:** [{website}]({website})")
        else:
            st.write("**Website:**", website)

        if "nse_profile" in info.index:
            st.write("**NSE Profile:**", info["nse_profile"])

        if "bse_profile" in info.index:
            st.write("**BSE Profile:**", info["bse_profile"])

    with c2:

        if "face_value" in info.index:
            st.write("**Face Value:**", info["face_value"])

        if "book_value" in info.index:
            st.write("**Book Value:**", info["book_value"])

st.divider()

st.success("Company Profile Loaded Successfully")