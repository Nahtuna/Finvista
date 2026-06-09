# -*- coding: utf-8 -*-
"""
🏆 FINVISTA QUANT PRO: UNIFIED COMMAND LINE INTERFACE (CLI)
==========================================================
Unified control center and quick-launch gateway for all Finvista Quant components.
Consolidates Covered Warrants calculations, Machine Learning Credit Risk distress engine,
HOSE-compliant paper trading portfolio management, and the FastAPI gateway.

Usage:
  python run.py api                      (Launch REST API Gateway)
  python run.py cw --strategy balanced   (Trigger Covered Warrants Market Scanner)
  python run.py credit --pipeline        (Run Credit Risk Ingestion & Classification)
  python run.py credit --train           (Train Credit Distress XGBoost Model)
  python run.py history --symbol CACB2510 (Analyze warrant historical volatility)
  python run.py trade --portfolio        (View paper trading account dashboard)
  python run.py trade --scan             (Scan BSM signals and execute paper trades)

Author: samvo
Version: 3.0 (Consolidated)
"""

import os
import sys
import argparse
import subprocess

# Prevent vnstock update check from hanging by mocking the upgrade module
from unittest.mock import MagicMock
mock_upgrade = MagicMock()
mock_upgrade.update_notice = lambda *args, **kwargs: None
sys.modules['vnstock.core.utils.upgrade'] = mock_upgrade

# Force terminal UTF-8 encoding on Windows to ensure flawless Vietnamese text rendering
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

# Ensure root folder is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def print_banner():
    banner = """
========================================================================================
     🏆  F I N V I S T A   Q U A N T   P R O   -   U N I F I E D   C L I  🏆
========================================================================================
    * Quantitative Covered Warrants Core Engine (Black-Scholes & Greeks)
    * Machine Learning Corporate Credit Distress Predictor (XGBoost Early Warning)
    * HOSE-Compliant Paper Trading & Multi-User Auth SQLite Database
    * High-Performance REST API & Live WebSockets Broadcasting Gateway
========================================================================================
"""
    print(banner)

def handle_api(args):
    print("🚀 Starting Finvista FastAPI Gateway on port 8008...")
    print("💡 Swagger API Docs: http://127.0.0.1:8008/docs")
    print("💡 WebSockets Live:  ws://127.0.0.1:8008/api/ws")
    print("=" * 88)
    
    try:
        import uvicorn
        uvicorn.run("src.api.main:app", host="127.0.0.1", port=8008, reload=True)
    except KeyboardInterrupt:
        print("\n🛑 API Gateway stopped successfully.")
    except Exception as e:
        print(f"❌ Error starting API Gateway: {e}")

def handle_cw(args):
    print("⏳ Đang khởi động engine chứng quyền (nạp thư viện, có thể mất 20–30 giây)...", flush=True)
    from src.quant.engines.run_analysis import main as run_cw_main
    print(f"🏁 Triggering Covered Warrant valuation scan with strategy: '{args.strategy}'...", flush=True)
    # Set sys.argv to mock the command line for run_analysis
    sys.argv = ['run_cw.py']
    if args.silent:
        sys.argv.append('--silent')
    if args.strategy:
        sys.argv.extend(['--strategy', args.strategy])
    if args.limit:
        sys.argv.extend(['--limit', str(args.limit)])
    if getattr(args, 'all', False):
        sys.argv.append('--all')
    if getattr(args, 'derivatives_filter', False):
        sys.argv.append('--derivatives-filter')

    run_cw_main()

def handle_credit(args):
    print("🚨 Accessing ML Corporate Credit Distress Pipeline...")
    if args.train:
        print("⚙️ [Training] Initializing XGBoost distress prediction model training...")
        from src.models.credit.credit_step6_train_model import train_prediction_model
        train_prediction_model()
    elif args.evaluate:
        print("🔍 [Evaluation] Running full-market quantitative credit health assessment...")
        from src.models.credit.credit_step7_evaluate_market import evaluate_market_health
        evaluate_market_health()
    elif args.contagion:
        print("🕸️ [Contagion] Simulating systematic risk contagion (DebtRank) across entire market...")
        from src.models.credit.credit_step8_contagion_model import evaluate_systemic_risk
        evaluate_systemic_risk()
    elif args.financial:
        print("🏦 [Financial] Running specialized health assessment for Banks, Securities, and Insurance...")
        from src.models.credit.financial_health_crawler import main as run_financial_gate
        run_financial_gate()
    else:
        print("⚡ [Pipeline] Running full 5-tier credit risk data ingestion & classification...")
        from src.models.credit.credit_pipeline import run_full_pipeline
        run_full_pipeline()

def handle_history(args):
    from src.quant.engines.history_analyzer import analyze_historical_warrant
    symbol = args.symbol.upper().strip()
    days = args.days
    print(f"📈 Analyzing historical volatility & leverage for warrant {symbol} over last {days} sessions...")
    analyze_historical_warrant(symbol, lookback_days=days)

def handle_trade(args):
    from src.trading.paper_trader import scan_and_trade, print_portfolio_dashboard, reset_portfolio
    
    if args.reset:
        reset_portfolio()
        print("✅ Demo paper trading account cash successfully reset to 100,000,000đ.")
        print_portfolio_dashboard()
        return
        
    if args.portfolio:
        print_portfolio_dashboard()
        return
        
    if args.scan:
        if args.loop:
            import time
            from datetime import datetime
            from src.quant.engines.run_analysis import main as refresh_analysis
            
            print(f"🔄 Starting continuous trade scanning loop every {args.loop} seconds...")
            print("💡 Automated routine:")
            print("   1. Ingest live warrant quotes & compute Greeks.")
            print("   2. Run risk locks (-15% SL, +20% TP, theta-decay warning).")
            print("   3. Auto-execute paper trades complying with HOSE rules.")
            print("=" * 90)
            
            orig_argv = sys.argv
            try:
                while True:
                    dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"\n[🔔 LOOP - {dt_str}] Refreshing live quantitative indicators...")
                    try:
                        sys.argv = ['run_cw.py', '--silent']
                        if getattr(args, 'derivatives_filter', False):
                            sys.argv.append('--derivatives-filter')
                        refresh_analysis()
                    except Exception as e:
                        print(f"⚠️ Live API warning: {e}. Falling back to cached data.")
                    
                    print("🏁 Scanning trading signals...")
                    actions = scan_and_trade(force=args.force)
                    print("📝 Executed transactions:")
                    for act in actions:
                        print(f"  * {act}")
                    
                    print("\n📊 UPDATED PORTFOLIO DASHBOARD:")
                    print_portfolio_dashboard()
                    
                    print(f"💤 Sleeping for {args.loop} seconds... Press Ctrl+C to terminate.")
                    time.sleep(args.loop)
            except KeyboardInterrupt:
                print("\n🛑 Automated loop stopped successfully.")
                sys.argv = orig_argv
        else:
            print("🏁 Scanning BSM signals and executing HOSE-compliant portfolio trades...")
            actions = scan_and_trade(force=args.force)
            print("\n📝 Execution logs:")
            for act in actions:
                print(f"  * {act}")
            print("\n📊 Updating portfolio dashboard...")
            print_portfolio_dashboard()

def handle_orchestrator(args):
    from src.services.orchestrator import FinvistaOrchestrator
    orchestrator = FinvistaOrchestrator()
    orchestrator.start()

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Unified Command Center CLI for Finvista Quant Pro Suite",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(title="Subcommands", dest="command", required=True)
    
    # ── SUBCOMMAND: API ──
    subparsers.add_parser('api', help="Launch FastAPI REST & WebSockets Server on port 8008")
    
    # ── SUBCOMMAND: CW / SCAN (Covered Warrants Core) ──
    def _add_cw_args(p):
        p.add_argument('--strategy', '-s', type=str, default='balanced', choices=['safe', 'balanced', 'aggressive'],
                       help="Select rating/scoring methodology (default: balanced)")
        p.add_argument('--limit', '-l', type=int, default=15, help="Number of opportunities to print in console")
        p.add_argument('--all', action='store_true', help="Display all covered warrants (overrides --limit)")
        p.add_argument('--silent', action='store_true', help="Suppress console outputs (save to CSV only)")
        p.add_argument('--derivatives-filter', '-df', action='store_true', help="Apply derivatives sentiment filter to tighten gates")

    parser_cw = subparsers.add_parser('cw', help="Run Black-Scholes & Greeks valuation scanner")
    _add_cw_args(parser_cw)
    parser_scan = subparsers.add_parser('scan', help="Alias for cw — quét thị trường chứng quyền")
    _add_cw_args(parser_scan)
    
    # ── SUBCOMMAND: CREDIT (XGBoost ML distress early warning) ──
    parser_credit = subparsers.add_parser('credit', help="Ingest financial ratios & run XGBoost credit engine")
    credit_group = parser_credit.add_mutually_exclusive_group()
    credit_group.add_argument('--pipeline', '-p', action='store_true', help="Run full credit risk data ingestion pipeline")
    credit_group.add_argument('--train', '-t', action='store_true', help="Re-train prediction model with Out-of-Time split")
    credit_group.add_argument('--evaluate', '-e', action='store_true', help="Run evaluation scanner on all 1,447 listed stocks")
    credit_group.add_argument('--contagion', '-c', action='store_true', help="Run Network DebtRank contagion simulation across entire market")
    credit_group.add_argument('--financial', '-f', action='store_true', help="Run specialized health assessment for Banks, Securities, and Insurance")
    
    # ── SUBCOMMAND: HISTORY (Warrants Volatility history tracker) ──
    parser_history = subparsers.add_parser('history', help="Track historical volatility & gearing for a specific CW")
    parser_history.add_argument('--symbol', '-s', type=str, required=True, help="Warrant ticker (e.g. CACB2510)")
    parser_history.add_argument('--days', '-d', type=int, default=15, help="Lookback trading days (default: 15)")
    
    # ── SUBCOMMAND: TRADE (HOSE Paper Trading & Risk validation) ──
    parser_trade = subparsers.add_parser('trade', help="Monitor & execute automated/manual paper trades")
    trade_group = parser_trade.add_mutually_exclusive_group(required=True)
    trade_group.add_argument('--portfolio', '-p', action='store_true', help="Print live quantitative account dashboard")
    trade_group.add_argument('--scan', '-s', action='store_true', help="Trigger BSM scoring buy/sell routine")
    trade_group.add_argument('--reset', '-r', action='store_true', help="Reset DEMO portfolio cash to 100,000,000đ")
    
    parser_trade.add_argument('--force', '-f', action='store_true', help="Bypass market hours check for simulation")
    parser_trade.add_argument('--loop', '-l', type=int, help="Run continuously in N-second interval scanner loops")
    parser_trade.add_argument('--derivatives-filter', '-df', action='store_true', help="Apply derivatives sentiment filter to trading signals")
    
    # ── SUBCOMMAND: INGEST (Quantitative data pipeline ingestion) ──
    parser_ingest = subparsers.add_parser('ingest', help="Download and import historical market data (Stock & CW)")
    parser_ingest.add_argument('--download', action='store_true', help="Download live history from SSI API (takes longer)")
    parser_ingest.add_argument('--events', action='store_true', help="Scrape corporate events and news from Vietstock")
    
    # ── SUBCOMMAND: OPTIMIZE (Quantitative parameter search) ──
    parser_opt = subparsers.add_parser('optimize', help="Run grid search parameter tuning")
    parser_opt.add_argument('--type', choices=['cw', 'stock', 'all'], default='cw', help="Type of parameters to optimize")
    
    # ── SUBCOMMAND: AUDIT (Strategy Walk-Forward audit) ──
    subparsers.add_parser('audit', help="Run walk-forward validation and audit V5 strategy")
    
    # ── SUBCOMMAND: STATS (Portfolio Optimization & Advanced Statistics) ──
    parser_stats = subparsers.add_parser('stats', help="Portfolio optimization (Kelly, Mean-Variance) & advanced trading analytics")
    parser_stats.add_argument('--backtest', '-b', action='store_true', help="Use backtest audit data instead of live Paper Trading history")

    # ── SUBCOMMAND: ORCHESTRATOR (Master automation service) ──
    subparsers.add_parser('orchestrator', help="Launch the Master Orchestrator (Auto Ingest + AI Analysis + Alerts)")

    args = parser.parse_args()
    
    # Dispatching routes
    if args.command == 'api':
        handle_api(args)
    elif args.command in ('cw', 'scan'):
        handle_cw(args)
    elif args.command == 'credit':
        handle_credit(args)
    elif args.command == 'history':
        handle_history(args)
    elif args.command == 'trade':
        handle_trade(args)
    elif args.command == 'ingest':
        handle_ingest(args)
    elif args.command == 'optimize':
        handle_optimize(args)
    elif args.command == 'audit':
        handle_audit(args)
    elif args.command == 'stats':
        handle_stats(args)
    elif args.command == 'orchestrator':
        handle_orchestrator(args)

def handle_ingest(args):
    print("\n📥 STEP 1: Importing local CSV data into SQLite DB...")
    try:
        subprocess.run([sys.executable, "-m", "src.etl.loaders.load_csv_to_db"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ DB Import failed with exit code {e.returncode}.")
        return
        
    if args.download:
        print("\n📥 STEP 2: Downloading Stock & CW History from SSI API...")
        try:
            subprocess.run([sys.executable, "-m", "src.etl.extractors.extract_ssi_stock_all"], check=True)
            subprocess.run([sys.executable, "-m", "src.etl.extractors.extract_ssi_cw_all"], check=True)
            subprocess.run([sys.executable, "-m", "src.etl.transformers.transform_stock_ta"], check=True)
            print("✅ Data download and ETL completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ SSI API Download failed with exit code {e.returncode}.")
            
    if args.events:
        print("\n📥 STEP 3: Scraping Corporate Events & News from Vietstock...")
        try:
            subprocess.run([sys.executable, "-m", "src.etl.extractors.vietstock_scraper"], check=True)
            print("✅ Vietstock scraping completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Vietstock scraping failed with exit code {e.returncode}.")

def handle_optimize(args):
    if args.type in ("cw", "all"):
        print("\n⚙️  Optimizing Covered Warrant Parameters (Grid Search)...")
        try:
            subprocess.run([sys.executable, "-m", "src.quant.engines.opt_cw_grid_search"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ CW Optimization failed: {e}")
    if args.type in ("stock", "all"):
        print("\n⚙️  Optimizing Stock Technical Indicators...")
        try:
            subprocess.run([sys.executable, "-m", "src.quant.indicators.opt_stock_ta"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Stock TA Optimization failed: {e}")

def handle_audit(args):
    print("\n🔍 Auditing V5 Strategy via Walk-Forward Validation (Train/Test 70/30)...")
    try:
        subprocess.run([sys.executable, "-m", "src.quant.engines.opt_cw_backtest_audit"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Strategy Audit failed: {e}")

def handle_stats(args):
    print("\n📊 Generating Portfolio Optimization & Advanced Trading Statistics...")
    from src.quant.engines.portfolio_optimizer import print_advanced_stats
    print_advanced_stats(use_backtest=getattr(args, 'backtest', False))

if __name__ == "__main__":
    main()
