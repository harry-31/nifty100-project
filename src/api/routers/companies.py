import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["Companies"])

DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"
TEARSHEET_DIR = DB_PATH.parent / "reports" / "tearsheets"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_year_condition(alias="r"):
    return f"""
        {alias}.year = (
            SELECT MAX(r2.year)
            FROM financial_ratios r2
            WHERE r2.company_id = {alias}.company_id
              AND r2.year != 'TTM'
        )
    """


@router.get("/companies")
def get_companies(
    sector: str | None = None,
    market_cap_category: str | None = None,
    search: str | None = None,
):
    conn = get_db()

    query = """
        SELECT
            c.id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.market_cap_category,
            c.roe_percentage AS roe_pct,
            c.roce_percentage AS roce_pct
        FROM companies c
        LEFT JOIN sectors s
            ON c.id = s.company_id
        WHERE 1=1
    """

    params = []

    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)

    if market_cap_category:
        query += " AND s.market_cap_category = ?"
        params.append(market_cap_category)

    if search:
        query += """
            AND (
                c.company_name LIKE ?
                OR c.id LIKE ?
            )
        """
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY c.id"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


@router.get("/companies/{ticker}")
def get_company(ticker: str):
    conn = get_db()

    query = f"""
        SELECT
            c.*,
            s.broad_sector,
            s.sub_sector,
            s.market_cap_category,
            s.index_weight_pct,

            r.year AS latest_year,
            r.net_profit_margin_pct,
            r.operating_profit_margin_pct,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.asset_turnover,
            r.free_cash_flow_cr,
            r.capex_cr,
            r.earnings_per_share,
            r.dividend_payout_ratio_pct,
            r.revenue_cagr,
            r.pat_cagr,
            r.eps_cagr

        FROM companies c

        LEFT JOIN sectors s
            ON c.id = s.company_id

        LEFT JOIN financial_ratios r
            ON c.id = r.company_id
            AND {get_latest_year_condition("r")}

        WHERE UPPER(c.id) = UPPER(?)
    """

    row = conn.execute(query, (ticker,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    return dict(row)


def get_history(
    ticker: str,
    table: str,
    from_year: str | None = None,
    to_year: str | None = None,
):
    conn = get_db()

    company = conn.execute(
        """
        SELECT id
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        """,
        (ticker,),
    ).fetchone()

    if not company:
        conn.close()
        raise HTTPException(status_code=404, detail="Company not found")

    query = f"""
        SELECT *
        FROM {table}
        WHERE UPPER(company_id) = UPPER(?)
    """

    params = [ticker]

    if from_year:
        query += " AND year >= ?"
        params.append(from_year)

    if to_year:
        query += " AND year <= ?"
        params.append(to_year)

    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


@router.get("/companies/{ticker}/pl")
def company_pl(
    ticker: str,
    from_year: str | None = None,
    to_year: str | None = None,
):
    return get_history(
        ticker,
        "profitandloss",
        from_year,
        to_year,
    )


@router.get("/companies/{ticker}/bs")
def company_bs(
    ticker: str,
    from_year: str | None = None,
    to_year: str | None = None,
):
    return get_history(
        ticker,
        "balancesheet",
        from_year,
        to_year,
    )


@router.get("/companies/{ticker}/cashflow")
def company_cashflow(
    ticker: str,
    from_year: str | None = None,
    to_year: str | None = None,
):
    return get_history(
        ticker,
        "cashflow",
        from_year,
        to_year,
    )


@router.get("/companies/{ticker}/ratios")
def company_ratios(
    ticker: str,
    year: str | None = None,
):
    conn = get_db()

    query = """
        SELECT *
        FROM financial_ratios
        WHERE UPPER(company_id) = UPPER(?)
    """

    params = [ticker]

    if year:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="Company ratios not found")

    return [dict(row) for row in rows]


@router.get("/companies/{ticker}/tearsheet")
def company_tearsheet(ticker: str):
    candidates = list(TEARSHEET_DIR.glob(f"*{ticker.upper()}*.pdf"))

    if not candidates:
        raise HTTPException(status_code=404, detail="Tearsheet not found")

    return FileResponse(
        candidates[0],
        media_type="application/pdf",
        filename=candidates[0].name,
    )
