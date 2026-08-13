\# Nifty100 Financial Intelligence Platform

\## Analyst User Guide



\### 1. Overview



The Nifty100 Financial Intelligence Platform is a financial analysis system covering 92 Nifty 100 companies.



It combines financial statements, calculated financial ratios, cash-flow analytics, valuation metrics, peer comparisons, sector analysis, clustering, and automated insights into a single platform.



The project uses SQLite for structured storage and Python-based analytics modules for processing and analysis.



\---



\## 2. Data and Analytics Flow



The general workflow is:



Raw Financial Data

&#x20;       ↓

ETL and Data Validation

&#x20;       ↓

SQLite Database

&#x20;       ↓

Financial KPI Calculation

&#x20;       ↓

Screening / Peer / Sector / Valuation Analysis

&#x20;       ↓

Reports and REST API



The database contains company information, financial statements, ratios, market data, peer groups, sectors, documents, analysis results, and generated insights.



\---



\## 3. Financial Analysis



The platform calculates and exposes multiple financial indicators, including:



\- Net Profit Margin

\- Operating Profit Margin

\- Return on Equity (ROE)

\- Debt to Equity

\- Interest Coverage

\- Asset Turnover

\- Free Cash Flow

\- Capital Expenditure

\- Earnings per Share

\- Dividend Payout Ratio

\- Revenue CAGR

\- PAT CAGR

\- EPS CAGR

\- Cash-flow quality indicators



These metrics can be used to evaluate profitability, leverage, operating efficiency, growth, and cash generation.



\---



\## 4. Financial Screener



The screener allows companies to be filtered using financial thresholds.



Examples include:



\- Minimum ROE

\- Maximum Debt/Equity

\- Minimum Free Cash Flow

\- Revenue CAGR

\- PAT CAGR

\- Operating Margin

\- P/E

\- P/B

\- Dividend Yield

\- Interest Coverage



Preset screening strategies are also available for common investment-analysis use cases.



\---



\## 5. Company Analysis



Individual companies can be analysed through their:



\- Profit and Loss history

\- Balance Sheet history

\- Cash Flow history

\- Financial ratios

\- Market-cap data

\- Documents

\- Peer comparison

\- Company tear sheet



The platform supports historical financial analysis rather than relying only on a single period.



\---



\## 6. Peer and Sector Analysis



Companies can be compared with their relevant peer groups.



Peer analysis supports comparison of financial metrics and helps identify companies performing above or below their peer group.



Sector analysis provides aggregated financial information across sectors and can be used to understand differences in profitability, growth, leverage, and valuation.



\---



\## 7. Clustering



The analytics layer also groups companies using financial characteristics.



The clustering model uses:



\- Return on Equity

\- Debt to Equity

\- Operating Profit Margin

\- Revenue CAGR

\- 5-year Free Cash Flow CAGR



K-Means clustering is used to identify groups of companies with similar financial characteristics.



Supporting outputs include:



\- Cluster labels

\- Cluster profiles

\- Cluster outliers

\- Elbow plot

\- Feature correlation heatmap



\---



\## 8. Valuation Analysis



The valuation module provides indicators such as:



\- Free Cash Flow Yield

\- Sector Median P/E

\- P/E versus Sector Median

\- Valuation Flags



Companies can be classified using valuation signals such as:



\- Fair

\- Discount

\- Caution



The analysis is intended to support comparison rather than replace investment judgement.



\---



\## 9. Cash Flow Intelligence



Cash-flow analysis evaluates:



\- Free Cash Flow

\- CFO quality

\- CapEx intensity

\- FCF conversion

\- Capital allocation behaviour

\- Distress signals

\- Debt-funded growth

\- Cash accumulation patterns



These indicators provide additional context beyond accounting profitability.



\---



\## 10. NLP Insights



The platform includes an NLP component for generating company-level pros and cons from available financial analysis.



Generated insights can be used as a quick summary before performing deeper fundamental analysis.



\---



\## 11. REST API



The platform exposes financial intelligence through a REST API.



Current API areas include:



\- Health check

\- Company listing

\- Company details

\- Profit and Loss

\- Balance Sheet

\- Cash Flow

\- Financial ratios

\- Company tear sheet

\- Screener

\- Sector analysis

\- Sector companies

\- Peer groups

\- Peer comparison

\- Market-cap data

\- Portfolio statistics

\- Company documents



The API provides programmatic access to the same underlying financial intelligence.



\---



\## 12. Portfolio Statistics



The portfolio statistics endpoint provides distribution statistics for major financial indicators.



For each metric it can provide:



\- P10

\- P25

\- P50

\- P75

\- P90

\- Mean

\- Standard Deviation



This allows analysts to understand the distribution of financial characteristics across the covered companies.



\---



\## 13. Reports and Outputs



Important generated outputs include:



\- Screener results

\- Peer comparison reports

\- Valuation summaries

\- Valuation flags

\- Capital allocation analysis

\- Cash-flow intelligence

\- Cluster labels

\- Cluster profiles

\- Cluster outliers

\- Portfolio statistics

\- Company tear sheets

\- Sector reports

\- Radar charts

\- API test reports

\- Performance validation notes



\---



\## 14. API Validation



The REST API has been validated using automated integration tests.



The API test suite covers important endpoints including:



\- Health

\- Companies

\- Company details

\- Ratios

\- Screener

\- Sectors

\- Portfolio statistics

\- Market cap

\- Documents



The complete regression suite currently passes successfully.



\---



\## 15. Performance Validation



API performance smoke tests cover repeated requests against:



\- Health endpoint

\- Company endpoint

\- Screener endpoint



The checks verify that the endpoints return successful responses within the configured validation threshold.



\---



\## 16. Testing



The project uses pytest for automated testing.



Testing covers:



\- ETL

\- Data normalisation

\- CAGR calculations

\- Cash-flow KPIs

\- Financial ratios

\- API integration

\- API performance



All implemented test groups should be run before final submission.



Command:



&#x20;   pytest -q



\---



\## 17. Running the Project



\### Create virtual environment



&#x20;   python -m venv venv



\### Activate on Windows



&#x20;   venv\\Scripts\\activate



\### Install dependencies



&#x20;   pip install -r requirements.txt



\### Run tests



&#x20;   pytest -q



\### Run the REST API



&#x20;   python -m uvicorn src.api.main:app --port 8001



\### API documentation



Once the API is running, the interactive API documentation is available through the FastAPI documentation endpoint.



\---



\## 18. Analyst Workflow



A typical analyst workflow is:



1\. Check the API/database health.

2\. Review the company or sector.

3\. Examine profitability and leverage ratios.

4\. Review historical growth and cash flow.

5\. Compare the company with peers.

6\. Check valuation indicators.

7\. Review generated pros and cons.

8\. Use clustering and portfolio statistics for additional context.

9\. Export or review the relevant reports.

10\. Perform final analyst judgement using multiple indicators.



\---



\## 19. Important Note



The platform is designed as a financial intelligence and analysis tool.



Screening, valuation flags, clustering, and generated insights should be treated as analytical aids. Final investment decisions should not be based on a single metric or automated signal.

