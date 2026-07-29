import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# Database Path
DB_PATH = Path(__file__).resolve().parents[3] / "nifty100.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# ----------------------------
# Companies
# ----------------------------

@st.cache_data(ttl=600)
def get_companies():
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM companies
        ORDER BY company_name
    """, conn)

    conn.close()
    return df


# ----------------------------
# Financial Ratios
# ----------------------------

@st.cache_data(ttl=600)
def get_ratios(company_id=None, year=None):
    conn = get_connection()

    query = "SELECT * FROM financial_ratios WHERE 1=1"
    params = []

    if company_id:
        query += " AND company_id=?"
        params.append(company_id)

    if year:
        query += " AND year LIKE ?"
        params.append(f"{year}%")
    
    query += " ORDER BY year"

    df = pd.read_sql(query, conn, params=params)

    conn.close()
    return df


# ----------------------------
# Profit & Loss
# ----------------------------

@st.cache_data(ttl=600)
def get_pl(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM profitandloss
        WHERE company_id=?
        ORDER BY year
    """, conn, params=[company_id])

    conn.close()
    return df


# ----------------------------
# Balance Sheet
# ----------------------------

@st.cache_data(ttl=600)
def get_bs(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM balancesheet
        WHERE company_id=?
        ORDER BY year
    """, conn, params=[company_id])

    conn.close()
    return df


# ----------------------------
# Cash Flow
# ----------------------------

@st.cache_data(ttl=600)
def get_cf(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM cashflow
        WHERE company_id=?
        ORDER BY year
    """, conn, params=[company_id])

    conn.close()
    return df


# ----------------------------
# Market Cap / Valuation
# ----------------------------

@st.cache_data(ttl=600)
def get_market_cap(year=None):
    conn = get_connection()

    query = "SELECT * FROM market_cap"
    params = []

    if year:
        query += " WHERE year=?"
        params.append(year)

    df = pd.read_sql(query, conn, params=params)

    conn.close()
    return df


@st.cache_data(ttl=600)
def get_valuation(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM market_cap
        WHERE company_id=?
        ORDER BY year
    """, conn, params=[company_id])

    conn.close()
    return df


# ----------------------------
# Sector Data
# ----------------------------

@st.cache_data(ttl=600)
def get_sectors():
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM sectors
        ORDER BY broad_sector, sub_sector
    """, conn)

    conn.close()
    return df


# ----------------------------
# Peer Groups
# ----------------------------

@st.cache_data(ttl=600)
def get_peers(peer_group_name=None):
    conn = get_connection()

    query = "SELECT * FROM peer_groups"
    params = []

    if peer_group_name:
        query += " WHERE peer_group_name=?"
        params.append(peer_group_name)

    df = pd.read_sql(query, conn, params=params)

    conn.close()
    return df


# ----------------------------
# Pros & Cons
# ----------------------------

@st.cache_data(ttl=600)
def get_pros_cons(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM prosandcons
        WHERE company_id=?
    """, conn, params=[company_id])

    conn.close()
    return df


# ----------------------------
# Annual Reports
# ----------------------------

@st.cache_data(ttl=600)
def get_documents(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM documents
        WHERE company_id=?
        ORDER BY Year DESC
    """, conn, params=[company_id])

    conn.close()
    return df

@st.cache_data(ttl=600)
def get_pros_cons(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM prosandcons
        WHERE company_id = ?
    """, conn, params=[company_id])

    conn.close()
    return df


@st.cache_data(ttl=600)
def get_company(company_id):
    conn = get_connection()

    df = pd.read_sql("""
        SELECT *
        FROM companies
        WHERE id = ?
    """, conn, params=[company_id])

    conn.close()
    return df