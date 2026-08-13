import pandas as pd
import plotly.express as px
import streamlit as st
from utils.db import get_companies, get_market_cap, get_ratios

st.set_page_config(page_title="Stock Screener", layout="wide")
st.title("📊 Nifty 100 Stock Screener")


SLIDERS = [
    {
        "key": "roe_min",
        "label": "ROE — min (%)",
        "column": "return_on_equity_pct",
        "kind": "min",
        "lo": 0.0,
        "hi": 60.0,
        "default": 0.0,
    },
    {
        "key": "de_max",
        "label": "Debt/Equity — max",
        "column": "debt_to_equity",
        "kind": "max",
        "lo": 0.0,
        "hi": 5.0,
        "default": 5.0,
    },
    {
        "key": "fcf_min",
        "label": "FCF — min (₹ Cr)",
        "column": "fcf",
        "kind": "min",
        "lo": -500.0,
        "hi": 5000.0,
        "default": -500.0,
    },
    {
        "key": "rev_min",
        "label": "Revenue CAGR — min (%)",
        "column": "revenue_cagr",
        "kind": "min",
        "lo": -10.0,
        "hi": 40.0,
        "default": -10.0,
    },
    {
        "key": "pat_min",
        "label": "PAT CAGR — min (%)",
        "column": "pat_cagr",
        "kind": "min",
        "lo": -10.0,
        "hi": 40.0,
        "default": -10.0,
    },
    {
        "key": "opm_min",
        "label": "OPM — min (%)",
        "column": "operating_profit_margin_pct",
        "kind": "min",
        "lo": 0.0,
        "hi": 60.0,
        "default": 0.0,
    },
    {
        "key": "pe_max",
        "label": "P/E — max",
        "column": "pe_ratio",
        "kind": "max",
        "lo": 0.0,
        "hi": 150.0,
        "default": 150.0,
    },
    {
        "key": "pb_max",
        "label": "P/B — max",
        "column": "pb_ratio",
        "kind": "max",
        "lo": 0.0,
        "hi": 50.0,
        "default": 50.0,
    },
    {
        "key": "divy_min",
        "label": "Dividend Yield — min (%)",
        "column": "dividend_yield_pct",
        "kind": "min",
        "lo": 0.0,
        "hi": 10.0,
        "default": 0.0,
    },
    {
        "key": "icr_min",
        "label": "Interest Coverage — min",
        "column": "interest_coverage_ratio",
        "kind": "min",
        "lo": 0.0,
        "hi": 30.0,
        "default": 0.0,
    },
]

PRESETS = {
    "🏆 Quality": {
        "roe_min": 20,
        "de_max": 0.5,
        "fcf_min": 0,
        "rev_min": 10,
        "pat_min": 10,
        "opm_min": 15,
        "pe_max": 150,
        "pb_max": 50,
        "divy_min": 0,
        "icr_min": 3,
    },
    "💰 Value": {
        "roe_min": 10,
        "de_max": 1.5,
        "fcf_min": 0,
        "rev_min": -10,
        "pat_min": -10,
        "opm_min": 0,
        "pe_max": 15,
        "pb_max": 2,
        "divy_min": 0,
        "icr_min": 1,
    },
    "🚀 Growth": {
        "roe_min": 15,
        "de_max": 2.0,
        "fcf_min": -500,
        "rev_min": 20,
        "pat_min": 20,
        "opm_min": 0,
        "pe_max": 150,
        "pb_max": 50,
        "divy_min": 0,
        "icr_min": 1,
    },
    "💵 Dividend": {
        "roe_min": 10,
        "de_max": 1.5,
        "fcf_min": 0,
        "rev_min": -10,
        "pat_min": -10,
        "opm_min": 0,
        "pe_max": 150,
        "pb_max": 50,
        "divy_min": 3,
        "icr_min": 2,
    },
    "🛡️ Debt-Free": {
        "roe_min": 0,
        "de_max": 0.1,
        "fcf_min": -500,
        "rev_min": -10,
        "pat_min": -10,
        "opm_min": 0,
        "pe_max": 150,
        "pb_max": 50,
        "divy_min": 0,
        "icr_min": 0,
    },
    "🔄 Turnaround": {
        "roe_min": 5,
        "de_max": 3.0,
        "fcf_min": -500,
        "rev_min": -10,
        "pat_min": 0,
        "opm_min": 0,
        "pe_max": 150,
        "pb_max": 50,
        "divy_min": 0,
        "icr_min": 1,
    },
}


def apply_preset(values: dict) -> None:
    """Callback: seed session_state before the sliders render this rerun."""
    for slider in SLIDERS:
        st.session_state[slider["key"]] = values[slider["key"]]


def reset_sliders() -> None:
    for slider in SLIDERS:
        st.session_state[slider["key"]] = slider["default"]


@st.cache_data(ttl=600, show_spinner=False)
def load_screener_data() -> pd.DataFrame:
    ratios = get_ratios()
    companies = get_companies()
    market = get_market_cap("2024")

    ratios = ratios[ratios["year"] != "TTM"]
    latest = ratios.sort_values("year").groupby("company_id").tail(1)

    merged = latest.merge(
        companies, left_on="company_id", right_on="id", how="left", suffixes=("", "_c")
    ).merge(market, on="company_id", how="left")

    margin_col = (
        "net_profit_margin_pct"
        if "net_profit_margin_pct" in merged.columns
        else "operating_profit_margin_pct"
    )
    merged["quality_score"] = (
        merged["return_on_equity_pct"].fillna(0) * 0.40
        + merged["revenue_cagr"].fillna(0) * 0.30
        + merged[margin_col].fillna(0) * 0.20
        - merged["debt_to_equity"].fillna(0) * 10
    )
    return merged


df = load_screener_data()

if df.empty:
    st.warning("No data available — check the database connection.")
    st.stop()


# ---------------------------------------------------------------------------
# Preset buttons
# ---------------------------------------------------------------------------

st.subheader("⚡ Quick Screeners")

cols = st.columns(len(PRESETS) + 1)
for col, (name, values) in zip(cols, PRESETS.items()):
    col.button(name, on_click=apply_preset, args=(values,), use_container_width=True)
cols[-1].button("🔄 Reset", on_click=reset_sliders, use_container_width=True)


# ---------------------------------------------------------------------------
# Sidebar: sector + search + 10 sliders
# ---------------------------------------------------------------------------

st.sidebar.header("Filters")

sector_list = ["All"]
if "broad_sector" in df.columns:
    sector_list += sorted(df["broad_sector"].dropna().unique().tolist())
selected_sector = st.sidebar.selectbox("Sector", sector_list)

search = st.sidebar.text_input("Search Company")

st.sidebar.divider()

slider_values = {}
for s in SLIDERS:
    slider_values[s["key"]] = st.sidebar.slider(
        s["label"],
        s["lo"],
        s["hi"],
        value=s["default"],
        key=s["key"],
    )


# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------

filtered = df.copy()

for s in SLIDERS:
    col = s["column"]
    if col not in filtered.columns:
        continue
    threshold = slider_values[s["key"]]
    mask = filtered[col].notna()
    if s["kind"] == "min":
        mask &= filtered[col] >= threshold
    else:
        mask &= filtered[col] <= threshold
    filtered = filtered[mask]

if selected_sector != "All":
    filtered = filtered[filtered["broad_sector"] == selected_sector]

if search:
    filtered = filtered[
        filtered["company_name"].str.contains(search, case=False, na=False)
    ]

st.info(f"**{len(filtered)}** companies match your filters")
st.divider()


# ---------------------------------------------------------------------------
# KPI summary
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
c1.metric("Matching Companies", len(filtered))
c2.metric(
    "Average ROE (%)",
    round(filtered["return_on_equity_pct"].mean(), 2) if not filtered.empty else "N/A",
)
c3.metric(
    "Average P/E",
    round(filtered["pe_ratio"].mean(), 2) if not filtered.empty else "N/A",
)
c4.metric(
    "Avg Quality Score",
    round(filtered["quality_score"].mean(), 2) if not filtered.empty else "N/A",
)

st.divider()


# ---------------------------------------------------------------------------
# Results table
# ---------------------------------------------------------------------------

st.subheader("📋 Screened Companies")

DISPLAY_COLUMNS = {
    "company_id": "Company ID",
    "company_name": "Company",
    "broad_sector": "Sector",
    "quality_score": "Quality Score",
    "return_on_equity_pct": "ROE %",
    "debt_to_equity": "Debt/Equity",
    "fcf": "FCF (₹ Cr)",
    "revenue_cagr": "Revenue CAGR %",
    "pat_cagr": "PAT CAGR %",
    "operating_profit_margin_pct": "OPM %",
    "pe_ratio": "P/E",
    "pb_ratio": "P/B",
    "dividend_yield_pct": "Dividend Yield %",
    "interest_coverage_ratio": "ICR",
    "market_cap_crore": "Market Cap (₹ Cr)",
}

available = [c for c in DISPLAY_COLUMNS if c in filtered.columns]
show = filtered[available].rename(columns=DISPLAY_COLUMNS)

if "Quality Score" in show.columns:
    show = show.sort_values("Quality Score", ascending=False)

for col in show.select_dtypes(include="number").columns:
    show[col] = show[col].round(2)

st.dataframe(show.fillna("N/A"), use_container_width=True, hide_index=True)

csv = show.to_csv(index=False)
st.download_button(
    "⬇ Download Filtered CSV",
    data=csv,
    file_name="screened_companies.csv",
    mime="text/csv",
)

st.divider()


# ---------------------------------------------------------------------------
# Top 10 chart + Top 5 table
# ---------------------------------------------------------------------------

if not filtered.empty:
    st.subheader("🏆 Top 10 by Quality Score")

    top = filtered.sort_values("quality_score", ascending=False).head(10)
    fig = px.bar(
        top,
        x="company_name",
        y="quality_score",
        text="quality_score",
        title="Top 10 Companies by Quality Score",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        xaxis_title="Company", yaxis_title="Quality Score", xaxis_tickangle=-45
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🥇 Top 5 Companies")

    top5 = top[
        [
            "company_name",
            "quality_score",
            "return_on_equity_pct",
            "revenue_cagr",
            "pe_ratio",
        ]
    ].copy()
    top5.columns = ["Company", "Quality Score", "ROE %", "Revenue CAGR", "P/E"]
    st.dataframe(top5, use_container_width=True, hide_index=True)
else:
    st.warning("No companies match the selected filters.")
