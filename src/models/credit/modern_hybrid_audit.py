# -*- coding: utf-8 -*-
"""
🧠 FINVISTA 2.0: MODERN HYBRID CREDIT AUDIT (NLP + STRUCTURAL + ML)
==================================================================
This script demonstrates the "Modern" approach to financial distress forecasting
by combining Machine Learning, Structural Models (Merton), and LLM-based 
Qualitative Sentiment Analysis.

It selects the highest risk companies and performs a deep "7-Layer Audit".
"""

import os
import pandas as pd
import numpy as np
import asyncio
import json
import sys

# Add project root to path
sys.path.insert(0, r'C:\Users\samvo\Downloads\Finvista')

from src.common.utils import logger
from src.common import config
from src.common.ai_client import get_ai_client

async def perform_hybrid_audit(top_n=3):
    logger.info(f"🛡️ INITIALIZING FINVISTA 2.0 HYBRID AUDIT FOR TOP {top_n} VULNERABLE COMPANIES")
    
    # 1. Load the existing market health report
    report_file = os.path.join(config.DATA_DIR, "raw", "financial_distress", "market_health_report.csv")
    if not os.path.exists(report_file):
        report_file = os.path.join(config.DATA_DIR, "market_health_report.csv")
        
    if not os.path.exists(report_file):
        logger.error("❌ Market Health Report not found. Please run Step 7 first.")
        return

    report_df = pd.read_csv(report_file)
    # Filter for the most distressed
    distressed = report_df.sort_values("ml_distress_probability", ascending=False).head(top_n)
    
    # 2. Load the full features dataset for deep details
    dataset_file = config.FINAL_DATASET_FILE
    full_df = pd.read_csv(dataset_file)
    
    # 3. Load News context
    news_file = os.path.join(config.DATA_DIR, "raw", "news_data.csv")
    if not os.path.exists(news_file):
        news_file = "data/raw/news_data.csv"
        
    news_df = pd.DataFrame()
    if os.path.exists(news_file):
        news_df = pd.read_csv(news_file)

    ai_client = get_ai_client()
    
    audit_results = []

    for _, row in distressed.iterrows():
        ticker = row['ticker']
        name = row['company_name']
        ml_prob = row['ml_distress_probability']
        z_score = row['altman_z_score']
        
        logger.info(f"🔍 Deep Auditing {ticker} ({name})...")
        
        # Get latest financial details
        ticker_data = full_df[full_df['ticker'] == ticker].sort_values("year").iloc[-1]
        
        # Calculate Merton PD
        merton_pd = ticker_data.get('merton_pd', 0.5)
        merton_dd = ticker_data.get('merton_dd', 0.0)
        
        # Search for news
        relevant_news = []
        if not news_df.empty:
            relevant_news_df = news_df[
                news_df['Title'].str.contains(ticker, case=False, na=False) |
                news_df['Summary'].str.contains(ticker, case=False, na=False) |
                news_df['Title'].str.contains(name[:10], case=False, na=False)
            ].head(5)
            relevant_news = relevant_news_df.to_dict('records')
            
        # AI Qualitative Audit
        prompt = f"""
        Hệ thống phát hiện doanh nghiệp {ticker} ({name}) có rủi ro kiệt quệ tài chính cực cao.
        
        CHỈ SỐ ĐỊNH LƯỢNG:
        - Xác suất vỡ nợ (ML XGBoost): {ml_prob:.2%}
        - Điểm Altman Z-Score: {z_score:.2f}
        - Merton Probability of Default: {merton_pd:.2%}
        - Merton Distance to Default: {merton_dd:.2f}
        - Tỷ lệ Nợ/Tài sản: {ticker_data.get('debt_ratio', 0):.2%}
        - Hệ số thanh toán hiện hành: {ticker_data.get('current_ratio', 0):.2f}
        - Lợi nhuận sau thuế: {ticker_data.get('profit_after_tax', 0):,.0f} VND
        
        TIN TỨC GẦN ĐÂY:
        {json.dumps(relevant_news, ensure_ascii=False) if relevant_news else "Không có tin tức cụ thể."}
        
        NHIỆM VỤ:
        Hãy đóng vai một Chuyên gia Phân tích Rủi ro Tín dụng Cao cấp. 
        1. Phân tích sự mâu thuẫn hoặc đồng thuận giữa các chỉ số (ML vs Merton vs Altman).
        2. Đánh giá rủi ro "chí mạng" dựa trên các con số trên.
        3. Đưa ra kết luận: Doanh nghiệp này có khả năng phục hồi hay đang ở giai đoạn "cuối"?
        4. (Nếu có tin tức) Phân tích tác động của tin tức đến khả năng thanh khoản.
        
        Viết ngắn gọn, chuyên nghiệp, sắc bén, bằng Tiếng Việt.
        """
        
        try:
            # Fix: Use the 'chat' method of AIClient
            audit_text = ai_client.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            audit_text = f"AI Audit failed: {e}"
            
        audit_results.append({
            "ticker": ticker,
            "name": name,
            "quantitative": {
                "ml_prob": ml_prob,
                "z_score": z_score,
                "merton_pd": merton_pd
            },
            "ai_audit": audit_text
        })
        
    # 4. Display
    print("\n" + "═"*100)
    print("🚩 FINVISTA 2.0 - MODERN HYBRID CREDIT AUDIT REPORT")
    print("═"*100)
    
    for res in audit_results:
        print(f"\n🏢 DOANH NGHIỆP: {res['ticker']} - {res['name']}")
        print(f"📊 ML Prob: {res['quantitative']['ml_prob']:.1%} | Z-Score: {res['quantitative']['z_score']:.2f} | Merton PD: {res['quantitative']['merton_pd']:.1%}")
        print(f"🤖 AI EXPERT AUDIT:\n{res['ai_audit']}")
        print("-" * 100)

if __name__ == "__main__":
    asyncio.run(perform_hybrid_audit())
