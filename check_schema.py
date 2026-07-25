import sqlite3

conn = sqlite3.connect("nifty100.db")
cur = conn.cursor()

tables = [
    "financial_ratios",
    "companies",
    "market_cap",
    "analysis"
]

for table in tables:
    print(f"\n===== {table} =====")

    try:
        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()

        if not cols:
            print("Table not found or empty.")
            continue

        for col in cols:
            print(col[1])

    except Exception as e:
        print(e)

conn.close()