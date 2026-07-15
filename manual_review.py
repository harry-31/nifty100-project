import sqlite3
import pandas as pd

conn = sqlite3.connect("nifty100.db")

companies = ["ABB", "TCS", "RELIANCE", "INFY", "HDFCBANK"]

for company in companies:
    print("=" * 60)
    print(company)

    df = pd.read_sql_query(
        f"""
        SELECT company_id, year
        FROM profitandloss
        WHERE company_id='{company}'
        ORDER BY year
        """,
        conn,
    )

    print(df)

conn.close()