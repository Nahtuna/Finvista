# 02. Database Schema - FinLens Clone

## 📋 Overview

Database schema được thiết kế dựa trên quan sát network traffic và phân tích dữ liệu từ FinLens. Schema sử dụng PostgreSQL với các bảng chính cho users, CW data, market data, và user portfolios.

---

## 👥 User Management Tables

### Table: users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    subscription_tier VARCHAR(20) DEFAULT 'demo' CHECK (subscription_tier IN ('demo', 'client', 'client_pro')),
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### Table: user_sessions
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(500) UNIQUE NOT NULL,
    access_token VARCHAR(500) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_refresh_token ON user_sessions(refresh_token);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);
```

### Table: subscription_payments
```sql
CREATE TABLE subscription_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'VND',
    payment_method VARCHAR(50) DEFAULT 'vietqr',
    transaction_id VARCHAR(100) UNIQUE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    subscription_tier VARCHAR(20) NOT NULL,
    duration_months INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);

CREATE INDEX idx_payments_user_id ON subscription_payments(user_id);
CREATE INDEX idx_payments_status ON subscription_payments(status);
CREATE INDEX idx_payments_created_at ON subscription_payments(created_at);
```

---

## 📊 Covered Warrant (CW) Data Tables

### Table: cw_info
```sql
CREATE TABLE cw_info (
    symbol VARCHAR(20) PRIMARY KEY,
    underlying VARCHAR(10) NOT NULL,
    issuer VARCHAR(50) NOT NULL,
    cw_type VARCHAR(20) CHECK (cw_type IN ('call', 'put')),
    exercise_style VARCHAR(20) DEFAULT 'european',
    duration VARCHAR(20),
    issue_date DATE,
    listing_date DATE,
    first_trade_date DATE,
    last_trade_date DATE,
    maturity_date DATE NOT NULL,
    conversion_ratio DECIMAL(10, 4),
    issue_price DECIMAL(10, 2),
    strike_price DECIMAL(10, 2) NOT NULL,
    listed_volume BIGINT,
    is_active BOOLEAN DEFAULT true,
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cw_info_underlying ON cw_info(underlying);
CREATE INDEX idx_cw_info_issuer ON cw_info(issuer);
CREATE INDEX idx_cw_info_maturity_date ON cw_info(maturity_date);
CREATE INDEX idx_cw_info_is_active ON cw_info(is_active);
```

### Table: cw_market_data
```sql
CREATE TABLE cw_market_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES cw_info(symbol) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_price DECIMAL(10, 2),
    high_price DECIMAL(10, 2),
    low_price DECIMAL(10, 2),
    close_price DECIMAL(10, 2),
    volume BIGINT,
    turnover DECIMAL(20, 2),
    bid_price DECIMAL(10, 2),
    ask_price DECIMAL(10, 2),
    bid_volume BIGINT,
    ask_volume BIGINT,
    ref_price DECIMAL(10, 2),
    change_price DECIMAL(10, 2),
    change_pct DECIMAL(5, 2),
    total_volume BIGINT,
    total_turnover DECIMAL(20, 2),
    CONSTRAINT unique_cw_time UNIQUE (symbol, timestamp)
);

CREATE INDEX idx_cw_market_symbol ON cw_market_data(symbol);
CREATE INDEX idx_cw_market_timestamp ON cw_market_data(timestamp);
CREATE INDEX idx_cw_market_symbol_time ON cw_market_data(symbol, timestamp DESC);
```

### Table: cw_analytics
```sql
CREATE TABLE cw_analytics (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES cw_info(symbol) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Pricing metrics
    intrinsic_value DECIMAL(10, 2),
    theoretical_price DECIMAL(10, 2),
    break_even_price DECIMAL(10, 2),
    premium_pct DECIMAL(5, 2),
    
    -- Greeks
    delta DECIMAL(5, 4),
    gamma DECIMAL(5, 4),
    theta DECIMAL(5, 4),
    vega DECIMAL(5, 4),
    rho DECIMAL(5, 4),
    
    -- Volatility
    implied_volatility DECIMAL(5, 4),
    historical_volatility DECIMAL(5, 4),
    garch_volatility DECIMAL(5, 4),
    
    -- Probability metrics
    prob_itm DECIMAL(5, 4),
    upside_pct DECIMAL(5, 2),
    downside_pct DECIMAL(5, 2),
    
    -- Risk metrics
    risk_monthly_pct DECIMAL(5, 2),
    moneyness_category VARCHAR(20),
    
    -- Regime analysis
    regime_score DECIMAL(5, 2),
    stability_score DECIMAL(5, 2),
    
    -- Opportunity score (DeepFinLens)
    opportunity_score DECIMAL(5, 2),
    decision_signal VARCHAR(20) CHECK (decision_signal IN ('buy', 'sell', 'hold', 'neutral')),
    
    CONSTRAINT unique_cw_analytics_time UNIQUE (symbol, timestamp)
);

CREATE INDEX idx_cw_analytics_symbol ON cw_analytics(symbol);
CREATE INDEX idx_cw_analytics_timestamp ON cw_analytics(timestamp);
CREATE INDEX idx_cw_analytics_opportunity_score ON cw_analytics(opportunity_score);
CREATE INDEX idx_cw_analytics_decision_signal ON cw_analytics(decision_signal);
```

---

## 📈 Underlying Stock Data Tables

### Table: stock_info
```sql
CREATE TABLE stock_info (
    symbol VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(200),
    sector VARCHAR(50),
    industry VARCHAR(100),
    market VARCHAR(20) CHECK (market IN ('HOSE', 'HNX', 'UPCOM')),
    listed_date DATE,
    outstanding_shares BIGINT,
    market_cap DECIMAL(20, 2),
    is_active BOOLEAN DEFAULT true,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_stock_info_sector ON stock_info(sector);
CREATE INDEX idx_stock_info_market ON stock_info(market);
```

### Table: stock_market_data
```sql
CREATE TABLE stock_market_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL REFERENCES stock_info(symbol) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_price DECIMAL(10, 2),
    high_price DECIMAL(10, 2),
    low_price DECIMAL(10, 2),
    close_price DECIMAL(10, 2),
    volume BIGINT,
    turnover DECIMAL(20, 2),
    ref_price DECIMAL(10, 2),
    change_price DECIMAL(10, 2),
    change_pct DECIMAL(5, 2),
    total_volume BIGINT,
    total_turnover DECIMAL(20, 2),
    foreign_buy_volume BIGINT,
    foreign_sell_volume BIGINT,
    CONSTRAINT unique_stock_time UNIQUE (symbol, timestamp)
);

CREATE INDEX idx_stock_market_symbol ON stock_market_data(symbol);
CREATE INDEX idx_stock_market_timestamp ON stock_market_data(timestamp);
CREATE INDEX idx_stock_market_symbol_time ON stock_market_data(symbol, timestamp DESC);
```

---

## 🏢 Corporate Data Tables

### Table: corporate_financials
```sql
CREATE TABLE corporate_financials (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL REFERENCES stock_info(symbol) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    quarter INTEGER CHECK (quarter IN (1, 2, 3, 4)),
    
    -- Balance sheet
    total_assets DECIMAL(20, 2),
    current_assets DECIMAL(20, 2),
    total_liabilities DECIMAL(20, 2),
    current_liabilities DECIMAL(20, 2),
    total_equity DECIMAL(20, 2),
    retained_earnings DECIMAL(20, 2),
    
    -- Income statement
    net_revenue DECIMAL(20, 2),
    profit_after_tax DECIMAL(20, 2),
    ebit DECIMAL(20, 2),
    interest_expense DECIMAL(20, 2),
    operating_cash_flow DECIMAL(20, 2),
    
    -- Market data
    market_cap DECIMAL(20, 2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_financials UNIQUE (ticker, year, quarter)
);

CREATE INDEX idx_corp_financials_ticker ON corporate_financials(ticker);
CREATE INDEX idx_corp_financials_year ON corporate_financials(year);
```

### Table: corporate_events
```sql
CREATE TABLE corporate_events (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL REFERENCES stock_info(symbol) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    description TEXT,
    impact_score DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_corp_events_ticker ON corporate_events(ticker);
CREATE INDEX idx_corp_events_date ON corporate_events(event_date);
CREATE INDEX idx_corp_events_type ON corporate_events(event_type);
```

### Table: corporate_news
```sql
CREATE TABLE corporate_news (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL REFERENCES stock_info(symbol) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    link TEXT UNIQUE NOT NULL,
    summary TEXT,
    sentiment_score DECIMAL(5, 2),
    category VARCHAR(50),
    source VARCHAR(50) DEFAULT 'Vietstock',
    published_date TIMESTAMP WITH TIME ZONE,
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_corp_news_ticker ON corporate_news(ticker);
CREATE INDEX idx_corp_news_published_date ON corporate_news(published_date);
CREATE INDEX idx_corp_news_sentiment ON corporate_news(sentiment_score);
```

---

## 🌊 Regime Analysis Tables

### Table: regime_data
```sql
CREATE TABLE regime_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL REFERENCES stock_info(symbol) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Regime classification
    regime VARCHAR(20) CHECK (regime IN ('bull', 'bear', 'sideways', 'volatile')),
    regime_probability DECIMAL(5, 4),
    
    -- Technical indicators
    sma_20 DECIMAL(10, 2),
    sma_50 DECIMAL(10, 2),
    ema_12 DECIMAL(10, 2),
    ema_26 DECIMAL(10, 2),
    rsi DECIMAL(5, 2),
    macd DECIMAL(10, 4),
    macd_signal DECIMAL(10, 4),
    bollinger_upper DECIMAL(10, 2),
    bollinger_lower DECIMAL(10, 2),
    
    -- Volatility metrics
    garch_volatility DECIMAL(5, 4),
    historical_volatility_20d DECIMAL(5, 4),
    historical_volatility_60d DECIMAL(5, 4),
    
    -- Trend indicators
    adx DECIMAL(5, 2),
    trend_strength VARCHAR(20),
    
    CONSTRAINT unique_regime_time UNIQUE (symbol, timestamp)
);

CREATE INDEX idx_regime_symbol ON regime_data(symbol);
CREATE INDEX idx_regime_timestamp ON regime_data(timestamp);
CREATE INDEX idx_regime_regime ON regime_data(regime);
```

### Table: deepfinlens_matrix
```sql
CREATE TABLE deepfinlens_matrix (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Matrix dimensions
    maturity_bucket INTEGER CHECK (maturity_bucket BETWEEN 1 AND 10),
    moneyness_bucket INTEGER CHECK (moneyness_bucket BETWEEN 1 AND 10),
    
    -- Matrix cell data
    cw_count INTEGER,
    avg_opportunity_score DECIMAL(5, 2),
    avg_stability_score DECIMAL(5, 2),
    avg_delta DECIMAL(5, 4),
    avg_premium_pct DECIMAL(5, 2),
    
    -- Cell classification
    cell_category VARCHAR(20),
    recommendation VARCHAR(20),
    
    -- Trend data
    trend_3d VARCHAR(10),
    trend_7d VARCHAR(10),
    trend_30d VARCHAR(10),
    
    CONSTRAINT unique_matrix_cell UNIQUE (timestamp, maturity_bucket, moneyness_bucket)
);

CREATE INDEX idx_matrix_timestamp ON deepfinlens_matrix(timestamp);
CREATE INDEX idx_matrix_maturity ON deepfinlens_matrix(maturity_bucket);
CREATE INDEX idx_matrix_moneyness ON deepfinlens_matrix(moneyness_bucket);
```

---

## 🏢 Sector Analysis Tables

### Table: sector_data
```sql
CREATE TABLE sector_data (
    id BIGSERIAL PRIMARY KEY,
    sector_name VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Sector performance
    avg_change_pct DECIMAL(5, 2),
    total_turnover DECIMAL(20, 2),
    advance_count INTEGER,
    decline_count INTEGER,
    unchanged_count INTEGER,
    
    -- Cashflow metrics
    net_cash_flow DECIMAL(20, 2),
    cash_flow_ratio DECIMAL(5, 2),
    
    -- OLS projection
    ols_slope DECIMAL(10, 6),
    ols_intercept DECIMAL(10, 2),
    ols_r_squared DECIMAL(5, 4),
    ols_forecast_7d DECIMAL(5, 2),
    ols_forecast_30d DECIMAL(5, 2),
    
    -- Sector ranking
    rank_position INTEGER,
    rank_score DECIMAL(5, 2),
    
    CONSTRAINT unique_sector_time UNIQUE (sector_name, timestamp)
);

CREATE INDEX idx_sector_name ON sector_data(sector_name);
CREATE INDEX idx_sector_timestamp ON sector_data(timestamp);
CREATE INDEX idx_sector_rank ON sector_data(rank_position);
```

### Table: sector_rotation
```sql
CREATE TABLE sector_rotation (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Rotation metrics
    leading_sector VARCHAR(50),
    lagging_sector VARCHAR(50),
    rotation_signal VARCHAR(20),
    rotation_strength DECIMAL(5, 2),
    
    -- Historical context
    avg_rotation_period_days DECIMAL(5, 2),
    current_rotation_days INTEGER
);

CREATE INDEX idx_sector_rotation_timestamp ON sector_rotation(timestamp);
```

---

## 👛 User Portfolio Tables

### Table: user_portfolios
```sql
CREATE TABLE user_portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    initial_capital DECIMAL(20, 2) DEFAULT 100000000,
    current_capital DECIMAL(20, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_portfolios_user_id ON user_portfolios(user_id);
CREATE INDEX idx_portfolios_is_active ON user_portfolios(is_active);
```

### Table: portfolio_positions
```sql
CREATE TABLE portfolio_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES user_portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    underlying VARCHAR(10),
    
    -- Position details
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10, 2) NOT NULL,
    current_price DECIMAL(10, 2),
    
    -- Trade details
    entry_date DATE NOT NULL,
    exit_date DATE,
    exit_price DECIMAL(10, 2),
    
    -- Performance
    unrealized_pnl DECIMAL(20, 2),
    realized_pnl DECIMAL(20, 2),
    return_pct DECIMAL(5, 2),
    
    -- Strategy metadata
    strategy VARCHAR(50),
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_positions_portfolio_id ON portfolio_positions(portfolio_id);
CREATE INDEX idx_positions_symbol ON portfolio_positions(symbol);
CREATE INDEX idx_positions_is_active ON portfolio_positions(is_active);
```

### Table: portfolio_transactions
```sql
CREATE TABLE portfolio_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES user_portfolios(id) ON DELETE CASCADE,
    position_id UUID REFERENCES portfolio_positions(id) ON DELETE SET NULL,
    
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('buy', 'sell', 'adjust')),
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    total_value DECIMAL(20, 2) NOT NULL,
    fee DECIMAL(10, 2) DEFAULT 0,
    
    transaction_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX idx_transactions_portfolio_id ON portfolio_transactions(portfolio_id);
CREATE INDEX idx_transactions_symbol ON portfolio_transactions(symbol);
CREATE INDEX idx_transactions_date ON portfolio_transactions(transaction_date);
```

---

## 🤖 AI Analysis Tables

### Table: ai_analysis_memory
```sql
CREATE TABLE ai_analysis_memory (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    underlying VARCHAR(10),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- AI decision
    decision VARCHAR(20) CHECK (decision IN ('buy', 'sell', 'hold', 'neutral')),
    consensus_score DECIMAL(5, 2),
    confidence_level DECIMAL(5, 2),
    
    -- Market context at analysis
    price_at_analysis DECIMAL(10, 2),
    underlying_price_at_analysis DECIMAL(10, 2),
    iv_at_analysis DECIMAL(5, 4),
    delta_at_analysis DECIMAL(5, 4),
    days_to_maturity INTEGER,
    
    -- AI reasoning
    rationale_summary TEXT,
    key_factors JSONB,
    
    -- Outcome tracking
    is_correct BOOLEAN,
    actual_outcome VARCHAR(20),
    max_upside_pct DECIMAL(5, 2),
    max_downside_pct DECIMAL(5, 2),
    result_commentary TEXT,
    
    outcome_checked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_ai_memory_symbol ON ai_analysis_memory(symbol);
CREATE INDEX idx_ai_memory_timestamp ON ai_analysis_memory(timestamp);
CREATE INDEX idx_ai_memory_decision ON ai_analysis_memory(decision);
```

---

## 📊 System Monitoring Tables

### Table: api_logs
```sql
CREATE TABLE api_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX idx_api_logs_timestamp ON api_logs(timestamp);
CREATE INDEX idx_api_logs_status_code ON api_logs(status_code);
```

### Table: system_metrics
```sql
CREATE TABLE system_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(20, 6),
    metric_unit VARCHAR(20),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp);
```

---

## 🔧 Database Views

### View: cw_market_summary
```sql
CREATE VIEW cw_market_summary AS
SELECT 
    cw.symbol,
    cw.underlying,
    cw.issuer,
    cw.strike_price,
    cw.maturity_date,
    md.close_price,
    md.change_pct,
    md.volume,
    md.turnover,
    ca.theoretical_price,
    ca.delta,
    ca.implied_volatility,
    ca.opportunity_score,
    ca.decision_signal,
    DATEDIFF(cw.maturity_date, CURRENT_DATE) as days_to_maturity
FROM cw_info cw
LEFT JOIN cw_market_data md ON cw.symbol = md.symbol 
    AND md.timestamp = (
        SELECT MAX(timestamp) FROM cw_market_data WHERE symbol = cw.symbol
    )
LEFT JOIN cw_analytics ca ON cw.symbol = ca.symbol
    AND ca.timestamp = (
        SELECT MAX(timestamp) FROM cw_analytics WHERE symbol = cw.symbol
    )
WHERE cw.is_active = true;
```

### View: user_portfolio_summary
```sql
CREATE VIEW user_portfolio_summary AS
SELECT 
    p.id as portfolio_id,
    p.user_id,
    p.name as portfolio_name,
    p.current_capital,
    p.initial_capital,
    COUNT(pos.id) as total_positions,
    SUM(CASE WHEN pos.is_active THEN 1 ELSE 0 END) as active_positions,
    SUM(pos.unrealized_pnl) as total_unrealized_pnl,
    SUM(pos.realized_pnl) as total_realized_pnl,
    (p.current_capital - p.initial_capital) / p.initial_capital * 100 as total_return_pct
FROM user_portfolios p
LEFT JOIN portfolio_positions pos ON p.id = pos.portfolio_id
WHERE p.is_active = true
GROUP BY p.id, p.user_id, p.name, p.current_capital, p.initial_capital;
```

---

## 🔄 Database Maintenance

### Partitioning Strategy
```sql
-- Partition large tables by time
CREATE TABLE cw_market_data_partitioned (
    LIKE cw_market_data INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Monthly partitions
CREATE TABLE cw_market_data_2024_01 PARTITION OF cw_market_data_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Indexing Strategy
- **Primary Keys**: All tables have UUID/BIGSERIAL primary keys
- **Foreign Keys**: Indexed for JOIN performance
- **Timestamp Columns**: Indexed for time-series queries
- **Frequently Filtered Columns**: Indexed (subscription_tier, is_active, etc.)
- **Composite Indexes**: For common query patterns (symbol + timestamp)

### Data Retention Policy
```sql
-- Delete market data older than 2 years
DELETE FROM cw_market_data 
WHERE timestamp < NOW() - INTERVAL '2 years';

-- Archive old analytics data
DELETE FROM cw_analytics 
WHERE timestamp < NOW() - INTERVAL '1 year';
```

---

## 📊 Database Statistics

### Estimated Storage Requirements
```yaml
cw_market_data: ~50GB/year (assuming 1,000 CWs * 400 trading days * 50 records/day)
stock_market_data: ~30GB/year (assuming 500 stocks * 400 trading days * 20 records/day)
cw_analytics: ~5GB/year
regime_data: ~2GB/year
api_logs: ~10GB/year (assuming 100K requests/day * 365 days)
Total: ~100GB/year initial growth
```

### Query Performance Targets
- **Simple SELECT by ID**: < 10ms
- **JOIN queries with indexes**: < 50ms
- **Time-series range queries**: < 100ms
- **Complex analytics queries**: < 500ms
