import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.title("📊 Nifty 100 Analytics")
st.sidebar.markdown("---")
st.sidebar.info("""
    **Sprint 4 Dashboard**

    Navigate using the Pages menu on the left.
    """)

# ----------------------------
# Home Page
# ----------------------------
st.title("📈 Nifty 100 Analytics")

st.markdown("""
Welcome to the **Nifty 100 Analytics Dashboard**.

This dashboard provides financial analysis and insights for all **92 Nifty 100 companies**.

Use the **Pages** section in the left sidebar to navigate through the dashboard.
""")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Dashboard Screens")
    st.markdown("""
- 🏠 Home
- 🏢 Company Profile
- 🔎 Screener
- 🧭 Peer Comparison
- 📈 Trend Analysis
- 🏭 Sector Analysis
- 🗺️ Capital Allocation
- 📄 Annual Reports
""")

with col2:
    st.subheader("🎯 Sprint 4 Goal")
    st.success("""
✔ 8 Interactive Streamlit Screens

✔ Financial Analytics

✔ Company Comparison

✔ Screener

✔ Trend Analysis

✔ Sector Insights

✔ Capital Allocation

✔ Annual Reports
""")

st.markdown("---")

st.caption("Bluestock Fintech Capstone • Nifty 100 Analytics Dashboard")
