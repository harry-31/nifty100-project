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
    PageBreak,
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
OUTPUT = ROOT / "reports" / "portfolio"

OUTPUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# COLORS / STYLES
# ============================================================

NAVY = colors.HexColor("#172B4D")
LIGHT_GREY = colors.HexColor("#F3F4F6")
MID_GREY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#111827")
GREEN = colors.HexColor("#15803D")
RED = colors.HexColor("#B91C1C")

styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "PortfolioTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    textColor=NAVY,
    spaceAfter=4,
)

SUBTITLE = ParagraphStyle(
    "PortfolioSubtitle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=MID_GREY,
)

SECTION = ParagraphStyle(
    "PortfolioSection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
    spaceBefore=4,
    spaceAfter=5,
)

CELL = ParagraphStyle(
    "PortfolioCell",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=DARK,
)

CELL_CENTER = ParagraphStyle(
    "PortfolioCellCenter",
    parent=CELL,
    alignment=TA_CENTER,
)

KPI_VALUE = ParagraphStyle(
    "PortfolioKPIValue",
    parent=CELL_CENTER,
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
)

KPI_LABEL = ParagraphStyle(
    "PortfolioKPILabel",
    parent=CELL_CENTER,
    fontSize=7,
    leading=8,
    textColor=MID_GREY,
)


# ============================================================
# HELPERS
# ============================================================


def normalize_year(value):
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    digits = ""
    for ch in text:
        if ch.isdigit():
            digits += ch

    if len(digits) >= 4:
        try:
            return int(digits[:4])
        except ValueError:
            return np.nan

    return np.nan


def safe_float(value):
    try:
        if pd.isna(value):
            return np.nan
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def fmt(value, suffix=""):
    value = safe_float(value)

    if pd.isna(value):
        return "N/A"

    if abs(value) >= 100000:
        return f"{value:,.0f}{suffix}"

    if abs(value) >= 1000:
        return f"{value:,.1f}{suffix}"

    return f"{value:.2f}{suffix}"


def trend_arrow(current, previous):
    current = safe_float(current)
    previous = safe_float(previous)

    if pd.isna(current) or pd.isna(previous):
        return "→"

    if previous == 0:
        return "→"

    change_pct = abs((current - previous) / abs(previous)) * 100

    if change_pct <= 2:
        return "→"

    if current > previous:
        return "↑"

    if current < previous:
        return "↓"

    return "→"


def arrow_color(arrow):
    if arrow == "↑":
        return GREEN

    if arrow == "↓":
        return RED

    return MID_GREY


# ============================================================
# DATA LOADING
# ============================================================


def load_data():
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql(
        "SELECT * FROM companies",
        conn,
    )

    sectors = pd.read_sql(
        "SELECT * FROM sectors",
        conn,
    )

    pnl = pd.read_sql(
        "SELECT * FROM profitandloss",
        conn,
    )

    ratios = pd.read_sql(
        "SELECT * FROM financial_ratios",
        conn,
    )

    cashflow = pd.read_sql(
        "SELECT * FROM cashflow",
        conn,
    )

    conn.close()

    for df in [pnl, ratios, cashflow]:
        if "year" in df.columns:
            df["year_num"] = df["year"].apply(normalize_year)

    return (
        companies,
        sectors,
        pnl,
        ratios,
        cashflow,
    )


# ============================================================
# COMPANY KPI CALCULATION
# ============================================================


def company_kpis(
    company_id,
    companies,
    sectors,
    pnl,
    ratios,
    cashflow,
):

    company_rows = companies[companies["id"].astype(str) == str(company_id)]

    sector_rows = sectors[sectors["company_id"].astype(str) == str(company_id)]

    pnl_c = pnl[pnl["company_id"].astype(str) == str(company_id)].copy()

    ratio_c = ratios[ratios["company_id"].astype(str) == str(company_id)].copy()

    cf_c = cashflow[cashflow["company_id"].astype(str) == str(company_id)].copy()

    pnl_c = pnl_c.sort_values("year_num")
    ratio_c = ratio_c.sort_values("year_num")
    cf_c = cf_c.sort_values("year_num")

    company_name = str(company_id)

    if not company_rows.empty:
        company_name = str(
            company_rows.iloc[0].get(
                "company_name",
                company_id,
            )
        )

    sector = "Unknown"

    if not sector_rows.empty:
        sector = str(
            sector_rows.iloc[0].get(
                "broad_sector",
                "Unknown",
            )
        )

    result = {
        "company_id": str(company_id),
        "company_name": company_name,
        "sector": sector,
    }

    # --------------------------------------------------------
    # Latest P&L
    # --------------------------------------------------------

    latest_pnl = pnl_c.iloc[-1] if not pnl_c.empty else None

    previous_pnl = pnl_c.iloc[-2] if len(pnl_c) >= 2 else None

    # --------------------------------------------------------
    # Latest ratios
    # --------------------------------------------------------

    latest_ratio = ratio_c.iloc[-1] if not ratio_c.empty else None

    previous_ratio = ratio_c.iloc[-2] if len(ratio_c) >= 2 else None

    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    revenue = (
        safe_float(latest_pnl["sales"])
        if latest_pnl is not None and "sales" in latest_pnl
        else np.nan
    )

    previous_revenue = (
        safe_float(previous_pnl["sales"])
        if previous_pnl is not None and "sales" in previous_pnl
        else np.nan
    )

    # --------------------------------------------------------
    # Net Profit
    # --------------------------------------------------------

    net_profit = (
        safe_float(latest_pnl["net_profit"])
        if latest_pnl is not None and "net_profit" in latest_pnl
        else np.nan
    )

    previous_profit = (
        safe_float(previous_pnl["net_profit"])
        if previous_pnl is not None and "net_profit" in previous_pnl
        else np.nan
    )

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe = (
        safe_float(latest_ratio["return_on_equity_pct"])
        if latest_ratio is not None and "return_on_equity_pct" in latest_ratio
        else np.nan
    )

    previous_roe = (
        safe_float(previous_ratio["return_on_equity_pct"])
        if previous_ratio is not None and "return_on_equity_pct" in previous_ratio
        else np.nan
    )

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce = np.nan

    if latest_ratio is not None and "return_on_equity_pct" in latest_ratio:
        pass

    # ROCE from companies master if available
    if not company_rows.empty:
        roce = safe_float(
            company_rows.iloc[0].get(
                "roce_percentage",
                np.nan,
            )
        )

    # --------------------------------------------------------
    # Debt / Equity
    # --------------------------------------------------------

    de = (
        safe_float(latest_ratio["debt_to_equity"])
        if latest_ratio is not None and "debt_to_equity" in latest_ratio
        else np.nan
    )

    previous_de = (
        safe_float(previous_ratio["debt_to_equity"])
        if previous_ratio is not None and "debt_to_equity" in previous_ratio
        else np.nan
    )

    # --------------------------------------------------------
    # Free Cash Flow
    # --------------------------------------------------------

    fcf = np.nan
    previous_fcf = np.nan

    if latest_ratio is not None:
        fcf = safe_float(
            latest_ratio.get(
                "free_cash_flow_cr",
                np.nan,
            )
        )

    if previous_ratio is not None:
        previous_fcf = safe_float(
            previous_ratio.get(
                "free_cash_flow_cr",
                np.nan,
            )
        )

    # Fallback: calculate FCF from cashflow
    if pd.isna(fcf) and not cf_c.empty:
        latest_cf = cf_c.iloc[-1]

        cfo = safe_float(
            latest_cf.get(
                "operating_activity",
                np.nan,
            )
        )

        cfi = safe_float(
            latest_cf.get(
                "investing_activity",
                np.nan,
            )
        )

        if not pd.isna(cfo) and not pd.isna(cfi):
            fcf = cfo + cfi

    if pd.isna(previous_fcf) and len(cf_c) >= 2:
        previous_cf = cf_c.iloc[-2]

        cfo = safe_float(
            previous_cf.get(
                "operating_activity",
                np.nan,
            )
        )

        cfi = safe_float(
            previous_cf.get(
                "investing_activity",
                np.nan,
            )
        )

        if not pd.isna(cfo) and not pd.isna(cfi):
            previous_fcf = cfo + cfi

    result.update(
        {
            "Revenue": revenue,
            "Net Profit": net_profit,
            "ROE": roe,
            "ROCE": roce,
            "D/E": de,
            "FCF": fcf,
            "Revenue_previous": previous_revenue,
            "Net Profit_previous": previous_profit,
            "ROE_previous": previous_roe,
            "ROCE_previous": np.nan,
            "D/E_previous": previous_de,
            "FCF_previous": previous_fcf,
        }
    )

    return result


# ============================================================
# KPI TABLE
# ============================================================


def kpi_table(data):

    metrics = [
        ("Revenue", "Revenue"),
        ("Net Profit", "Net Profit"),
        ("ROE", "ROE"),
        ("ROCE", "ROCE"),
        ("D/E", "D/E"),
        ("FCF", "FCF"),
    ]

    values = []
    arrows = []

    for label, key in metrics:

        value = data.get(key, np.nan)
        previous = data.get(
            f"{key}_previous",
            np.nan,
        )

        arrow = trend_arrow(
            value,
            previous,
        )

        values.append(
            Paragraph(
                fmt(value),
                KPI_VALUE,
            )
        )

        arrows.append(
            Paragraph(
                f'<font color="{arrow_color(arrow).hexval()}">{arrow}</font>',
                KPI_VALUE,
            )
        )

    labels = [
        Paragraph(
            label,
            KPI_LABEL,
        )
        for label, _ in metrics
    ]

    table_data = [
        values[:3],
        labels[:3],
        arrows[:3],
        values[3:],
        labels[3:],
        arrows[3:],
    ]

    table = Table(
        table_data,
        colWidths=[
            60 * mm,
            60 * mm,
            60 * mm,
        ],
        rowHeights=[
            9 * mm,
            5 * mm,
            5 * mm,
            9 * mm,
            5 * mm,
            5 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.lightgrey,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.white,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    return table


# ============================================================
# BUILD ONE COMPANY PAGE
# ============================================================


def company_page(data):

    story = []

    story.append(
        Table(
            [
                [
                    Paragraph(
                        data["company_name"],
                        ParagraphStyle(
                            "HeaderName",
                            parent=TITLE,
                            textColor=colors.white,
                            fontSize=17,
                        ),
                    ),
                    Paragraph(
                        data["company_id"],
                        ParagraphStyle(
                            "HeaderTicker",
                            parent=TITLE,
                            textColor=colors.white,
                            fontSize=12,
                            alignment=TA_CENTER,
                        ),
                    ),
                ]
            ],
            colWidths=[
                130 * mm,
                50 * mm,
            ],
            style=TableStyle(
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
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            ),
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            f"Sector: {data['sector']}",
            SUBTITLE,
        )
    )

    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "Top 6 KPIs & Trend Direction",
            SECTION,
        )
    )

    story.append(kpi_table(data))

    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            "Trend Interpretation",
            SECTION,
        )
    )

    trend_rows = []

    for key in [
        "Revenue",
        "Net Profit",
        "ROE",
        "ROCE",
        "D/E",
        "FCF",
    ]:

        arrow = trend_arrow(
            data.get(key),
            data.get(
                f"{key}_previous",
                np.nan,
            ),
        )

        trend_rows.append(
            [
                Paragraph(key, CELL),
                Paragraph(
                    fmt(data.get(key)),
                    CELL_CENTER,
                ),
                Paragraph(
                    arrow,
                    ParagraphStyle(
                        "Arrow",
                        parent=CELL_CENTER,
                        fontName="Helvetica-Bold",
                        fontSize=13,
                        textColor=arrow_color(arrow),
                    ),
                ),
            ]
        )

    trend_table = Table(
        trend_rows,
        colWidths=[
            80 * mm,
            65 * mm,
            35 * mm,
        ],
    )

    trend_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.white,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -1),
                    [
                        colors.white,
                        LIGHT_GREY,
                    ],
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.lightgrey,
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
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    story.append(trend_table)

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "Portfolio Summary",
            SECTION,
        )
    )

    story.append(
        Paragraph(
            "This page presents the latest six key financial "
            "indicators for the company together with their "
            "latest-year trend direction. An upward arrow "
            "indicates improvement, a downward arrow indicates "
            "decline, and a right arrow indicates a movement "
            "within 2% or insufficient comparable data.",
            CELL,
        )
    )

    return story


# ============================================================
# BUILD PORTFOLIO PDF
# ============================================================


def build_portfolio_summary():

    (
        companies,
        sectors,
        pnl,
        ratios,
        cashflow,
    ) = load_data()

    company_ids = sorted(companies["id"].astype(str).unique())

    print()
    print("=" * 70)
    print("DAY 35 — PORTFOLIO SUMMARY")
    print("=" * 70)
    print("Master companies:", len(company_ids))

    output = OUTPUT / "portfolio_summary.pdf"

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Nifty100 Portfolio Summary",
        author="Nifty100 Financial Intelligence Platform",
    )

    story = []

    successful = 0
    failed = []

    for index, company_id in enumerate(
        company_ids,
        start=1,
    ):

        print(f"[{index}/{len(company_ids)}] {company_id}")

        try:

            data = company_kpis(
                company_id,
                companies,
                sectors,
                pnl,
                ratios,
                cashflow,
            )

            story.extend(company_page(data))

            successful += 1

            if index < len(company_ids):
                story.append(PageBreak())

        except Exception as exc:  # noqa: BLE001  # noqa: BLE001

            print(f"FAILED: {company_id} -> {exc}")

            failed.append(company_id)

    doc.build(story)

    print()
    print("Output:", output)
    print(
        "Successful:",
        successful,
    )
    print(
        "Failed:",
        failed,
    )

    return output


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    build_portfolio_summary()
