import pandas as pd

for file in [
    "data/raw/cashflow.xlsx",
    "data/raw/balancesheet.xlsx",
    "data/raw/profitandloss.xlsx",
]:
    print("\n" + "=" * 80)
    print(file)
    print("=" * 80)

    df = pd.read_excel(file)

    print("Shape:", df.shape)
    print("Columns:", list(df.columns))

    for ticker in ["ATGL", "SBIN"]:
        matches = df[
            df.astype(str)
            .apply(
                lambda row: row.str.contains(
                    ticker,
                    case=False,
                    na=False,
                    regex=False
                ).any(),
                axis=1
            )
        ]

        print(f"\n{ticker} rows:", len(matches))

        if len(matches):
            print(matches.to_string(index=False))

