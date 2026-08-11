# -*- coding: utf-8 -*-
"""Integration tests for database operations."""

import pytest
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.database import (
    Base, User, Portfolio, 
    Position, TransactionHistory, PortfolioNavHistory, MarketOpportunity
)


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Use the temporary database
    test_db_url = f"sqlite:///{db_path}"
    
    # Create a new engine for the test database
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create a test session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    try:
        os.close(db_fd)
        os.unlink(db_path)
    except Exception:
        pass  # Handle case where file might already be deleted


def test_create_user(test_db):
    """Test creating a user in the database."""
    user = User(
        username="test_user",
        hashed_password="hashed_password_here"
    )
    test_db.add(user)
    test_db.commit()
    
    retrieved_user = test_db.query(User).filter(User.username == "test_user").first()
    assert retrieved_user is not None
    assert retrieved_user.username == "test_user"


def test_user_portfolio_relationship(test_db):
    """Test user-portfolio relationship."""
    user = User(
        username="test_user_portfolio",
        hashed_password="hashed_password_here"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    portfolio = Portfolio(
        user_id=user.id,
        cash=100000000.0,
        initial_cash=100000000.0
    )
    test_db.add(portfolio)
    test_db.commit()
    
    retrieved_user = test_db.query(User).filter(User.username == "test_user_portfolio").first()
    assert retrieved_user.portfolio is not None
    assert retrieved_user.portfolio.cash == 100000000.0


def test_user_positions_relationship(test_db):
    """Test user-positions relationship."""
    user = User(
        username="test_user_positions",
        hashed_password="hashed_password_here"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    position = Position(
        user_id=user.id,
        symbol="CACB2511",
        underlying="ACB",
        qty=100,
        buy_price=1900.0,
        buy_date="2026-08-05 10:00:00",
        settlement_date="2026-08-07 10:00:00",
        total_cost=190000.0
    )
    test_db.add(position)
    test_db.commit()
    
    retrieved_user = test_db.query(User).filter(User.username == "test_user_positions").first()
    assert len(retrieved_user.positions) == 1
    assert retrieved_user.positions[0].symbol == "CACB2511"


def test_transaction_history(test_db):
    """Test transaction history creation."""
    user = User(
        username="test_user_transactions",
        hashed_password="hashed_password_here"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    transaction = TransactionHistory(
        user_id=user.id,
        symbol="CACB2511",
        underlying="ACB",
        type="BUY",
        qty=100,
        price=1900.0,
        value=190000.0,
        fee=190.0,
        date="2026-08-05 10:00:00",
        reason="Test transaction"
    )
    test_db.add(transaction)
    test_db.commit()
    
    retrieved_transaction = test_db.query(TransactionHistory).filter(
        TransactionHistory.user_id == user.id
    ).first()
    assert retrieved_transaction is not None
    assert retrieved_transaction.type == "BUY"
    assert retrieved_transaction.value == 190000.0


def test_market_opportunity(test_db):
    """Test market opportunity creation."""
    opportunity = MarketOpportunity(
        symbol="CACB2511",
        underlying="ACB",
        issuer="SSI",
        price=1900.0,
        price_change_pct=1.5,
        premium_pct=15.5,
        gearing=4.2,
        days_to_maturity=87,
        score=85.0,
        decision_signal="BUY",
        underlying_price=22600.0,
        ratio="1:1",
        strike_price=19832.0,
        volume=50000.0,
        implied_volatility_pct=30.48,
        delta=0.65,
        theta_burn_day=-12.5
    )
    test_db.add(opportunity)
    test_db.commit()
    
    retrieved_opportunity = test_db.query(MarketOpportunity).filter(
        MarketOpportunity.symbol == "CACB2511"
    ).first()
    assert retrieved_opportunity is not None
    assert retrieved_opportunity.score == 85.0
    assert retrieved_opportunity.decision_signal == "BUY"


def test_portfolio_nav_history(test_db):
    """Test portfolio NAV history creation."""
    user = User(
        username="test_user_nav",
        hashed_password="hashed_password_here"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    nav_history = PortfolioNavHistory(
        user_id=user.id,
        total_nav=100500000.0,
        cash=98000000.0,
        positions_value=2500000.0,
        date="2026-08-05 10:00:00"
    )
    test_db.add(nav_history)
    test_db.commit()
    
    retrieved_nav = test_db.query(PortfolioNavHistory).filter(
        PortfolioNavHistory.user_id == user.id
    ).first()
    assert retrieved_nav is not None
    assert retrieved_nav.total_nav == 100500000.0


def test_cascade_delete_user(test_db):
    """Test that deleting a user cascades to related records."""
    user = User(
        username="test_user_cascade",
        hashed_password="hashed_password_here"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Add related records
    portfolio = Portfolio(user_id=user.id, cash=100000000.0, initial_cash=100000000.0)
    position = Position(
        user_id=user.id,
        symbol="CACB2511",
        underlying="ACB",
        qty=100,
        buy_price=1900.0,
        buy_date="2026-08-05 10:00:00",
        settlement_date="2026-08-07 10:00:00",
        total_cost=190000.0
    )
    test_db.add(portfolio)
    test_db.add(position)
    test_db.commit()
    
    # Delete user
    test_db.delete(user)
    test_db.commit()
    
    # Check that related records are deleted
    assert test_db.query(Portfolio).filter(Portfolio.user_id == user.id).first() is None
    assert test_db.query(Position).filter(Position.user_id == user.id).first() is None
