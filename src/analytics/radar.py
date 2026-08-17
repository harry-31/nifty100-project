import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.analytics.peer import DB_PATH


def generate_radar_chart(company_id, filename=None):
    """
    Generate a radar chart for the latest available annual record
    of a company directly from financial_ratios.
    """

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            company_id,
            year,
            return_on_equity_pct,
            operating_profit_margin_pct,
            revenue_cagr,
            pat_cagr,
            interest_coverage
        FROM financial_ratios
        WHERE company_id = ?
          AND UPPER(CAST(year AS TEXT)) != 'TTM'
        ORDER BY CAST(SUBSTR(year, 1, 4) AS INTEGER) DESC
        LIMIT 1
    """

    row = conn.execute(query, (company_id,)).fetchone()
    conn.close()

    if row is None:
        raise ValueError(
            f"Company '{company_id}' not found in financial ratios."
        )

    metrics = [
        "return_on_equity_pct",
        "operating_profit_margin_pct",
        "revenue_cagr",
        "pat_cagr",
        "interest_coverage",
    ]

    values = list(row[2:])

    # Replace missing values with 0 so every company gets a chart.
    values = [
        0 if value is None or pd_isna(value) else float(value)
        for value in values
    ]

    values += values[:1]

    angles = np.linspace(
        0,
        2 * np.pi,
        len(metrics),
        endpoint=False,
    ).tolist()

    angles += angles[:1]

    _fig, ax = plt.subplots(
        figsize=(6, 6),
        subplot_kw={"polar": True},
    )

    ax.plot(angles, values)
    ax.fill(angles, values, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(
        [
            "ROE",
            "OPM",
            "Revenue CAGR",
            "PAT CAGR",
            "Interest Coverage",
        ]
    )

    if filename is None:
        filename = f"reports/radar_charts/{company_id}_radar.png"

    output = Path(filename)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output)
    plt.close()

    return output


def pd_isna(value):
    return value != value