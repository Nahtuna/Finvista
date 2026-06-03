# -*- coding: utf-8 -*-
"""CSV export, SQLite sync, Telegram alerts, and CLI terminal reporting."""

import os
import sys
import pandas as pd
from datetime import datetime

REPORT_PATH = os.path.join('data', 'excel_cw_report.csv')


def export_csv(df: pd.DataFrame, path: str = REPORT_PATH) -> str:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    df.to_csv(path, index=False)
    print(f'💾 Analysis complete! Full dataset exported successfully to {path}')
    return path


def save_opportunities_to_db(df: pd.DataFrame):
    """Persist quantitative scan results to SQLite Database (market_opportunities table)."""
    try:
        from src.common.database import SessionLocal, MarketOpportunity
        from datetime import datetime
        
        db = SessionLocal()
        try:
            # Clear existing table to perform full reload
            db.query(MarketOpportunity).delete()
            
            for _, row in df.iterrows():
                symbol = str(row.get('A_MaCW', '')).strip().upper()
                if not symbol:
                    continue
                
                opp = MarketOpportunity(
                    symbol=symbol,
                    underlying=row.get('B_MaCPCS'),
                    issuer=row.get('issuer'),
                    price=float(row.get('C_GiaCW', 0.0)) if pd.notna(row.get('C_GiaCW')) else None,
                    price_change_pct=float(row.get('price_change_pct', 0.0)) if pd.notna(row.get('price_change_pct')) else None,
                    intrinsic_value=float(row.get('intrinsic_value', 0.0)) if pd.notna(row.get('intrinsic_value')) else None,
                    break_even_price=float(row.get('M_GiaHL', 0.0)) if pd.notna(row.get('M_GiaHL')) else None,
                    premium_pct=float(row.get('Premium_Pct', 0.0)) if pd.notna(row.get('Premium_Pct')) else None,
                    risk_monthly_pct=float(row.get('risk_monthly_pct', 0.0)) if pd.notna(row.get('risk_monthly_pct')) else None,
                    gearing=float(row.get('F_DonBay', 0.0)) if pd.notna(row.get('F_DonBay')) else None,
                    days_to_maturity=int(row.get('L_Ngay', 0)) if pd.notna(row.get('L_Ngay')) else None,
                    score=float(row.get('G_Score', 0.0)) if pd.notna(row.get('G_Score')) else None,
                    decision_signal=row.get('U_Signal'),
                    
                    underlying_price=float(row.get('hidden_underlying_price', 0.0)) if pd.notna(row.get('hidden_underlying_price')) else None,
                    ratio=str(row.get('hidden_ratio', '1:1')),
                    strike_price=float(row.get('R_Strike', 0.0)) if pd.notna(row.get('R_Strike')) else None,
                    volume=float(row.get('D_Volume', 0.0)) if pd.notna(row.get('D_Volume')) else None,
                    turnover=float(row.get('E_GTGD', 0.0)) if pd.notna(row.get('E_GTGD')) else None,
                    implied_volatility_pct=float(row.get('S_IV_Pct', 0.0)) if pd.notna(row.get('S_IV_Pct')) else None,
                    historical_volatility_pct=float(row.get('S_HV_Pct', 0.0)) if pd.notna(row.get('S_HV_Pct')) else None,
                    delta=float(row.get('T_Delta', 0.0)) if pd.notna(row.get('T_Delta')) else None,
                    gamma=float(row.get('T_Gamma', 0.0)) if pd.notna(row.get('T_Gamma')) else None,
                    theta_burn_day=float(row.get('T_Theta', 0.0)) if pd.notna(row.get('T_Theta')) else None,
                    vega=float(row.get('T_Vega', 0.0)) if pd.notna(row.get('T_Vega')) else None,
                    prob_itm=float(row.get('prob_itm', 0.0)) if pd.notna(row.get('prob_itm')) else None,
                    theoretical_price=float(row.get('theo_price', 0.0)) if pd.notna(row.get('theo_price')) else None,
                    upside_pct=float(row.get('I_Upside', 0.0)) if pd.notna(row.get('I_Upside')) else None,
                    proj_3d_flat_pct=float(row.get('proj_3d_flat_pct', 0.0)) if pd.notna(row.get('proj_3d_flat_pct')) else None,
                    proj_3d_up_pct=float(row.get('proj_3d_up_pct', 0.0)) if pd.notna(row.get('proj_3d_up_pct')) else None,
                    proj_3d_down_pct=float(row.get('proj_3d_down_pct', 0.0)) if pd.notna(row.get('proj_3d_down_pct')) else None,
                    moneyness_category=row.get('K_ITM_OTM'),
                    
                    underlying_distress_prob=float(row.get('underlying_distress_prob', 0.0)) if pd.notna(row.get('underlying_distress_prob')) else None,
                    underlying_is_distressed=int(row.get('underlying_is_distressed', 0)) if pd.notna(row.get('underlying_is_distressed')) else None,
                    underlying_altman_z=float(row.get('underlying_altman_z', 3.0)) if pd.notna(row.get('underlying_altman_z')) else None,
                    last_updated=datetime.utcnow()
                )
                db.add(opp)
            db.commit()
            print("🚀 Successfully synchronized pricing opportunities to finvista.db!")
        except Exception as e:
            db.rollback()
            print(f"⚠️ Failed to save opportunities to SQLite: {e}")
        finally:
            db.close()
    except Exception as e:
         print(f"⚠️ Database import error in run_analysis: {e}")


def print_terminal_report(final_df, args):
    # Calculate market breadth metrics
    active_df = final_df[final_df['C_GiaCW'] > 0]
    up_cnt = len(active_df[active_df['C_GiaCW'] > active_df['ref_price']])
    down_cnt = len(active_df[active_df['C_GiaCW'] < active_df['ref_price']])
    flat_cnt = len(active_df[active_df['C_GiaCW'] == active_df['ref_price']])
    total_cnt = len(final_df)
    print("\n" + "=" * 110)
    print(" 📡 THỐNG KÊ TOÀN CẢNH ĐỘ RỘNG THỊ TRƯỜNG CHỨNG QUYỀN (Market Breadth)")
    print("=" * 110)
    print(f"  Tổng số mã quét: {total_cnt:<3} |  📈 Tăng giá: {up_cnt:<3} |  📉 Giảm giá: {down_cnt:<3} |  ➖ Tham chiếu: {flat_cnt:<3}")
    print("=" * 110)
    
    # Determine limits
    display_limit = len(final_df) if args.all else args.limit
    
    trading_cols = {
        'A_MaCW': 'Mã CW',
        'B_MaCPCS': 'Mã CPCS',
        'issuer': 'TCPH',
        'C_GiaCW': 'Giá CW',
        'price_change_pct': '+/- (%)',
        'intrinsic_value': 'Nội Tại',
        'M_GiaHL': 'Hòa Vốn',
        'Premium_Pct': 'Premium',
        'risk_monthly_pct': 'Độ Rủi Ro',
        'F_DonBay': 'Đòn Bẩy',
        'L_Ngay': 'Đáo Hạn',
        'G_Score': 'Điểm',
        'U_Signal': 'Khuyến Nghị'
    }
    
    quant_cols = {
        'A_MaCW': 'Mã CW',
        'B_MaCPCS': 'Mã CPCS',
        'hidden_underlying_price': 'Giá CPCS',
        'hidden_ratio': 'Tỷ Lệ',
        'R_Strike': 'Giá TH',
        'D_Volume': 'KLGD',
        'E_GTGD': 'GTGD',
        'S_IV_Pct': 'IV',
        'S_HV_Pct': 'HV',
        'T_Delta': 'Delta',
        'T_Theta': 'Θ/Ngày',
        'G_Score': 'Điểm',
        'U_Signal': 'Khuyến Nghị'
    }
    
    forecast_cols = {
        'A_MaCW': 'Mã CW',
        'B_MaCPCS': 'Mã CPCS',
        'C_GiaCW': 'Giá CW',
        'proj_3d_down_pct': 'T+3 Giảm (-2%)',
        'proj_3d_flat_pct': 'T+3 Đi Ngang (0%)',
        'proj_3d_up_pct': 'T+3 Tăng (+2%)',
        'U_Signal': 'Khuyến Nghị'
    }
    
    # Slice the top N warrants for display
    top_df = final_df.head(display_limit).copy()
    
    if args.group_by:
        group_col = 'B_MaCPCS' if args.group_by == 'cpcs' else 'issuer'
        group_label = 'CỔ PHIẾU CƠ SỞ (CPCS)' if args.group_by == 'cpcs' else 'NHÀ PHÁT HÀNH (TCPH)'
        
        print("\n" + "=" * 145)
        print(f" 🏆 VN-QUANT: PHÂN TÍCH NHÓM THEO {group_label}")
        print("=" * 145)
        
        # Group by and print
        grouped = top_df.groupby(group_col, sort=True)
        for g_name, g_df in grouped:
            if g_df.empty:
                continue
                
            clean_g_name = g_name if g_name else "Không xác định"
            print(f"\n📂 Nhóm: {clean_g_name} ({len(g_df)} mã cơ hội)")
            print("-" * 145)
            
            # --- BẢNG 1: THỰC CHIẾN ---
            print("📊 BẢNG 1: THỰC CHIẾN & TÍN HIỆU GIAO DỊCH (Trading View)")
            print("-" * 145)
            table1_df = g_df[list(trading_cols.keys())].copy()
            table1_df['C_GiaCW'] = table1_df['C_GiaCW'].map('{:,.0f}đ'.format)
            table1_df['price_change_pct'] = table1_df['price_change_pct'].map('{:+.1f}%'.format)
            table1_df['intrinsic_value'] = table1_df['intrinsic_value'].map('{:,.0f}đ'.format)
            table1_df['M_GiaHL'] = table1_df['M_GiaHL'].map('{:,.0f}'.format)
            table1_df['Premium_Pct'] = table1_df['Premium_Pct'].map('{:+.1f}%'.format)
            table1_df['risk_monthly_pct'] = table1_df['risk_monthly_pct'].map('{:+.2f}%'.format)
            table1_df['F_DonBay'] = table1_df['F_DonBay'].map('{:.1f}x'.format)
            table1_df['L_Ngay'] = table1_df['L_Ngay'].map('{:.0f}'.format)
            table1_df['G_Score'] = table1_df['G_Score'].map('{:.1f}'.format)
            
            table1_df = table1_df.rename(columns=trading_cols)
            if args.group_by == 'cpcs':
                table1_df = table1_df.drop(columns=['Mã CPCS'], errors='ignore')
            elif args.group_by == 'tcph':
                table1_df = table1_df.drop(columns=['TCPH'], errors='ignore')
            print(table1_df.to_string(index=False))
            print("-" * 145)
            
            # --- BẢNG 2: ĐỊNH LƯỢNG ---
            print("🔬 BẢNG 2: THÔNG SỐ ĐỊNH LƯỢNG & THAM CHIẾU CƠ BẢN (Quant View)")
            print("-" * 145)
            table2_df = g_df[list(quant_cols.keys())].copy()
            table2_df['hidden_underlying_price'] = table2_df['hidden_underlying_price'].map('{:,.0f}đ'.format)
            table2_df['R_Strike'] = table2_df['R_Strike'].map('{:,.0f}đ'.format)
            table2_df['D_Volume'] = table2_df['D_Volume'].map('{:,.0f}'.format)
            table2_df['E_GTGD'] = table2_df['E_GTGD'].map('{:,.1f}tr'.format)
            table2_df['S_IV_Pct'] = table2_df['S_IV_Pct'].map('{:.1f}%'.format)
            table2_df['S_HV_Pct'] = table2_df['S_HV_Pct'].map('{:.1f}%'.format)
            table2_df['T_Delta'] = table2_df['T_Delta'].map('{:.2f}'.format)
            table2_df['T_Theta'] = table2_df['T_Theta'].map(lambda x: f'{x:+.0f}đ' if x != 0 else '0đ')
            table2_df['G_Score'] = table2_df['G_Score'].map('{:.1f}'.format)
            
            table2_df = table2_df.rename(columns=quant_cols)
            if args.group_by == 'cpcs':
                table2_df = table2_df.drop(columns=['Mã CPCS', 'Giá CPCS'], errors='ignore')
            print(table2_df.to_string(index=False))
            print("-" * 145)

            # --- BẢNG 3: DỰ BÁO T+3 ---
            print("🔮 BẢNG 3: DỰ BÁO T+3 THỰC CHIẾN (T+3 Settlement Clearing Forecast)")
            print("-" * 145)
            table3_df = g_df[list(forecast_cols.keys())].copy()
            table3_df['C_GiaCW'] = table3_df['C_GiaCW'].map('{:,.0f}đ'.format)
            table3_df['proj_3d_down_pct'] = table3_df['proj_3d_down_pct'].map('{:+.1f}%'.format)
            table3_df['proj_3d_flat_pct'] = table3_df['proj_3d_flat_pct'].map('{:+.1f}%'.format)
            table3_df['proj_3d_up_pct'] = table3_df['proj_3d_up_pct'].map('{:+.1f}%'.format)
            
            table3_df = table3_df.rename(columns=forecast_cols)
            if args.group_by == 'cpcs':
                table3_df = table3_df.drop(columns=['Mã CPCS'], errors='ignore')
            print(table3_df.to_string(index=False))
            print("-" * 145)
            
    else:
        # Standard list representation
        print("\n" + "=" * 135)
        print(f" 🏆 TOP {display_limit} COVERED WARRANT OPPORTUNITIES (Vietnam Live Market)")
        print("=" * 135)
        
        # ----------------------------------------------------
        # BẢNG 1: THỰC CHIẾN & KHUYẾN NGHỊ (Trading View)
        # ----------------------------------------------------
        print("\n📊 BẢNG 1: THỰC CHIẾN & TÍN HIỆU GIAO DỊCH (Trading View)")
        print("-" * 135)
        table1_df = top_df[list(trading_cols.keys())].copy()
        table1_df['C_GiaCW'] = table1_df['C_GiaCW'].map('{:,.0f}đ'.format)
        table1_df['price_change_pct'] = table1_df['price_change_pct'].map('{:+.1f}%'.format)
        table1_df['intrinsic_value'] = table1_df['intrinsic_value'].map('{:,.0f}đ'.format)
        table1_df['M_GiaHL'] = table1_df['M_GiaHL'].map('{:,.0f}'.format)
        table1_df['Premium_Pct'] = table1_df['Premium_Pct'].map('{:+.1f}%'.format)
        table1_df['risk_monthly_pct'] = table1_df['risk_monthly_pct'].map('{:+.2f}%'.format)
        table1_df['F_DonBay'] = table1_df['F_DonBay'].map('{:.1f}x'.format)
        table1_df['L_Ngay'] = table1_df['L_Ngay'].map('{:.0f}'.format)
        table1_df['G_Score'] = table1_df['G_Score'].map('{:.1f}'.format)
        
        table1_df = table1_df.rename(columns=trading_cols)
        print(table1_df.to_string(index=False))
        print("-" * 135)
        
        # ----------------------------------------------------
        # BẢNG 2: THÔNG SỐ CƠ BẢN & ĐỊNH LƯỢNG (Quant View)
        # ----------------------------------------------------
        print("\n🔬 BẢNG 2: THÔNG SỐ ĐỊNH LƯỢNG & CƠ BẢN (Quant View)")
        print("-" * 135)
        table2_df = top_df[list(quant_cols.keys())].copy()
        table2_df['hidden_underlying_price'] = table2_df['hidden_underlying_price'].map('{:,.0f}đ'.format)
        table2_df['R_Strike'] = table2_df['R_Strike'].map('{:,.0f}đ'.format)
        table2_df['D_Volume'] = table2_df['D_Volume'].map('{:,.0f}'.format)
        table2_df['E_GTGD'] = table2_df['E_GTGD'].map('{:,.1f}tr'.format)
        table2_df['S_IV_Pct'] = table2_df['S_IV_Pct'].map('{:.1f}%'.format)
        table2_df['S_HV_Pct'] = table2_df['S_HV_Pct'].map('{:.1f}%'.format)
        table2_df['T_Delta'] = table2_df['T_Delta'].map('{:.2f}'.format)
        table2_df['T_Theta'] = table2_df['T_Theta'].map(lambda x: f'{x:+.0f}đ' if x != 0 else '0đ')
        table2_df['G_Score'] = table2_df['G_Score'].map('{:.1f}'.format)
        
        table2_df = table2_df.rename(columns=quant_cols)
        print(table2_df.to_string(index=False))
        print("=" * 135)

        # ----------------------------------------------------
        # BẢNG 3: DỰ BÁO T+3 THỰC CHIẾN (T+3 Settlement Clearing Forecast)
        # ----------------------------------------------------
        print("\n🔮 BẢNG 3: DỰ BÁO T+3 THỰC CHIẾN (T+3 Settlement Clearing Forecast)")
        print("-" * 135)
        table3_df = top_df[list(forecast_cols.keys())].copy()
        table3_df['C_GiaCW'] = table3_df['C_GiaCW'].map('{:,.0f}đ'.format)
        table3_df['proj_3d_down_pct'] = table3_df['proj_3d_down_pct'].map('{:+.1f}%'.format)
        table3_df['proj_3d_flat_pct'] = table3_df['proj_3d_flat_pct'].map('{:+.1f}%'.format)
        table3_df['proj_3d_up_pct'] = table3_df['proj_3d_up_pct'].map('{:+.1f}%'.format)
        
        table3_df = table3_df.rename(columns=forecast_cols)
        print(table3_df.to_string(index=False))
        print("=" * 135)


def dispatch_telegram_alerts(final_df):
    # --- TELEGRAM WEBHOOK ALERTS ---
    try:
        from src.common.telegram_alerts import send_telegram_alert_batch, send_credit_distress_alert_batch
        strong_buys = final_df[final_df['U_Signal'] == 'STRONG BUY'].to_dict('records')
        near_expiry = final_df[(final_df['L_Ngay'] < 14) & (final_df['L_Ngay'] > 0)].to_dict('records')
        send_telegram_alert_batch(strong_buys, near_expiry)
        
        # Dispatch credit risk alerts for underlyings in Danger Zone
        distressed_warrants = final_df[final_df['underlying_is_distressed'] == 1]
        if not distressed_warrants.empty:
            unique_underlyings = distressed_warrants['B_MaCPCS'].unique()
            formatted_recs = []
            
            # Retrieve dynamic ML properties calculated during Step 4 mapping
            for ticker in unique_underlyings:
                match_row = distressed_warrants[distressed_warrants['B_MaCPCS'] == ticker].iloc[0]
                
                # Fetch actual live financial metrics from the latest record in final dataset
                # to build high-fidelity natural language commentary for the alert message
                from src.common import config
                distress_file = config.FINAL_DATASET_FILE
                c_ratio = 1.0
                d_ratio = 0.5
                pat_val = 0.0
                ocf_val = 0.0
                icr_val = 9999.0
                if os.path.exists(distress_file):
                    distress_df = pd.read_csv(distress_file)
                    latest_recs = distress_df[distress_df['ticker'] == ticker].sort_values('year')
                    if not latest_recs.empty:
                        last_row = latest_recs.iloc[-1]
                        c_ratio = float(last_row.get('current_ratio', 1.0))
                        d_ratio = float(last_row.get('debt_ratio', 0.5))
                        pat_val = float(last_row.get('profit_after_tax', 0.0))
                        ocf_val = float(last_row.get('operating_cash_flow', 0.0))
                        icr_val = float(last_row.get('ebit_to_interest', 9999.0))
                
                formatted_recs.append({
                    'ticker': ticker,
                    'altman_z_score': float(match_row.get('underlying_altman_z', 0.0)),
                    'xgboost_distress_probability': float(match_row.get('underlying_distress_prob', 0.0)),
                    'current_ratio': c_ratio,
                    'debt_ratio': d_ratio,
                    'profit_after_tax': pat_val,
                    'operating_cash_flow': ocf_val,
                    'ebit_to_interest': icr_val
                })
            send_credit_distress_alert_batch(formatted_recs)
    except Exception as e:
        import sys
        sys.stderr.write(f"\n⚠️ Failed to dispatch Telegram Webhook alerts: {e}\n")
