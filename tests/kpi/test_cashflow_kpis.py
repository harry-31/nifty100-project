from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern
)


def test_free_cash_flow():
    assert free_cash_flow(1000, -300) == 700


def test_cfo_quality_high():
    assert cfo_quality_score(120, 100) == "High Quality"


def test_cfo_quality_moderate():
    assert cfo_quality_score(70, 100) == "Moderate"


def test_cfo_quality_accrual():
    assert cfo_quality_score(40, 100) == "Accrual Risk"


def test_cfo_quality_zero_pat():
    assert cfo_quality_score(100, 0) is None


def test_capex_intensity_asset_light():
    value, label = capex_intensity(-20, 1000)
    assert value == 2.0
    assert label == "Asset Light"


def test_capex_intensity_moderate():
    value, label = capex_intensity(-50, 1000)
    assert value == 5.0
    assert label == "Moderate"


def test_capex_intensity_capital_intensive():
    value, label = capex_intensity(-150, 1000)
    assert value == 15.0
    assert label == "Capital Intensive"


def test_fcf_conversion_rate():
    assert fcf_conversion_rate(700, 1000) == 70.0


def test_fcf_conversion_zero_profit():
    assert fcf_conversion_rate(700, 0) is None

    def test_reinvestor():

        assert capital_allocation_pattern(100, -50, -30) == "Reinvestor"


def test_shareholder_returns():
    assert capital_allocation_pattern(
        100,
        -50,
        -30,
        cfo_pat_ratio=1.5
    ) == "Shareholder Returns"


def test_liquidating_assets():
    assert capital_allocation_pattern(
        100,
        50,
        -30
    ) == "Liquidating Assets"


def test_distress_signal():
    assert capital_allocation_pattern(
        -100,
        50,
        20
    ) == "Distress Signal"


def test_growth_funded_by_debt():
    assert capital_allocation_pattern(
        -100,
        -50,
        40
    ) == "Growth Funded by Debt"


def test_cash_accumulator():
    assert capital_allocation_pattern(
        100,
        50,
        40
    ) == "Cash Accumulator"


def test_pre_revenue():
    assert capital_allocation_pattern(
        -100,
        -50,
        -40
    ) == "Pre-Revenue"


def test_mixed():
    assert capital_allocation_pattern(
        100,
        -50,
        40
    ) == "Mixed"