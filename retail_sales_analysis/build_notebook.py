"""Builds and executes notebooks/Retail_Sales_Analysis.ipynb (outputs saved in the file)."""
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
NB = ROOT / "notebooks" / "Retail_Sales_Analysis.ipynb"

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
    md("# Retail Sales Analysis — ShopSmart India (2024–2025)\n"
       "**Tools:** Python · pandas · NumPy · Matplotlib · statistics / SciPy · Excel (openpyxl)\n\n"
       "**Business questions**\n"
       "1. How is revenue trending, and is there seasonality?\n"
       "2. Which categories, regions and customers drive revenue?\n"
       "3. Do discounts change buying behaviour?\n"
       "4. What drives returns and low ratings?\n\n"
       "Workflow: **load → clean → explore → test → visualise → report**"),
    code("import sys, statistics as st\n"
         "sys.path.insert(0, '../src')\n"
         "import numpy as np, pandas as pd, matplotlib.pyplot as plt\n"
         "from IPython.display import Image, display\n"
         "from clean import clean, RAW\n"
         "from analysis import (kpis, descriptive_stats, iqr_outliers, aggregates,\n"
         "                      statistical_tests, correlation_matrix, key_insights)\n"
         "pd.set_option('display.float_format', '{:,.2f}'.format)\n"
         "pd.set_option('display.max_colwidth', 100)"),

    md("## 1. Load the raw data & assess quality"),
    code("raw = pd.read_csv(RAW)\nprint(raw.shape)\nraw.head()"),
    code("raw.info()"),
    code("quality = pd.DataFrame({'missing': raw.isna().sum(),\n"
         "                        'missing_%': raw.isna().mean() * 100,\n"
         "                        'unique': raw.nunique()})\n"
         "print('Duplicate rows:', raw.duplicated().sum())\n"
         "quality[quality['missing'] > 0]"),
    code("# Inconsistent text values that need standardising\n"
         "print(raw['category'].value_counts().head(10))\n"
         "print(raw['returned'].value_counts())\n"
         "print('Negative prices:', (raw['unit_price'] < 0).sum(),\n"
         "      '| qty = 999:', (raw['quantity'] == 999).sum(),\n"
         "      '| age > 100:', (raw['customer_age'] > 100).sum())"),

    md("## 2. Clean the data\nAll rules live in `src/clean.py`; every step is logged."),
    code("df, log = clean(raw)\nprint(f'{len(raw):,} raw rows -> {len(df):,} clean rows')\nlog"),
    code("df[['order_date','category','region','unit_price','quantity','discount_pct','net_sales']].head()"),

    md("## 3. KPIs"),
    code("k = kpis(df)\npd.Series(k).to_frame('value')"),

    md("## 4. Descriptive statistics\nUsing Python's built-in `statistics` module plus NumPy percentiles."),
    code("descriptive_stats(df)"),
    code("# Quick demo of the statistics module on order value\n"
         "x = df['net_sales'].tolist()\n"
         "print(f'mean   = {st.mean(x):,.0f}')\n"
         "print(f'median = {st.median(x):,.0f}')\n"
         "print(f'stdev  = {st.stdev(x):,.0f}')\n"
         "print(f'deciles= {[round(q) for q in st.quantiles(x, n=10)]}')"),
    md("Order value is **heavily right-skewed** (skew ≈ 5): the mean is ~3.5× the median, "
       "so the median is the better 'typical order'."),
    code("iqr_outliers(df).T"),

    md("## 5. Exploratory analysis (pandas groupby / pivot)"),
    code("a = aggregates(df)\na['category']"),
    code("a['region']"),
    code("a['pivot_region_cat'].style.format('{:,.0f}').background_gradient(cmap='Blues', axis=None)"),
    code("a['seasonality'].style.format('{:,.0f}')"),
    code("a['segments']"),

    md("## 6. Hypothesis testing (α = 0.05)"),
    code("tests = statistical_tests(df, a['monthly'])\n"
         "tests[['test','question','statistic','p_value','result','interpretation']]"),
    code("correlation_matrix(df)"),

    md("## 7. Visualisations (Matplotlib)\nCharts are produced by `src/visualize.py` and saved to `outputs/charts/`."),
    code("from visualize import make_all\n"
         "charts = make_all(df, k, a, correlation_matrix(df))\n"
         "for p in charts:\n    display(Image(filename=str(p), width=850))"),

    md("## 8. Key insights"),
    code("for i, s in enumerate(key_insights(k, a, tests), 1):\n    print(f'{i}. {s}')"),
    md("## 9. Recommendations\n"
       "- **Protect Electronics** (≈69% of revenue): stock depth and pricing before Oct–Nov.\n"
       "- **Plan for Diwali**: festive months bring ~1.7× revenue from *more orders* — scale "
       "logistics and customer support, not just discounts.\n"
       "- **Fix East-region delivery**: slowest deliveries and lowest ratings; every extra day "
       "costs ~0.2 rating points.\n"
       "- **Reduce Fashion returns** (~21%): better size guides and product photos.\n"
       "- **Use discounts deliberately**: they raise units per order, so target bundles/multi-buy.\n"
       "- **Retain Premium customers**: top 25% bring ~70% of revenue — loyalty programme.\n\n"
       "The full formatted workbook is at `outputs/reports/Sales_Analysis_Report.xlsx`."),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
NB.parent.mkdir(parents=True, exist_ok=True)
NotebookClient(nb, timeout=300, kernel_name="python3",
               resources={"metadata": {"path": str(NB.parent)}}).execute()
nbf.write(nb, NB)
print("Saved", NB)
