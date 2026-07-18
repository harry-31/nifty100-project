import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    check_opm_difference,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
)

def test_net_profit_margin_normal():
    assert net_profit_margin(200, 1000) == 20.00


def test_net_profit_margin_zero_sales():
    assert net_profit_margin(200, 0) is None

def test_operating_profit_margin_normal():
    assert operating_profit_margin(250, 1000) == 25.00


def test_opm_difference_flag():
    assert check_opm_difference(25.0, 23.5) is True


def test_return_on_equity_normal():
    assert return_on_equity(200, 500, 500) == 20.00


def test_return_on_equity_negative_equity():
    assert return_on_equity(200, -500, 300) is None

def test_return_on_capital_employed_normal():
    assert return_on_capital_employed(300, 500, 500, 500) == 20.00

def test_return_on_assets_zero_assets():
    assert return_on_assets(100, 0) is None


from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning_flag,
    net_debt,
    asset_turnover,
)


def test_debt_to_equity_normal():
    assert debt_to_equity(500, 500, 500) == 0.50


def test_debt_to_equity_debt_free():
    assert debt_to_equity(0, 500, 500) == 0


def test_high_leverage_flag():
    assert high_leverage_flag(6.2, "IT") is True


def test_high_leverage_financials():
    assert high_leverage_flag(8.5, "Financials") is False


def test_interest_coverage_ratio_normal():
    assert interest_coverage_ratio(1000, 200, 100) == 12.00


def test_interest_coverage_ratio_zero_interest():
    assert interest_coverage_ratio(1000, 200, 0) is None


def test_icr_label():
    assert icr_label(None) == "Debt Free"


def test_asset_turnover():
    assert asset_turnover(1000, 500) == 2.00