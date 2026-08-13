# -*- coding: utf-8 -*-
"""Unit tests for the SQLite-to-PostgreSQL migration tool."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.database import Base, User, Portfolio
from scripts.maintenance.migrate_sqlite_to_postgres import MODELS_TO_MIGRATE

def test_migration_logic(tmp_path):
    """Test that database records are successfully copied between databases."""
    # 1. Setup Source SQLite DB
    src_db_file = tmp_path / "source.db"
    src_url = f"sqlite:///{src_db_file}"
    src_engine = create_engine(src_url)
    Base.metadata.create_all(bind=src_engine)
    
    SrcSession = sessionmaker(bind=src_engine)
    src_session = SrcSession()
    
    # Add dummy source records
    user = User(username="migrate_user", hashed_password="hashed_pw")
    src_session.add(user)
    src_session.commit()
    src_session.refresh(user)
    
    portfolio = Portfolio(user_id=user.id, cash=50000.0, initial_cash=50000.0)
    src_session.add(portfolio)
    src_session.commit()
    
    # Verify records exist in source
    assert src_session.query(User).count() == 1
    assert src_session.query(Portfolio).count() == 1
    
    # 2. Setup Target SQLite DB (acting as a clean target database)
    target_db_file = tmp_path / "target.db"
    target_url = f"sqlite:///{target_db_file}"
    target_engine = create_engine(target_url)
    Base.metadata.create_all(bind=target_engine)
    
    TargetSession = sessionmaker(bind=target_engine)
    target_session = TargetSession()
    
    # Verify target starts empty
    assert target_session.query(User).count() == 0
    assert target_session.query(Portfolio).count() == 0
    
    # 3. Simulate Migration Copy Loop
    try:
        for model in MODELS_TO_MIGRATE:
            sqlite_data = src_session.query(model).all()
            if not sqlite_data:
                continue
                
            for obj in sqlite_data:
                from sqlalchemy import inspect
                attrs = {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}
                new_obj = model(**attrs)
                target_session.add(new_obj)
                
            target_session.commit()
            
        # 4. Assert all items copied correctly to the target DB
        assert target_session.query(User).count() == 1
        assert target_session.query(Portfolio).count() == 1
        
        target_user = target_session.query(User).filter_by(username="migrate_user").first()
        assert target_user is not None
        assert target_user.portfolio is not None
        assert target_user.portfolio.cash == 50000.0
        
    finally:
        src_session.close()
        target_session.close()
        src_engine.dispose()
        target_engine.dispose()
