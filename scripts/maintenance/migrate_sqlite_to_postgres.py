# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: SQLITE TO POSTGRESQL DATA MIGRATION TOOL
===================================================
Automates copying schemas and data from the local SQLite database to a PostgreSQL target.
Handles foreign keys, large tables, and updates PostgreSQL primary key sequences.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.database import (
    Base, User, Portfolio, Position, TransactionHistory, PortfolioNavHistory,
    MarketOpportunity, CWHistoricalPrice, StockHistoricalPrice, SMCFeatures,
    AIAnalysisMemory, CorporateNews, CorporateEvent, CompanyDistressAnalysis,
    CompanyFinancial, ScraperState, CorporateMertonCredit, ATCSyncLog,
    DataFreshnessState
)

# Load environment variables
load_dotenv()

# Ordered list of models to migrate (parents first, then children to respect FK constraints)
MODELS_TO_MIGRATE = [
    User,
    Portfolio,
    Position,
    TransactionHistory,
    PortfolioNavHistory,
    MarketOpportunity,
    CWHistoricalPrice,
    StockHistoricalPrice,
    SMCFeatures,
    AIAnalysisMemory,
    CorporateNews,
    CorporateEvent,
    CompanyDistressAnalysis,
    CompanyFinancial,
    ScraperState,
    CorporateMertonCredit,
    ATCSyncLog,
    DataFreshnessState
]

def migrate():
    # 1. Setup Source SQLite Database
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sqlite_db_path = os.path.join(BASE_DIR, "data", "finvista.db")
    sqlite_url = f"sqlite:///{sqlite_db_path}"
    
    if not os.path.exists(sqlite_db_path):
        print(f"❌ Source SQLite database not found at: {sqlite_db_path}")
        return
        
    print(f"🔌 Source SQLite database: {sqlite_url}")
    sqlite_engine = create_engine(sqlite_url)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    # 2. Setup Target PostgreSQL Database
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url or "sqlite" in postgres_url or "user:password@host:port" in postgres_url:
        print("❌ Please configure a valid PostgreSQL DATABASE_URL in your `.env` file.")
        print("Example: DATABASE_URL=postgresql://user:password@localhost:5432/finvista")
        return
        
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)
        
    print(f"🔌 Target PostgreSQL database: {postgres_url}")
    postgres_engine = create_engine(postgres_url)
    
    # 3. Create target schemas in PostgreSQL
    print("🏗️ Creating table schemas in PostgreSQL...")
    Base.metadata.create_all(bind=postgres_engine)
    
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()
    
    try:
        # Disable trigger and check constraints temporarily to speed up and avoid FK errors during batch
        print("⚡ Beginning data migration...")
        
        for model in MODELS_TO_MIGRATE:
            table_name = model.__tablename__
            print(f"📦 Migrating table: '{table_name}'...")
            
            # Query all from SQLite
            sqlite_data = sqlite_session.query(model).all()
            total_records = len(sqlite_data)
            print(f"   - Found {total_records:,} records in SQLite.")
            
            if total_records == 0:
                print("   - Skipping (no data).")
                continue
                
            # Clear existing data in target PostgreSQL (optional, safe fallback)
            postgres_session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            postgres_session.commit()
            
            # Copy objects to postgres (clone attributes to avoid session/instrumentation issues)
            batch_size = 500
            for i in range(0, total_records, batch_size):
                batch = sqlite_data[i:i+batch_size]
                
                for obj in batch:
                    # Extract attributes using SQLAlchemy inspect to clone cleanly
                    from sqlalchemy import inspect
                    attrs = {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}
                    new_obj = model(**attrs)
                    postgres_session.add(new_obj)
                
                postgres_session.commit()
                print(f"   - Inserted records {i+1} to {min(i+batch_size, total_records)}...")
                
            print(f"   ✅ Table '{table_name}' migrated successfully!")
            
        # 4. Synchronize auto-increment sequences for tables with integer primary keys in PostgreSQL
        print("🔄 Resynchronizing PostgreSQL primary key sequences...")
        for model in MODELS_TO_MIGRATE:
            table_name = model.__tablename__
            # Check if table has serial key 'id'
            if 'id' in model.__table__.columns:
                seq_query = text(f"""
                    SELECT pg_get_serial_sequence('{table_name}', 'id');
                """)
                seq_name_res = postgres_session.execute(seq_query).fetchone()
                if seq_name_res and seq_name_res[0]:
                    seq_name = seq_name_res[0]
                    reset_query = text(f"""
                        SELECT setval('{seq_name}', COALESCE((SELECT MAX(id)+1 FROM {table_name}), 1), false);
                    """)
                    postgres_session.execute(reset_query)
                    postgres_session.commit()
                    print(f"   - Reset sequence for '{table_name}' using: {seq_name}")

        print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        postgres_session.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    migrate()
