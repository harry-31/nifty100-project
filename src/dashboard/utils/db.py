from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "nifty100.db"

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}")


RATIOS_COLUMN_MAP = {
    "interest_coverage": "interest_coverage_ratio",
    "free_cash_flow_cr": "fcf",
}


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _conn() -> sqlite3.Connection:
    """One shared connection, reused across reruns instead of open/close per call."""
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def _read(query: str, params: tuple = ()) -> pd.DataFrame:
    """
    Shared query path for every function below.

    Returns an empty DataFrame if the query fails — including when a
    table doesn't exist, so optional tables (prosandcons,
    capital_allocation) degrade gracefully — but surfaces the real
    error via st.error() rather than silently swallowing it.
    """
    try:
        return pd.read_sql_query(query, _conn(), params=params)
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        st.error(f"Database error: {exc}")
        return pd.DataFrame()


def _add_ticker(df: pd.DataFrame) -> pd.DataFrame:
    """Alias `id` as `ticker` for pages that expect a ticker-like field."""
    if not df.empty and "id" in df.columns:
        df["ticker"] = df["id"]
    return df

# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_companies() -> pd.DataFrame:
    """Return all companies, ordered by name."""
    df = _read("SELECT * FROM companies ORDER BY company_name")
    return _add_ticker(df)


@st.cache_data(ttl=600, show_spinner=False)
def get_company(company_id: str) -> pd.DataFrame:
    """Return a single company row by id."""
    df = _read(
        """
        SELECT *
        FROM companies
        WHERE id = ?
        """,
        (company_id,),
    )
    return _add_ticker(df)


# ---------------------------------------------------------------------------
# Financial Ratios
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_ratios(company_id: str | None = None, year: str | int | None = None) -> pd.DataFrame:
    """
    Return financial ratio history, optionally scoped to one company
    and/or one year. `year` matches as a prefix (e.g. "2024" matches
    "2024" and "2024-25").
    """
    query = "SELECT * FROM financial_ratios WHERE 1 = 1"
    params: list = []

    if company_id is not None:
        query += " AND company_id = ?"
        params.append(company_id)

    if year is not None:
        query += " AND year LIKE ?"
        params.append(f"{year}%")

    query += " ORDER BY year"

    df = _read(query, tuple(params))
    if not df.empty:
        df = df.rename(columns=RATIOS_COLUMN_MAP)
    return df


# ---------------------------------------------------------------------------
# Profit & Loss / Balance Sheet / Cash Flow
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_pl(company_id: str) -> pd.DataFrame:
    """Return profit & loss history for one company."""
    return _read(
        """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    )


@st.cache_data(ttl=600, show_spinner=False)
def get_bs(company_id: str) -> pd.DataFrame:
    """Return balance sheet history for one company."""
    return _read(
        """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    )


@st.cache_data(ttl=600, show_spinner=False)
def get_cf(company_id: str) -> pd.DataFrame:
    """Return cash flow history for one company."""
    return _read(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    )


# ---------------------------------------------------------------------------
# Market Cap / Valuation
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_market_cap(year: str | int | None = None) -> pd.DataFrame:
    """Return market cap rows, optionally scoped to one year."""
    if year is not None:
        return _read(
            """
            SELECT *
            FROM market_cap
            WHERE year = ?
            """,
            (year,),
        )
    return _read("SELECT * FROM market_cap")


@st.cache_data(ttl=600, show_spinner=False)
def get_valuation(company_id: str) -> pd.DataFrame:
    """
    Return valuation-relevant history for one company.

    NOTE: there's no dedicated `valuation` table in the current schema,
    so this reads from market_cap as a placeholder until/unless the
    Day 26 valuation module's output gets loaded into its own table.
    """
    return _read(
        """
        SELECT *
        FROM market_cap
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    )


# ---------------------------------------------------------------------------
# Sectors / Peer Groups
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_sectors() -> pd.DataFrame:
    """Return all sector / sub-sector rows."""
    return _read("SELECT * FROM sectors ORDER BY broad_sector, sub_sector")


@st.cache_data(ttl=600, show_spinner=False)
def get_peers(peer_group_name: str | None = None) -> pd.DataFrame:
    """
    Return peer group membership rows, optionally scoped to one group.
    Pass no argument to get every row (useful for building a list of
    all distinct peer group names).
    """
    if peer_group_name is not None:
        return _read(
            """
            SELECT *
            FROM peer_groups
            WHERE peer_group_name = ?
            """,
            (peer_group_name,),
        )
    return _read("SELECT * FROM peer_groups")


# ---------------------------------------------------------------------------
# Pros & Cons (optional table — returns empty DataFrame if absent)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_pros_cons(company_id: str) -> pd.DataFrame:
    """Return pros/cons rows for one company, if the table exists."""
    return _read(
        """
        SELECT *
        FROM prosandcons
        WHERE company_id = ?
        """,
        (company_id,),
    )


# ---------------------------------------------------------------------------
# Documents / Annual Reports
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_documents(company_id: str) -> pd.DataFrame:
    """Return raw document rows (annual reports, etc.) for one company."""
    return _read(
        """
        SELECT *
        FROM documents
        WHERE company_id = ?
        ORDER BY Year DESC
        """,
        (company_id,),
    )


@st.cache_data(ttl=600, show_spinner=False)
def get_annual_reports(company_id: str) -> pd.DataFrame:
    """
    Return annual report links for one company, normalised to the
    columns pages expect: `year`, `pdf_url`.
    """
    df = get_documents(company_id)
    if df.empty:
        return pd.DataFrame(columns=["year", "pdf_url"])
    return df.rename(columns={"Year": "year", "Annual_Report": "pdf_url"})[["year", "pdf_url"]]


# ---------------------------------------------------------------------------
# Capital Allocation (optional table — returns empty DataFrame if absent)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def get_capital_allocation():
    return pd.DataFrame(columns=["company_id", "pattern"])

    if company_id is not None:
        df = _read(
            """
            SELECT *
            FROM capital_allocation
            WHERE company_id = ?
            """,
            (company_id,),
        )
    else:
        df = _read("SELECT * FROM capital_allocation")

    if df.empty:
        return pd.DataFrame(columns=["company_id", "pattern"])
    return df