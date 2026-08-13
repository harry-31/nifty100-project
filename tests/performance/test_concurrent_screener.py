import threading
import time

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

results = []
lock = threading.Lock()


def call_api():
    start = time.perf_counter()
    response = client.get("/api/v1/screener?min_roe=15")
    elapsed = time.perf_counter() - start

    with lock:
        results.append((response.status_code, elapsed))


threads = [threading.Thread(target=call_api) for _ in range(10)]

start = time.perf_counter()

for t in threads:
    t.start()

for t in threads:
    t.join()

total = time.perf_counter() - start

print("REQUESTS:", len(results))
print("STATUS CODES:", [x[0] for x in results])
print("TOTAL TIME:", round(total, 3), "seconds")
print("MAX REQUEST TIME:", round(max(x[1] for x in results), 3), "seconds")

assert len(results) == 10
assert all(status == 200 for status, _ in results)
assert total < 10

print("DAY 43 CONCURRENT LOAD TEST: PASS")
