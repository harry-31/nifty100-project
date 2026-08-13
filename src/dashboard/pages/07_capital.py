import pandas as pd
import plotly.express as px
import streamlit as st
from utils.db import get_capital_allocation

st.set_page_config(page_title="Capital Allocation Map", layout="wide")
st.title("🗺️ Capital Allocation Map")

st.caption(
    "Each tile is a company, grouped by its dominant capital allocation "
    "pattern. Tile size reflects the number of companies in that group. "
    "Click any tile to see the full company list for that pattern."
)


@st.cache_data(ttl=600, show_spinner=False)
def load_capital_data() -> pd.DataFrame:
    return get_capital_allocation()


df = load_capital_data()

if df.empty:
    st.info("Capital Allocation data is not available in the current database.")
    st.markdown("""
### Expected Table

This page requires a table like:

| company_id | pattern |
|------------|----------|
| 1 | Growth |
| 2 | Dividend |
| 3 | Debt Reduction |

Since your database doesn't contain this table, this page cannot generate the treemap.
""")
    st.stop()

pattern_counts = df["pattern"].value_counts().reset_index()
pattern_counts.columns = ["pattern", "company_count"]

st.divider()


# ---------------------------------------------------------------------------
# Treemap
# ---------------------------------------------------------------------------

fig = px.treemap(
    df,
    path=[px.Constant("All Companies"), "pattern", "company_name"],
    color="pattern",
    title="Capital Allocation Patterns — 92 Companies",
)
fig.update_traces(root_color="lightgrey")
fig.update_layout(margin={"t": 50, "l": 10, "r": 10, "b": 10})

selection = st.plotly_chart(
    fig,
    use_container_width=True,
    on_select="rerun",
    key="capital_treemap",
)

st.divider()


# ---------------------------------------------------------------------------
# Selected pattern -> company list
# ---------------------------------------------------------------------------

clicked_label = None

if selection and selection.get("selection", {}).get("points"):
    point = selection["selection"]["points"][0]
    # Plotly treemap click gives the tile label — could be a pattern
    # name or a leaf-level company name; resolve either to its pattern.
    label = point.get("label")
    if label in df["pattern"].values:
        clicked_label = label
    elif label in df["company_name"].values:
        clicked_label = df.loc[df["company_name"] == label, "pattern"].iloc[0]

if clicked_label:
    st.subheader(f"📋 Companies — {clicked_label}")
    subset = df[df["pattern"] == clicked_label][
        ["company_name", "ticker", "broad_sector"]
    ]
    subset.columns = ["Company", "Ticker", "Sector"]
    st.dataframe(
        subset.sort_values("Company"), use_container_width=True, hide_index=True
    )
else:
    st.info("Click a pattern or company tile above to see its full company list.")

st.divider()


# ---------------------------------------------------------------------------
# Pattern summary table
# ---------------------------------------------------------------------------

st.subheader("📊 Pattern Summary")
st.dataframe(
    pattern_counts.rename(columns={"pattern": "Pattern", "company_count": "Companies"}),
    use_container_width=True,
    hide_index=True,
)
