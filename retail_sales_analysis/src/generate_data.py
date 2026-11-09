"""
Step 0 - Generate a realistic (and deliberately messy) retail sales dataset.

Business context: "ShopSmart India", an online retailer selling across 4 regions.
Period: Jan 2024 - Dec 2025 (24 months).

Real patterns baked into the data (so the analysis has something to find):
  * Festive-season spike in Oct-Nov (Diwali) and a smaller one in Dec.
  * ~12% year-on-year growth.
  * Discounts increase quantity bought.
  * Electronics & Fashion have higher return rates.
  * Longer delivery times lower customer ratings.

Real-world mess injected (so the cleaning step has something to fix):
  * Duplicate rows, missing values, inconsistent text casing / spacing,
    mixed date formats, impossible values (negative prices, qty = 999).
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_ORDERS = 6000
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "sales_raw.csv"

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- reference data
REGIONS = {
    "North": ["Delhi", "Jaipur", "Lucknow", "Chandigarh"],
    "South": ["Bengaluru", "Chennai", "Hyderabad", "Kochi"],
    "East": ["Kolkata", "Bhubaneswar", "Patna", "Guwahati"],
    "West": ["Mumbai", "Pune", "Ahmedabad", "Surat"],
}
REGION_WEIGHTS = [0.27, 0.30, 0.18, 0.25]

# category -> (sub-categories, price range INR, return probability)
CATEGORIES = {
    "Electronics": (["Mobiles", "Headphones", "Smartwatches", "Laptops"], (1500, 65000), 0.14),
    "Fashion": (["Men's Wear", "Women's Wear", "Footwear", "Accessories"], (400, 4500), 0.18),
    "Home & Kitchen": (["Cookware", "Decor", "Furnishing", "Appliances"], (300, 12000), 0.07),
    "Beauty": (["Skincare", "Haircare", "Fragrance", "Makeup"], (200, 3000), 0.05),
    "Books": (["Fiction", "Non-Fiction", "Academic", "Children"], (150, 1200), 0.03),
    "Sports": (["Fitness", "Cricket", "Cycling", "Outdoor"], (350, 15000), 0.06),
}
CAT_WEIGHTS = [0.22, 0.26, 0.17, 0.14, 0.11, 0.10]
PAYMENT = ["UPI", "Credit Card", "Debit Card", "Cash on Delivery", "Net Banking"]
PAY_WEIGHTS = [0.42, 0.20, 0.14, 0.17, 0.07]

# Monthly seasonality multipliers (Jan..Dec) - Diwali spike in Oct/Nov
SEASON = np.array([0.85, 0.80, 0.90, 0.88, 0.92, 0.90, 0.95, 1.00, 1.05, 1.45, 1.55, 1.20])


def random_dates(n: int) -> pd.Series:
    """Draw order dates weighted by seasonality and 12% YoY growth."""
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    w = SEASON[days.month - 1] * np.where(days.year == 2025, 1.12, 1.0)
    w = w * np.where(days.dayofweek >= 5, 1.15, 1.0)  # weekends slightly busier
    return pd.Series(rng.choice(days, size=n, p=w / w.sum())).sort_values(ignore_index=True)


def build() -> pd.DataFrame:
    n = N_ORDERS
    dates = random_dates(n)

    region = rng.choice(list(REGIONS), size=n, p=REGION_WEIGHTS)
    city = [rng.choice(REGIONS[r]) for r in region]
    category = rng.choice(list(CATEGORIES), size=n, p=CAT_WEIGHTS)

    sub_cat, price, ret_p = [], [], []
    for c in category:
        subs, (lo, hi), rp = CATEGORIES[c]
        sub_cat.append(rng.choice(subs))
        # log-uniform prices: many cheap items, few expensive ones
        price.append(round(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))), -1))
        ret_p.append(rp)

    # Discounts: bigger during festive months
    festive = dates.dt.month.isin([10, 11]).to_numpy()
    discount = rng.choice([0, 5, 10, 15, 20, 30], size=n, p=[0.35, 0.2, 0.18, 0.12, 0.1, 0.05])
    discount = np.where(festive & (rng.random(n) < 0.5), discount + 10, discount)

    # Quantity rises with discount (Poisson with discount-driven mean)
    quantity = 1 + rng.poisson(0.6 + discount / 25)

    delivery_days = np.clip(rng.normal(4, 1.6, n).round(), 1, 12).astype(int)
    delivery_days = delivery_days + np.where(region == "East", 1, 0)  # logistics gap

    # Rating falls with slow delivery
    rating = np.clip(np.round(rng.normal(4.6 - 0.18 * delivery_days, 0.7)), 1, 5).astype(int)

    returned = rng.random(n) < np.array(ret_p)

    age = np.clip(rng.normal(32, 9, n).round(), 18, 70).astype(int)
    gender = rng.choice(["Male", "Female", "Other"], size=n, p=[0.52, 0.46, 0.02])
    customer_id = [f"C{v:05d}" for v in rng.integers(1, 2200, n)]  # repeat buyers

    df = pd.DataFrame({
        "order_id": [f"ORD{100000 + i}" for i in range(n)],
        "order_date": dates.dt.strftime("%Y-%m-%d"),
        "customer_id": customer_id,
        "customer_age": age.astype(float),
        "gender": gender,
        "city": city,
        "region": region,
        "category": category,
        "sub_category": sub_cat,
        "unit_price": price,
        "quantity": quantity,
        "discount_pct": discount,
        "payment_method": rng.choice(PAYMENT, size=n, p=PAY_WEIGHTS),
        "delivery_days": delivery_days,
        "rating": rating.astype(float),
        "returned": np.where(returned, "Yes", "No"),
    })
    return df


def make_messy(df: pd.DataFrame) -> pd.DataFrame:
    """Inject the kind of problems seen in real exports."""
    df = df.copy()
    n = len(df)

    def pick(frac):
        return rng.choice(n, size=int(n * frac), replace=False)

    # 1) Missing values
    df.loc[pick(0.04), "customer_age"] = np.nan
    df.loc[pick(0.06), "rating"] = np.nan            # customer never rated
    df.loc[pick(0.015), "payment_method"] = np.nan
    df.loc[pick(0.01), "region"] = np.nan             # recoverable from city

    # 2) Inconsistent text
    idx = pick(0.05)
    df.loc[idx, "city"] = df.loc[idx, "city"].str.upper()
    idx = pick(0.04)
    df.loc[idx, "city"] = "  " + df.loc[idx, "city"] + " "
    idx = pick(0.03)
    df.loc[idx, "category"] = df.loc[idx, "category"].str.lower()
    df.loc[pick(0.02), "payment_method"] = "upi"
    df.loc[pick(0.02), "returned"] = "Y"
    df.loc[pick(0.02), "returned"] = "N"

    # 3) Mixed date format (some rows exported as DD/MM/YYYY)
    idx = pick(0.05)
    df.loc[idx, "order_date"] = pd.to_datetime(df.loc[idx, "order_date"]).dt.strftime("%d/%m/%Y")

    # 4) Impossible values / data-entry errors
    df.loc[pick(0.003), "quantity"] = 999
    df.loc[pick(0.003), "unit_price"] *= -1
    df.loc[pick(0.002), "customer_age"] = 150

    # 5) Duplicate rows (same order exported twice)
    dupes = df.sample(frac=0.015, random_state=SEED)
    df = pd.concat([df, dupes]).sample(frac=1, random_state=SEED).reset_index(drop=True)
    return df


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    raw = make_messy(build())
    raw.to_csv(OUT, index=False)
    print(f"Saved {len(raw):,} rows x {raw.shape[1]} cols -> {OUT}")
