import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["Screener"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@router.get("/screener")
def screener(
    min_roe: float | None = Query(None, ge=-1000, le=1000),
    max_de: float | None = Query(None, ge=0, le=1000),
    min_fcf: float | None = None,
    sector: str | None = None,
    min_rev_cagr_5yr: float | None = Query(None),
    min_pat_cagr_5yr: float | None = Query(None),
    max_pe: float | None = Query(None, ge=0),
):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT
            c.id,
            c.company_name,
            s.broad_sector,
            r.year,
            r.return_on_equity_pct AS roe,
            r.debt_to_equity AS de,
            r.free_cash_flow_cr AS fcf,
            r.revenue_cagr,
            r.pat_cagr,
            m.pe_ratio AS pe
        FROM companies c
        JOIN financial_ratios r
            ON c.id = r.company_id
        LEFT JOIN sectors s
            ON c.id = s.company_id
        LEFT JOIN market_cap m
            ON c.id = m.company_id
            AND CAST(r.year AS INTEGER) = m.year
        WHERE r.year = (
            SELECT MAX(r2.year)
            FROM financial_ratios r2
            WHERE r2.company_id = r.company_id
              AND r2.year != 'TTM'
        )
    """

    params = []

    if min_roe is not None:
        query += " AND r.return_on_equity_pct >= ?"
        params.append(min_roe)

    if max_de is not None:
        query += " AND r.debt_to_equity <= ?"
        params.append(max_de)

    if min_fcf is not None:
        query += " AND r.free_cash_flow_cr >= ?"
        params.append(min_fcf)

    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)

    if min_rev_cagr_5yr is not None:
        query += " AND r.revenue_cagr >= ?"
        params.append(min_rev_cagr_5yr)

    if min_pat_cagr_5yr is not None:
        query += " AND r.pat_cagr >= ?"
        params.append(min_pat_cagr_5yr)

    if max_pe is not None:
        query += " AND m.pe_ratio <= ?"
        params.append(max_pe)

    query += " ORDER BY r.return_on_equity_pct DESC"

    try:
        rows = conn.execute(query, params).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    conn.close()

    return [dict(row) for row in rows]