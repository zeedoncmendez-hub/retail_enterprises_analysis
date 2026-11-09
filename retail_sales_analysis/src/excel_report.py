"""
Step 4 - Build a formatted, formula-driven Excel report with openpyxl.

Summary sheets use live Excel formulas (SUMIFS, COUNTIFS, AVERAGEIFS, MEDIAN,
STDEV...) that point at the Clean_Data sheet, so the workbook recalculates if
the data changes. Hypothesis-test results come from Python (scipy) and are
labelled as such.
"""
from pathlib import Path

import pandas as pd
try:
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
except ModuleNotFoundError as exc:
    if exc.name != "openpyxl":
        raise
    raise ModuleNotFoundError(
        "The Excel report requires openpyxl. Install it with: "
        "python -m pip install openpyxl"
    ) from exc

OUT = Path(__file__).resolve().parents[1] / "outputs" / "reports" / "Sales_Analysis_Report.xlsx"

FONT = "Arial"
NAVY, BLUE, LIGHT, GREY = "1F3B5C", "2A78D6", "EAF2FC", "F4F4F2"
INR = '"₹"#,##0'
INR2 = '"₹"#,##0.00'
PCT = "0.0%"
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

DATA_COLS = ["order_id", "order_date", "month", "year", "quarter", "customer_id", "customer_age",
             "age_group", "gender", "city", "region", "category", "sub_category", "unit_price",
             "quantity", "discount_pct", "gross_sales", "discount_amt", "net_sales",
             "payment_method", "delivery_days", "rating", "returned", "is_returned",
             "first_order"]


# ------------------------------------------------------------------ helpers
def f(bold=False, size=10, color="000000", italic=False):
    return Font(name=FONT, bold=bold, size=size, color=color, italic=italic)


def title(ws, text, sub=None):
    ws["A1"] = text
    ws["A1"].font = f(True, 16, NAVY)
    if sub:
        ws["A2"] = sub
        ws["A2"].font = f(size=10, color="595959", italic=True)
    ws.sheet_view.showGridLines = False


def header(ws, row, col, labels):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.font = f(True, 10, "FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX


def body(ws, r1, r2, c1, c2, zebra=True):
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = BOX
            if cell.font.name != FONT:          # keep fonts already styled above
                cell.font = f(bold=cell.font.bold)
            if zebra and (r - r1) % 2 == 1:
                cell.fill = PatternFill("solid", fgColor=GREY)


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def note(ws, cell, text):
    ws[cell] = text
    ws[cell].font = f(size=9, color="7F7F7F", italic=True)


class Data:
    """Absolute range references into the Clean_Data sheet."""

    def __init__(self, n_rows):
        self.last = n_rows + 1

    def __call__(self, col):
        L = get_column_letter(DATA_COLS.index(col) + 1)
        return f"Clean_Data!${L}$2:${L}${self.last}"


# ------------------------------------------------------------------- sheets
def sheet_clean_data(wb, df):
    ws = wb.create_sheet("Clean_Data")
    df = df.copy()
    # 1 on each customer's first order -> SUM gives unique customers cheaply
    df["first_order"] = (~df["customer_id"].duplicated()).astype(int)
    d = df[DATA_COLS].copy()
    d["order_date"] = d["order_date"].dt.date
    d["age_group"] = d["age_group"].astype(str)
    d["year"] = d["year"].astype(int)
    ws.append(DATA_COLS)
    for row in d.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in row])
    n = len(d) + 1
    tab = Table(displayName="SalesData", ref=f"A1:{get_column_letter(len(DATA_COLS))}{n}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(tab)
    fmt = {"order_date": "dd-mmm-yyyy", "unit_price": INR, "gross_sales": INR,
           "discount_amt": INR2, "net_sales": INR2}
    for col, nf in fmt.items():
        L = get_column_letter(DATA_COLS.index(col) + 1)
        for r in range(2, n + 1):
            ws[f"{L}{r}"].number_format = nf
    for i, col in enumerate(DATA_COLS, 1):
        ws.column_dimensions[get_column_letter(i)].width = max(11, len(col) + 3)
    for row in ws.iter_rows(min_row=1, max_row=n):
        for c in row:
            c.font = f(bold=(c.row == 1), color="FFFFFF" if c.row == 1 else "000000")
    ws.freeze_panes = "B2"
    return ws


def sheet_dashboard(wb, D, k, insights, monthly_ws_rows):
    ws = wb.create_sheet("Dashboard", 0)
    title(ws, "ShopSmart India — Sales Analysis 2024–2025",
          "All KPI values are live formulas on the Clean_Data sheet")

    kpis = [
        ("Total revenue", f"=SUM({D('net_sales')})", INR),
        ("Total orders", f"=COUNTA({D('order_id')})", "#,##0"),
        ("Unique customers", f"=SUM({D('first_order')})", "#,##0"),
        ("Units sold", f"=SUM({D('quantity')})", "#,##0"),
        ("Average order value", f"=AVERAGE({D('net_sales')})", INR),
        ("Median order value", f"=MEDIAN({D('net_sales')})", INR),
        ("Total discount given", f"=SUM({D('discount_amt')})", INR),
        ("Return rate", f"=AVERAGE({D('is_returned')})", PCT),
        ("Average rating (1–5)", f"=AVERAGE({D('rating')})", "0.00"),
        ("Revenue 2024", f"=SUMIFS({D('net_sales')},{D('year')},2024)", INR),
        ("Revenue 2025", f"=SUMIFS({D('net_sales')},{D('year')},2025)", INR),
        ("YoY revenue growth", "=IFERROR(B15/B14-1,0)", PCT),
    ]
    header(ws, 4, 1, ["KPI", "Value"])
    for i, (lab, formula, nf) in enumerate(kpis, start=5):
        ws.cell(row=i, column=1, value=lab).font = f(True)
        c = ws.cell(row=i, column=2, value=formula)
        c.number_format = nf
        c.font = f(True, 11, NAVY)
        c.alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(row=i, column=1).alignment = Alignment(vertical="center")
        ws.row_dimensions[i].height = 26
    body(ws, 5, 4 + len(kpis), 1, 2, zebra=True)

    ws["D4"] = "Key insights"
    ws["D4"].font = f(True, 12, NAVY)
    for i, text in enumerate(insights, start=5):
        c = ws.cell(row=i, column=4, value=f"{i - 4}.  {text}")
        c.font = f(size=10)
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.merge_cells(start_row=i, start_column=4, end_row=i, end_column=12)

    # Native Excel line chart of monthly revenue (data on Monthly_Trend sheet)
    mt = wb["Monthly_Trend"]
    ch = LineChart()
    ch.title = "Monthly net revenue (₹)"
    ch.height, ch.width = 8, 26
    ch.y_axis.numFmt = '"₹"#,##0'
    ch.y_axis.majorGridlines = None
    ch.add_data(Reference(mt, min_col=2, min_row=4, max_row=4 + monthly_ws_rows), titles_from_data=True)
    ch.set_categories(Reference(mt, min_col=1, min_row=5, max_row=4 + monthly_ws_rows))
    ch.series[0].graphicalProperties.line.solidFill = BLUE
    ch.series[0].graphicalProperties.line.width = 28000
    ch.series[0].smooth = False
    ch.legend = None
    ws.add_chart(ch, "A19")

    widths(ws, {"A": 26, "B": 18, "C": 3})
    for col in "DEFGHIJKL":
        ws.column_dimensions[col].width = 13
    return ws


def sheet_monthly(wb, D, months):
    ws = wb.create_sheet("Monthly_Trend")
    title(ws, "Monthly performance", "SUMIFS / COUNTIFS / AVERAGEIFS formulas over Clean_Data")
    cols = ["Month", "Net revenue", "Orders", "Units", "Avg order value", "Return rate", "MoM growth"]
    header(ws, 4, 1, cols)
    for i, m in enumerate(months, start=5):
        ws.cell(row=i, column=1, value=m)
        ws.cell(row=i, column=2, value=f"=SUMIFS({D('net_sales')},{D('month')},A{i})").number_format = INR
        ws.cell(row=i, column=3, value=f"=COUNTIFS({D('month')},A{i})").number_format = "#,##0"
        ws.cell(row=i, column=4, value=f"=SUMIFS({D('quantity')},{D('month')},A{i})").number_format = "#,##0"
        ws.cell(row=i, column=5, value=f"=IFERROR(B{i}/C{i},0)").number_format = INR
        ws.cell(row=i, column=6, value=f"=IFERROR(AVERAGEIFS({D('is_returned')},{D('month')},A{i}),0)").number_format = PCT
        ws.cell(row=i, column=7, value=None if i == 5 else f"=IFERROR(B{i}/B{i - 1}-1,0)").number_format = PCT
    last = 4 + len(months)
    t = last + 1
    ws.cell(row=t, column=1, value="Total")
    ws.cell(row=t, column=2, value=f"=SUM(B5:B{last})").number_format = INR
    ws.cell(row=t, column=3, value=f"=SUM(C5:C{last})").number_format = "#,##0"
    ws.cell(row=t, column=4, value=f"=SUM(D5:D{last})").number_format = "#,##0"
    ws.cell(row=t, column=5, value=f"=IFERROR(B{t}/C{t},0)").number_format = INR
    body(ws, 5, t, 1, 7)
    for c in range(1, 8):
        ws.cell(row=t, column=c).font = f(True)
        ws.cell(row=t, column=c).fill = PatternFill("solid", fgColor=LIGHT)
    ws.conditional_formatting.add(f"B5:B{last}", DataBarRule(start_type="min", end_type="max", color="6DA7EC"))
    ws.conditional_formatting.add(f"G6:G{last}", ColorScaleRule(
        start_type="min", start_color="F4B6A8", mid_type="num", mid_value=0, mid_color="FFFFFF",
        end_type="max", end_color="9EC5F4"))

    ch = BarChart()
    ch.type = "col"
    ch.title = "Orders per month"
    ch.height, ch.width = 7.5, 18
    ch.add_data(Reference(ws, min_col=3, min_row=4, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=last))
    ch.series[0].graphicalProperties.solidFill = BLUE
    ch.legend = None
    ch.y_axis.majorGridlines = None
    ws.add_chart(ch, "I4")
    widths(ws, {"A": 12, "B": 16, "C": 10, "D": 10, "E": 16, "F": 12, "G": 12})
    ws.freeze_panes = "A5"
    return len(months)


def sheet_category_region(wb, D, cats, regions):
    ws = wb.create_sheet("Category_Region")
    title(ws, "Category & region analysis", "Pivot-style tables built with SUMIFS / COUNTIFS")

    # Table 1: category summary
    header(ws, 4, 1, ["Category", "Net revenue", "Revenue share", "Orders", "Avg order value",
                      "Return rate", "Avg rating"])
    r0 = 5
    rl = r0 + len(cats) - 1
    for i, c in enumerate(cats, start=r0):
        ws.cell(row=i, column=1, value=c)
        ws.cell(row=i, column=2, value=f"=SUMIFS({D('net_sales')},{D('category')},A{i})").number_format = INR
        ws.cell(row=i, column=3, value=f"=B{i}/SUM($B${r0}:$B${rl})").number_format = PCT
        ws.cell(row=i, column=4, value=f"=COUNTIFS({D('category')},A{i})").number_format = "#,##0"
        ws.cell(row=i, column=5, value=f"=IFERROR(B{i}/D{i},0)").number_format = INR
        ws.cell(row=i, column=6, value=f"=AVERAGEIFS({D('is_returned')},{D('category')},A{i})").number_format = PCT
        ws.cell(row=i, column=7, value=f"=AVERAGEIFS({D('rating')},{D('category')},A{i})").number_format = "0.00"
    body(ws, r0, rl, 1, 7)
    ws.conditional_formatting.add(f"C{r0}:C{rl}", DataBarRule(start_type="num", start_value=0,
                                                               end_type="max", color="6DA7EC"))
    ws.conditional_formatting.add(f"F{r0}:F{rl}", ColorScaleRule(
        start_type="min", start_color="FFFFFF", end_type="max", end_color="F4B6A8"))

    ch = BarChart()
    ch.type = "bar"
    ch.title = "Net revenue by category (₹)"
    ch.height, ch.width = 7, 16
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_row=rl), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=r0, max_row=rl))
    ch.series[0].graphicalProperties.solidFill = BLUE
    ch.legend = None
    ch.y_axis.numFmt = '"₹"#,##0'
    ch.y_axis.majorGridlines = None
    ch.x_axis.scaling.orientation = "maxMin"
    ws.add_chart(ch, "I4")

    # Table 2: region x category pivot
    p0 = rl + 4
    ws.cell(row=p0 - 1, column=1, value="Net revenue: region × category").font = f(True, 12, NAVY)
    header(ws, p0, 1, ["Region"] + list(cats) + ["Total"])
    for i, reg in enumerate(regions, start=p0 + 1):
        ws.cell(row=i, column=1, value=reg)
        for j in range(len(cats)):
            col = get_column_letter(2 + j)
            ws.cell(row=i, column=2 + j,
                    value=f"=SUMIFS({D('net_sales')},{D('region')},$A{i},{D('category')},{col}${p0})"
                    ).number_format = INR
        tc = get_column_letter(1 + len(cats))
        ws.cell(row=i, column=2 + len(cats), value=f"=SUM(B{i}:{tc}{i})").number_format = INR
    pl = p0 + len(regions)
    tr = pl + 1
    ws.cell(row=tr, column=1, value="Total")
    for j in range(len(cats) + 1):
        col = get_column_letter(2 + j)
        ws.cell(row=tr, column=2 + j, value=f"=SUM({col}{p0 + 1}:{col}{pl})").number_format = INR
    body(ws, p0 + 1, tr, 1, 2 + len(cats), zebra=False)
    for c in range(1, 3 + len(cats)):
        ws.cell(row=tr, column=c).font = f(True)
        ws.cell(row=tr, column=c).fill = PatternFill("solid", fgColor=LIGHT)
    last_cat_col = get_column_letter(1 + len(cats))
    ws.conditional_formatting.add(f"B{p0 + 1}:{last_cat_col}{pl}", ColorScaleRule(
        start_type="min", start_color="FFFFFF", end_type="max", end_color="6DA7EC"))

    # Table 3: region summary
    q0 = tr + 3
    ws.cell(row=q0 - 1, column=1, value="Region summary").font = f(True, 12, NAVY)
    header(ws, q0, 1, ["Region", "Net revenue", "Orders", "Avg order value", "Return rate",
                       "Avg delivery days", "Avg rating"])
    for i, reg in enumerate(regions, start=q0 + 1):
        ws.cell(row=i, column=1, value=reg)
        ws.cell(row=i, column=2, value=f"=SUMIFS({D('net_sales')},{D('region')},A{i})").number_format = INR
        ws.cell(row=i, column=3, value=f"=COUNTIFS({D('region')},A{i})").number_format = "#,##0"
        ws.cell(row=i, column=4, value=f"=IFERROR(B{i}/C{i},0)").number_format = INR
        ws.cell(row=i, column=5, value=f"=AVERAGEIFS({D('is_returned')},{D('region')},A{i})").number_format = PCT
        ws.cell(row=i, column=6, value=f"=AVERAGEIFS({D('delivery_days')},{D('region')},A{i})").number_format = "0.0"
        ws.cell(row=i, column=7, value=f"=AVERAGEIFS({D('rating')},{D('region')},A{i})").number_format = "0.00"
    body(ws, q0 + 1, q0 + len(regions), 1, 7)

    widths(ws, {"A": 18, "B": 15, "C": 15, "D": 15, "E": 16, "F": 15, "G": 15, "H": 15})
    return ws


def sheet_statistics(wb, D, tests, outliers):
    ws = wb.create_sheet("Statistics")
    title(ws, "Statistical analysis",
          "Descriptive stats are Excel formulas; hypothesis tests were run in Python (scipy.stats)")

    metrics = ["net_sales", "unit_price", "quantity", "customer_age", "delivery_days", "rating"]
    header(ws, 4, 1, ["Statistic"] + metrics)
    stats_rows = [
        ("Count", "COUNT({r})", "#,##0"),
        ("Mean", "AVERAGE({r})", "#,##0.00"),
        ("Median", "MEDIAN({r})", "#,##0.00"),
        ("Mode", "MODE({r})", "#,##0.00"),
        ("Std deviation", "STDEV({r})", "#,##0.00"),
        ("Variance", "VAR({r})", "#,##0.00"),
        ("Minimum", "MIN({r})", "#,##0.00"),
        ("Q1 (25th pct)", "QUARTILE({r},1)", "#,##0.00"),
        ("Q3 (75th pct)", "QUARTILE({r},3)", "#,##0.00"),
        ("Maximum", "MAX({r})", "#,##0.00"),
        ("IQR", None, "#,##0.00"),
        ("Skewness", "SKEW({r})", "0.00"),
        ("Coeff. of variation", None, PCT),
    ]
    for i, (lab, tmpl, nf) in enumerate(stats_rows, start=5):
        ws.cell(row=i, column=1, value=lab).font = f(True)
        for j, m in enumerate(metrics, start=2):
            col = get_column_letter(j)
            if lab == "IQR":
                v = f"={col}13-{col}12"
            elif lab == "Coeff. of variation":
                v = f"=IFERROR({col}9/{col}6,0)"
            else:
                v = "=" + tmpl.format(r=D(m))
            ws.cell(row=i, column=j, value=v).number_format = nf
    end = 4 + len(stats_rows)
    body(ws, 5, end, 1, 1 + len(metrics))

    # Outliers
    o0 = end + 4
    ws.cell(row=o0 - 1, column=1, value="Outlier check — IQR method on net_sales").font = f(True, 12, NAVY)
    o = outliers.iloc[0]
    rows = [("Q1", f"=QUARTILE({D('net_sales')},1)", INR),
            ("Q3", f"=QUARTILE({D('net_sales')},3)", INR),
            ("Upper fence (Q3 + 1.5×IQR)", f"=B{o0 + 2}+1.5*(B{o0 + 2}-B{o0 + 1})", INR),
            ("Orders above fence", f"=COUNTIF({D('net_sales')},\">\"&B{o0 + 3})", "#,##0"),
            ("Share of orders", f"=B{o0 + 4}/COUNT({D('net_sales')})", PCT),
            ("Share of revenue", f"=SUMIF({D('net_sales')},\">\"&B{o0 + 3})/SUM({D('net_sales')})", PCT),
            ("Decision", o["decision"], "@")]
    header(ws, o0, 1, ["Measure", "Value"])
    for i, (lab, v, nf) in enumerate(rows, start=o0 + 1):
        ws.cell(row=i, column=1, value=lab).font = f(True)
        ws.cell(row=i, column=2, value=v).number_format = nf
    body(ws, o0 + 1, o0 + len(rows), 1, 2)
    ws.merge_cells(start_row=o0 + 7, start_column=2, end_row=o0 + 7, end_column=7)
    widths(ws, {"A": 28, "B": 16, "C": 16, "D": 16, "E": 16, "F": 16, "G": 16})

    # Hypothesis tests - own sheet (needs wide text columns)
    ws = wb.create_sheet("Hypothesis_Tests")
    title(ws, "Hypothesis tests (α = 0.05)",
          "Run in Python with scipy.stats — values are static results from src/analysis.py")
    h0 = 4
    header(ws, h0, 1, ["Test", "Business question", "Statistic", "p-value", "Result", "Interpretation"])
    for i, r in enumerate(tests.itertuples(index=False), start=h0 + 1):
        ws.cell(row=i, column=1, value=r.test)
        ws.cell(row=i, column=2, value=r.question)
        ws.cell(row=i, column=3, value=float(r.statistic)).number_format = "#,##0.000"
        pv = ws.cell(row=i, column=4, value=None if pd.isna(r.p_value) else float(r.p_value))
        pv.number_format = "0.000E+00" if (not pd.isna(r.p_value) and r.p_value < 0.001) else "0.000"
        res = ws.cell(row=i, column=5, value=r.result)
        ws.cell(row=i, column=6, value=r.interpretation)
        for c in range(1, 7):
            ws.cell(row=i, column=c).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 45
    hl = h0 + len(tests)
    body(ws, h0 + 1, hl, 1, 6)
    for i in range(h0 + 1, hl + 1):
        res = ws.cell(row=i, column=5)
        color = "006100" if res.value == "Significant" else ("9C5700" if res.value == "Not significant" else "1F3B5C")
        res.font = f(True, color=color)
    widths(ws, {"A": 34, "B": 44, "C": 14, "D": 13, "E": 16, "F": 70})
    ws.freeze_panes = "A5"
    return ws


def sheet_df(wb, name, heading, sub, df, formats, start_col_widths=None):
    ws = wb.create_sheet(name)
    title(ws, heading, sub)
    header(ws, 4, 1, list(df.columns))
    for i, row in enumerate(df.itertuples(index=False), start=5):
        for j, v in enumerate(row, start=1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            c = ws.cell(row=i, column=j, value=v)
            col = df.columns[j - 1]
            if col in formats:
                c.number_format = formats[col]
    body(ws, 5, 4 + len(df), 1, len(df.columns))
    for j, col in enumerate(df.columns, start=1):
        ws.column_dimensions[get_column_letter(j)].width = (start_col_widths or {}).get(col, max(14, len(col) + 4))
    return ws


def sheet_charts(wb, chart_paths):
    ws = wb.create_sheet("Charts")
    title(ws, "Charts (Matplotlib)", "Generated by src/visualize.py — PNG files are also in outputs/charts/")
    row, pair_h = 4, 0
    for i, p in enumerate(chart_paths):
        img = XLImage(str(p))
        scale = 620 / img.width
        img.width, img.height = int(img.width * scale), int(img.height * scale)
        col = "A" if i % 2 == 0 else "L"
        ws.add_image(img, f"{col}{row}")
        pair_h = max(pair_h, img.height)
        if i % 2 == 1 or i == len(chart_paths) - 1:
            row += int(pair_h / 20) + 3          # default row ≈ 20 px
            pair_h = 0
    return ws


# --------------------------------------------------------------------- main
def build_report(df, log, k, a, tests, outliers, insights, chart_paths):
    wb = Workbook()
    wb.remove(wb.active)

    D = Data(len(df))
    months = sorted(df["month"].unique())
    cats = a["category"]["category"].tolist()
    regions = a["region"]["region"].tolist()

    n_months = sheet_monthly(wb, D, months)
    sheet_dashboard(wb, D, k, insights, n_months)
    sheet_category_region(wb, D, cats, regions)
    sheet_statistics(wb, D, tests, outliers)

    seg = a["segments"].copy()
    seg["segment"] = seg["segment"].astype(str)
    seg["revenue_share_%"] = seg["revenue_share_%"] / 100
    seg.columns = ["Segment", "Customers", "Avg orders", "Avg lifetime value", "Total revenue",
                   "Revenue share"]
    sheet_df(wb, "Customer_Segments", "Customer segmentation",
             "Customers split into 4 equal groups by lifetime spend (pandas qcut)", seg,
             {"Avg orders": "0.00", "Avg lifetime value": INR, "Total revenue": INR,
              "Revenue share": PCT}, {"Avg lifetime value": 20})

    pay = a["payment"][["payment_method", "orders", "order_share_%", "revenue", "avg_order_value"]].copy()
    pay["order_share_%"] = pay["order_share_%"] / 100
    pay.columns = ["Payment method", "Orders", "Order share", "Net revenue", "Avg order value"]
    sheet_df(wb, "Payment_Methods", "Payment method mix", "Orders and revenue by payment method", pay,
             {"Orders": "#,##0", "Order share": PCT, "Net revenue": INR, "Avg order value": INR},
             {"Payment method": 20, "Avg order value": 18})

    sheet_df(wb, "Cleaning_Log", "Data cleaning log",
             "Every transformation applied to the raw export (src/clean.py)",
             log.rename(columns={"step": "Step", "rows_affected": "Rows affected", "detail": "Detail"}),
             {"Rows affected": "#,##0"}, {"Step": 30, "Rows affected": 15, "Detail": 90})

    sheet_charts(wb, chart_paths)
    sheet_clean_data(wb, df)

    for ws in wb.worksheets:                      # print-ready: landscape, 1 page wide
        if ws.title != "Clean_Data":
            ws.page_setup.orientation = "landscape"
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
    wb["Dashboard"].sheet_properties.tabColor = NAVY
    wb["Clean_Data"].sheet_properties.tabColor = "A6A6A6"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    return OUT
