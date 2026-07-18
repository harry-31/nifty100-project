from typing import Optional

def free_cash_flow(
    operating_activity: float,
    investing_activity: float,
) -> float:

    return round(operating_activity + investing_activity, 2)


def cfo_quality_score(
    cfo: float,
    pat: float,
) -> Optional[str]:
    
    if pat == 0:
        return None

    ratio = cfo / pat

    if ratio > 1:
        return "High Quality"

    if ratio >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_intensity(
    investing_activity: float,
    sales: float,
):
    
    if sales == 0:
        return None

    capex = abs(investing_activity) / sales * 100

    if capex < 3:
        label = "Asset Light"
    elif capex <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return round(capex, 2), label


def fcf_conversion_rate(
    free_cash_flow: float,
    operating_profit: float,
):
    
    if operating_profit == 0:
        return None

    return round((free_cash_flow / operating_profit) * 100, 2)

def capital_allocation_pattern(
    cfo: float,
    cfi: float,
    cff: float,
    cfo_pat_ratio: float = None,
):
    """
    Returns capital allocation pattern.
    """

    cfo_sign = "+" if cfo >= 0 else "-"
    cfi_sign = "+" if cfi >= 0 else "-"
    cff_sign = "+" if cff >= 0 else "-"

    # (+,-,-)
    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "-":
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1:
            return "Shareholder Returns"
        return "Reinvestor"

    # (+,+,-)
    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "-":
        return "Liquidating Assets"

    # (-,+,+)
    if cfo_sign == "-" and cfi_sign == "+" and cff_sign == "+":
        return "Distress Signal"

    # (-,-,+)
    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "+":
        return "Growth Funded by Debt"

    # (+,+,+)
    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "+":
        return "Cash Accumulator"

    # (-,-,-)
    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "-":
        return "Pre-Revenue"

    # (+,-,+)
    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "+":
        return "Mixed"

    return "Unknown"