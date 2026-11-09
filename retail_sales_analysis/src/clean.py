"""
Step 1 - Data cleaning with pandas & numpy.

Every fix is logged so the cleaning is auditable (the log is also written
to the Excel report).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "sales_raw.csv"
CLEAN = ROOT / "data" / "processed" / "sales_clean.csv"

CITY_TO_REGION = {
    "Delhi": "North", "Jaipur": "North", "Lucknow": "North", "Chandigarh": "North",
    "Bengaluru": "South", "Chennai": "South", "Hyderabad": "South", "Kochi": "South",
    "Kolkata": "East", "Bhubaneswar": "East", "Patna": "East", "Guwahati": "East",
    "Mumbai": "West", "Pune": "West", "Ahmedabad": "West", "Surat": "West",
}


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = raw.copy()
    log = []

    def note(step, rows, detail):
        log.append({"step": step, "rows_affected": int(rows), "detail": detail})

    # 1. Exact duplicate rows
    n = df.duplicated().sum()
    df = df.drop_duplicates().reset_index(drop=True)
    note("Remove duplicates", n, "Dropped exact duplicate rows (same order exported twice)")

    # 2. Standardise text columns (whitespace + casing)
    for col in ["city", "category", "gender"]:
        before = df[col].copy()
        df[col] = df[col].str.strip().str.title()
        note(f"Standardise '{col}'", (before != df[col]).sum(), "Trimmed spaces, applied Title Case")

    pay_map = {"upi": "UPI"}
    n = df["payment_method"].isin(pay_map.keys()).sum()
    df["payment_method"] = df["payment_method"].replace(pay_map)
    note("Standardise 'payment_method'", n, "'upi' -> 'UPI'")

    n = df["returned"].isin(["Y", "N"]).sum()
    df["returned"] = df["returned"].replace({"Y": "Yes", "N": "No"})
    note("Standardise 'returned'", n, "'Y'/'N' -> 'Yes'/'No'")

    # 3. Parse mixed date formats (YYYY-MM-DD and DD/MM/YYYY)
    iso = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(df["order_date"], format="%d/%m/%Y", errors="coerce")
    note("Parse dates", iso.isna().sum(), "Converted DD/MM/YYYY rows to proper dates")
    df["order_date"] = iso.fillna(dmy)

    # 4. Impossible values -> treat as data-entry errors
    bad_price = df["unit_price"] < 0
    df.loc[bad_price, "unit_price"] = df.loc[bad_price, "unit_price"].abs()
    note("Fix negative prices", bad_price.sum(), "Sign error - took absolute value")

    bad_qty = df["quantity"] >= 999
    df = df[~bad_qty].copy()
    note("Drop placeholder quantity", bad_qty.sum(), "quantity = 999 is a system placeholder, rows removed")

    bad_age = df["customer_age"] > 100
    df.loc[bad_age, "customer_age"] = np.nan
    note("Invalid ages", bad_age.sum(), "Age > 100 set to missing (imputed next)")

    # 5. Missing values
    n = df["region"].isna().sum()
    df["region"] = df["region"].fillna(df["city"].map(CITY_TO_REGION))
    note("Impute region", n, "Recovered from city -> region lookup")

    n = df["customer_age"].isna().sum()
    df["customer_age"] = df["customer_age"].fillna(df["customer_age"].median()).astype(int)
    note("Impute age", n, "Filled with median age (robust to outliers)")

    n = df["payment_method"].isna().sum()
    df["payment_method"] = df["payment_method"].fillna("Unknown")
    note("Missing payment method", n, "Labelled 'Unknown' (not guessed)")

    n = df["rating"].isna().sum()
    note("Missing rating", n, "Left as NaN - customer did not rate; excluded from rating stats")

    # 6. Feature engineering
    df["gross_sales"] = df["unit_price"] * df["quantity"]
    df["discount_amt"] = (df["gross_sales"] * df["discount_pct"] / 100).round(2)
    df["net_sales"] = (df["gross_sales"] - df["discount_amt"]).round(2)
    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    df["month_name"] = df["order_date"].dt.strftime("%b")
    df["quarter"] = "Q" + df["order_date"].dt.quarter.astype(str)
    df["weekday"] = df["order_date"].dt.day_name()
    df["is_returned"] = (df["returned"] == "Yes").astype(int)
    df["has_discount"] = np.where(df["discount_pct"] > 0, "Discounted", "Full price")
    df["age_group"] = pd.cut(df["customer_age"], bins=[17, 24, 34, 44, 54, 100],
                             labels=["18-24", "25-34", "35-44", "45-54", "55+"])
    note("Feature engineering", len(df),
         "Added gross/net sales, discount amount, year, month, quarter, weekday, age group")

    df = df.sort_values("order_date").reset_index(drop=True)
    return df, pd.DataFrame(log)


if __name__ == "__main__":
    raw = pd.read_csv(RAW)
    df, log = clean(raw)
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN, index=False)
    print(log.to_string(index=False))
    print(f"\n{len(raw):,} raw rows -> {len(df):,} clean rows")
