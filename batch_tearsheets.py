import sqlite3
import csv
from pathlib import Path

from src.reports.tearsheet import (
    build_tearsheet,
    load_company,
)

ROOT = Path(__file__).resolve().parent

OUTPUT = ROOT / "reports" / "tearsheets"

SKIPPED = ROOT / "output" / "skipped_tearsheets.csv"

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

SKIPPED.parent.mkdir(
    parents=True,
    exist_ok=True,
)


def main():

    conn = sqlite3.connect(
        ROOT / "nifty100.db"
    )

    rows = conn.execute(
        "SELECT id FROM companies ORDER BY id"
    ).fetchall()

    conn.close()

    tickers = [
        str(row[0])
        for row in rows
    ]

    print("=" * 70)
    print("DAY 34 — BATCH TEARSHEET GENERATION")
    print("=" * 70)

    print(
        "Companies in master:",
        len(tickers)
    )

    skipped = []
    generated = []
    failed = []

    for index, ticker in enumerate(
        tickers,
        start=1
    ):

        print()
        print(
            f"[{index}/{len(tickers)}] {ticker}"
        )

        try:

            data = load_company(
                ticker
            )

            pnl = data["pnl"]

            if pnl.empty:

                print(
                    "SKIPPED — no P&L data"
                )

                skipped.append(
                    (
                        ticker,
                        "No P&L data",
                    )
                )

                continue

            if "year_num" in pnl.columns:

                years = (
                    pnl["year_num"]
                    .dropna()
                    .nunique()
                )

            else:

                years = (
                    pnl["year"]
                    .apply(
                        lambda x: str(x)
                    )
                    .nunique()
                )

            if years < 3:

                print(
                    f"SKIPPED — only {years} years"
                )

                skipped.append(
                    (
                        ticker,
                        f"Fewer than 3 years ({years})",
                    )
                )

                continue

            path = build_tearsheet(
                ticker
            )

            size_kb = (
                path.stat().st_size
                / 1024
            )

            print(
                f"Generated: {path.name}"
            )

            print(
                f"Size: {size_kb:.1f} KB"
            )

            generated.append(
                ticker
            )

        except Exception as exc:

            print(
                f"FAILED: {exc}"
            )

            failed.append(
                (
                    ticker,
                    str(exc),
                )
            )

    # --------------------------------------------------------
    # SKIPPED FILE
    # --------------------------------------------------------

    with open(
        SKIPPED,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "ticker",
                "reason",
            ]
        )

        writer.writerows(
            skipped
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    pdfs = list(
        OUTPUT.glob(
            "*_tearsheet.pdf"
        )
    )

    print()
    print("=" * 70)
    print("DAY 34 BATCH SUMMARY")
    print("=" * 70)

    print(
        "Master companies:",
        len(tickers)
    )

    print(
        "Generated:",
        len(generated)
    )

    print(
        "Skipped:",
        len(skipped)
    )

    print(
        "Failed:",
        len(failed)
    )

    print(
        "PDF files found:",
        len(pdfs)
    )

    print(
        "Skipped file:",
        SKIPPED
    )

    if skipped:
        print()
        print("SKIPPED:")
        for ticker, reason in skipped:
            print(
                f"  {ticker}: {reason}"
            )

    if failed:
        print()
        print("FAILED:")
        for ticker, reason in failed:
            print(
                f"  {ticker}: {reason}"
            )

    if len(generated) == 92:
        print()
        print("STATUS: DAY 34 TEARSHEET BATCH COMPLETE")

    elif len(generated) + len(skipped) == 92:
        print()
        print(
            "STATUS: BATCH COMPLETE WITH SKIPPED COMPANIES"
        )

    else:
        print()
        print(
            "STATUS: BATCH NEEDS REVIEW"
        )


if __name__ == "__main__":
    main()
