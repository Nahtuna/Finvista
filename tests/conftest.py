# -*- coding: utf-8 -*-
import os
import sys

# Find workspace root containing the 'data' directory
current_dir = os.path.dirname(os.path.abspath(__file__))
while current_dir and not os.path.exists(os.path.join(current_dir, "data")):
    parent = os.path.dirname(current_dir)
    if parent == current_dir:
        break
    current_dir = parent
test_db_path = os.path.join(current_dir, "data", "test_finvista_suite.db")

# Force DATABASE_URL to use this test SQLite DB
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Fixture to clean up the test database before and after the test session."""
    # Cleanup before test session starts
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
                
    # Re-initialize the test database schema
    from backend.core.database import init_db
    init_db()
                
    yield
    
    # Cleanup test database files
    for ext in ["", "-wal", "-shm"]:
        path = test_db_path + ext
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

