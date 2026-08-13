# -*- coding: utf-8 -*-
"""
🎬 FINVISTA MAINTENANCE: EXPORT DB FINANCIALS TO CSV
===================================================
Queries all company financials from PostgreSQL or SQLite database
and exports them directly to cleaned_financials.csv.
This allows the credit distress pipeline to run smoothly without web scraping.

Author: samvo
"""

import os
import sys
import pandas as pd

# Add root directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.core.database import SessionLocal, CompanyFinancial
from backend.core import config
from backend.core.utils import logger

def export_db_financials():
    logger.info("⚡ Connecting to database to fetch company financials...")
    session = SessionLocal()
    try:
        # Query all records
        records = session.query(CompanyFinancial).all()
        if not records:
            logger.warning("⚠️  Database table 'company_financials' is empty. No data to export.")
            return False
            
        # Convert ORM objects to dict list
        data = []
        for r in records:
            row = {c.name: getattr(r, c.name) for c in CompanyFinancial.__table__.columns}
            data.append(row)
            
        df = pd.DataFrame(data)
        logger.info(f"✅ Loaded {len(df)} financial records from database.")
        
        # Ensure output directory exists
        output_file = config.CLEANED_FINANCIALS_FILE
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save to CSV
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        logger.info(f"🎉 Successfully exported raw financials to: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to export database financials: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    export_db_financials()
