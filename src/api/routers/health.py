import sqlite3
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["Health"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@router.get("/health")
def health():
    conn = sqlite3.connect(DB_PATH)

    tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "stock_prices",
        "financial_ratios",
    ]

    counts = {}

    for table in tables:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.Error:
            counts[table] = 0

    conn.close()

    return {
        "status": "ok",
        "db_row_counts": counts,
        "uptime_seconds": 0,
        "version": "1.0.0",
    }
