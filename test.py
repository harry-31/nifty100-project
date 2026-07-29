from src.dashboard.utils.db import get_ratios

df = get_ratios()

print(df.columns)
print(df.head())
from src.dashboard.utils.db import get_market_cap, get_companies

print(get_market_cap("2024").columns)
print(get_companies().columns)
print(get_market_cap("2024").head())
print(get_companies().head())