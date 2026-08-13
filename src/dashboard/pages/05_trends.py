import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.db import get_companies, get_ratios

st.set_page_config(page_title="Trend Analysis", layout="wide")
st.title("📈 Trend Analysis")


# ---------------------------------------------------------------------------
# Metric catalogue. "axis" groups metrics that share a comparable scale —
# the first selected metric's axis group becomes the primary y-axis, any
# metric from a different group goes on the secondary y-axis.
# ---------------------------------------------------------------------------

METRICS = {
    "ROE %": {
        "column": "return_on_equity_pct",
        "axis": "pct",
    },
    "Net Margin %": {
        "column": "net_profit_margin_pct",
        "axis": "pct",
    },
    "OPM %": {
        "column": "operating_profit_margin_pct",
        "axis": "pct",
    },
    "Revenue CAGR %": {
        "column": "revenue_cagr",
        "axis": "pct",
    },
    "PAT CAGR %": {
        "column": "pat_cagr",
        "axis": "pct",
    },
    "Debt/Equity": {
        "column": "debt_to_equity",
        "axis": "ratio",
    },
    "Interest Coverage": {
        "column": "interest_coverage_ratio",
        "axis": "ratio",
    },
    "FCF (₹ Cr)": {
        "column": "fcf",
        "axis": "value",
    },
}

COLORS = ["#2563EB", "#DC2626", "#059669"]  # up to 3 metric lines


# ---------------------------------------------------------------------------
# Company search
# ---------------------------------------------------------------------------


@st.cache_data(ttl=600, show_spinner=False)
def load_company_options() -> pd.DataFrame:
    companies = get_companies()
    companies["display"] = companies["company_name"] + " (" + companies["ticker"] + ")"
    return companies.sort_values("company_name")


companies_df = load_company_options()

if companies_df.empty:
    st.warning("No companies found.")
    st.stop()

selected_display = st.selectbox(
    "Search Company",
    companies_df["display"].tolist(),
    help="Type to filter by company name or ticker",
)
selected_row = companies_df[companies_df["display"] == selected_display].iloc[0]
company_id = selected_row["id"]

st.divider()


# ---------------------------------------------------------------------------
# Metric selector (max 3)
# ---------------------------------------------------------------------------

selected_labels = st.multiselect(
    "Metrics to overlay (up to 3)",
    options=list(METRICS.keys()),
    default=["ROE %"],
    max_selections=3,
)

if not selected_labels:
    st.info("Select at least one metric to plot.")
    st.stop()


# ---------------------------------------------------------------------------
# Load 10-year history for this company
# ---------------------------------------------------------------------------


@st.cache_data(ttl=600, show_spinner=False)
def load_history(company_id: str) -> pd.DataFrame:
    hist = get_ratios(company_id=company_id)
    hist = hist[hist["year"] != "TTM"]
    return hist.sort_values("year").tail(10)


history = load_history(company_id)

if history.empty:
    st.warning(f"No historical data available for **{selected_row['company_name']}**.")
    st.stop()

if len(history) < 10:
    st.caption(f"ℹ️ Only {len(history)} year(s) of data available for this company.")


# ---------------------------------------------------------------------------
# Build overlay chart
# ---------------------------------------------------------------------------

st.subheader(f"{selected_row['company_name']} — {len(history)}-Year Trend")

primary_axis_group = METRICS[selected_labels[0]]["axis"]

fig = go.Figure()

for i, label in enumerate(selected_labels):
    meta = METRICS[label]
    column = meta["column"]

    if column not in history.columns:
        st.warning(f"Column `{column}` for **{label}** not found — skipping.")
        continue

    series = history[["year", column]].copy()
    yoy_pct = series[column].pct_change() * 100
    yoy_text = [""] + [f"{v:+.1f}%" for v in yoy_pct.iloc[1:]]

    on_secondary = meta["axis"] != primary_axis_group

    fig.add_trace(
        go.Scatter(
            x=series["year"],
            y=series[column],
            mode="lines+markers+text",
            name=label,
            text=yoy_text,
            textposition="top center",
            textfont={"size": 10, "color": COLORS[i % len(COLORS)]},
            line={"color": COLORS[i % len(COLORS)], "width": 2},
            marker={"size": 7},
            yaxis="y2" if on_secondary else "y1",
        )
    )

fig.update_layout(
    xaxis={"title": "Year"},
    yaxis={"title": selected_labels[0]},
    yaxis2={
        "title": "Secondary scale",
        "overlaying": "y",
        "side": "right",
        "showgrid": False,
    },
    legend={
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "right",
        "x": 1,
    },
    hovermode="x unified",
    margin={"t": 60, "b": 40},
)

st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Labels above each point show year-over-year % change. Metrics on a different scale from the first selection are plotted on the right-hand axis."
)

st.divider()


# ---------------------------------------------------------------------------
# Underlying data table
# ---------------------------------------------------------------------------

st.subheader("📋 Underlying Data")

table_cols = ["year"] + [
    METRICS[l]["column"]
    for l in selected_labels
    if METRICS[l]["column"] in history.columns
]
table = history[table_cols].copy()
table.columns = ["Year"] + [
    l for l in selected_labels if METRICS[l]["column"] in history.columns
]

for col in table.select_dtypes(include="number").columns:
    table[col] = table[col].round(2)

st.dataframe(table.fillna("N/A"), use_container_width=True, hide_index=True)
