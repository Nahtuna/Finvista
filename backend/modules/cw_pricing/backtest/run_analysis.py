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

# Force UTF-8 encoding for stdout/stderr on Windows to handle emoji characters
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

os.environ["VNSTOCK_SHOW_ADS"] = "False"

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

import pandas as pd

from backend.modules.cw_pricing.backtest.fetcher import fetch_market_cw_data, fetch_underlying_historical_volatilities
from backend.modules.cw_pricing.models.pricing_core import (
    fetch_dynamic_risk_free_rate,
    make_decision,
    score_cw,
)
from backend.modules.cw_pricing.backtest.ranker import run_quant_calculations, simulate_cw_scenarios
from backend.modules.cw_pricing.backtest.reporter import (
    REPORT_PATH,

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
        help="Warrant symbol to generate 2D P/L scenario matrix for (e.g. CACB2511)",
    )
    parser.add_argument("--silent", action="store_true", help="Silence terminal table printout completely")
    parser.add_argument("--derivatives-filter", action="store_true", help="Apply derivatives sentiment filter to tighten gates")
    args = parser.parse_args()

    try:
        print("=" * 75)
        print(f" 🚀 VN-QUANT COVERED WARRANT TERMINAL PIPELINE (Profile: {args.strategy.upper()})")
        print("=" * 75)
    except Exception:
        pass

    try:
        print("📡 Fetching dynamic risk-free rate (Vietnam 1Y Gov Bond Yield)...")
    except Exception:
        pass
    dynamic_r = fetch_dynamic_risk_free_rate()
    from backend.modules.cw_pricing.models import pricing_core

    pricing_core.RISK_FREE_RATE = dynamic_r
    try:
        print(f"📈 Risk-Free Rate successfully set to: {dynamic_r * 100:.3f}% (Continuous compounding)")
        print("=" * 75)
    except Exception:
        pass

    raw_df = fetch_market_cw_data(bypass_cache=True)
    if raw_df.empty:
        try:
            print("❌ Ingestion yielded no results. Exiting.")
        except Exception:
            pass
        return

    underlyings = raw_df["B_MaCPCS"].dropna().unique().tolist()
    hv_map = fetch_underlying_historical_volatilities(underlyings)

    try:
        print("📈 Running Black-Scholes pricing models, Greeks and Newton-Raphson solvers...")
    except Exception:
        pass
    calc_df = run_quant_calculations(raw_df, hv_map)

    try:
        print("📈 Enriching with underlying stock momentum data...")
    except Exception:
        pass
    from backend.modules.cw_pricing.backtest.momentum_enricher import enrich_with_underlying_momentum
    calc_df = enrich_with_underlying_momentum(calc_df, include_chart_patterns=True)

    try:
        print("🎯 Computing composite scores and evaluating risk limits...")
    except Exception:
        pass
    final_df = score_cw(calc_df, strategy=args.strategy)
    
    # --- Integrate Industry Analysis (Top-Down Layer) ---
    try:
        print("📈 Applying Top-Down Industry Analysis & Sectoral Risk Mapping...")
    except Exception:
        pass
    from backend.modules.cw_pricing.backtest.industry_analyzer import apply_industry_logic_to_pipeline
    final_df = apply_industry_logic_to_pipeline(final_df)
    
    # --- Integrate Risk Factor Engine (CAPM/Factor Layer) ---
    try:
        print("🛡️ Applying Systematic Risk (Beta) & Factor Adjustments...")
    except Exception:
        pass
    from backend.modules.cw_pricing.backtest.risk_engine import enrich_with_risk_factors
    from backend.core import config
    hist_file = os.path.join(config.PROCESSED_DATA_DIR, "all_stock_historical_prices.csv")
    if os.path.exists(hist_file):
        final_df = enrich_with_risk_factors(final_df, hist_file)
    # --------------------------------------------------------
    
    # --- FINVISTA INSTITUTIONAL UPGRADE: MACRO LIQUIDITY STRESS FILTER ---
    try:
        print("🏦 Checking Macro Liquidity Stress (Interbank Rates)...")
    except Exception:
        pass
    is_liquidity_stressed = False
    try:
        from backend.infra.sbv_scraper import fetch_svb_interbank_rates
        sbv_rates = fetch_svb_interbank_rates()
        on_rate = sbv_rates.get("on_rate", 0.0425)
        if on_rate > 0.08:
            is_liquidity_stressed = True
            try:
                print(f"[WARNING] LIQUIDITY STRESS DETECTED: SBV Overnight Interbank Rate ~ {on_rate*100:.2f}% > 8.0%")
                print("🛑 CIRCUIT BREAKER ACTIVATED: All BUY signals will be downgraded to WATCH/SKIP.")
            except Exception:
                pass
        else:
            try:
                print(f"🏦 Macro Liquidity is safe (SBV Overnight Interbank Rate: {on_rate*100:.2f}%)")
            except Exception:
                pass
    except Exception as e:
        try:
            print(f"[WARNING] Could not verify macro liquidity: {e}")
        except Exception:
            pass

    final_df["U_Signal"] = final_df.apply(lambda r: make_decision(r, use_derivatives_filter=args.derivatives_filter), axis=1)
    
    # Apply Circuit Breaker Downgrade
    if is_liquidity_stressed:
        final_df["U_Signal"] = final_df["U_Signal"].replace({"STRONG BUY": "WATCH (STRESS)", "BUY": "SKIP (STRESS)"})
        
    final_df = final_df.sort_values("G_Score", ascending=False)

    export_csv(final_df, REPORT_PATH)
    save_opportunities_to_db(final_df)

    if args.simulate:
        symbol = args.simulate.upper().strip()
        match_rows = final_df[final_df["A_MaCW"] == symbol]
        if match_rows.empty:
            try:
                print(f"❌ Warrant symbol '{symbol}' not found in live market list. Please double check the symbol name.")
            except Exception:
                pass
            return
        simulate_cw_scenarios(match_rows.iloc[0])
        return

    if not args.silent:
        try:
            print_terminal_report(final_df, args)
        except Exception:
            pass


def run_quant_pipeline_programmatic(strategy: str = "balanced", use_derivatives_filter: bool = False) -> pd.DataFrame:
    """
    Programmatic execution of the Covered Warrant pricing & credit health mapping pipeline.
    Returns the analyzed DataFrame, suitable for REST API integration.
    """
    dynamic_r = fetch_dynamic_risk_free_rate()
    from backend.modules.cw_pricing.models import pricing_core

    pricing_core.RISK_FREE_RATE = dynamic_r

    raw_df = fetch_market_cw_data(bypass_cache=True)
    if raw_df.empty:
        return pd.DataFrame()

    underlyings = raw_df["B_MaCPCS"].dropna().unique().tolist()
    hv_map = fetch_underlying_historical_volatilities(underlyings)
    calc_df = run_quant_calculations(raw_df, hv_map)

    from backend.modules.cw_pricing.backtest.momentum_enricher import enrich_with_underlying_momentum
    calc_df = enrich_with_underlying_momentum(calc_df, include_chart_patterns=True)

    # Get current market regime for adaptive filtering
    market_regime = 'NEUTRAL'  # Default fallback
    try:
        from backend.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
        regime_data = calculate_vnindex_regime(days=1250)
        market_regime = regime_data.get('regime', 'NEUTRAL')
        try:
            print(f"[Regime] Current market regime: {market_regime}")
        except (ValueError, OSError):
            pass
    except Exception as e:
        market_regime = 'NEUTRAL'  # Ensure fallback

    final_df = score_cw(calc_df, strategy=strategy, market_regime=market_regime)
    
    # --- Integrate Industry Analysis (Top-Down Layer) ---
    from backend.modules.cw_pricing.backtest.industry_analyzer import apply_industry_logic_to_pipeline
    final_df = apply_industry_logic_to_pipeline(final_df)
    # ----------------------------------------------------
    
    final_df["U_Signal"] = final_df.apply(lambda r: make_decision(r, use_derivatives_filter=use_derivatives_filter, market_regime=market_regime), axis=1)
    sorted_df = final_df.sort_values("G_Score", ascending=False)

    save_opportunities_to_db(sorted_df)
    return sorted_df


if __name__ == "__main__":
    main()
