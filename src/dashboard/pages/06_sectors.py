import pandas as pd
import plotly.express as px
import streamlit as st
from utils.db import (
    get_companies,
    get_market_cap,
    get_pl,
    get_ratios,
    get_sectors,
)

st.set_page_config(
    page_title="Sector Analysis",
    layout="wide",
)

st.title("🏭 Sector Analysis")

KPI_COLUMNS = {
    "return_on_equity_pct": "ROE %",
    "debt_to_equity": "Debt / Equity",
    "revenue_cagr": "Revenue CAGR %",
    "operating_profit_margin_pct": "OPM %",
}


@st.cache_data(ttl=600, show_spinner=False)
def load_sector_data() -> pd.DataFrame:

    companies = get_companies()
    sectors = get_sectors()

    # -----------------------------
    # Latest Financial Ratios
    # -----------------------------
    ratios = get_ratios()
    ratios = ratios[ratios["year"] != "TTM"]

    latest_ratios = ratios.sort_values("year").groupby("company_id").tail(1)

    # -----------------------------
    # Latest Revenue
    # -----------------------------
    revenue_rows = []

    for _, row in companies.iterrows():
        pl = get_pl(row["id"])

        if not pl.empty:
            latest = pl.sort_values("year").tail(1)

            revenue_rows.append(
                {
                    "company_id": row["id"],
                    "sales": latest.iloc[0]["sales"],
                }
            )

    revenue_df = pd.DataFrame(revenue_rows)

    # -----------------------------
    # Market Cap
    # -----------------------------
    market = get_market_cap()

    # -----------------------------
    # Merge all data
    # -----------------------------
    merged = companies.merge(
        sectors[["company_id", "broad_sector", "sub_sector"]],
        left_on="id",
        right_on="company_id",
        how="left",
    )

    merged = merged.merge(
        latest_ratios[
            [
                "company_id",
                "return_on_equity_pct",
                "debt_to_equity",
                "revenue_cagr",
                "operating_profit_margin_pct",
            ]
        ],
        left_on="id",
        right_on="company_id",
        how="left",
        suffixes=("", "_ratio"),
    )

    if not revenue_df.empty:
        merged = merged.merge(
            revenue_df,
            left_on="id",
            right_on="company_id",
            how="left",
            suffixes=("", "_rev"),
        )

    if not market.empty:
        merged = merged.merge(
            market,
            left_on="id",
            right_on="company_id",
            how="left",
            suffixes=("", "_market"),
        )

    return merged


df = load_sector_data()

if df.empty:
    st.warning("No data available.")
    st.stop()

if "broad_sector" not in df.columns:
    st.warning("Sector information not found.")
    st.stop()

sector_list = sorted(df["broad_sector"].dropna().unique())

if len(sector_list) == 0:
    st.warning("No sectors found.")
    st.stop()

selected_sector = st.selectbox(
    "Select Sector",
    sector_list,
)

sector_df = df[df["broad_sector"] == selected_sector].copy()

st.subheader(f"🏭 {selected_sector}")

required = [
    "sales",
    "return_on_equity_pct",
    "market_cap_crore",
]

missing = [c for c in required if c not in sector_df.columns]

if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

st.divider()

st.subheader("📈 Revenue vs ROE")

plot_df = sector_df.dropna(
    subset=[
        "sales",
        "return_on_equity_pct",
        "market_cap_crore",
    ]
)

if plot_df.empty:
    st.info("No companies have complete Revenue, ROE and Market Cap data.")
else:
    fig = px.scatter(
        plot_df,
        x="sales",
        y="return_on_equity_pct",
        size="market_cap_crore",
        hover_name="company_name",
        color="sub_sector",
        size_max=50,
        labels={
            "sales": "Revenue (₹ Cr)",
            "return_on_equity_pct": "ROE (%)",
            "market_cap_crore": "Market Cap (₹ Cr)",
        },
        title=f"{selected_sector} Companies",
    )

    fig.update_layout(
        xaxis_title="Revenue (₹ Cr)",
        yaxis_title="ROE (%)",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

st.subheader("📊 Sector Median KPIs")

available_kpis = [c for c in KPI_COLUMNS if c in sector_df.columns]

if not available_kpis:
    st.info("No KPI data available.")
else:

    median_df = sector_df[available_kpis].median(numeric_only=True).reset_index()

    median_df.columns = ["Metric", "Median"]

    median_df["Metric"] = median_df["Metric"].map(KPI_COLUMNS)

    fig2 = px.bar(
        median_df,
        x="Metric",
        y="Median",
        text="Median",
        title=f"{selected_sector} Median KPIs",
    )

    fig2.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
    )

    fig2.update_layout(
        xaxis_title="",
        yaxis_title="Median Value",
    )

    st.plotly_chart(
        fig2,
        use_container_width=True,
    )

    st.dataframe(
        median_df,
        use_container_width=True,
        hide_index=True,
    )

st.divider()

st.subheader("🏢 Companies in Sector")

display_cols = [
    "company_name",
    "sub_sector",
]

optional_cols = [
    "sales",
    "return_on_equity_pct",
    "debt_to_equity",
    "operating_profit_margin_pct",
    "revenue_cagr",
    "market_cap_crore",
]

for col in optional_cols:
    if col in sector_df.columns:
        display_cols.append(col)

st.dataframe(
    sector_df[display_cols].sort_values("company_name"),
    use_container_width=True,
    hide_index=True,
)

st.success(f"Total Companies: {len(sector_df)}")
