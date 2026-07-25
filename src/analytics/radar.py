import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from src.analytics.peer import calculate_peer_rankings


def generate_radar_chart(company_id, filename=None):
    """
    Generate a radar chart for the latest available record of a company.
    """
    df = calculate_peer_rankings()

    company_df = df[df["company_id"] == company_id]

    if company_df.empty:
        raise ValueError(f"Company '{company_id}' not found in peer comparison data.")

    company = company_df.sort_values("year").iloc[-1]

    metrics = [
        "return_on_equity_pct",
        "operating_profit_margin_pct",
        "revenue_cagr",
        "pat_cagr",
        "interest_coverage",
    ]

    values = company[metrics].tolist()  

    values += values[:1]

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    ax.plot(angles, values)
    ax.fill(angles, values, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([
        "ROE",
        "OPM",
        "Revenue CAGR",
        "PAT CAGR",
        "Interest Coverage",
    ])
    
    if filename is None:
     filename = f"reports/radar_charts/{company_id}_radar.png"
    
    output = Path(filename)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output)
    plt.close()

    return output