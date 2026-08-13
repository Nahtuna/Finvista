# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: TIMESCALEDB & BRIN INDEX SETUP TOOL
==============================================
Configures TimescaleDB extension, converts history tables to hypertables,
sets up compression policies, and creates BRIN indexes on the time column.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()

def setup_timescaledb():
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url or "sqlite" in postgres_url or "user:password@host:port" in postgres_url:
        print("❌ Please configure a valid PostgreSQL DATABASE_URL in your `.env` file first.")
        return
        
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)
        
    print(f"🔌 Connecting to PostgreSQL database: {postgres_url}")
    engine = create_engine(postgres_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Try to enable TimescaleDB extension
        print("🔧 Attempting to enable TimescaleDB extension...")
        try:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            session.commit()
            print("   ✅ TimescaleDB extension is active!")
            has_timescale = True
        except Exception as ext_err:
            session.rollback()
            print(f"   ⚠️ TimescaleDB extension installation failed or not supported by your Postgres host: {ext_err}")
            print("   ℹ️ We will fall back to standard PostgreSQL Table Partitioning and BRIN indexes.")
            has_timescale = False

        # 2. Modify date columns from VARCHAR to DATE if needed
        # TimescaleDB hypertables require date/timestamp types for the partition column.
        print("📅 Upgrading date columns to native DATE type in PostgreSQL...")
        for table in ["cw_history", "stock_history"]:
            try:
                # Check current type of 'date' column
                type_query = text(f"""
                    SELECT data_type FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = 'date';
                """)
                res = session.execute(type_query).fetchone()
                if res and res[0] in ['character varying', 'text']:
                    print(f"   - Converting '{table}.date' from VARCHAR/TEXT to DATE...")
                    alter_query = text(f"""
                        ALTER TABLE {table} ALTER COLUMN date TYPE DATE USING date::DATE;
                    """)
                    session.execute(alter_query)
                    session.commit()
                    print(f"   ✅ '{table}.date' is now DATE type.")
                else:
                    print(f"   - '{table}.date' is already a date/timestamp type ({res[0] if res else 'unknown'}).")
            except Exception as e:
                session.rollback()
                print(f"   ❌ Error converting date column in '{table}': {e}")

        # 3. Setup TimescaleDB Hypertables
        if has_timescale:
            print("🏗️ Creating TimescaleDB Hypertables...")
            for table in ["cw_history", "stock_history"]:
                try:
                    # Drop constraints/indexes if necessary as create_hypertable has requirements
                    # Check if already a hypertable
                    check_hyper = text(f"""
                        SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = '{table}';
                    """)
                    is_hyper = session.execute(check_hyper).fetchone()
                    
                    if not is_hyper:
                        # Drop primary key constraint since hypertables require PK to include the partitioning column (date)
                        print(f"   - Adapting primary key constraint for '{table}'...")
                        session.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_pkey CASCADE;"))
                        session.execute(text(f"ALTER TABLE {table} ADD PRIMARY KEY (id, date);"))
                        session.commit()

                        print(f"   - Registering '{table}' as a hypertable partitioned by 'date'...")
                        session.execute(text(f"SELECT create_hypertable('{table}', 'date', if_not_exists => TRUE);"))
                        session.commit()
                        print(f"   ✅ Table '{table}' successfully transformed to a TimescaleDB Hypertable!")
                    else:
                        print(f"   - Table '{table}' is already a hypertable.")
                except Exception as e:
                    session.rollback()
                    print(f"   ❌ Error creating hypertable for '{table}': {e}")
                    
            # 4. Configure TimescaleDB Compression Policies
            print("💾 Configuring Compression Policies (90-day retention)...")
            for table in ["cw_history", "stock_history"]:
                try:
                    print(f"   - Enabling compression on table '{table}'...")
                    session.execute(text(f"""
                        ALTER TABLE {table} SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'symbol'
                        );
                    """))
                    session.commit()
                    
                    # Add policy
                    session.execute(text(f"""
                        SELECT add_compression_policy('{table}', INTERVAL '90 days', if_not_exists => TRUE);
                    """))
                    session.commit()
                    print(f"   ✅ Compression policy added for '{table}' successfully!")
                except Exception as e:
                    session.rollback()
                    print(f"   ❌ Error setting compression policy for '{table}': {e}")
                    
        # 5. Setup BRIN (Block Range Index) for PostgreSQL (native & highly effective for time series)
        print("⚡ Creating BRIN Indexes on date columns...")
        for table in ["cw_history", "stock_history"]:
            try:
                index_name = f"idx_{table}_date_brin"
                # Drop existing index if it was standard B-tree
                session.execute(text(f"DROP INDEX IF EXISTS idx_{table}_date;"))
                session.execute(text(f"DROP INDEX IF EXISTS {index_name};"))
                
                # Create BRIN Index
                print(f"   - Creating BRIN index on '{table}(date)'...")
                session.execute(text(f"""
                    CREATE INDEX {index_name} ON {table} USING BRIN (date);
                """))
                session.commit()
                print(f"   ✅ Created BRIN index '{index_name}'!")
            except Exception as e:
                session.rollback()
                print(f"   ❌ Error creating BRIN index for '{table}': {e}")
                
        print("\n🎉 PHASE 2 DATABASE OPTIMIZATIONS APPLIED SUCCESSFULLY!")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Setup failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    setup_timescaledb()
