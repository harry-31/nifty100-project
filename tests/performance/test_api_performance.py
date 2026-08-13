import time

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_api_health_performance():
    start = time.perf_counter()

    for _ in range(20):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    elapsed = time.perf_counter() - start

    print(f"\n20 health requests: {elapsed:.3f}s")
    assert elapsed < 10


def test_company_api_performance():
    start = time.perf_counter()

    for _ in range(10):
        response = client.get("/api/v1/companies/TCS")
        assert response.status_code == 200

    elapsed = time.perf_counter() - start

    print(f"\n10 company requests: {elapsed:.3f}s")
    assert elapsed < 10


def test_screener_api_performance():
    start = time.perf_counter()

    for _ in range(10):
        response = client.get("/api/v1/screener?min_roe=15")
        assert response.status_code == 200

    elapsed = time.perf_counter() - start

    print(f"\n10 screener requests: {elapsed:.3f}s")
    assert elapsed < 10
