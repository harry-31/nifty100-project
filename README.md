# 📈 Nifty 100 Analytics Platform

A Streamlit-based financial analytics dashboard for analyzing **92 Nifty 100 companies** using financial statements, market data, valuation metrics, and peer comparisons.

Built as a **Bluestock Fintech  Project (Sprint 4)**.

---

## 📌 Project Overview

This project turns raw financial statement data (P&L, Balance Sheet, Cash Flow, Ratios, Market Cap, Peer Groups, etc.) into an interactive analytics platform. Data is loaded from Excel sources into a local SQLite database, processed through an ETL + analytics pipeline, and served through an 8-screen Streamlit dashboard.

**Main objective:** Give a quick, data-driven way to screen, compare, and evaluate Nifty 100 companies on fundamentals, valuation, and trends — without manually digging through annual reports and spreadsheets.

- **Companies covered:** 92 Nifty 100 companies
- **Interface:** Multi-page Streamlit dashboard
- **Storage:** SQLite (`nifty100.db`)
- **Analytics:** Ratio computation, CAGR, peer benchmarking, sector aggregation, valuation flagging

### Highlights
- 📊 Streamlit Dashboard (8 screens)
- 📁 Financial Analytics (ratios, CAGR, cash flow KPIs)
- 🗄️ SQLite Database with 12 tables
- 📈 Interactive Plotly Charts
- 💰 Valuation Module (FCF Yield, Sector P/E comparison, valuation flags)
- 📤 CSV / Excel Export
- 📄 Annual Report links (BSE)
- ✅ Unit-tested ETL and KPI modules (pytest)

---

## ✨ Features

✔ Dashboard Overview (Home / KPIs)
✔ Company Profile
✔ Financial Screener (with presets)
✔ Peer Comparison (radar chart)
✔ Trend Analysis (multi-metric, YoY)
✔ Sector Analysis
✔ Capital Allocation Map
✔ Annual Reports
✔ Valuation Module
✔ CSV Export
✔ Interactive Plotly Charts

---

## 🛠️ Tech Stack

- Python
- Streamlit
- SQLite
- Pandas
- NumPy
- Plotly
- OpenPyXL
- Requests
- PyYAML
- Matplotlib
- Pytest
- Git

---

## 📂 Project Structure

```
nifty100-project/
│
├── config/
│   └── screener_config.yaml
│
├── data/
│   └── raw/                     # Source Excel files (companies, ratios, market cap, etc.)
│
├── db/
│   └── schema.sql               # Database schema
│
├── notebooks/
│   ├── 01_validation_checks.ipynb
│   └── exploratory_queries.sql
│
├── output/
│   ├── valuation_summary.xlsx
│   ├── valuation_flags.csv
│   ├── screener_output.xlsx
│   ├── peer_comparison.xlsx
│   ├── capital_allocation.csv
│   ├── charts/
│   └── load_audit.csv
│
├── reports/
│   └── radar_charts/
│
├── src/
│   ├── analytics/
│   │   ├── valuation.py
│   │   ├── cagr.py
│   │   ├── capital_allocation.py
│   │   ├── cashflow_kpis.py
│   │   ├── peer.py
│   │   ├── radar.py
│   │   └── ratios.py
│   │
│   ├── dashboard/
│   │   ├── app.py               # Entry point
│   │   ├── pages/               # 01_home ... 08_reports
│   │   └── utils/
│   │       └── db.py
│   │
│   ├── etl/
│   │   ├── loader.py
│   │   ├── db_loader.py
│   │   ├── normaliser.py
│   │   └── validator.py
│   │
│   └── screener/
│       └── engine.py
│
├── tests/
│   ├── etl/
│   └── kpi/
│
├── nifty100.db
├── requirements.txt
├── Makefile
└── README.md
```

---

## 🗄️ Database

`nifty100.db` (SQLite) contains the following tables:

- `companies`
- `financial_ratios`
- `market_cap`
- `stock_prices`
- `peer_groups`
- `peer_percentiles`
- `sectors`
- `documents`
- `analysis`
- `profitandloss`
- `balancesheet`
- `cashflow`
- `prosandcons`

> Note: there is no `capital_allocation` table in the current database — see the [Capital Allocation](#capital-allocation) section below.

---

## ⚙️ Installation

```bash
git clone <repository>
cd nifty100-project

python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS / Linux

pip install -r requirements.txt
```

---

## ▶️ Running the Dashboard

```bash
streamlit run src/dashboard/app.py
```

The dashboard opens at:

```
http://localhost:8501
```

---

## 🖥️ Dashboard Screens

### 1. Home
- KPI Cards (total companies, average ROE, median Debt/Equity)
- Sector Distribution
- Quality Ranking

### 2. Company Profile
- Company Details
- Revenue Chart
- ROE / ROCE
- Pros & Cons

### 3. Screener
- Financial Filters (ROE, D/E, FCF, Revenue/PAT CAGR, OPM, P/E, P/B, Dividend Yield, Interest Coverage)
- Presets (Quality, Value, Growth, Dividend, Debt-Free, Turnaround)
- CSV Download

### 4. Peer Comparison
- Radar Chart (8 metrics: ROE, ROCE, Net Margin, OPM, Debt/Equity, Revenue CAGR, P/E, Dividend Yield)
- KPI Comparison Table

### 5. Trend Analysis
- Multi-metric trend view per company
- YoY analysis across ratios, margins, and cash flow

### 6. Sector Analysis
- Bubble Chart (ROE, Revenue CAGR, market cap by sector)
- Sector-level KPI aggregation

### 7. Capital Allocation
The dashboard includes a Capital Allocation Map screen (treemap of companies by capital allocation pattern). **The current `nifty100.db` does not contain a `capital_allocation` table**, so this screen shows an informational placeholder message (with the expected table schema) instead of live data. Once a `capital_allocation` table is populated, the treemap will render automatically — no code changes needed.

### 8. Annual Reports
- Annual Report links per company
- BSE PDF links

---

## 💰 Valuation Module

`src/analytics/valuation.py` computes, per company:

- **FCF Yield** (Free Cash Flow ÷ Market Cap)
- **Sector Median P/E**
- **P/E vs Sector Median (%)**
- **Valuation Flag**
  - `Fair` — P/E within ±30–50% of sector median
  - `Discount` — P/E below 70% of sector median
  - `Caution` — P/E above 150% of sector median

**Outputs:**
- `output/valuation_summary.xlsx`
- `output/valuation_flags.csv` (companies flagged `Discount` or `Caution`)

---

## 📤 Output Files

- `output/valuation_summary.xlsx`
- `output/valuation_flags.csv`
- `output/screener_output.xlsx`
- `output/peer_comparison.xlsx`
- CSV exports generated directly from the Screener page in the dashboard

---

## 🖼️ Screenshots

> Add screenshots of each screen below before submitting.

- Home Dashboard
- Company Profile
- Screener
- Peer Comparison
- Trend Analysis
- Sector Analysis
- Capital Allocation
- Annual Reports

---

## ✅ Testing

- ETL modules (`loader`, `normaliser`) covered by unit tests in `tests/etl/`
- KPI modules (`cagr`, `cashflow_kpis`, `ratios`) covered by unit tests in `tests/kpi/`
- Dashboard manually tested across multiple companies and sectors
- Missing/NaN values handled gracefully (e.g. "N/A" fallback in Company Profile)
- CSV export from Screener verified
- Valuation module verified against `valuation_summary.xlsx` / `valuation_flags.csv`
- Dashboard confirmed to load successfully via `streamlit run src/dashboard/app.py`

Run tests with:

```bash
pytest -v
```

---

## 🚀 Future Improvements

- Live NSE/BSE API integration for real-time prices
- AI-based stock recommendation engine
- Portfolio tracking
- User authentication
- Populate a real `capital_allocation` table and remove the placeholder
- Cloud deployment (Streamlit Community Cloud / Docker)

---

## 👤 Contributors

**Himani**
