import streamlit as st
import plotly.express as px

from utils.db import (
    get_sectors,
    get_companies
)

st.set_page_config(
    page_title="Sector Analysis",
    layout="wide"
)

st.title("🏭 Sector Analysis")

sectors = get_sectors()
companies = get_companies()

df = sectors.merge(
    companies,
    left_on="company_id",
    right_on="id",
    how="left"
)

st.metric(
    "Total Companies",
    len(df)
)

st.divider()

sector_count = (
    df.groupby("broad_sector")
      .size()
      .reset_index(name="Companies")
)

fig = px.pie(
    sector_count,
    names="broad_sector",
    values="Companies",
    hole=0.45,
    title="Companies by Sector"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.divider()

st.subheader("Sector-wise Company List")

st.dataframe(
    df[
        [
            "company_name",
            "broad_sector",
            "sub_sector"
        ]
    ].rename(
        columns={
            "company_name":"Company",
            "broad_sector":"Sector",
            "sub_sector":"Sub Sector"
        }
    ),
    use_container_width=True,
    hide_index=True
)