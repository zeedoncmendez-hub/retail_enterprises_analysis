"""
Retail Sales Analysis - end-to-end pipeline.

    python main.py

Runs: generate raw data -> clean -> analyse & test -> charts -> Excel report.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import generate_data                                  # noqa: E402
from analysis import (aggregates, correlation_matrix, descriptive_stats,  # noqa: E402
                      iqr_outliers, key_insights, kpis, statistical_tests)
from clean import CLEAN, RAW, clean                   # noqa: E402
from excel_report import build_report                 # noqa: E402
from visualize import make_all                        # noqa: E402


def banner(text):
    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}")


def main():
    pd.set_option("display.width", 160)
    pd.set_option("display.max_colwidth", 90)

    banner("STEP 0 | Generate raw data")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    generate_data.make_messy(generate_data.build()).to_csv(RAW, index=False)
    raw = pd.read_csv(RAW)
    print(f"Raw shape: {raw.shape}")
    print(f"Missing values:\n{raw.isna().sum()[raw.isna().sum() > 0]}")
    print(f"Duplicate rows: {raw.duplicated().sum()}")

    banner("STEP 1 | Clean")
    df, log = clean(raw)
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN, index=False)
    print(log.to_string(index=False))
    print(f"\nClean shape: {df.shape}")

    banner("STEP 2 | KPIs")
    k = kpis(df)
    for name, val in k.items():
        print(f"{name:<30} {val:>16,.2f}")

    banner("STEP 2 | Descriptive statistics")
    desc = descriptive_stats(df)
    print(desc.round(2).to_string(index=False))
    out = iqr_outliers(df)

    banner("STEP 2 | Hypothesis tests")
    a = aggregates(df)
    tests = statistical_tests(df, a["monthly"])
    for r in tests.itertuples():
        print(f"- {r.test}: p = {r.p_value:.3g} -> {r.result}\n    {r.interpretation}")

    insights = key_insights(k, a, tests)
    banner("KEY INSIGHTS")
    for i, s in enumerate(insights, 1):
        print(f"{i}. {s}")

    banner("STEP 3 | Charts")
    charts = make_all(df, k, a, correlation_matrix(df))
    print(f"{len(charts)} charts saved to outputs/charts/")

    banner("STEP 4 | Excel report")
    path = build_report(df, log, k, a, tests, out, insights, charts)
    print(f"Saved -> {path.relative_to(ROOT)}")

    # Plain-text summary for the README / presentation
    (ROOT / "outputs" / "reports" / "key_insights.md").write_text(
        "# Key insights\n\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(insights, 1)) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
