import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Peers"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


@router.get("/peers/{group_name}")
def get_peers(group_name: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            p.peer_group_name,
            p.company_id,
            p.is_benchmark,
            c.company_name,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.operating_profit_margin_pct,
            r.revenue_cagr,
            r.pat_cagr
        FROM peer_groups p
        JOIN companies c
            ON p.company_id = c.id
        LEFT JOIN financial_ratios r
            ON p.company_id = r.company_id
        WHERE p.peer_group_name = ?
          AND r.year = (
              SELECT MAX(r2.year)
              FROM financial_ratios r2
              WHERE r2.company_id = p.company_id
                AND r2.year != 'TTM'
          )
        ORDER BY p.company_id
        """,
        (group_name,),
    ).fetchall()

    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Peer group not found",
        )

    return [dict(row) for row in rows]


@router.get("/companies/{ticker}/peers/compare")
def compare_peers(ticker: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    company = conn.execute(
        """
        SELECT
            c.id,
            c.company_name,
            r.return_on_equity_pct AS roe,
            r.debt_to_equity AS de,
            r.operating_profit_margin_pct AS opm,
            r.revenue_cagr,
            r.pat_cagr,
            r.free_cash_flow_cr AS fcf,
            r.interest_coverage,
            r.asset_turnover
        FROM companies c
        LEFT JOIN financial_ratios r
            ON c.id = r.company_id
        WHERE UPPER(c.id) = UPPER(?)
          AND r.year = (
              SELECT MAX(r2.year)
              FROM financial_ratios r2
              WHERE r2.company_id = c.id
                AND r2.year != 'TTM'
          )
        """,
        (ticker,),
    ).fetchone()

    if not company:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    group = conn.execute(
        """
        SELECT peer_group_name
        FROM peer_groups
        WHERE UPPER(company_id) = UPPER(?)
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()

    group_name = group[0] if group else None

    peer_average = None

    if group_name:
        peer_average = conn.execute(
            """
            SELECT
                AVG(r.return_on_equity_pct),
                AVG(r.debt_to_equity),
                AVG(r.operating_profit_margin_pct),
                AVG(r.revenue_cagr),
                AVG(r.pat_cagr),
                AVG(r.free_cash_flow_cr),
                AVG(r.interest_coverage),
                AVG(r.asset_turnover)
            FROM peer_groups p
            JOIN financial_ratios r
                ON p.company_id = r.company_id
            WHERE p.peer_group_name = ?
              AND r.year = (
                  SELECT MAX(r2.year)
                  FROM financial_ratios r2
                  WHERE r2.company_id = p.company_id
                    AND r2.year != 'TTM'
              )
            """,
            (group_name,),
        ).fetchone()

    conn.close()

    axes = [
        "roe",
        "de",
        "opm",
        "revenue_cagr",
        "pat_cagr",
        "fcf",
        "interest_coverage",
        "asset_turnover",
    ]

    return {
        "company": dict(company),
        "peer_group": group_name,
        "peer_group_average": (
            dict(zip(axes, peer_average))
            if peer_average
            else None
        ),
        "benchmark_company": None,
    }