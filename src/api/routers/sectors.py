import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Sectors"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@router.get("/sectors")
def get_sectors():
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute("""
        SELECT
            s.broad_sector,
            COUNT(DISTINCT s.company_id) AS company_count,

            ROUND(AVG(r.return_on_equity_pct), 2) AS median_roe,
            ROUND(AVG(m.pe_ratio), 2) AS median_pe,
            ROUND(AVG(r.debt_to_equity), 2) AS median_de

        FROM sectors s

        LEFT JOIN financial_ratios r
            ON s.company_id = r.company_id

        LEFT JOIN market_cap m
            ON s.company_id = m.company_id
            AND CAST(r.year AS INTEGER) = m.year

        WHERE r.year = (
            SELECT MAX(r2.year)
            FROM financial_ratios r2
            WHERE r2.company_id = r.company_id
              AND r2.year != 'TTM'
        )

        GROUP BY s.broad_sector
        ORDER BY s.broad_sector
        """).fetchall()

    conn.close()

    return [
        {
            "sector": row[0],
            "company_count": row[1],
            "median_roe": row[2],
            "median_pe": row[3],
            "median_de": row[4],
        }
        for row in rows
    ]


@router.get("/sectors/{sector}/companies")
def get_sector_companies(sector: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            c.id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            r.year,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.operating_profit_margin_pct,
            r.revenue_cagr,
            r.pat_cagr

        FROM companies c

        JOIN sectors s
            ON c.id = s.company_id

        LEFT JOIN financial_ratios r
            ON c.id = r.company_id

        WHERE s.broad_sector = ?

          AND r.year = (
              SELECT MAX(r2.year)
              FROM financial_ratios r2
              WHERE r2.company_id = c.id
                AND r2.year != 'TTM'
          )

        ORDER BY c.id
        """,
        (sector,),
    ).fetchall()

    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Unknown sector",
        )

    return [dict(row) for row in rows]
