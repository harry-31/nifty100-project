import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.db import get_companies, get_peers, get_ratios

st.set_page_config(page_title="Peer Comparison", layout="wide")
st.title("🧭 Peer Comparison")


# ---------------------------------------------------------------------------
# 8 metrics shown on the radar / table.
# "higher_is_better" controls normalisation direction so the radar always
# reads as "bigger area = stronger" regardless of the metric's natural sign.
# ---------------------------------------------------------------------------

METRICS = [
    {"column": "return_on_equity_pct", "label": "ROE %", "higher_is_better": True},
    {
        "column": "return_on_capital_employed_pct",
        "label": "ROCE %",
        "higher_is_better": True,
    },
    {
        "column": "net_profit_margin_pct",
        "label": "Net Margin %",
        "higher_is_better": True,
    },
    {
        "column": "operating_profit_margin_pct",
        "label": "OPM %",
        "higher_is_better": True,
    },
    {"column": "debt_to_equity", "label": "Debt/Equity", "higher_is_better": False},
    {"column": "revenue_cagr", "label": "Revenue CAGR %", "higher_is_better": True},
    {"column": "pe_ratio", "label": "P/E", "higher_is_better": False},
    {
        "column": "dividend_yield_pct",
        "label": "Dividend Yield %",
        "higher_is_better": True,
    },
]


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------


@st.cache_data(ttl=600, show_spinner=False)
def load_peer_groups() -> list[str]:
    peers = get_peers()

    if peers.empty:
        return []

    return sorted(peers["peer_group_name"].dropna().unique().tolist())


@st.cache_data(ttl=600, show_spinner=False)
def load_group_metrics(group_name: str) -> pd.DataFrame:
    peers = get_peers(group_name)

    if peers.empty:
        return pd.DataFrame()

    companies = get_companies()

    ratios = get_ratios()
    ratios = ratios[ratios["year"] != "TTM"]
    latest = ratios.sort_values("year").groupby("company_id").tail(1)

    df = peers.merge(companies, left_on="company_id", right_on="id", how="left")
    df = df.merge(latest, on="company_id", how="left")

    return df


groups = load_peer_groups()

if not groups:
    st.warning(
        "No peer groups found. Check that the `sectors` table has a `peer_group` column populated."
    )
    st.stop()

col_a, col_b = st.columns([2, 2])

with col_a:
    selected_group = st.selectbox("Peer Group", groups)

group_df = load_group_metrics(selected_group)

if group_df.empty:
    st.warning(f"No companies found in peer group **{selected_group}**.")
    st.stop()

with col_b:
    benchmark_company = st.selectbox(
        "Benchmark Company", group_df["company_name"].tolist()
    )

st.divider()


# ---------------------------------------------------------------------------
# Radar chart: benchmark vs peer group average
# ---------------------------------------------------------------------------

st.subheader(f"📡 {benchmark_company} vs. {selected_group} Average")

available_metrics = [m for m in METRICS if m["column"] in group_df.columns]

if not available_metrics:
    st.warning("None of the expected metric columns were found in the ratios table.")
else:
    benchmark_row = group_df[group_df["company_name"] == benchmark_company].iloc[0]
    group_avg = group_df[[m["column"] for m in available_metrics]].mean()

    def normalise(value: float, column: str, higher_is_better: bool) -> float:
        """Min-max scale a metric to 0-100 within the peer group, flipping
        the axis for 'lower is better' metrics so radar area is always
        interpretable as 'more = stronger'."""
        series = group_df[column].dropna()
        if series.empty or pd.isna(value):
            return 0.0
        lo, hi = series.min(), series.max()
        if hi == lo:
            return 50.0
        scaled = (value - lo) / (hi - lo) * 100
        return scaled if higher_is_better else 100 - scaled

    labels = [m["label"] for m in available_metrics]
    benchmark_scaled = [
        normalise(benchmark_row[m["column"]], m["column"], m["higher_is_better"])
        for m in available_metrics
    ]
    average_scaled = [
        normalise(group_avg[m["column"]], m["column"], m["higher_is_better"])
        for m in available_metrics
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=benchmark_scaled + benchmark_scaled[:1],
            theta=labels + labels[:1],
            fill="toself",
            name=benchmark_company,
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=average_scaled + average_scaled[:1],
            theta=labels + labels[:1],
            fill="toself",
            name=f"{selected_group} Average",
            opacity=0.6,
        )
    )
    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, 100]}},
        showlegend=True,
        margin={"t": 30, "b": 30},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Values are normalised 0–100 within the peer group for comparability. Raw figures are in the table below."
    )

st.divider()


# ---------------------------------------------------------------------------
# Side-by-side KPI table, benchmark row highlighted
# ---------------------------------------------------------------------------

st.subheader("📋 Peer Group Comparison")

table_columns = ["company_name"] + [m["column"] for m in available_metrics]
table = group_df[[c for c in table_columns if c in group_df.columns]].copy()

rename_map = {"company_name": "Company"} | {
    m["column"]: m["label"] for m in available_metrics
}
table = table.rename(columns=rename_map)

for col in table.select_dtypes(include="number").columns:
    table[col] = table[col].round(2)

table = table.sort_values("Company").reset_index(drop=True)


def highlight_benchmark(row: pd.Series) -> list[str]:
    is_benchmark = row["Company"] == benchmark_company
    style = "background-color: #FFF3B0; font-weight: 600;" if is_benchmark else ""
    return [style] * len(row)


st.dataframe(
    table.style.apply(highlight_benchmark, axis=1).format(precision=2),
    use_container_width=True,
    hide_index=True,
)
