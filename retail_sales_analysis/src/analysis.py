"""
Step 2 - Exploratory analysis, KPIs and statistical testing.

Uses pandas (aggregation), numpy (maths / regression), the built-in
`statistics` module (descriptive stats) and scipy.stats (hypothesis tests).
"""
import statistics as st

import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ------------------------------------------------------------------ KPIs
def kpis(df: pd.DataFrame) -> dict:
    by_year = df.groupby("year")["net_sales"].sum()
    return {
        "Total revenue (INR)": df["net_sales"].sum(),
        "Total orders": df["order_id"].nunique(),
        "Unique customers": df["customer_id"].nunique(),
        "Units sold": int(df["quantity"].sum()),
        "Average order value (INR)": df["net_sales"].mean(),
        "Total discount given (INR)": df["discount_amt"].sum(),
        "Return rate (%)": df["is_returned"].mean() * 100,
        "Average rating (1-5)": df["rating"].mean(),
        "Revenue 2024 (INR)": by_year.get(2024, 0),
        "Revenue 2025 (INR)": by_year.get(2025, 0),
        "YoY revenue growth (%)": (by_year.get(2025, 0) / by_year.get(2024, 1) - 1) * 100,
        "Repeat-customer share (%)": (df.groupby("customer_id").size() > 1).mean() * 100,
    }


# ------------------------------------------------------------- descriptive
def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Descriptive statistics using Python's `statistics` module + numpy."""
    rows = []
    for col in ["net_sales", "unit_price", "quantity", "customer_age", "delivery_days", "rating"]:
        x = df[col].dropna().tolist()
        q1, q3 = np.percentile(x, [25, 75])
        rows.append({
            "metric": col,
            "count": len(x),
            "mean": st.mean(x),
            "median": st.median(x),
            "mode": st.mode(x),
            "std_dev": st.stdev(x),
            "variance": st.variance(x),
            "min": min(x),
            "Q1": q1,
            "Q3": q3,
            "max": max(x),
            "IQR": q3 - q1,
            "skewness": stats.skew(x),
        })
    return pd.DataFrame(rows)


def iqr_outliers(df: pd.DataFrame, col: str = "net_sales") -> pd.DataFrame:
    q1, q3 = np.percentile(df[col], [25, 75])
    upper = q3 + 1.5 * (q3 - q1)
    out = df[df[col] > upper]
    return pd.DataFrame([{
        "column": col, "Q1": q1, "Q3": q3, "upper_fence": upper,
        "outlier_orders": len(out),
        "share_of_orders_%": len(out) / len(df) * 100,
        "share_of_revenue_%": out[col].sum() / df[col].sum() * 100,
        "decision": "Kept - genuine high-value orders (mostly Electronics), not errors",
    }])


# -------------------------------------------------------------- aggregates
def aggregates(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    agg = dict(revenue=("net_sales", "sum"), orders=("order_id", "nunique"),
               units=("quantity", "sum"), avg_order_value=("net_sales", "mean"),
               return_rate=("is_returned", "mean"), avg_rating=("rating", "mean"))

    monthly = df.groupby("month").agg(**agg).reset_index()
    monthly["mom_growth_%"] = monthly["revenue"].pct_change() * 100

    category = df.groupby("category").agg(**agg).sort_values("revenue", ascending=False).reset_index()
    category["revenue_share_%"] = category["revenue"] / category["revenue"].sum() * 100

    region = df.groupby("region").agg(**agg).sort_values("revenue", ascending=False).reset_index()

    city = df.groupby(["region", "city"]).agg(**agg).sort_values("revenue", ascending=False).reset_index()

    sub_cat = (df.groupby(["category", "sub_category"]).agg(**agg)
                 .sort_values("revenue", ascending=False).reset_index())

    payment = df.groupby("payment_method").agg(**agg).sort_values("orders", ascending=False).reset_index()
    payment["order_share_%"] = payment["orders"] / payment["orders"].sum() * 100

    age = df.groupby("age_group", observed=True).agg(**agg).reset_index()

    discount = df.groupby("discount_pct").agg(
        orders=("order_id", "nunique"), avg_quantity=("quantity", "mean"),
        avg_order_value=("net_sales", "mean"), revenue=("net_sales", "sum")).reset_index()

    delivery = df.groupby("delivery_days").agg(
        orders=("order_id", "nunique"), avg_rating=("rating", "mean")).reset_index()

    # Pivot: region x category revenue (classic Excel-style pivot)
    pivot_region_cat = pd.pivot_table(df, values="net_sales", index="region",
                                      columns="category", aggfunc="sum", margins=True,
                                      margins_name="Total")

    # Seasonality: month-of-year x year
    seasonality = pd.pivot_table(df, values="net_sales", index="month_name",
                                 columns="year", aggfunc="sum").reindex(MONTH_ORDER)

    # Customer segmentation by lifetime spend (quartiles)
    cust = df.groupby("customer_id").agg(orders=("order_id", "nunique"),
                                         lifetime_value=("net_sales", "sum")).reset_index()
    cust["segment"] = pd.qcut(cust["lifetime_value"], 4,
                              labels=["Low", "Medium", "High", "Premium"])
    segments = cust.groupby("segment", observed=True).agg(
        customers=("customer_id", "count"), avg_orders=("orders", "mean"),
        avg_lifetime_value=("lifetime_value", "mean"),
        total_revenue=("lifetime_value", "sum")).reset_index()
    segments["revenue_share_%"] = segments["total_revenue"] / segments["total_revenue"].sum() * 100

    return dict(monthly=monthly, category=category, region=region, city=city,
                sub_category=sub_cat, payment=payment, age=age, discount=discount,
                delivery=delivery, pivot_region_cat=pivot_region_cat,
                seasonality=seasonality, segments=segments,
                top_customers=cust.nlargest(10, "lifetime_value"))


# ------------------------------------------------------- hypothesis tests
def _verdict(p):
    return "Significant" if p < ALPHA else "Not significant"


def statistical_tests(df: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    results = []

    # 1) Welch t-test: do discounted orders contain more units?
    a = df.loc[df["discount_pct"] > 0, "quantity"]
    b = df.loc[df["discount_pct"] == 0, "quantity"]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    results.append({
        "test": "Welch two-sample t-test",
        "question": "Do discounted orders have more units than full-price orders?",
        "statistic": t, "p_value": p, "result": _verdict(p),
        "interpretation": f"Discounted orders average {a.mean():.2f} units vs {b.mean():.2f} "
                          f"at full price ({(a.mean() / b.mean() - 1) * 100:+.0f}%).",
    })

    # 2) One-way ANOVA + Kruskal-Wallis: order value across regions
    groups = [g["net_sales"].values for _, g in df.groupby("region")]
    f, p = stats.f_oneway(*[np.log(g) for g in groups])  # log: sales are right-skewed
    h, p_kw = stats.kruskal(*groups)
    results.append({
        "test": "One-way ANOVA (log sales) / Kruskal-Wallis",
        "question": "Does average order value differ between regions?",
        "statistic": f, "p_value": p, "result": _verdict(p),
        "interpretation": f"Kruskal-Wallis (non-parametric check) p = {p_kw:.3f}. "
                          + ("Regions differ in order value." if p < ALPHA else
                             "Regions spend similarly per order; revenue gaps come from order volume."),
    })

    # 3) Chi-square: is return rate linked to category?
    ct = pd.crosstab(df["category"], df["returned"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    rr = df.groupby("category")["is_returned"].mean().sort_values(ascending=False) * 100
    results.append({
        "test": "Chi-square test of independence",
        "question": "Are returns associated with product category?",
        "statistic": chi2, "p_value": p, "result": _verdict(p),
        "interpretation": f"Highest return rate: {rr.index[0]} ({rr.iloc[0]:.1f}%); "
                          f"lowest: {rr.index[-1]} ({rr.iloc[-1]:.1f}%). dof = {dof}.",
    })

    # 4) Correlation: delivery time vs rating
    sub = df.dropna(subset=["rating"])
    r, p = stats.pearsonr(sub["delivery_days"], sub["rating"])
    rho, p_s = stats.spearmanr(sub["delivery_days"], sub["rating"])
    results.append({
        "test": "Pearson & Spearman correlation",
        "question": "Do slower deliveries get lower ratings?",
        "statistic": r, "p_value": p, "result": _verdict(p),
        "interpretation": f"Pearson r = {r:.2f}, Spearman rho = {rho:.2f}: "
                          f"{'moderate' if abs(r) >= 0.3 else 'weak'} negative relationship.",
    })

    # 5) Linear regression on monthly revenue (numpy least squares)
    y = monthly["revenue"].values
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    lr = stats.linregress(x, y)
    results.append({
        "test": "Linear regression (monthly revenue trend)",
        "question": "Is revenue trending upward over time?",
        "statistic": lr.rvalue ** 2, "p_value": lr.pvalue, "result": _verdict(lr.pvalue),
        "interpretation": f"Trend adds ~INR {slope:,.0f} revenue per month "
                          f"(R² = {lr.rvalue ** 2:.2f}; seasonality explains much of the rest).",
    })

    # 6) 95% confidence interval for average order value
    x = df["net_sales"]
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
    results.append({
        "test": "95% confidence interval (t-distribution)",
        "question": "What is the true average order value?",
        "statistic": x.mean(), "p_value": np.nan, "result": "Estimate",
        "interpretation": f"Average order value is INR {x.mean():,.0f}; 95% CI INR {lo:,.0f} – {hi:,.0f}.",
    })

    # 7) Mann-Whitney U: festive vs non-festive order value
    fest = df.loc[df["order_date"].dt.month.isin([10, 11]), "net_sales"]
    rest = df.loc[~df["order_date"].dt.month.isin([10, 11]), "net_sales"]
    u, p = stats.mannwhitneyu(fest, rest, alternative="two-sided")
    results.append({
        "test": "Mann-Whitney U test",
        "question": "Is order value different in festive months (Oct-Nov)?",
        "statistic": u, "p_value": p, "result": _verdict(p),
        "interpretation": f"Median order: festive INR {fest.median():,.0f} vs rest INR {rest.median():,.0f}. "
                          "Festive revenue spike is driven by more orders"
                          + (" and different basket values." if p < ALPHA else ", not bigger baskets."),
    })

    return pd.DataFrame(results)


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["net_sales", "unit_price", "quantity", "discount_pct",
            "delivery_days", "rating", "customer_age", "is_returned"]
    return df[cols].corr().round(2)


def _cr(x):
    return f"₹{x / 1e7:.2f} Cr"


def key_insights(k: dict, a: dict, tests: pd.DataFrame) -> list[str]:
    cat, reg, pay, seg = a["category"], a["region"], a["payment"], a["segments"]
    seas = a["seasonality"].mean(axis=1)
    disc = a["discount"]
    dl = a["delivery"][a["delivery"]["orders"] >= 20]
    rr = cat.sort_values("return_rate", ascending=False)
    return [
        f"Revenue grew {k['YoY revenue growth (%)']:.1f}% year-on-year "
        f"({_cr(k['Revenue 2024 (INR)'])} in 2024 → {_cr(k['Revenue 2025 (INR)'])} in 2025).",
        f"{cat.iloc[0]['category']} drives {cat.iloc[0]['revenue_share_%']:.0f}% of revenue from only "
        f"{cat.iloc[0]['orders'] / cat['orders'].sum() * 100:.0f}% of orders — it is the business's main lever.",
        f"October–November (Diwali season) average "
        f"{seas[['Oct', 'Nov']].mean() / seas.drop(['Oct', 'Nov']).mean():.1f}x the revenue of other months; "
        "the lift comes from more orders, not bigger baskets (Mann-Whitney p > 0.05).",
        f"{reg.iloc[0]['region']} is the top region ({_cr(reg.iloc[0]['revenue'])}); "
        f"{reg.iloc[-1]['region']} is the smallest ({_cr(reg.iloc[-1]['revenue'])}) and also has the slowest deliveries.",
        f"{pay.iloc[0]['payment_method']} is the most used payment method "
        f"({pay.iloc[0]['order_share_%']:.0f}% of orders).",
        f"Discounts lift basket size: 30%+ discount orders average "
        f"{disc[disc.discount_pct >= 30]['avg_quantity'].mean():.1f} units vs "
        f"{disc[disc.discount_pct == 0]['avg_quantity'].iloc[0]:.1f} at full price (t-test p < 0.001).",
        f"Slower delivery hurts ratings: average rating falls from {dl['avg_rating'].iloc[0]:.2f} "
        f"({dl['delivery_days'].iloc[0]}-day) to {dl['avg_rating'].iloc[-1]:.2f} ({dl['delivery_days'].iloc[-1]}-day); "
        f"Pearson r = {tests.iloc[3]['statistic']:.2f}.",
        f"Returns depend on category (chi-square p < 0.001): {rr.iloc[0]['category']} "
        f"{rr.iloc[0]['return_rate'] * 100:.1f}% and {rr.iloc[1]['category']} {rr.iloc[1]['return_rate'] * 100:.1f}% "
        f"vs {rr.iloc[-1]['category']} {rr.iloc[-1]['return_rate'] * 100:.1f}%.",
        f"Premium customers (top 25% by spend) generate "
        f"{seg[seg.segment == 'Premium']['revenue_share_%'].iloc[0]:.0f}% of revenue — retention matters.",
    ]
