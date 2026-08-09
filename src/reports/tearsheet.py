from pathlib import Path
import sqlite3
import re

import pandas as pd
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from reportlab.graphics.shapes import (
    Drawing,
    Rect,
    String,
    Line,
)

from reportlab.graphics.charts.barcharts import (
    VerticalBarChart
)

from reportlab.graphics.charts.linecharts import (
    HorizontalLineChart
)


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"

OUTPUT = ROOT / "reports" / "tearsheets"

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# COLORS
# ============================================================

NAVY = colors.HexColor("#172B4D")
GREEN = colors.HexColor("#15803D")
RED = colors.HexColor("#B91C1C")

LIGHT_GREEN = colors.HexColor("#DCFCE7")
LIGHT_RED = colors.HexColor("#FEE2E2")
LIGHT_GREY = colors.HexColor("#F3F4F6")

MID_GREY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#111827")

WHITE = colors.white


# ============================================================
# STYLES
# ============================================================

styles = getSampleStyleSheet()


BODY = ParagraphStyle(
    "BodyCustom",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=DARK,
    spaceAfter=3,
)


SECTION = ParagraphStyle(
    "SectionCustom",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
    spaceBefore=3,
    spaceAfter=4,
)


KPI_VALUE = ParagraphStyle(
    "KPIValue",
    parent=BODY,
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=14,
    alignment=TA_CENTER,
)


KPI_LABEL = ParagraphStyle(
    "KPILabel",
    parent=BODY,
    fontSize=7,
    leading=8,
    alignment=TA_CENTER,
    textColor=MID_GREY,
)


BULLET_GREEN = ParagraphStyle(
    "BulletGreen",
    parent=BODY,
    leftIndent=8,
    firstLineIndent=-6,
)


BULLET_RED = ParagraphStyle(
    "BulletRed",
    parent=BODY,
    leftIndent=8,
    firstLineIndent=-6,
)


print("Tearsheet module loaded")
# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def fmt(value, suffix=""):
    value = safe_float(value)

    if value is None:
        return "N/A"

    if abs(value) >= 1000:
        return f"{value:,.0f}{suffix}"

    return f"{value:,.2f}{suffix}"


def normalize_year(value):
    text = str(value).strip()

    years = re.findall(r"(20\d{2})", text)

    if years:
        return int(years[-1])

    match = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[-_ ](\d{2})$",
        text,
        re.IGNORECASE,
    )

    if match:
        return 2000 + int(match.group(1))

    return None


def first_existing(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def get_columns(conn, table):
    return [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    ]


def query_table(conn, table, company_id):

    columns = get_columns(
        conn,
        table
    )

    id_col = first_existing(
        columns,
        [
            "company_id",
            "id",
            "ticker",
            "symbol",
        ],
    )

    if not id_col:
        return pd.DataFrame()

    return pd.read_sql(
        f'''
        SELECT *
        FROM "{table}"
        WHERE "{id_col}" = ?
        ''',
        conn,
        params=[company_id],
    )


# ============================================================
# COMPANY DATA LOADER
# ============================================================

def load_company(company_id):

    conn = sqlite3.connect(
        DB_PATH
    )

    company = pd.read_sql(
        """
        SELECT *
        FROM companies
        WHERE id = ?
        """,
        conn,
        params=[company_id],
    )

    if company.empty:
        conn.close()

        raise ValueError(
            f"Company not found: {company_id}"
        )

    company = company.iloc[0].to_dict()

    pnl = query_table(
        conn,
        "profitandloss",
        company_id,
    )

    balance = query_table(
        conn,
        "balancesheet",
        company_id,
    )

    cashflow = query_table(
        conn,
        "cashflow",
        company_id,
    )

    ratios = query_table(
        conn,
        "financial_ratios",
        company_id,
    )

    sectors = query_table(
        conn,
        "sectors",
        company_id,
    )

    conn.close()

    # Normalize years

    for df in [
        pnl,
        balance,
        cashflow,
        ratios,
    ]:

        if not df.empty and "year" in df.columns:

            df["year_num"] = (
                df["year"]
                .apply(normalize_year)
            )

    return {
        "company": company,
        "pnl": pnl,
        "balance": balance,
        "cashflow": cashflow,
        "ratios": ratios,
        "sectors": sectors,
    }


# ============================================================
# LATEST VALUE
# ============================================================

def latest_value(df, column):

    if (
        df.empty
        or column is None
        or column not in df.columns
    ):
        return None

    x = df.copy()

    if "year_num" in x.columns:

        x = (
            x.dropna(
                subset=["year_num"]
            )
            .sort_values("year_num")
        )

    if x.empty:
        return None

    return safe_float(
        x.iloc[-1][column]
    )


# ============================================================
# PROS / CONS
# ============================================================

def load_pros_cons(company_id):

    path = (
        ROOT
        / "output"
        / "pros_cons_generated.csv"
    )

    if not path.exists():
        return [], []

    df = pd.read_csv(path)

    df["company_id"] = (
        df["company_id"]
        .astype(str)
    )

    rows = df[
        df["company_id"]
        == str(company_id)
    ].copy()

    if rows.empty:
        return [], []

    pros = rows[
        rows["type"]
        .astype(str)
        .str.lower()
        == "pro"
    ]["text"].dropna().tolist()

    cons = rows[
        rows["type"]
        .astype(str)
        .str.lower()
        == "con"
    ]["text"].dropna().tolist()

    return pros, cons


# ============================================================
# CAPITAL ALLOCATION
# ============================================================

def load_capital_allocation(company_id):

    path = (
        ROOT
        / "output"
        / "cashflow_intelligence.xlsx"
    )

    if not path.exists():
        return "Insufficient Data"

    df = pd.read_excel(path)

    if "company_id" not in df.columns:
        return "Insufficient Data"

    rows = df[
        df["company_id"]
        .astype(str)
        == str(company_id)
    ]

    if rows.empty:
        return "Insufficient Data"

    column = "capital_allocation_label"

    if column not in rows.columns:
        return "Insufficient Data"

    value = rows.iloc[0][column]

    if pd.isna(value):
        return "Insufficient Data"

    return str(value)


print("Part 2 loaded")
# ============================================================
# ROCE CALCULATION
# ============================================================

def calculate_roce_series(data):

    pnl = data["pnl"].copy()
    balance = data["balance"].copy()

    if pnl.empty or balance.empty:
        return pd.DataFrame(
            columns=[
                "year_num",
                "roce",
            ]
        )

    if "year_num" not in pnl.columns:
        pnl["year_num"] = (
            pnl["year"]
            .apply(normalize_year)
        )

    if "year_num" not in balance.columns:
        balance["year_num"] = (
            balance["year"]
            .apply(normalize_year)
        )

    required_pnl = [
        "year_num",
        "operating_profit",
    ]

    required_balance = [
        "year_num",
        "equity_capital",
        "reserves",
        "borrowings",
    ]

    if any(
        col not in pnl.columns
        for col in required_pnl
    ):
        return pd.DataFrame(
            columns=[
                "year_num",
                "roce",
            ]
        )

    if any(
        col not in balance.columns
        for col in required_balance
    ):
        return pd.DataFrame(
            columns=[
                "year_num",
                "roce",
            ]
        )

    merged = pnl[
        required_pnl
    ].merge(
        balance[
            required_balance
        ],
        on="year_num",
        how="inner",
    )

    if merged.empty:
        return pd.DataFrame(
            columns=[
                "year_num",
                "roce",
            ]
        )

    operating_profit = pd.to_numeric(
        merged["operating_profit"],
        errors="coerce",
    )

    equity_capital = pd.to_numeric(
        merged["equity_capital"],
        errors="coerce",
    ).fillna(0)

    reserves = pd.to_numeric(
        merged["reserves"],
        errors="coerce",
    ).fillna(0)

    borrowings = pd.to_numeric(
        merged["borrowings"],
        errors="coerce",
    ).fillna(0)

    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    merged["roce"] = np.where(
        capital_employed != 0,
        operating_profit
        / capital_employed
        * 100,
        np.nan,
    )

    return (
        merged[
            [
                "year_num",
                "roce",
            ]
        ]
        .sort_values("year_num")
        .reset_index(drop=True)
    )


# ============================================================
# KPI CALCULATIONS
# ============================================================

def calculate_kpis(data):

    pnl = data["pnl"]
    cashflow = data["cashflow"]
    ratios = data["ratios"]

    result = {}

    # --------------------------------------------------------
    # REVENUE
    # --------------------------------------------------------

    revenue_col = first_existing(
        pnl.columns,
        [
            "sales",
            "revenue",
            "total_revenue",
        ],
    )

    result["Revenue"] = (
        latest_value(
            pnl,
            revenue_col,
        )
        if revenue_col
        else None
    )

    # --------------------------------------------------------
    # NET PROFIT
    # --------------------------------------------------------

    profit_col = first_existing(
        pnl.columns,
        [
            "net_profit",
            "net_profit_after_tax",
            "pat",
        ],
    )

    result["Net Profit"] = (
        latest_value(
            pnl,
            profit_col,
        )
        if profit_col
        else None
    )

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe_col = first_existing(
        ratios.columns,
        [
            "return_on_equity_pct",
            "roe",
            "ROE",
        ],
    )

    result["ROE"] = (
        latest_value(
            ratios,
            roe_col,
        )
        if roe_col
        else None
    )

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce = calculate_roce_series(
        data
    )

    result["ROCE"] = (
        safe_float(
            roce.iloc[-1]["roce"]
        )
        if not roce.empty
        else None
    )

    # --------------------------------------------------------
    # DEBT / EQUITY
    # --------------------------------------------------------

    de_col = first_existing(
        ratios.columns,
        [
            "debt_to_equity",
            "de_ratio",
            "d_e",
        ],
    )

    result["D/E"] = (
        latest_value(
            ratios,
            de_col,
        )
        if de_col
        else None
    )

    # --------------------------------------------------------
    # FREE CASH FLOW
    # --------------------------------------------------------

    cfo_col = first_existing(
        cashflow.columns,
        [
            "operating_activity",
            "cfo",
        ],
    )

    cfi_col = first_existing(
        cashflow.columns,
        [
            "investing_activity",
            "cfi",
        ],
    )

    cfo = (
        latest_value(
            cashflow,
            cfo_col,
        )
        if cfo_col
        else None
    )

    cfi = (
        latest_value(
            cashflow,
            cfi_col,
        )
        if cfi_col
        else None
    )

    if (
        cfo is not None
        and cfi is not None
    ):
        result["FCF"] = cfo + cfi
    else:
        result["FCF"] = None

    return result


print("Part 3 loaded")
# ============================================================
# REVENUE + NET PROFIT BAR CHART
# ============================================================

def create_revenue_profit_png(data, company_id):

    pnl = data["pnl"].copy()

    if pnl.empty:
        return Drawing(520, 155)

    revenue_col = first_existing(
        pnl.columns,
        [
            "sales",
            "revenue",
            "total_revenue",
        ],
    )

    profit_col = first_existing(
        pnl.columns,
        [
            "net_profit",
            "net_profit_after_tax",
            "pat",
        ],
    )

    if not revenue_col or not profit_col:
        return Drawing(520, 155)

    if "year_num" not in pnl.columns:
        pnl["year_num"] = (
            pnl["year"]
            .apply(normalize_year)
        )

    x = pnl[
        [
            "year_num",
            revenue_col,
            profit_col,
        ]
    ].copy()

    x["year_num"] = pd.to_numeric(
        x["year_num"],
        errors="coerce",
    )

    x[revenue_col] = pd.to_numeric(
        x[revenue_col],
        errors="coerce",
    )

    x[profit_col] = pd.to_numeric(
        x[profit_col],
        errors="coerce",
    )

    x = (
        x.dropna(
            subset=[
                "year_num",
                revenue_col,
                profit_col,
            ]
        )
        .sort_values("year_num")
        .tail(10)
    )

    if x.empty:
        return Drawing(520, 155)

    d = Drawing(
        520,
        155
    )

    chart = VerticalBarChart()

    chart.x = 45
    chart.y = 25
    chart.width = 450
    chart.height = 105

    chart.data = [
        x[revenue_col].tolist(),
        x[profit_col].tolist(),
    ]

    chart.categoryAxis.categoryNames = [
        str(int(year))
        for year in x["year_num"]
    ]

    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.angle = 0

    chart.valueAxis.labels.fontSize = 6

    chart.groupSpacing = 8
    chart.barWidth = 8

    chart.bars[0].fillColor = NAVY
    chart.bars[1].fillColor = GREEN

    d.add(chart)

    d.add(
        String(
            55,
            143,
            "Revenue",
            fontSize=7,
            fillColor=NAVY,
        )
    )

    d.add(
        String(
            105,
            143,
            "Net Profit",
            fontSize=7,
            fillColor=GREEN,
        )
    )

    return d


# ============================================================
# ROE + ROCE LINE CHART
# ============================================================

def create_roe_roce_png(data, company_id):

    ratios = data["ratios"].copy()

    if ratios.empty:
        return Drawing(520, 155)

    roe_col = first_existing(
        ratios.columns,
        [
            "return_on_equity_pct",
            "roe",
            "ROE",
        ],
    )

    if not roe_col:
        return Drawing(520, 155)

    if "year_num" not in ratios.columns:
        ratios["year_num"] = (
            ratios["year"]
            .apply(normalize_year)
        )

    roe_data = ratios[
        [
            "year_num",
            roe_col,
        ]
    ].copy()

    roe_data["year_num"] = pd.to_numeric(
        roe_data["year_num"],
        errors="coerce",
    )

    roe_data[roe_col] = pd.to_numeric(
        roe_data[roe_col],
        errors="coerce",
    )

    roce_data = calculate_roce_series(
        data
    )

    x = roe_data.merge(
        roce_data,
        on="year_num",
        how="left",
    )

    x = (
        x.dropna(
            subset=["year_num"]
        )
        .sort_values("year_num")
        .tail(10)
    )

    if x.empty:
        return Drawing(520, 155)

    d = Drawing(
        520,
        155
    )

    chart = HorizontalLineChart()

    chart.x = 45
    chart.y = 25
    chart.width = 450
    chart.height = 105

    chart.data = [
        [
            safe_float(v) or 0
            for v in x[roe_col]
        ],
        [
            safe_float(v) or 0
            for v in x["roce"]
        ],
    ]

    chart.categoryAxis.categoryNames = [
        str(int(year))
        for year in x["year_num"]
    ]

    chart.categoryAxis.labels.fontSize = 6

    chart.valueAxis.labels.fontSize = 6

    chart.lines[0].strokeColor = NAVY
    chart.lines[0].strokeWidth = 1.5

    chart.lines[1].strokeColor = GREEN
    chart.lines[1].strokeWidth = 1.5

    d.add(chart)

    d.add(
        String(
            55,
            143,
            "ROE",
            fontSize=7,
            fillColor=NAVY,
        )
    )

    d.add(
        String(
            90,
            143,
            "ROCE",
            fontSize=7,
            fillColor=GREEN,
        )
    )

    return d


print("Part 4 loaded")
# ============================================================
# BALANCE SHEET COMPOSITION CHART
# ============================================================

def create_balance_png(data, company_id):

    balance = data["balance"].copy()

    if balance.empty:
        return Drawing(520, 155)

    if "year_num" not in balance.columns:
        balance["year_num"] = (
            balance["year"]
            .apply(normalize_year)
        )

    required = [
        "year_num",
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
    ]

    if any(
        col not in balance.columns
        for col in required
    ):
        return Drawing(520, 155)

    x = balance[
        required
    ].copy()

    x["year_num"] = pd.to_numeric(
        x["year_num"],
        errors="coerce",
    )

    for col in [
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
    ]:
        x[col] = pd.to_numeric(
            x[col],
            errors="coerce",
        ).fillna(0)

    x = (
        x.dropna(
            subset=["year_num"]
        )
        .sort_values("year_num")
        .tail(10)
    )

    if x.empty:
        return Drawing(520, 155)

    # Equity = equity capital + reserves
    x["equity"] = (
        x["equity_capital"]
        + x["reserves"]
    )

    d = Drawing(
        520,
        155
    )

    chart = VerticalBarChart()

    chart.x = 45
    chart.y = 25
    chart.width = 450
    chart.height = 105

    chart.data = [
        x["equity"].tolist(),
        x["borrowings"].tolist(),
        x["other_liabilities"].tolist(),
    ]

    chart.categoryAxis.categoryNames = [
        str(int(year))
        for year in x["year_num"]
    ]

    chart.categoryAxis.labels.fontSize = 6
    chart.valueAxis.labels.fontSize = 6

    chart.groupSpacing = 8
    chart.barWidth = 8

    chart.bars[0].fillColor = NAVY
    chart.bars[1].fillColor = RED
    chart.bars[2].fillColor = MID_GREY

    d.add(chart)

    d.add(
        String(
            55,
            143,
            "Equity",
            fontSize=7,
            fillColor=NAVY,
        )
    )

    d.add(
        String(
            105,
            143,
            "Borrowings",
            fontSize=7,
            fillColor=RED,
        )
    )

    d.add(
        String(
            170,
            143,
            "Other Liabilities",
            fontSize=7,
            fillColor=MID_GREY,
        )
    )

    return d


# ============================================================
# CASH FLOW WATERFALL
# ============================================================

def create_cashflow_png(data, company_id):

    cashflow = data["cashflow"].copy()

    d = Drawing(
        520,
        170
    )

    if cashflow.empty:
        return d

    if "year_num" not in cashflow.columns:
        cashflow["year_num"] = (
            cashflow["year"]
            .apply(normalize_year)
        )

    required = [
        "year_num",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    if any(
        col not in cashflow.columns
        for col in required
    ):
        return d

    x = cashflow[
        required
    ].copy()

    x["year_num"] = pd.to_numeric(
        x["year_num"],
        errors="coerce",
    )

    for col in required[1:]:
        x[col] = pd.to_numeric(
            x[col],
            errors="coerce",
        )

    x = (
        x.dropna(
            subset=["year_num"]
        )
        .sort_values("year_num")
    )

    if x.empty:
        return d

    row = x.iloc[-1]

    values = [
        safe_float(
            row["operating_activity"]
        ),
        safe_float(
            row["investing_activity"]
        ),
        safe_float(
            row["financing_activity"]
        ),
        safe_float(
            row["net_cash_flow"]
        ),
    ]

    labels = [
        "CFO",
        "CFI",
        "CFF",
        "Net Cash Flow",
    ]

    # Replace missing values with zero
    values = [
        0 if value is None else value
        for value in values
    ]

    max_abs = max(
        [
            abs(value)
            for value in values
        ] + [1]
    )

    baseline = 65
    bar_width = 70
    gap = 40

    # Baseline
    d.add(
        Line(
            20,
            baseline,
            500,
            baseline,
            strokeColor=DARK,
            strokeWidth=0.6,
        )
    )

    for i, (label, value) in enumerate(
        zip(labels, values)
    ):

        x_pos = (
            25
            + i * (
                bar_width + gap
            )
        )

        height = (
            abs(value)
            / max_abs
            * 75
        )

        if height < 2:
            height = 2

        if value >= 0:
            y_pos = baseline
            bar_color = GREEN
        else:
            y_pos = baseline - height
            bar_color = RED

        d.add(
            Rect(
                x_pos,
                y_pos,
                bar_width,
                height,
                fillColor=bar_color,
                strokeColor=None,
            )
        )

        d.add(
            String(
                x_pos + bar_width / 2,
                42,
                label,
                fontSize=7,
                textAnchor="middle",
            )
        )

        d.add(
            String(
                x_pos + bar_width / 2,
                y_pos + height + 5,
                fmt(value),
                fontSize=6,
                textAnchor="middle",
            )
        )

    d.add(
        String(
            25,
            150,
            f"Latest Year: {int(row['year_num'])}",
            fontSize=7,
            fillColor=MID_GREY,
        )
    )

    return d


print("Part 5 loaded")
# ============================================================
# PAGE HEADER
# ============================================================

def header(company_name, ticker):

    data = [
        [
            Paragraph(
                f"<b>{company_name}</b>",
                ParagraphStyle(
                    "HeaderCompany",
                    fontName="Helvetica-Bold",
                    fontSize=16,
                    textColor=WHITE,
                ),
            ),
            Paragraph(
                f"<b>{ticker}</b>",
                ParagraphStyle(
                    "HeaderTicker",
                    fontName="Helvetica-Bold",
                    fontSize=12,
                    textColor=WHITE,
                    alignment=TA_CENTER,
                ),
            ),
        ]
    ]

    table = Table(
        data,
        colWidths=[
            145 * mm,
            35 * mm,
        ],
        rowHeights=[
            18 * mm
        ],
    )

    table.setStyle(
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
            ]
        )
    )

    return table


# ============================================================
# KPI TILES
# ============================================================

def kpi_tiles(kpis):

    labels = [
        ("Revenue", ""),
        ("Net Profit", ""),
        ("ROE", "%"),
        ("ROCE", "%"),
        ("D/E", "x"),
        ("FCF", ""),
    ]

    cells = []

    for label, suffix in labels:

        value = kpis.get(label)

        if label in [
            "ROE",
            "ROCE",
        ]:

            value_text = fmt(
                value,
                "%",
            )

        elif label == "D/E":

            value_text = fmt(
                value,
                "x",
            )

        else:

            value_text = fmt(
                value
            )

        cell = [
            Paragraph(
                value_text,
                KPI_VALUE,
            ),
            Paragraph(
                label,
                KPI_LABEL,
            ),
        ]

        cells.append(cell)

    table_data = [
        cells[:3],
        cells[3:6],
    ]

    table = Table(
        table_data,
        colWidths=[
            60 * mm,
            60 * mm,
            60 * mm,
        ],
        rowHeights=[
            20 * mm,
            20 * mm,
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
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    2,
                    WHITE,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    WHITE,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
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
            ]
        )
    )

    return table


# ============================================================
# PROS + CONS
# ============================================================

def pros_cons_table(pros, cons):

    # Limit content so Page 2 stays inside the page.
    pros = pros[:5]
    cons = cons[:5]

    pro_content = [
        Paragraph(
            "<b>Pros</b>",
            ParagraphStyle(
                "ProHeading",
                parent=SECTION,
                textColor=GREEN,
            ),
        )
    ]

    con_content = [
        Paragraph(
            "<b>Cons</b>",
            ParagraphStyle(
                "ConHeading",
                parent=SECTION,
                textColor=RED,
            ),
        )
    ]

    if not pros:

        pro_content.append(
            Paragraph(
                "• No qualifying positive signal available.",
                BULLET_GREEN,
            )
        )

    else:

        for text in pros:

            pro_content.append(
                Paragraph(
                    f"• {text}",
                    BULLET_GREEN,
                )
            )

    if not cons:

        con_content.append(
            Paragraph(
                "• No qualifying negative signal available.",
                BULLET_RED,
            )
        )

    else:

        for text in cons:

            con_content.append(
                Paragraph(
                    f"• {text}",
                    BULLET_RED,
                )
            )

    table = Table(
        [
            [
                pro_content,
                con_content,
            ]
        ],
        colWidths=[
            90 * mm,
            90 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    LIGHT_GREEN,
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    LIGHT_RED,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
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
        )
    )

    return table


# ============================================================
# CAPITAL ALLOCATION BADGE
# ============================================================

def allocation_badge(pattern):

    table = Table(
        [
            [
                Paragraph(
                    f"<b>CAPITAL ALLOCATION</b><br/>{pattern}",
                    ParagraphStyle(
                        "AllocationBadge",
                        parent=BODY,
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        leading=13,
                        alignment=TA_CENTER,
                        textColor=WHITE,
                    ),
                )
            ]
        ],
        colWidths=[
            180 * mm
        ],
    )

    table.setStyle(
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
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    return table


print("Part 6 loaded")
# ============================================================
# COMPLETE 2-PAGE TEARSHEET
# ============================================================

def build_tearsheet(company_id):

    data = load_company(company_id)

    company = data["company"]

    company_name = str(
        company.get(
            "name",
            company.get(
                "company_name",
                company_id,
            ),
        )
    )

    ticker = str(
        company.get(
            "id",
            company_id,
        )
    )

    output_path = (
        OUTPUT
        / f"{ticker}_tearsheet.pdf"
    )

    kpis = calculate_kpis(data)

    pros, cons = load_pros_cons(
        company_id
    )

    allocation = load_capital_allocation(
        company_id
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"{ticker} Company Tearsheet",
        author="Nifty100 Financial Intelligence Platform",
    )

    story = []

    # ========================================================
    # PAGE 1
    # ========================================================

    story.append(
        header(
            company_name,
            ticker,
        )
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    story.append(
        kpi_tiles(kpis)
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    story.append(
        Paragraph(
            "10-Year Revenue & Net Profit",
            SECTION,
        )
    )

    story.append(
        create_revenue_profit_png(data, company_id)
    )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        Paragraph(
            "ROE & ROCE Trend",
            SECTION,
        )
    )

    story.append(
        create_roe_roce_png(data, company_id)
    )

    # Force exactly one page break
    story.append(
        PageBreak()
    )

    # ========================================================
    # PAGE 2
    # ========================================================

    story.append(
        Paragraph(
            "Balance Sheet Composition",
            SECTION,
        )
    )

    story.append(
        create_balance_png(data, company_id)
    )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        Paragraph(
            "Latest-Year Cash Flow",
            SECTION,
        )
    )

    story.append(
        create_cashflow_png(data, company_id)
    )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        pros_cons_table(
            pros,
            cons,
        )
    )

    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    story.append(
        allocation_badge(
            allocation
        )
    )

    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        story
    )

    return output_path


# ============================================================
# TEST FIVE COMPANIES
# ============================================================

def test_five_tearsheets():

    tickers = [
        "TCS",
        "HDFCBANK",
        "RELIANCE",
        "SUNPHARMA",
        "TATASTEEL",
    ]

    print()
    print("=" * 70)
    print("DAY 33 — TEARSHEET TEST")
    print("=" * 70)

    successful = []
    failed = []

    for ticker in tickers:

        print()
        print(
            f"Generating {ticker}..."
        )

        try:

            path = build_tearsheet(
                ticker
            )

            size_kb = (
                path.stat().st_size
                / 1024
            )

            print(
                f"Created: {path}"
            )

            print(
                f"Size: {size_kb:.1f} KB"
            )

            successful.append(
                ticker
            )

        except Exception as exc:

            print(
                f"FAILED: {ticker}"
            )

            print(
                f"Error: {exc}"
            )

            failed.append(
                ticker
            )

    print()
    print(
        "Successful:",
        successful,
    )

    print(
        "Failed:",
        failed,
    )

    print()
    print("PDF files:")

    for ticker in successful:

        path = (
            OUTPUT
            / f"{ticker}_tearsheet.pdf"
        )

        if path.exists():

            print(
                f"{path.name:<30}"
                f"{path.stat().st_size / 1024:.1f} KB"
            )


# ============================================================
# MODULE ENTRY POINT
# ============================================================

if __name__ == "__main__":

    test_five_tearsheets()
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt

CHART_OUTPUT = ROOT / "output" / "tearsheet_charts"
CHART_OUTPUT.mkdir(parents=True, exist_ok=True)


def _chart_path(company_id, name):
    return CHART_OUTPUT / f"{company_id}_{name}.png"


def create_revenue_profit_png(data, company_id):

    pnl = data["pnl"].copy()

    if pnl.empty:
        return None

    if "year_num" not in pnl.columns:
        pnl["year_num"] = pnl["year"].apply(normalize_year)

    revenue_col = first_existing(
        pnl.columns,
        ["sales", "revenue", "total_revenue"]
    )

    profit_col = first_existing(
        pnl.columns,
        ["net_profit", "net_profit_after_tax", "pat"]
    )

    if not revenue_col or not profit_col:
        return None

    x = pnl[
        ["year_num", revenue_col, profit_col]
    ].copy()

    x[revenue_col] = pd.to_numeric(
        x[revenue_col], errors="coerce"
    )

    x[profit_col] = pd.to_numeric(
        x[profit_col], errors="coerce"
    )

    x = (
        x.dropna()
        .sort_values("year_num")
        .tail(10)
    )

    if x.empty:
        return None

    path = _chart_path(
        company_id,
        "revenue_profit"
    )

    fig, ax = plt.subplots(
        figsize=(8.5, 2.6),
        dpi=180
    )

    positions = np.arange(len(x))
    width = 0.36

    ax.bar(
        positions - width / 2,
        x[revenue_col],
        width,
        label="Revenue"
    )

    ax.bar(
        positions + width / 2,
        x[profit_col],
        width,
        label="Net Profit"
    )

    ax.set_xticks(
        positions
    )

    ax.set_xticklabels(
        [str(int(y)) for y in x["year_num"]],
        fontsize=7
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    ax.set_title(
        "10-Year Revenue & Net Profit",
        fontsize=9
    )

    ax.legend(
        fontsize=7,
        loc="upper left"
    )

    ax.grid(
        axis="y",
        alpha=0.2
    )

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)

    return Image(
        str(path),
        width=180 * mm,
        height=55 * mm,
    )


def create_roe_roce_png(data, company_id):

    ratios = data["ratios"].copy()

    if ratios.empty:
        return None

    if "year_num" not in ratios.columns:
        ratios["year_num"] = (
            ratios["year"].apply(normalize_year)
        )

    roe_col = first_existing(
        ratios.columns,
        [
            "return_on_equity_pct",
            "roe",
            "ROE"
        ]
    )

    if not roe_col:
        return None

    roe = ratios[
        ["year_num", roe_col]
    ].copy()

    roe[roe_col] = pd.to_numeric(
        roe[roe_col],
        errors="coerce"
    )

    roce = calculate_roce_series(data)

    x = roe.merge(
        roce,
        on="year_num",
        how="left"
    )

    x = (
        x.dropna(
            subset=["year_num"]
        )
        .sort_values("year_num")
        .tail(10)
    )

    if x.empty:
        return None

    path = _chart_path(
        company_id,
        "roe_roce"
    )

    fig, ax = plt.subplots(
        figsize=(8.5, 2.6),
        dpi=180
    )

    ax.plot(
        x["year_num"],
        x[roe_col],
        marker="o",
        linewidth=1.5,
        label="ROE"
    )

    ax.plot(
        x["year_num"],
        x["roce"],
        marker="o",
        linewidth=1.5,
        label="ROCE"
    )

    ax.set_title(
        "ROE & ROCE Trend",
        fontsize=9
    )

    ax.set_xticks(
        x["year_num"]
    )

    ax.set_xticklabels(
        [str(int(y)) for y in x["year_num"]],
        fontsize=7
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    ax.legend(
        fontsize=7
    )

    ax.grid(
        alpha=0.2
    )

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)

    return Image(
        str(path),
        width=180 * mm,
        height=55 * mm,
    )


def create_balance_png(data, company_id):

    balance = data["balance"].copy()

    if balance.empty:
        return None

    if "year_num" not in balance.columns:
        balance["year_num"] = (
            balance["year"].apply(normalize_year)
        )

    required = [
        "year_num",
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities"
    ]

    if any(
        c not in balance.columns
        for c in required
    ):
        return None

    x = balance[required].copy()

    for c in required[1:]:
        x[c] = pd.to_numeric(
            x[c],
            errors="coerce"
        ).fillna(0)

    x = (
        x.dropna(
            subset=["year_num"]
        )
        .sort_values("year_num")
        .tail(10)
    )

    if x.empty:
        return None

    x["equity"] = (
        x["equity_capital"]
        + x["reserves"]
    )

    path = _chart_path(
        company_id,
        "balance"
    )

    fig, ax = plt.subplots(
        figsize=(8.5, 2.6),
        dpi=180
    )

    years = [
        str(int(y))
        for y in x["year_num"]
    ]

    ax.bar(
        years,
        x["equity"],
        label="Equity"
    )

    ax.bar(
        years,
        x["borrowings"],
        bottom=x["equity"],
        label="Borrowings"
    )

    bottom = (
        x["equity"]
        + x["borrowings"]
    )

    ax.bar(
        years,
        x["other_liabilities"],
        bottom=bottom,
        label="Other Liabilities"
    )

    ax.set_title(
        "Balance Sheet Composition",
        fontsize=9
    )

    ax.tick_params(
        axis="x",
        labelsize=7
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    ax.legend(
        fontsize=7,
        loc="upper left"
    )

    ax.grid(
        axis="y",
        alpha=0.2
    )

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)

    return Image(
        str(path),
        width=180 * mm,
        height=55 * mm,
    )


def create_cashflow_png(data, company_id):

    cashflow = data["cashflow"].copy()

    if cashflow.empty:
        return None

    if "year_num" not in cashflow.columns:
        cashflow["year_num"] = (
            cashflow["year"].apply(normalize_year)
        )

    required = [
        "year_num",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow"
    ]

    if any(
        c not in cashflow.columns
        for c in required
    ):
        return None

    x = (
        cashflow[required]
        .dropna(
            subset=["year_num"]
        )
        .sort_values("year_num")
    )

    if x.empty:
        return None

    row = x.iloc[-1]

    labels = [
        "CFO",
        "CFI",
        "CFF",
        "Net Cash Flow"
    ]

    values = [
        float(row["operating_activity"]),
        float(row["investing_activity"]),
        float(row["financing_activity"]),
        float(row["net_cash_flow"])
    ]

    path = _chart_path(
        company_id,
        "cashflow"
    )

    fig, ax = plt.subplots(
        figsize=(8.5, 2.6),
        dpi=180
    )

    positions = np.arange(
        len(labels)
    )

    ax.bar(
        positions,
        values
    )

    ax.axhline(
        0,
        linewidth=0.8
    )

    ax.set_xticks(
        positions
    )

    ax.set_xticklabels(
        labels,
        fontsize=8
    )

    ax.set_title(
        f"Latest-Year Cash Flow ({int(row['year_num'])})",
        fontsize=9
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    ax.grid(
        axis="y",
        alpha=0.2
    )

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)

    return Image(
        str(path),
        width=180 * mm,
        height=55 * mm,
    )


print("High-resolution chart functions loaded")
