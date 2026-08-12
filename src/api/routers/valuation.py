import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Valuation"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@router.get("/market-cap/{ticker}")
def get_market_cap(ticker: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            year,
            market_cap_crore,
            enterprise_value_crore,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY year
        """,
        (ticker,),
    ).fetchall()

    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Valuation data not found",
        )

    return [dict(row) for row in rows]