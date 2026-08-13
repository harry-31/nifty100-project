import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "nifty100.db"

START_TIME = time.time()

app = FastAPI(
    title="Nifty100 Financial Intelligence API",
    version="1.0.0",
    description="REST API for Nifty100 financial intelligence platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start

        print(
            f"{request.method} {request.url.path} "
            f"{response.status_code} {elapsed:.4f}s"
        )

        return response


app.add_middleware(RequestLoggingMiddleware)

PREFIX = "/api/v1"

app.include_router(health.router, prefix=PREFIX)
app.include_router(companies.router, prefix=PREFIX)
app.include_router(screener.router, prefix=PREFIX)
app.include_router(sectors.router, prefix=PREFIX)
app.include_router(peers.router, prefix=PREFIX)
app.include_router(valuation.router, prefix=PREFIX)
app.include_router(portfolio.router, prefix=PREFIX)
app.include_router(documents.router, prefix=PREFIX)


@app.get("/")
def root():
    return {
        "name": "Nifty100 Financial Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "ok",
    }


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_uptime():
    return round(time.time() - START_TIME, 2)
