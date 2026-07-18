from typing import Optional


def net_profit_margin(net_profit: float, sales: float) -> Optional[float]:

    if sales == 0:
        return None
    return round((net_profit / sales) * 100, 2)


def operating_profit_margin(operating_profit: float, sales: float) -> Optional[float]:
    
    if sales == 0:
        return None
    return round((operating_profit / sales) * 100, 2)


def check_opm_difference(calculated_opm: float, source_opm: float) -> bool:
    
    return abs(calculated_opm - source_opm) > 1


def return_on_equity(
    net_profit: float,
    equity_capital: float,
    reserves: float,
) -> Optional[float]:
    
    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return round((net_profit / equity) * 100, 2)


def return_on_capital_employed(
    ebit: float,
    equity_capital: float,
    reserves: float,
    borrowings: float,
) -> Optional[float]:
    
    capital = equity_capital + reserves + borrowings

    if capital <= 0:
        return None

    return round((ebit / capital) * 100, 2)


def return_on_assets(
    net_profit: float,
    total_assets: float,
) -> Optional[float]:
    
    if total_assets == 0:
        return None

    return round((net_profit / total_assets) * 100, 2)

def debt_to_equity(
    borrowings: float,
    equity_capital: float,
    reserves: float,
):
   
    if borrowings == 0:
        return 0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return round(borrowings / equity, 2)


def high_leverage_flag(de_ratio: float, sector: str) -> bool:
    
    if sector.lower() == "financials":
        return False

    return de_ratio is not None and de_ratio > 5


def interest_coverage_ratio(
    operating_profit: float,
    other_income: float,
    interest: float,
):
    
    if interest == 0:
        return None

    return round((operating_profit + other_income) / interest, 2)


def icr_label(icr):
    
    if icr is None:
        return "Debt Free"

    return 


def icr_warning_flag(icr) -> bool:
    
    if icr is None:
        return False

    return icr < 1.5


def net_debt(
    borrowings: float,
    investments: float,
):

    return round(borrowings - investments, 2)


def asset_turnover(
    sales: float,
    total_assets: float,
):
    
    if total_assets == 0:
        return None

    return round(sales / total_assets, 2)