"""
Step 3 - Visualisation with Matplotlib.

Design rules followed: one colour per job (single hue for one series, fixed
categorical order for multiple series), no pie charts, no dual axes,
recessive grid, direct value labels, titles that state the finding.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

CHART_DIR = Path(__file__).resolve().parents[1] / "outputs" / "charts"

# ---- palette (validated, colour-blind-safe order) --------------------------
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE_SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlepad": 22, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2, "legend.frameon": False, "lines.linewidth": 2,
})


def inr(x, _=None):
    """Indian-style short currency: 1.2Cr / 35L / 12K."""
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.2f}".rstrip("0").rstrip(".") + "Cr"
    if abs(x) >= 1e6:
        return f"₹{x / 1e5:.0f}L"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.1f}".rstrip("0").rstrip(".") + "L"
    if abs(x) >= 1e3:
        return f"₹{x / 1e3:.0f}K"
    return f"₹{x:.0f}"


def subtitle(ax, text):
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK2, fontsize=9.5, va="bottom")


def save(fig, name):
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def hbar(ax, labels, values, fmt, color=BLUE):
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=color, height=0.62, edgecolor=SURFACE, linewidth=1)
    ax.set_yticks(y, labels)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    for yi, v in zip(y, values):
        ax.text(v, yi, "  " + fmt(v), va="center", color=INK, fontsize=9)
    ax.set_xlim(0, max(values) * 1.18)


# ------------------------------------------------------------------- charts
def monthly_trend(monthly):
    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = np.arange(len(monthly))
    y = monthly["revenue"].values
    ax.plot(x, y, color=BLUE, marker="o", markersize=4, label="Monthly revenue")
    slope, intercept = np.polyfit(x, y, 1)
    ax.plot(x, slope * x + intercept, color=MUTED, linestyle="--", linewidth=1.5, label="Linear trend")
    ax.grid(axis="x", visible=False)
    for i in [monthly[monthly["month"].str.startswith(yr)]["revenue"].idxmax() for yr in ("2024", "2025")]:
        ax.annotate(f"{monthly['month'].iloc[i]}\n{inr(y[i])}", (x[i], y[i]),
                    xytext=(0, 10), textcoords="offset points", ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(x[::2], monthly["month"].iloc[::2], rotation=45, ha="right")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(inr))
    ax.set_ylim(0, y.max() * 1.2)
    ax.set_title("Revenue is growing, with a sharp festive peak every Oct–Nov")
    subtitle(ax, f"Monthly net revenue, Jan 2024 – Dec 2025 · trend ≈ +{inr(slope)} per month")
    ax.legend(loc="upper left")
    return save(fig, "01_monthly_revenue_trend.png")


def seasonality(season):
    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = np.arange(12)
    for year, color in zip(season.columns, [BLUE, ORANGE]):
        ax.plot(x, season[year].values, color=color, marker="o", markersize=4, label=str(year))
        ax.text(11.2, season[year].values[-1], str(year), color=INK2, va="center", fontsize=9)
    ax.set_ylim(0, season.values.max() * 1.15)
    ax.grid(axis="x", visible=False)
    ax.axvspan(8.5, 10.5, color=GRID, alpha=0.5, zorder=0)
    ax.text(9.5, season.values.max() * 0.08, "Diwali season", ha="center", color=INK2, fontsize=9)
    ax.set_xticks(x, season.index)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(inr))
    ax.set_xlim(-0.4, 11.8)
    ax.set_title("2025 outsold 2024 in most months; both years peak in Oct–Nov")
    subtitle(ax, "Net revenue by month of year")
    ax.legend(loc="upper left", ncol=2)
    return save(fig, "02_seasonality_yoy.png")


def category_revenue(cat):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    hbar(ax, cat["category"], cat["revenue"],
         lambda v: f"{inr(v)}  ({v / cat['revenue'].sum() * 100:.0f}%)")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(inr))
    ax.set_title("Electronics alone brings in over two-thirds of revenue")
    subtitle(ax, "Net revenue by category, 2024–2025")
    return save(fig, "03_revenue_by_category.png")


def region_revenue(reg):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    hbar(ax, reg["region"], reg["revenue"],
         lambda v: f"{inr(v)}")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(inr))
    ax.set_title("South leads; East brings in about half of South's revenue")
    subtitle(ax, "Net revenue by region")
    return save(fig, "04_revenue_by_region.png")


def return_rate(cat, overall):
    c = cat.sort_values("return_rate", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    hbar(ax, c["category"], c["return_rate"] * 100, lambda v: f"{v:.1f}%")
    ax.axvline(overall, color=INK2, linestyle="--", linewidth=1)
    ax.text(overall, 0, f"  overall average {overall:.1f}%", color=INK2, fontsize=8.5, va="center")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("Fashion and Electronics are returned far more often")
    subtitle(ax, "Share of orders returned, by category (chi-square p < 0.001)")
    return save(fig, "05_return_rate_by_category.png")


def discount_effect(disc):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(disc))
    ax.bar(x, disc["avg_quantity"], color=BLUE, width=0.6, edgecolor=SURFACE, linewidth=1)
    for xi, v in zip(x, disc["avg_quantity"]):
        ax.text(xi, v + 0.05, f"{v:.2f}", ha="center", color=INK, fontsize=9)
    ax.set_xticks(x, [f"{d}%" for d in disc["discount_pct"]])
    ax.set_xlabel("Discount offered")
    ax.set_ylabel("Avg units per order")
    ax.grid(axis="x", visible=False)
    ax.set_title("Bigger discounts → bigger baskets")
    subtitle(ax, "Average units per order by discount level (Welch t-test p < 0.001)")
    return save(fig, "06_discount_vs_quantity.png")


def delivery_rating(deliv):
    d = deliv[deliv["orders"] >= 20]  # hide tiny, noisy groups
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(d["delivery_days"], d["avg_rating"], color=BLUE, marker="o", markersize=6)
    for _, r in d.iterrows():
        ax.text(r["delivery_days"], r["avg_rating"] + 0.06, f"{r['avg_rating']:.2f}",
                ha="center", fontsize=8.5, color=INK)
    ax.set_xlabel("Delivery time (days)")
    ax.set_ylabel("Average rating (1–5)")
    ax.set_ylim(2.5, 5)
    ax.grid(axis="x", visible=False)
    ax.set_xticks(d["delivery_days"])
    ax.set_title("Each extra day of delivery costs ~0.2 rating points")
    subtitle(ax, "Average customer rating by delivery time (groups with 20+ orders)")
    return save(fig, "07_delivery_vs_rating.png")


def order_value_distribution(df):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bins = np.logspace(np.log10(df["net_sales"].min()), np.log10(df["net_sales"].max()), 40)
    ax.hist(df["net_sales"], bins=bins, color=BLUE, edgecolor=SURFACE, linewidth=1)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(inr))
    for val, lab in [(df["net_sales"].median(), "median"), (df["net_sales"].mean(), "mean")]:
        ax.axvline(val, color=INK2, linestyle="--", linewidth=1)
        ax.text(val, ax.get_ylim()[1] * 0.95, f" {lab} ₹{val:,.0f}", color=INK2, fontsize=8.5)
    ax.set_xlabel("Order value (log scale)")
    ax.set_ylabel("Number of orders")
    ax.grid(axis="x", visible=False)
    ax.set_title("Most orders are small; a few big tickets pull the mean up")
    subtitle(ax, "Distribution of net order value — right-skewed, so median is the better 'typical' order")
    return save(fig, "08_order_value_distribution.png")


def correlation_heatmap(corr):
    cmap = LinearSegmentedColormap.from_list(
        "div", ["#d03b3b", "#ec835a", "#f0efec", "#6da7ec", "#184f95"])
    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr)), corr.index)
    ax.grid(False)
    for i in range(len(corr)):
        for j in range(len(corr)):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(v) > 0.6 else INK)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cb.outline.set_visible(False)
    ax.set_title("Discount ↔ quantity and delivery ↔ rating stand out")
    subtitle(ax, "Pearson correlation between numeric variables (blue = positive, red = negative)")
    return save(fig, "09_correlation_heatmap.png")


def region_category_heatmap(pivot):
    p = pivot.drop(index="Total", columns="Total")
    cmap = LinearSegmentedColormap.from_list("seq", BLUE_SEQ)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    im = ax.imshow(p.values, cmap=cmap, aspect="auto")
    ax.set_xticks(range(p.shape[1]), p.columns)
    ax.set_yticks(range(p.shape[0]), p.index)
    ax.grid(False)
    vmax = p.values.max()
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.values[i, j]
            ax.text(j, i, inr(v), ha="center", va="center", fontsize=9,
                    color="white" if v > vmax * 0.5 else INK)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Electronics dominates in every region")
    subtitle(ax, "Net revenue by region × category (darker = more revenue)")
    return save(fig, "10_region_category_heatmap.png")


def payment_mix(pay):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    hbar(ax, pay["payment_method"], pay["order_share_%"], lambda v: f"{v:.1f}%")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("UPI is the payment method of choice")
    subtitle(ax, "Share of orders by payment method")
    return save(fig, "11_payment_mix.png")


def customer_segments(seg):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    s = seg.iloc[::-1]
    hbar(ax, s["segment"].astype(str) + " spenders", s["revenue_share_%"], lambda v: f"{v:.1f}%")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("The top 25% of customers generate ~70% of revenue")
    subtitle(ax, "Revenue share by customer spend quartile (equal-sized groups)")
    return save(fig, "12_customer_segments.png")


def dashboard(k, monthly, cat, reg, disc):
    """One-page summary: KPI tiles + 4 panels."""
    fig = plt.figure(figsize=(16, 9.5))
    gs = fig.add_gridspec(3, 4, height_ratios=[0.3, 1, 1], hspace=0.6, wspace=0.45,
                          top=0.9)
    fig.suptitle("ShopSmart India — Sales Performance Dashboard (2024–2025)",
                 x=0.06, y=0.97, ha="left", fontsize=17, fontweight="bold", color=INK)

    tiles = [("Total revenue", inr(k["Total revenue (INR)"])),
             ("Orders", f"{k['Total orders']:,}"),
             ("YoY growth", f"+{k['YoY revenue growth (%)']:.1f}%"),
             ("Avg order value", f"₹{k['Average order value (INR)']:,.0f}")]
    for i, (lab, val) in enumerate(tiles):
        ax = fig.add_subplot(gs[0, i])
        ax.axis("off")
        ax.text(0, 0.75, lab, fontsize=11, color=INK2, transform=ax.transAxes)
        ax.text(0, 0.05, val, fontsize=26, fontweight="bold", color=INK, transform=ax.transAxes)

    ax = fig.add_subplot(gs[1, :])
    x = np.arange(len(monthly))
    ax.plot(x, monthly["revenue"], color=BLUE, marker="o", markersize=3)
    ax.set_xticks(x[::2], monthly["month"].iloc[::2], rotation=30, ha="right", fontsize=8)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(inr))
    ax.set_ylim(0, monthly["revenue"].max() * 1.15)
    ax.grid(axis="x", visible=False)
    ax.set_title("Monthly revenue — festive peaks every Oct–Nov", fontsize=12, pad=8)

    ax = fig.add_subplot(gs[2, 0:2])
    hbar(ax, cat["category"], cat["revenue"], inr)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(inr))
    ax.set_title("Revenue by category", fontsize=12, pad=8)

    ax = fig.add_subplot(gs[2, 2])
    hbar(ax, reg["region"], reg["revenue"], inr)
    ax.set_xticks([])
    ax.set_title("Revenue by region", fontsize=12, pad=8)

    ax = fig.add_subplot(gs[2, 3])
    ax.bar(range(len(disc)), disc["avg_quantity"], color=BLUE, width=0.6)
    ax.set_xticks(range(len(disc)), [f"{d}%" for d in disc["discount_pct"]], fontsize=8)
    ax.grid(axis="x", visible=False)
    ax.set_title("Avg units by discount", fontsize=12, pad=8)
    return save(fig, "00_dashboard.png")


def make_all(df, k, a, corr):
    overall_rr = df["is_returned"].mean() * 100
    return [
        dashboard(k, a["monthly"], a["category"], a["region"], a["discount"]),
        monthly_trend(a["monthly"]),
        seasonality(a["seasonality"]),
        category_revenue(a["category"]),
        region_revenue(a["region"]),
        return_rate(a["category"], overall_rr),
        discount_effect(a["discount"]),
        delivery_rating(a["delivery"]),
        order_value_distribution(df),
        correlation_heatmap(corr),
        region_category_heatmap(a["pivot_region_cat"]),
        payment_mix(a["payment"]),
        customer_segments(a["segments"]),
    ]
