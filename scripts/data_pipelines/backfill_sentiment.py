# -*- coding: utf-8 -*-
"""
🔄 FINVISTA: NEWS SENTIMENT BULK BACKFILL UTILITY
===================================================
Pre-calculates and caches sentiment for all corporate news and FireAnt articles 
in the database using AI (with automatic rule-based fallback).
This avoids calling the AI API live during web requests, eliminating rate limit (429) errors.
"""

import os
import sys
import time

# Ensure workspace root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.core.database import SessionLocal, CorporateNews
from backend.modules.news_impact.news_step1_prepare import (
    load_sentiment_cache,
    save_sentiment_cache,
    classify_sentiment,
    check_proxy_online
)
from sqlalchemy import text

def backfill_all_sentiments():
    print("=========================================================================")
    print("      🚀  F I N V I S T A   S E N T I M E N T   B A C K F I L L  🚀      ")
    print("=========================================================================")
    
    db = SessionLocal()
    cache = load_sentiment_cache()
    is_ai_online = check_proxy_online()
    
    print(f"ℹ️ AI Client Online: {is_ai_online}")
    print(f"💾 Current cache size: {len(cache)} items")
    
    # 1. Fetch CorporateNews
    print("\n[1/2] Loading Corporate News from database...")
    corp_news = db.query(CorporateNews).all()
    print(f"   Loaded {len(corp_news)} corporate news articles.")
    
    # 2. Fetch FireAnt Articles
    print("\n[2/2] Loading FireAnt Articles from database...")
    fa_articles = []
    try:
        fa_articles = db.execute(text("SELECT id, title, content FROM fireant_articles")).all()
        print(f"   Loaded {len(fa_articles)} FireAnt articles.")
    except Exception as e:
        print(f"   ⚠️ Could not load fireant_articles (table might not exist yet): {e}")

    total_articles = len(corp_news) + len(fa_articles)
    print(f"\n📊 Total articles to analyze: {total_articles}")
    
    processed = 0
    new_classifications = 0
    
    # Process Corporate News
    for idx, item in enumerate(corp_news):
        news_id = str(item.id)
        if news_id in cache:
            processed += 1
            continue
            
        # Classify
        classify_sentiment(item.id, item.title, item.summary or "", cache, is_ai_online)
        new_classifications += 1
        processed += 1
        
        # Output progress every 10 items
        if new_classifications % 10 == 0:
            print(f"   Processed {processed}/{total_articles} articles... ({new_classifications} new sentiments)")
            save_sentiment_cache(cache)
            # Sleep slightly to prevent aggressive rate limits if AI is online
            if is_ai_online:
                time.sleep(0.5)

    # Process FireAnt Articles
    for idx, item in enumerate(fa_articles):
        # fa_articles query returns (id, title, content)
        art_id = f"fa_{item[0]}"
        if art_id in cache:
            processed += 1
            continue
            
        # Classify
        classify_sentiment(art_id, item[1], item[2] or "", cache, is_ai_online)
        new_classifications += 1
        processed += 1
        
        if new_classifications % 10 == 0:
            print(f"   Processed {processed}/{total_articles} articles... ({new_classifications} new sentiments)")
            save_sentiment_cache(cache)
            if is_ai_online:
                time.sleep(0.5)

    # Final save
    save_sentiment_cache(cache)
    db.close()
    
    print("\n=========================================================================")
    print(f"✅ Backfill completed!")
    print(f"   - Total processed: {processed}")
    print(f"   - New classifications added: {new_classifications}")
    print(f"   - Final sentiment cache size: {len(cache)} items")
    print("=========================================================================")

if __name__ == "__main__":
    backfill_all_sentiments()
