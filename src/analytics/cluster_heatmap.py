import pandas as pd
import matplotlib.pyplot as plt


CLUSTER_FILE = "output/cluster_labels.csv"


FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "operating_profit_margin_pct",
    "revenue_cagr",
    "fcf_cagr_5yr",
]


def create_correlation_heatmap():
    df = pd.read_csv(CLUSTER_FILE)

    correlation = df[FEATURES].corr()

    print("Correlation Matrix:")
    print(correlation.round(2))

    plt.figure(figsize=(8, 6))
    plt.imshow(correlation, aspect="auto")
    plt.colorbar(label="Correlation")

    plt.xticks(
        range(len(FEATURES)),
        FEATURES,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        range(len(FEATURES)),
        FEATURES
    )

    plt.title("Clustering Feature Correlation")
    plt.tight_layout()

    plt.savefig(
        "reports/clustering_correlation_heatmap.png",
        dpi=150
    )

    plt.close()

    print(
        "Saved: reports/clustering_correlation_heatmap.png"
    )


if __name__ == "__main__":
    create_correlation_heatmap()