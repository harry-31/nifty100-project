import pandas as pd


CLUSTER_FILE = "output/cluster_labels.csv"


def load_cluster_data():
    return pd.read_csv(CLUSTER_FILE)


def create_cluster_profile(df):
    features = [
        "return_on_equity_pct",
        "debt_to_equity",
        "operating_profit_margin_pct",
        "revenue_cagr",
        "fcf_cagr_5yr",
    ]

    profile = (
        df.groupby("cluster_id")[features]
        .mean()
        .round(2)
    )

    return profile

CLUSTER_NAMES = {
    0: "Balanced Compounders",
    1: "Extreme Growth Outlier",
    2: "Extreme ROE Leaders",
    3: "High-Leverage Growth",
    4: "High-Margin Quality",
}

def save_cluster_profile(profile):
    profile.to_csv("output/cluster_profile.csv")
    print("Saved: output/cluster_profile.csv")

def save_outliers(df):
    outliers = (
        df.sort_values("centroid_distance", ascending=False)
        .head(15)
        [
            [
                "company_id",
                "cluster_id",
                "centroid_distance",
            ]
        ]
    )

    outliers.to_csv(
        "output/cluster_outliers.csv",
        index=False
    )

    print("Saved: output/cluster_outliers.csv")
    
if __name__ == "__main__":
    df = load_cluster_data()

    profile = create_cluster_profile(df)
    profile["cluster_name"] = profile.index.map(CLUSTER_NAMES)

    print("Cluster Mean Profile:")
    print(profile)

    save_cluster_profile(profile)
    save_outliers(df)