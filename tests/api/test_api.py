from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_companies():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 92


def test_company_tcs():
    response = client.get("/api/v1/companies/TCS")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "TCS"


def test_tcs_ratios():
    response = client.get("/api/v1/companies/TCS/ratios")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_screener():
    response = client.get("/api/v1/screener?min_roe=15")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_sectors():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    assert len(response.json()) == 10


def test_portfolio_stats():
    response = client.get("/api/v1/portfolio/stats")
    assert response.status_code == 200

    data = response.json()

    assert "return_on_equity_pct" in data
    assert "debt_to_equity" in data
    assert "free_cash_flow_cr" in data

    assert data["return_on_equity_pct"]["P50"] is not None


def test_market_cap():
    response = client.get("/api/v1/market-cap/TCS")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_documents():
    response = client.get("/api/v1/companies/TCS/documents")
    assert response.status_code == 200
    assert len(response.json()) > 0