# -*- coding: utf-8 -*-
"""
🚀 VN-QUANT: MINIMALIST COVERED WARRANT RUNNER & PIPELINE
======================================================
Orchestrates data fetch, Greeks, scoring, export, and CLI output.

Usage:
  python run_analysis.py --strategy balanced

Author: samvo
Version: 2.0 (Super Minimalist)
"""

import argparse
import os
import sys

os.environ["VNSTOCK_SHOW_ADS"] = "False"

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

import pandas as pd

from src.cw_engine.fetcher import fetch_market_cw_data, fetch_underlying_historical_volatilities
from src.cw_engine.pricing_core import (
    fetch_dynamic_risk_free_rate,
    make_decision,
    score_cw,
)
from src.cw_engine.ranker import run_quant_calculations, simulate_cw_scenarios
from src.cw_engine.reporter import (
    REPORT_PATH,
    dispatch_telegram_alerts,
    export_csv,
    print_terminal_report,
    save_opportunities_to_db,
)

# Re-export for backward compatibility
__all__ = [
    "main",
    "run_quant_pipeline_programmatic",
    "fetch_market_cw_data",
    "save_opportunities_to_db",
]


def silence_print_decorator(func):
    def wrapper(*args, **kwargs):
        import builtins

        silent = "--silent" in sys.argv
        orig_print = builtins.print
        if silent:
            builtins.print = lambda *a, **k: None
        try:
            return func(*args, **kwargs)
        finally:
            builtins.print = orig_print

    return wrapper


@silence_print_decorator
def main():
    parser = argparse.ArgumentParser(description="VN-Quant Covered Warrant Minimalist Analyzer")
    parser.add_argument(
        "--strategy",
        type=str,
        default="balanced",
        choices=["safe", "balanced", "aggressive"],
        help="Scoring strategy (safe, balanced, aggressive)",
    )
    parser.add_argument("--limit", type=int, default=15, help="Number of rows to display in terminal")
    parser.add_argument("--all", action="store_true", help="Display all covered warrants (overrides --limit)")
    parser.add_argument(
        "--group-by",
        type=str,
        choices=["cpcs", "tcph"],
        default=None,
        help="Group and display warrants by underlying stock (cpcs) or issuer (tcph)",
    )
    parser.add_argument(
        "--simulate",
        type=str,
        default=None,
        help="Warrant symbol to generate 2D P/L scenario matrix for (e.g. CACB2510)",
    )
    parser.add_argument("--silent", action="store_true", help="Silence terminal table printout completely")
    args = parser.parse_args()

    print("=" * 75)
    print(f" 🚀 VN-QUANT COVERED WARRANT TERMINAL PIPELINE (Profile: {args.strategy.upper()})")
    print("=" * 75)

    print("📡 Fetching dynamic risk-free rate (Vietnam 1Y Gov Bond Yield)...")
    dynamic_r = fetch_dynamic_risk_free_rate()
    from src.cw_engine import pricing_core

    pricing_core.RISK_FREE_RATE = dynamic_r
    print(f"📈 Risk-Free Rate successfully set to: {dynamic_r * 100:.3f}% (Continuous compounding)")
    print("=" * 75)

    raw_df = fetch_market_cw_data()
    if raw_df.empty:
        print("❌ Ingestion yielded no results. Exiting.")
        return

    underlyings = raw_df["B_MaCPCS"].dropna().unique().tolist()
    hv_map = fetch_underlying_historical_volatilities(underlyings)

    print("📈 Running Black-Scholes pricing models, Greeks and Newton-Raphson solvers...")
    calc_df = run_quant_calculations(raw_df, hv_map)

    print("🎯 Computing composite scores and evaluating risk limits...")
    final_df = score_cw(calc_df, strategy=args.strategy)
    final_df["U_Signal"] = final_df.apply(make_decision, axis=1)
    final_df = final_df.sort_values("G_Score", ascending=False)

    export_csv(final_df, REPORT_PATH)
    save_opportunities_to_db(final_df)

    if args.simulate:
        symbol = args.simulate.upper().strip()
        match_rows = final_df[final_df["A_MaCW"] == symbol]
        if match_rows.empty:
            print(f"❌ Warrant symbol '{symbol}' not found in live market list. Please double check the symbol name.")
            return
        simulate_cw_scenarios(match_rows.iloc[0])
        return

    if not args.silent:
        print_terminal_report(final_df, args)

    dispatch_telegram_alerts(final_df)


def run_quant_pipeline_programmatic(strategy: str = "balanced") -> pd.DataFrame:
    """
    Programmatic execution of the Covered Warrant pricing & credit health mapping pipeline.
    Returns the analyzed DataFrame, suitable for REST API integration.
    """
    dynamic_r = fetch_dynamic_risk_free_rate()
    from src.cw_engine import pricing_core

    pricing_core.RISK_FREE_RATE = dynamic_r

    raw_df = fetch_market_cw_data()
    if raw_df.empty:
        return pd.DataFrame()

    underlyings = raw_df["B_MaCPCS"].dropna().unique().tolist()
    hv_map = fetch_underlying_historical_volatilities(underlyings)
    calc_df = run_quant_calculations(raw_df, hv_map)

    final_df = score_cw(calc_df, strategy=strategy)
    final_df["U_Signal"] = final_df.apply(make_decision, axis=1)
    sorted_df = final_df.sort_values("G_Score", ascending=False)

    save_opportunities_to_db(sorted_df)
    return sorted_df


if __name__ == "__main__":
    main()
