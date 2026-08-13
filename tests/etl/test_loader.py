from src.etl.loader import load_excel


def test_load_companies():
    df = load_excel("data/raw/companies.xlsx")
    assert len(df) == 92


def test_load_profitandloss():
    df = load_excel("data/raw/profitandloss.xlsx")
    assert len(df) > 0


def test_load_balancesheet():
    df = load_excel("data/raw/balancesheet.xlsx")
    assert len(df) > 0


def test_load_cashflow():
    df = load_excel("data/raw/cashflow.xlsx")
    assert len(df) > 0
