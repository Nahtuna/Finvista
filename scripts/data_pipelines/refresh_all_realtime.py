# -*- coding: utf-8 -*-
"""
🔄 FINVISTA: REAL-TIME DATA REFRESH SCRIPT
============================================
Script để cập nhật toàn bộ data real-time từ các nguồn:
- Market opportunities (CW data)
- Stock history
- CW history  
- Market indices (VNINDEX, VN30, HNXINDEX)
- Macro data (USD/VND, Gold, VIX, Oil)
- Derivatives data (VN30F1M)
- US indices (S&P 500, NASDAQ)

Chạy script này để refresh data ngay lập tức thay vì đợi scheduler.
"""

import os
import sys
from datetime import datetime

# Fix Windows console encoding
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def refresh_market_opportunities():
    """Refresh CW market opportunities data."""
    print("\n📊 [1/7] Refreshing Market Opportunities (CW data)...")
    try:
        from backend.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
        run_quant_pipeline_programmatic(strategy="balanced")
        print("✅ Market opportunities refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing market opportunities: {e}")
        return False


def refresh_stock_history():
    """Refresh stock history data."""
    print("\n📈 [2/7] Refreshing Stock History...")
    try:
        from backend.modules.atc_manager.service import sync_atc_data, get_last_trading_day
        expected_trading_day = get_last_trading_day()
        sync_atc_data(
            sync_type="STOCK",
            trigger_source="MANUAL",
            target_date=expected_trading_day,
            force=True,
        )
        print(f"✅ Stock history refreshed for {expected_trading_day}")
        return True
    except Exception as e:
        print(f"❌ Error refreshing stock history: {e}")
        return False


def refresh_cw_history():
    """Refresh CW history data."""
    print("\n📉 [3/7] Refreshing CW History...")
    try:
        from backend.modules.atc_manager.service import sync_atc_data, get_last_trading_day
        expected_trading_day = get_last_trading_day()
        sync_atc_data(
            sync_type="CW",
            trigger_source="MANUAL",
            target_date=expected_trading_day,
            force=True,
        )
        print(f"✅ CW history refreshed for {expected_trading_day}")
        return True
    except Exception as e:
        print(f"❌ Error refreshing CW history: {e}")
        return False


def refresh_market_indices():
    """Refresh market indices (VNINDEX, VN30, HNXINDEX)."""
    print("\n📊 [4/7] Refreshing Market Indices...")
    try:
        from scripts.data_pipelines.backfill_indices import backfill_index
        indices = ["VNINDEX", "VN30", "HNXINDEX"]
        for idx in indices:
            try:
                backfill_index(idx)
                print(f"   ✅ {idx} refreshed")
            except Exception as e:
                print(f"   ⚠️ {idx} skipped: {e}")
        print("✅ Market indices refresh completed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing market indices: {e}")
        return False


def refresh_macro_data():
    """Refresh macro data (USD/VND, Gold, VIX, Oil)."""
    print("\n💰 [5/7] Refreshing Macro Data...")
    try:
        from backend.modules.regime_analysis.etl.macro_scraper import fetch_macro_indicators
        fetch_macro_indicators()
        print("✅ Macro data refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing macro data: {e}")
        return False


def refresh_derivatives_data():
    """Refresh derivatives data (VN30F1M)."""
    print("\n📈 [6/7] Refreshing Derivatives Data...")
    try:
        from backend.modules.cw_pricing.backtest.fetcher import fetch_derivatives_sentiment
        fetch_derivatives_sentiment()
        print("✅ Derivatives data refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing derivatives data: {e}")
        return False


def refresh_us_indices():
    """Refresh US indices (S&P 500, NASDAQ)."""
    print("\n🇺🇸 [7/12] Refreshing US Indices...")
    try:
        import yfinance as yf
        import pandas as pd
        from backend.core.database import SessionLocal, StockHistoricalPrice
        
        db = SessionLocal()
        try:
            symbols = [
                ("^GSPC", "SPX"),  # S&P 500
                ("^NDX", "NDX")    # NASDAQ 100
            ]
            
            for yf_symbol, db_symbol in symbols:
                try:
                    df = yf.download(yf_symbol, period="5d", progress=False)
                    if df.empty:
                        print(f"   ⚠️ {yf_symbol}: No data")
                        continue
                        
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    latest = df['Close'].dropna().iloc[-1]
                    latest_date = df.index[-1]
                    date_str = latest_date.strftime('%Y-%m-%d')
                    
                    existing = db.query(StockHistoricalPrice).filter(
                        StockHistoricalPrice.symbol == db_symbol,
                        StockHistoricalPrice.date == date_str
                    ).first()
                    
                    if existing:
                        existing.close = float(latest)
                        existing.open = float(df['Open'].dropna().iloc[-1]) if not df['Open'].dropna().empty else float(latest)
                        existing.high = float(df['High'].dropna().iloc[-1]) if not df['High'].dropna().empty else float(latest)
                        existing.low = float(df['Low'].dropna().iloc[-1]) if not df['Low'].dropna().empty else float(latest)
                        existing.volume = float(df['Volume'].dropna().iloc[-1]) if not df['Volume'].dropna().empty else 0.0
                        existing.ref_price = float(latest)
                    else:
                        new_record = StockHistoricalPrice(
                            symbol=db_symbol,
                            date=date_str,
                            open=float(df['Open'].dropna().iloc[-1]) if not df['Open'].dropna().empty else float(latest),
                            high=float(df['High'].dropna().iloc[-1]) if not df['High'].dropna().empty else float(latest),
                            low=float(df['Low'].dropna().iloc[-1]) if not df['Low'].dropna().empty else float(latest),
                            close=float(latest),
                            volume=float(df['Volume'].dropna().iloc[-1]) if not df['Volume'].dropna().empty else 0.0,
                            ref_price=float(latest)
                        )
                        db.add(new_record)
                    
                    db.commit()
                    print(f"   ✅ {db_symbol}: {latest:.2f} ({date_str})")
                    
                except Exception as e:
                    print(f"   ❌ Error fetching {yf_symbol}: {e}")
                    db.rollback()
                    
        finally:
            db.close()
        
        print("✅ US indices refresh completed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing US indices: {e}")
        return False


def refresh_merton_credit_model():
    """Refresh Merton credit risk model data."""
    print("\n🏦 [8/12] Refreshing Merton Credit Risk Model...")
    try:
        from backend.modules.credit_risk.etl.merton_calculator import calculate_merton_for_all_companies
        calculate_merton_for_all_companies()
        print("✅ Merton credit risk model refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing Merton credit model: {e}")
        return False


def refresh_company_distress_analysis():
    """Refresh company distress analysis model."""
    print("\n📉 [9/12] Refreshing Company Distress Analysis...")
    try:
        from backend.modules.credit_risk.etl.distress_analyzer import analyze_all_companies_distress
        analyze_all_companies_distress()
        print("✅ Company distress analysis refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing distress analysis: {e}")
        return False


def refresh_garch_volatility_model():
    """Refresh GARCH volatility model data."""
    print("\n📊 [10/12] Refreshing GARCH Volatility Model...")
    try:
        from backend.modules.regime_analysis.etl.garch_volatility import calculate_garch_for_all_symbols
        calculate_garch_for_all_symbols()
        print("✅ GARCH volatility model refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing GARCH model: {e}")
        return False


def refresh_gamma_exposure_model():
    """Refresh VN30 gamma exposure model."""
    print("\n📈 [11/12] Refreshing VN30 Gamma Exposure Model...")
    try:
        from backend.modules.regime_analysis.etl.gamma_exposure import calculate_vn30_gamma_exposure
        calculate_vn30_gamma_exposure()
        print("✅ VN30 gamma exposure model refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing gamma exposure: {e}")
        return False


def refresh_regime_analysis():
    """Refresh market regime analysis model."""
    print("\n🔄 [12/12] Refreshing Market Regime Analysis...")
    try:
        from backend.modules.regime_analysis.etl.regime_detector import detect_market_regime
        detect_market_regime()
        print("✅ Market regime analysis refreshed")
        return True
    except Exception as e:
        print(f"❌ Error refreshing regime analysis: {e}")
        return False


def check_database_status():
    """Check current status of database data."""
    print("\n📋 Checking Database Status...")
    try:
        import sqlite3
        db_path = os.path.join(BASE_DIR, "data", "finvista.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check market opportunities
        cursor.execute("SELECT MAX(last_updated) FROM market_opportunities")
        opp_update = cursor.fetchone()[0]
        print(f"   Market opportunities last update: {opp_update}")
        
        # Check stock history
        cursor.execute("SELECT MAX(date) FROM stock_history")
        stock_date = cursor.fetchone()[0]
        print(f"   Stock history last date: {stock_date}")
        
        # Check CW history
        cursor.execute("SELECT MAX(date) FROM cw_history")
        cw_date = cursor.fetchone()[0]
        print(f"   CW history last date: {cw_date}")
        
        # Check model data
        cursor.execute("SELECT MAX(date) FROM corporate_merton_credit")
        merton_date = cursor.fetchone()[0]
        print(f"   Merton credit model last date: {merton_date}")
        
        cursor.execute("SELECT MAX(year) FROM company_distress_analysis")
        distress_year = cursor.fetchone()[0]
        print(f"   Company distress analysis last year: {distress_year}")
        
        cursor.execute("SELECT MAX(last_updated) FROM garch_vol_report")
        garch_update = cursor.fetchone()[0]
        print(f"   GARCH volatility model last update: {garch_update}")
        
        cursor.execute("SELECT MAX(date) FROM vn30_gamma_exposure")
        gamma_date = cursor.fetchone()[0]
        print(f"   VN30 gamma exposure last date: {gamma_date}")
        
        cursor.execute("SELECT MAX(timestamp) FROM ai_analysis_memory")
        ai_update = cursor.fetchone()[0]
        print(f"   AI analysis memory last update: {ai_update}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error checking database status: {e}")
        return False


def main():
    """Main function to run all refresh tasks."""
    print("=" * 60)
    print("🔄 FINVISTA REAL-TIME DATA REFRESH")
    print("=" * 60)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check current status
    check_database_status()
    
    # Run all refresh tasks
    results = {
        "market_opportunities": refresh_market_opportunities(),
        "stock_history": refresh_stock_history(),
        "cw_history": refresh_cw_history(),
        "market_indices": refresh_market_indices(),
        "macro_data": refresh_macro_data(),
        "derivatives_data": refresh_derivatives_data(),
        "us_indices": refresh_us_indices(),
        "merton_credit_model": refresh_merton_credit_model(),
        "company_distress_analysis": refresh_company_distress_analysis(),
        "garch_volatility_model": refresh_garch_volatility_model(),
        "gamma_exposure_model": refresh_gamma_exposure_model(),
        "regime_analysis": refresh_regime_analysis(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 REFRESH SUMMARY")
    print("=" * 60)
    for task, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status:12} - {task}")
    
    print(f"\n⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check final status
    print("\n📋 Final Database Status:")
    check_database_status()
    
    total_success = sum(results.values())
    total_tasks = len(results)
    print(f"\n🎯 Overall: {total_success}/{total_tasks} tasks completed")


if __name__ == "__main__":
    main()
