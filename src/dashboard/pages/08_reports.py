import streamlit as st
import pandas as pd

from utils.db import get_companies, get_annual_reports

st.set_page_config(page_title="Annual Reports", layout="wide")

st.title("📄 Annual Reports")


@st.cache_data(ttl=600)
def load_company_options():
    companies = get_companies()

    if companies.empty:
        return companies

    companies["display"] = (
        companies["company_name"] + " (" + companies["ticker"].astype(str) + ")"
    )

    return companies.sort_values("company_name")


companies_df = load_company_options()

if companies_df.empty:
    st.warning("No companies found.")
    st.stop()


selected_company = st.selectbox(
    "Search Company",
    companies_df["display"],
)

selected_row = companies_df[
    companies_df["display"] == selected_company
].iloc[0]

company_id = selected_row["id"]

st.divider()

st.subheader(
    f"📄 {selected_row['company_name']} — Annual Reports"
)

reports = get_annual_reports(company_id)

if reports.empty:
    st.info("No annual reports available.")
    st.stop()

reports = reports.sort_values(
    by="year",
    ascending=False
)

for _, row in reports.iterrows():

    year = row["year"]
    url = row["pdf_url"]

    col1, col2 = st.columns([1, 5])

    with col1:
        st.markdown(f"**{year}**")

    with col2:

        if pd.notna(url) and str(url).strip() != "":
            st.link_button(
                "📄 View Annual Report",
                url,
                use_container_width=True,
            )
        else:
            st.error("Report link not available")


st.divider()

st.caption(
    "Annual report links are fetched from the database."
)