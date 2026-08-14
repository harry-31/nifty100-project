import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT = ROOT / "reports" / "sector"

OUTPUT.mkdir(parents=True, exist_ok=True)

# ============================================================
# STYLES
# ============================================================

NAVY = colors.HexColor("#172B4D")
LIGHT_GREY = colors.HexColor("#F3F4F6")
DARK = colors.HexColor("#111827")
MID_GREY = colors.HexColor("#6B7280")
WHITE = colors.white

styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "SectorTitle",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    textColor=WHITE,
    alignment=TA_CENTER,
)

SECTION = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
    spaceBefore=4,
    spaceAfter=5,
)

BODY = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9,
    textColor=DARK,
)

SMALL = ParagraphStyle(
    "Small",
    parent=BODY,
    fontSize=6.5,
    leading=8,
)

# ============================================================
# DATABASE LOAD
# ============================================================


def load_data():

    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        conn,
    )

    sectors = pd.read_sql(
        """
        SELECT
            company_id,
            broad_sector,
            sub_sector
        FROM sectors
        """,
        conn,
    )

    ratios = pd.read_sql(
        """
        SELECT *
        FROM financial_ratios
        """,
        conn,
    )

    pnl = pd.read_sql(
        """
        SELECT
            company_id,
            year,
            sales,
            net_profit,
            opm_percentage,
            eps
        FROM profitandloss
        """,
        conn,
    )

    cashflow = pd.read_sql(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity
        FROM cashflow
        """,
        conn,
    )

    conn.close()

    return (
        companies,
        sectors,
        ratios,
        pnl,
        cashflow,
    )


# ============================================================
# YEAR NORMALIZATION
# ============================================================


def normalize_year(value):

    if pd.isna(value):
        return np.nan

    text = str(value)

    import re

    match = re.search(r"(19|20)\d{2}", text)

    if match:
        return int(match.group())

    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return np.nan


# ============================================================
# LATEST VALUE
# ============================================================


def latest_value(df, column):

    if df.empty or column not in df.columns:
        return np.nan

    temp = df.copy()

    temp["year_num"] = temp["year"].apply(normalize_year)

    temp = temp.dropna(subset=["year_num"]).sort_values("year_num")

    if temp.empty:
        return np.nan

    return pd.to_numeric(
        temp.iloc[-1][column],
        errors="coerce",
    )


# ============================================================
# COMPANY KPI TABLE
# ============================================================


def build_company_kpis(
    companies,
    sectors,
    ratios,
    pnl,
    cashflow,
):

    sector_map = sectors[
        [
            "company_id",
            "broad_sector",
            "sub_sector",
        ]
    ].drop_duplicates("company_id")

    base = companies.merge(
        sector_map,
        on="company_id",
        how="left",
    )

    records = []

    for company_id in base["company_id"]:

        company_row = base[base["company_id"] == company_id].iloc[0]

        rr = ratios[ratios["company_id"].astype(str) == str(company_id)].copy()

        pl = pnl[pnl["company_id"].astype(str) == str(company_id)].copy()

        cf = cashflow[cashflow["company_id"].astype(str) == str(company_id)].copy()

        record = {
            "company_id": company_id,
            "company_name": company_row["company_name"],
            "broad_sector": company_row["broad_sector"],
            "sub_sector": company_row["sub_sector"],
            "Revenue": latest_value(
                pl,
                "sales",
            ),
            "Net Profit": latest_value(
                pl,
                "net_profit",
            ),
            "ROE": latest_value(
                rr,
                "return_on_equity_pct",
            ),
            "D/E": latest_value(
                rr,
                "debt_to_equity",
            ),
            "OPM": latest_value(
                pl,
                "opm_percentage",
            ),
            "FCF": np.nan,
        }

        if not cf.empty:

            cf["year_num"] = cf["year"].apply(normalize_year)

            cf = cf.dropna(subset=["year_num"]).sort_values("year_num")

            if not cf.empty:

                latest = cf.iloc[-1]

                cfo = pd.to_numeric(
                    latest["operating_activity"],
                    errors="coerce",
                )

                cfi = pd.to_numeric(
                    latest["investing_activity"],
                    errors="coerce",
                )

                if pd.notna(cfo) and pd.notna(cfi):
                    record["FCF"] = cfo + cfi

        records.append(record)

    return pd.DataFrame(records)


# ============================================================
# SECTOR SUMMARY
# ============================================================


def sector_summary(
    company_kpis,
    sector,
):

    data = company_kpis[company_kpis["broad_sector"] == sector].copy()

    numeric = [
        "Revenue",
        "Net Profit",
        "ROE",
        "D/E",
        "OPM",
        "FCF",
    ]

    rows = []

    for col in numeric:

        value = pd.to_numeric(
            data[col],
            errors="coerce",
        ).median()

        rows.append(
            [
                col,
                (f"{value:,.2f}" if pd.notna(value) else "N/A"),
            ]
        )

    return rows


# ============================================================
# TABLE HELPER
# ============================================================


def make_table(
    data,
    col_widths,
    header=True,
):

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1 if header else 0,
    )

    commands = [
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.4,
            colors.HexColor("#D1D5DB"),
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
    ]

    if header:

        commands.extend(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    WHITE,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
            ]
        )

    table.setStyle(TableStyle(commands))

    return table


# ============================================================
# BUILD SECTOR REPORT
# ============================================================


def build_sector_report(
    sector,
    company_kpis,
):

    output = OUTPUT / f"{sector.replace('/', '_')}_report.pdf"

    data = company_kpis[company_kpis["broad_sector"] == sector].copy()

    data = data.sort_values("company_id")

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"{sector} Sector Report",
    )

    story = []

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    header_table = Table(
        [
            [
                Paragraph(
                    f"{sector}<br/>Sector Report",
                    TITLE,
                )
            ]
        ],
        colWidths=[186 * mm],
        rowHeights=[28 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    story.append(header_table)

    story.append(Spacer(1, 6 * mm))

    # --------------------------------------------------------
    # SECTOR SUMMARY
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Sector Summary — Median KPIs",
            SECTION,
        )
    )

    summary = [
        [
            Paragraph(
                "Metric",
                BODY,
            ),
            Paragraph(
                "Median",
                BODY,
            ),
        ]
    ]

    for metric, value in sector_summary(
        company_kpis,
        sector,
    ):

        summary.append(
            [
                Paragraph(
                    metric,
                    BODY,
                ),
                Paragraph(
                    value,
                    BODY,
                ),
            ]
        )

    story.append(
        make_table(
            summary,
            [
                90 * mm,
                90 * mm,
            ],
        )
    )

    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            f"Companies in sector: {len(data)}",
            BODY,
        )
    )

    story.append(Spacer(1, 4 * mm))

    # --------------------------------------------------------
    # COMPANY TABLE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Company Metrics",
            SECTION,
        )
    )

    table_data = [
        [
            Paragraph("Ticker", SMALL),
            Paragraph("Company", SMALL),
            Paragraph("Revenue", SMALL),
            Paragraph("Net Profit", SMALL),
            Paragraph("ROE", SMALL),
            Paragraph("D/E", SMALL),
            Paragraph("OPM", SMALL),
            Paragraph("FCF", SMALL),
        ]
    ]

    for _, row in data.iterrows():

        def fmt(value):

            if pd.isna(value):
                return "N/A"

            return f"{float(value):,.2f}"

        table_data.append(
            [
                Paragraph(
                    str(row["company_id"]),
                    SMALL,
                ),
                Paragraph(
                    str(row["company_name"]),
                    SMALL,
                ),
                Paragraph(
                    fmt(row["Revenue"]),
                    SMALL,
                ),
                Paragraph(
                    fmt(row["Net Profit"]),
                    SMALL,
                ),
                Paragraph(
                    fmt(row["ROE"]),
                    SMALL,
                ),
                Paragraph(
                    fmt(row["D/E"]),
                    SMALL,
                ),
                Paragraph(
                    fmt(row["OPM"]),
                    SMALL,
                ),
                Paragraph(
                    fmt(row["FCF"]),
                    SMALL,
                ),
            ]
        )

    story.append(
        make_table(
            table_data,
            [
                20 * mm,
                46 * mm,
                20 * mm,
                20 * mm,
                17 * mm,
                17 * mm,
                17 * mm,
                25 * mm,
            ],
        )
    )

    doc.build(story)

    return output


# ============================================================
# MAIN
# ============================================================


def main():

    print("=" * 70)
    print("DAY 34 — SECTOR REPORT GENERATION")
    print("=" * 70)

    (
        companies,
        sectors,
        ratios,
        pnl,
        cashflow,
    ) = load_data()

    print(
        "Master companies:",
        len(companies),
    )

    company_kpis = build_company_kpis(
        companies,
        sectors,
        ratios,
        pnl,
        cashflow,
    )

    sector_list = sorted(company_kpis["broad_sector"].dropna().unique())

    print(
        "Distinct sectors:",
        len(sector_list),
    )

    print(
        "Sectors:",
        sector_list,
    )

    generated = []
    failed = []

    for index, sector in enumerate(
        sector_list,
        start=1,
    ):

        print()
        print(f"[{index}/{len(sector_list)}] " f"{sector}")

        try:

            path = build_sector_report(
                sector,
                company_kpis,
            )

            size_kb = path.stat().st_size / 1024

            print(f"Generated: {path.name}")

            print(f"Size: {size_kb:.1f} KB")

            generated.append(sector)

        except Exception as exc:  # noqa: BLE001

            print(
                "FAILED:",
                sector,
            )

            print(
                "Error:",
                exc,
            )

            failed.append(sector)

    print()
    print("=" * 70)
    print("DAY 34 — SECTOR REPORT RESULT")
    print("=" * 70)

    print(
        "Expected sectors:",
        len(sector_list),
    )

    print(
        "Generated:",
        len(generated),
    )

    print(
        "Failed:",
        len(failed),
    )

    print(
        "Output directory:",
        OUTPUT,
    )

    if failed:

        print(
            "Failed sectors:",
            failed,
        )

    if (
        len(generated) == len(sector_list)
        and len(sector_list) == 11
        and len(failed) == 0
    ):

        print("STATUS: SECTOR REPORTS COMPLETE")

    else:

        print("STATUS: SECTOR REPORTS NEED REVIEW")


if __name__ == "__main__":
    main()


def build_portfolio_sector_summary(company_kpis):

    output = OUTPUT / "Portfolio_Sector_Summary_report.pdf"

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Portfolio Sector Summary",
    )

    story = []

    header_table = Table(
        [
            [
                Paragraph(
                    "NIFTY 100<br/>Portfolio Sector Summary",
                    TITLE,
                )
            ]
        ],
        colWidths=[186 * mm],
        rowHeights=[28 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            "Portfolio-wide Median KPIs",
            SECTION,
        )
    )

    metrics = [
        "Revenue",
        "Net Profit",
        "ROE",
        "D/E",
        "OPM",
        "FCF",
    ]

    summary = [
        [
            Paragraph("Metric", BODY),
            Paragraph("Portfolio Median", BODY),
        ]
    ]

    for metric in metrics:

        value = pd.to_numeric(
            company_kpis[metric],
            errors="coerce",
        ).median()

        summary.append(
            [
                Paragraph(metric, BODY),
                Paragraph(
                    f"{value:,.2f}" if pd.notna(value) else "N/A",
                    BODY,
                ),
            ]
        )

    story.append(
        make_table(
            summary,
            [90 * mm, 90 * mm],
        )
    )

    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            "Sector-level Comparison",
            SECTION,
        )
    )

    sector_rows = [
        [
            Paragraph("Sector", SMALL),
            Paragraph("Companies", SMALL),
            Paragraph("Median ROE", SMALL),
            Paragraph("Median D/E", SMALL),
            Paragraph("Median OPM", SMALL),
        ]
    ]

    for sector in sorted(company_kpis["broad_sector"].dropna().unique()):

        data = company_kpis[company_kpis["broad_sector"] == sector]

        roe = pd.to_numeric(
            data["ROE"],
            errors="coerce",
        ).median()

        de = pd.to_numeric(
            data["D/E"],
            errors="coerce",
        ).median()

        opm = pd.to_numeric(
            data["OPM"],
            errors="coerce",
        ).median()

        sector_rows.append(
            [
                Paragraph(str(sector), SMALL),
                Paragraph(
                    str(len(data)),
                    SMALL,
                ),
                Paragraph(
                    f"{roe:.2f}" if pd.notna(roe) else "N/A",
                    SMALL,
                ),
                Paragraph(
                    f"{de:.2f}" if pd.notna(de) else "N/A",
                    SMALL,
                ),
                Paragraph(
                    f"{opm:.2f}" if pd.notna(opm) else "N/A",
                    SMALL,
                ),
            ]
        )

    story.append(
        make_table(
            sector_rows,
            [
                75 * mm,
                25 * mm,
                25 * mm,
                25 * mm,
                30 * mm,
            ],
        )
    )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "Note: The current Nifty 100 database contains "
            "10 broad sectors covering all 92 companies. "
            "This portfolio-wide report is generated as the "
            "11th PDF deliverable without assigning companies "
            "to an artificial sector.",
            SMALL,
        )
    )

    doc.build(story)

    return output
