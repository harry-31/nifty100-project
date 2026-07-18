import pandas as pd

from src.analytics.cashflow_kpis import capital_allocation_pattern


def generate_capital_allocation(
    input_file="data/raw/cashflow.xlsx",
    output_file="output/capital_allocation.csv",
):
    """
    Generate Capital Allocation CSV.
    """

    df = pd.read_excel(input_file, skiprows=1)

    rows = []

    for _, row in df.iterrows():

        pattern = capital_allocation_pattern(
            row["operating_activity"],
            row["investing_activity"],
            row["financing_activity"],
        )

        rows.append(
            {
                "company_id": row["company_id"],
                "year": row["year"],
                "cfo_sign": "+" if row["operating_activity"] >= 0 else "-",
                "cfi_sign": "+" if row["investing_activity"] >= 0 else "-",
                "cff_sign": "+" if row["financing_activity"] >= 0 else "-",
                "pattern_label": pattern,
            }
        )

    result = pd.DataFrame(rows)

    result.to_csv(output_file, index=False)

    return result