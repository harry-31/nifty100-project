from src.etl.loader import load_excel
from src.etl.validator import (
    validate_primary_key,
    validate_company_year,
    validate_positive_sales
)

companies = load_excel("data/raw/companies.xlsx")
pl = load_excel("data/raw/profitandloss.xlsx")

print("=" * 50)
print("DQ-01 Primary Key")
print(validate_primary_key(companies, "id"))

print("=" * 50)
print("DQ-02 Duplicate Company-Year")
print(validate_company_year(pl))

print("=" * 50)
print("DQ-06 Positive Sales")
print(validate_positive_sales(pl))