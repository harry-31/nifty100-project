import streamlit as st

from utils.db import (
    get_companies
)

st.set_page_config(
    page_title="Reports",
    layout="wide"
)

st.title("📄 Company Reports")

companies = get_companies()

company = st.selectbox(
    "Select Company",
    companies["company_name"]
)

row = companies[
    companies["company_name"] == company
].iloc[0]

st.divider()

c1, c2 = st.columns(2)

with c1:
    st.subheader("Company Details")

    st.write("**Company** :", row["company_name"])
    st.write("**Website** :", row["website"])
    st.write("**ROE** :", row["roe_percentage"])
    st.write("**ROCE** :", row["roce_percentage"])

with c2:
    st.subheader("About Company")

    st.write(row["about_company"])

st.divider()

st.subheader("External Links")

st.markdown(
    f"""
- 🌐 Website : {row["website"]}

- 📈 NSE Profile : {row["nse_profile"]}

- 📊 BSE Profile : {row["bse_profile"]}
"""
)

st.divider()

st.success("Reports page loaded successfully.")