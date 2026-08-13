import sqlite3
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["Documents"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@router.get("/companies/{ticker}/documents")
def get_documents(ticker: str):
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT
            Year,
            Annual_Report
        FROM documents
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY Year
        """,
        (ticker,),
    ).fetchall()

    conn.close()

    return [
        {
            "year": row[0],
            "annual_report": row[1],
            "is_url_valid": bool(
                row[1] and str(row[1]).startswith(("http://", "https://"))
            ),
        }
        for row in rows
    ]
