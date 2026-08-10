import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

DB_PATH = Path("nifty100.db")


def load_financial_data():
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        debt_to_equity,
        operating_profit_margin_pct,
        revenue_cagr,
        free_cash_flow_cr
    FROM financial_ratios
    WHERE year != 'TTM'
    ORDER BY company_id, year
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df
def calculate_fcf_cagr(group):
    group = group.sort_values("year").reset_index(drop=True)

    if len(group) < 6:
        return None

    start = group.iloc[-6]["free_cash_flow_cr"]
    end = group.iloc[-1]["free_cash_flow_cr"]

    if pd.isna(start) or pd.isna(end):
        return None

    if start <= 0 or end <= 0:
        return None

    return round(((end / start) ** (1 / 5) - 1) * 100, 2)
def prepare_clustering_data(df):
    latest = df.groupby("company_id").tail(1).copy()

    fcf_results = []

    for company_id, group in df.groupby("company_id"):
        cagr = calculate_fcf_cagr(group)

        fcf_results.append({
            "company_id": company_id,
            "fcf_cagr_5yr": cagr
        })

    fcf_cagr = pd.DataFrame(fcf_results)

    features = [
        "return_on_equity_pct",
        "debt_to_equity",
        "operating_profit_margin_pct",
        "revenue_cagr",
    ]

    latest = latest[
        ["company_id"] + features
    ]

    result = latest.merge(
        fcf_cagr,
        on="company_id",
        how="left"
    )
    sector_df = pd.read_sql_query(
        "SELECT company_id, broad_sector FROM sectors",
        sqlite3.connect(DB_PATH)
    )
    sector_df = sector_df.rename(columns={"broad_sector": "sector"})

    result = result.merge(
        sector_df,
        on="company_id",
        how="left"
    )

    cluster_features = [
        "return_on_equity_pct",
        "debt_to_equity",
        "operating_profit_margin_pct",
        "revenue_cagr",
        "fcf_cagr_5yr",
    ]

    for col in cluster_features:
        result[col] = result.groupby("sector")[col].transform(
            lambda x: x.fillna(x.median())
        )
    return result
def run_kmeans(clustering_data):
    cluster_features = [
        "return_on_equity_pct",
        "debt_to_equity",
        "operating_profit_margin_pct",
        "revenue_cagr",
        "fcf_cagr_5yr",
    ]

    scaler = StandardScaler()

    X = scaler.fit_transform(
        clustering_data[cluster_features]
    )

    kmeans = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=10
    )

    clustering_data = clustering_data.copy()

    clustering_data["cluster_id"] = kmeans.fit_predict(X)

    distances = kmeans.transform(X)

    clustering_data["centroid_distance"] = distances.min(axis=1)

    return clustering_data, kmeans, scaler

def create_elbow_plot(clustering_data):
    cluster_features = [
        "return_on_equity_pct",
        "debt_to_equity",
        "operating_profit_margin_pct",
        "revenue_cagr",
        "fcf_cagr_5yr",
    ]

    scaler = StandardScaler()
    X = scaler.fit_transform(clustering_data[cluster_features])

    k_values = range(2, 11)
    inertias = []

    for k in k_values:
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )
        model.fit(X)
        inertias.append(model.inertia_)

    Path("reports").mkdir(exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.plot(k_values, inertias, marker="o")
    plt.xlabel("Number of Clusters (k)")
    plt.ylabel("Inertia")
    plt.title("Elbow Method for KMeans Clustering")
    plt.xticks(list(k_values))
    plt.tight_layout()
    plt.savefig("reports/elbow_plot.png", dpi=150)
    plt.close()

    print("Saved: reports/elbow_plot.png")
    
if __name__ == "__main__":
    df = load_financial_data()

    clustering_data = prepare_clustering_data(df)

    clustered_data, kmeans, scaler = run_kmeans(
        clustering_data
    )
    output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

cluster_output = clustered_data[
    [
        "company_id",
        "cluster_id",
        "centroid_distance",
        "return_on_equity_pct",
        "debt_to_equity",
        "operating_profit_margin_pct",
        "revenue_cagr",
        "fcf_cagr_5yr",
    ]
]

cluster_output.to_csv(
    output_dir / "cluster_labels.csv",
    index=False
)

print("Saved:", output_dir / "cluster_labels.csv")
    
print("Cluster counts:")
print(clustered_data["cluster_id"].value_counts().sort_index())

print("\nClustered data:")
print(clustered_data.head())

print("\nInertia:", kmeans.inertia_)
create_elbow_plot(clustering_data)