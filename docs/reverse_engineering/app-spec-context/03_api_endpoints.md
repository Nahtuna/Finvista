# 03. API Endpoints - FinLens Clone

## 📋 Overview

API endpoints được thiết kế theo RESTful principles với OpenAPI/Swagger documentation. Tất cả endpoints sử dụng JWT authentication và rate limiting.

---

## 🔐 Authentication Endpoints

### POST /api/v1/auth/register
**Mô tả**: Đăng ký user mới

**Request Body**:
```json
{
  "email": "user@example.com",
  "username": "trader123",
  "password": "SecurePass123!",
  "full_name": "Nguyen Van A",
  "phone": "+84912345678"
}
```

**Response** (201):
```json
{
  "success": true,
  "message": "Registration successful. Please check your email to verify.",
  "data": {
    "user_id": "uuid-here",
    "email": "user@example.com",
    "username": "trader123",
    "subscription_tier": "demo",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Error Response** (400):
```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Email already exists",
  "details": {
    "field": "email",
    "constraint": "unique"
  }
}
```

---

### POST /api/v1/auth/login
**Mô tả**: Đăng nhập và nhận JWT tokens

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid-here",
      "email": "user@example.com",
      "username": "trader123",
      "subscription_tier": "client",
      "subscription_expires_at": "2024-12-31T23:59:59Z"
    }
  }
}
```

---

### POST /api/v1/auth/refresh
**Mô tả**: Refresh access token

**Request Headers**:
```
Authorization: Bearer <refresh_token>
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "access_token": "new-access-token",
    "expires_in": 900
  }
}
```

---

### POST /api/v1/auth/logout
**Mô tả**: Đăng xuất và invalidate tokens

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200):
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 📊 CW Data Endpoints

### GET /api/v1/cw/list
**Mô tả**: Lấy danh sách CW đang giao dịch

**Query Parameters**:
- `underlying` (optional): Filter by underlying stock
- `issuer` (optional): Filter by issuer
- `min_days_to_maturity` (optional): Minimum days to maturity
- `max_days_to_maturity` (optional): Maximum days to maturity
- `cw_type` (optional): call/put
- `page` (default: 1): Page number
- `limit` (default: 50): Items per page

**Response** (200):
```json
{
  "success": true,
  "data": {
    "total": 150,
    "page": 1,
    "limit": 50,
    "items": [
      {
        "symbol": "CACB2511",
        "underlying": "ACB",
        "issuer": "SSI",
        "cw_type": "call",
        "strike_price": 25.5,
        "maturity_date": "2025-11-20",
        "days_to_maturity": 120,
        "conversion_ratio": 1.0,
        "issue_price": 1.5,
        "is_active": true
      }
    ]
  }
}
```

---

### GET /api/v1/cw/{symbol}
**Mô tả**: Lấy chi tiết một CW

**Response** (200):
```json
{
  "success": true,
  "data": {
    "symbol": "CACB2511",
    "underlying": "ACB",
    "issuer": "SSI",
    "cw_type": "call",
    "strike_price": 25.5,
    "maturity_date": "2025-11-20",
    "days_to_maturity": 120,
    "conversion_ratio": 1.0,
    "issue_price": 1.5,
    "listing_date": "2024-05-15",
    "last_trade_date": "2025-11-19",
    "listed_volume": 10000000,
    "is_active": true,
    "current_market_data": {
      "close_price": 2.3,
      "change_pct": 5.2,
      "volume": 150000,
      "turnover": 345000000,
      "bid_price": 2.25,
      "ask_price": 2.35,
      "ref_price": 2.19
    },
    "analytics": {
      "theoretical_price": 2.15,
      "intrinsic_value": 0.5,
      "premium_pct": 15.2,
      "delta": 0.65,
      "gamma": 0.08,
      "theta": -0.02,
      "vega": 0.15,
      "implied_volatility": 0.35,
      "historical_volatility": 0.28,
      "prob_itm": 0.72,
      "upside_pct": 25.5,
      "opportunity_score": 78.5,
      "decision_signal": "buy"
    }
  }
}
```

---

### GET /api/v1/cw/{symbol}/history
**Mô tả**: Lấy lịch sử giá CW

**Query Parameters**:
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `interval` (default: daily): daily, hourly

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2024-01-15T09:00:00Z",
      "open_price": 2.1,
      "high_price": 2.4,
      "low_price": 2.05,
      "close_price": 2.3,
      "volume": 150000,
      "turnover": 345000000
    }
  ]
}
```

---

### GET /api/v1/cw/dashboard
**Mô tả**: Lấy dữ liệu dashboard (Scatter plot, Pareto chart)

**Query Parameters**:
- `strategy` (default: balanced): balanced, safe, aggressive
- `min_score` (optional): Minimum opportunity score
- `max_premium` (optional): Maximum premium percentage

**Response** (200):
```json
{
  "success": true,
  "data": {
    "scatter_data": [
      {
        "symbol": "CACB2511",
        "x": 0.65,
        "y": 15.2,
        "size": 150000,
        "color": "#4CAF50",
        "opportunity_score": 78.5,
        "decision_signal": "buy"
      }
    ],
    "pareto_data": [
      {
        "symbol": "CACB2511",
        "expected_return": 25.5,
        "cumulative_return": 25.5,
        "rank": 1
      }
    ],
    "summary": {
      "total_cw": 150,
      "buy_signals": 45,
      "sell_signals": 30,
      "hold_signals": 75,
      "avg_opportunity_score": 65.2
    }
  }
}
```

---

## 🌊 DeepFinLens Endpoints

### GET /api/v1/deepfinlens/matrix
**Mô tả**: Lấy ma trận DeepFinLens 10x10

**Query Parameters**:
- `timestamp` (optional): Specific timestamp (default: latest)

**Response** (200):
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T15:00:00Z",
    "matrix": [
      {
        "maturity_bucket": 1,
        "moneyness_bucket": 1,
        "cw_count": 5,
        "avg_opportunity_score": 85.2,
        "avg_stability_score": 72.5,
        "avg_delta": 0.85,
        "avg_premium_pct": 12.3,
        "cell_category": "high_opportunity",
        "recommendation": "buy",
        "trend_3d": "up",
        "trend_7d": "up",
        "trend_30d": "sideways"
      }
    ],
    "summary": {
      "total_cells": 100,
      "active_cells": 78,
      "high_opportunity_cells": 12,
      "avg_matrix_score": 68.5
    }
  }
}
```

---

### GET /api/v1/deepfinlens/matrix/{maturity_bucket}/{moneyness_bucket}
**Mô tả**: Lấy chi tiết một ô trong ma trận

**Response** (200):
```json
{
  "success": true,
  "data": {
    "maturity_bucket": 1,
    "moneyness_bucket": 1,
    "cw_list": [
      {
        "symbol": "CACB2511",
        "opportunity_score": 85.2,
        "stability_score": 72.5,
        "decision_signal": "buy"
      }
    ],
    "cell_analysis": {
      "avg_delta": 0.85,
      "avg_premium_pct": 12.3,
      "volatility_regime": "high",
      "trend_strength": "strong"
    }
  }
}
```

---

### GET /api/v1/deepfinlens/classification
**Mô tả**: Lấy phân loại CW theo DeepFinLens

**Query Parameters**:
- `category` (optional): Filter by category

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "symbol": "CACB2511",
      "category": "high_delta_low_premium",
      "subcategory": "aggressive_growth",
      "confidence": 0.85,
      "key_factors": ["strong_underlying_trend", "low_iv", "good_liquidity"]
    }
  ]
}
```

---

## 🏢 Sector Analysis Endpoints

### GET /api/v1/sectors
**Mô tả**: Lấy danh sách các ngành

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "sector_name": "Banking",
      "current_rank": 1,
      "avg_change_pct": 2.5,
      "total_turnover": 15000000000,
      "net_cash_flow": 5000000000,
      "cash_flow_ratio": 1.3
    }
  ]
}
```

---

### GET /api/v1/sectors/{sector_name}
**Mô tả**: Lấy chi tiết phân tích ngành

**Response** (200):
```json
{
  "success": true,
  "data": {
    "sector_name": "Banking",
    "current_rank": 1,
    "performance": {
      "avg_change_pct": 2.5,
      "advance_count": 15,
      "decline_count": 3,
      "unchanged_count": 2
    },
    "cashflow": {
      "net_cash_flow": 5000000000,
      "cash_flow_ratio": 1.3,
      "flow_trend": "inflow"
    },
    "ols_projection": {
      "slope": 0.05,
      "intercept": 100.0,
      "r_squared": 0.85,
      "forecast_7d": 2.8,
      "forecast_30d": 8.5
    },
    "top_stocks": [
      {
        "symbol": "ACB",
        "change_pct": 3.2,
        "volume": 5000000
      }
    ]
  }
}
```

---

### GET /api/v1/sectors/rotation
**Mô tả**: Lấy dữ liệu sector rotation

**Response** (200):
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T15:00:00Z",
    "leading_sector": "Banking",
    "lagging_sector": "Real Estate",
    "rotation_signal": "rotate_to_banking",
    "rotation_strength": 0.75,
    "historical_context": {
      "avg_rotation_period_days": 15,
      "current_rotation_days": 12
    }
  }
}
```

---

## 👛 Portfolio Endpoints

### GET /api/v1/portfolio
**Mô tả**: Lấy danh sách portfolio của user

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "id": "portfolio-uuid",
      "name": "Main Portfolio",
      "description": "My main trading portfolio",
      "initial_capital": 100000000,
      "current_capital": 123456789,
      "total_return_pct": 23.46,
      "total_positions": 15,
      "active_positions": 10,
      "created_at": "2024-01-01T00:00:00Z",
      "is_active": true
    }
  ]
}
```

---

### POST /api/v1/portfolio
**Mô tả**: Tạo portfolio mới

**Request Body**:
```json
{
  "name": "Growth Portfolio",
  "description": "Aggressive growth strategy",
  "initial_capital": 50000000
}
```

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "new-portfolio-uuid",
    "name": "Growth Portfolio",
    "initial_capital": 50000000,
    "current_capital": 50000000,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### GET /api/v1/portfolio/{portfolio_id}
**Mô tả**: Lấy chi tiết portfolio

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "portfolio-uuid",
    "name": "Main Portfolio",
    "current_capital": 123456789,
    "initial_capital": 100000000,
    "total_return_pct": 23.46,
    "positions": [
      {
        "id": "position-uuid",
        "symbol": "CACB2511",
        "underlying": "ACB",
        "quantity": 10000,
        "entry_price": 2.1,
        "current_price": 2.3,
        "entry_date": "2024-01-10",
        "unrealized_pnl": 200000,
        "return_pct": 9.52,
        "is_active": true
      }
    ],
    "summary": {
      "total_positions": 15,
      "active_positions": 10,
      "total_unrealized_pnl": 23456789,
      "total_realized_pnl": 5000000,
      "win_rate": 0.65
    }
  }
}
```

---

### POST /api/v1/portfolio/{portfolio_id}/position
**Mô tả**: Thêm position vào portfolio

**Request Body**:
```json
{
  "symbol": "CACB2511",
  "quantity": 10000,
  "entry_price": 2.1,
  "strategy": "volatility_arbitrage",
  "notes": "Strong buy signal from DeepFinLens"
}
```

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "position-uuid",
    "symbol": "CACB2511",
    "quantity": 10000,
    "entry_price": 2.1,
    "total_value": 21000000,
    "entry_date": "2024-01-15T10:30:00Z"
  }
}
```

---

### PUT /api/v1/portfolio/{portfolio_id}/position/{position_id}
**Mô tả**: Cập nhật position (partial close, adjust)

**Request Body**:
```json
{
  "action": "partial_close",
  "quantity": 5000,
  "exit_price": 2.5,
  "notes": "Take partial profit"
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "position-uuid",
    "remaining_quantity": 5000,
    "realized_pnl": 200000,
    "transaction_id": "txn-uuid"
  }
}
```

---

## 💰 Subscription Endpoints

### GET /api/v1/subscription/plans
**Mô tả**: Lấy danh sách gói subscription

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "tier": "demo",
      "name": "Demo Plan",
      "price": 0,
      "duration_days": 0,
      "features": [
        "Basic dashboard access",
        "Delayed data (15 min)",
        "Limited signals"
      ]
    },
    {
      "tier": "client",
      "name": "Client Plan",
      "price": 500000,
      "duration_days": 30,
      "features": [
        "Full dashboard access",
        "Real-time data",
        "All signals",
        "Portfolio management"
      ]
    },
    {
      "tier": "client_pro",
      "name": "Client Pro Plan",
      "price": 1500000,
      "duration_days": 30,
      "features": [
        "All Client features",
        "DeepFinLens access",
        "AI recommendations",
        "API access",
        "Priority support"
      ]
    }
  ]
}
```

---

### POST /api/v1/subscription/checkout
**Mô tả**: Tạo payment checkout

**Request Body**:
```json
{
  "tier": "client",
  "duration_months": 1,
  "payment_method": "vietqr"
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "payment_id": "payment-uuid",
    "amount": 500000,
    "currency": "VND",
    "qr_code_url": "https://api.vietqr.io/...",
    "expiry_minutes": 15,
    "status": "pending"
  }
}
```

---

### GET /api/v1/subscription/status
**Mô tả**: Lấy trạng thái subscription hiện tại

**Response** (200):
```json
{
  "success": true,
  "data": {
    "tier": "client",
    "expires_at": "2024-12-31T23:59:59Z",
    "days_remaining": 15,
    "is_active": true,
    "features": [
      "Full dashboard access",
      "Real-time data",
      "All signals"
    ]
  }
}
```

---

## 🤖 AI Analysis Endpoints

### POST /api/v1/ai/analyze
**Mô tả**: Y cầu AI phân tích một CW

**Request Body**:
```json
{
  "symbol": "CACB2511",
  "analysis_type": "trading_decision"
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "symbol": "CACB2511",
    "decision": "buy",
    "consensus_score": 0.85,
    "confidence_level": 0.78,
    "rationale": "Strong buy signal based on high delta, low premium, and bullish underlying trend",
    "key_factors": [
      {
        "factor": "delta",
        "value": 0.65,
        "weight": 0.3,
        "sentiment": "positive"
      },
      {
        "factor": "premium",
        "value": 15.2,
        "weight": 0.25,
        "sentiment": "positive"
      }
    ],
    "market_context": {
      "regime": "bull",
      "volatility": "moderate",
      "trend": "upward"
    }
  }
}
```

---

### GET /api/v1/ai/memory/{symbol}
**Mô tả**: Lấy lịch sử phân tích AI của một CW

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "decision": "buy",
      "consensus_score": 0.85,
      "is_correct": true,
      "actual_outcome": "profit",
      "max_upside_pct": 15.2
    }
  ]
}
```

---

## 📊 Market Data Endpoints

### GET /api/v1/market/indices
**Mô tả**: Lấy dữ liệu các chỉ số thị trường

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "symbol": "VNINDEX",
      "name": "VN-Index",
      "current_value": 1250.5,
      "change_pct": 1.2,
      "volume": 500000000,
      "turnover": 15000000000000
    },
    {
      "symbol": "VN30",
      "name": "VN30",
      "current_value": 1180.3,
      "change_pct": 0.8,
      "volume": 200000000,
      "turnover": 8000000000000
    }
  ]
}
```

---

### GET /api/v1/market/stock/{symbol}
**Mô tả**: Lấy dữ liệu cổ phiếu cơ sở

**Response** (200):
```json
{
  "success": true,
  "data": {
    "symbol": "ACB",
    "company_name": "Asia Commercial Bank",
    "sector": "Banking",
    "current_price": 25.5,
    "change_pct": 2.1,
    "volume": 5000000,
    "turnover": 127500000000,
    "market_cap": 50000000000000,
    "regime": {
      "current_regime": "bull",
      "regime_probability": 0.75,
      "trend_strength": "strong"
    }
  }
}
```

---

## 🔔 WebSocket Endpoints

### WS /api/v1/ws
**Mô tả**: WebSocket connection cho real-time data

**Connection**:
```
wss://api.finlensclone.com/api/v1/ws
```

**Authentication**: Query parameter `?token=<access_token>`

**Message Format (Client → Server)**:
```json
{
  "action": "subscribe",
  "channels": ["cw_prices", "market_data", "signals"]
}
```

**Message Format (Server → Client)**:
```json
{
  "channel": "cw_prices",
  "data": {
    "symbol": "CACB2511",
    "price": 2.3,
    "change_pct": 5.2,
    "volume": 150000,
    "timestamp": "2024-01-15T15:30:00Z"
  }
}
```

**Available Channels**:
- `cw_prices`: Real-time CW price updates
- `market_data`: Market indices and stock prices
- `signals`: Trading signals and alerts
- `portfolio_updates`: User portfolio changes
- `ai_analysis`: AI analysis updates

---

## 📋 System Endpoints

### GET /health
**Mô tả**: Health check endpoint

**Response** (200):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T15:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "websocket": "healthy",
    "external_apis": "healthy"
  }
}
```

---

### GET /api/v1/docs
**Mô tả**: Swagger UI documentation

**Response**: HTML page with interactive API documentation

---

## 🔒 Rate Limiting

**Default Limits**:
- **Anonymous**: 100 requests/minute
- **Authenticated**: 1000 requests/minute
- **WebSocket**: 100 messages/second

**Rate Limit Headers**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1642245600
```

**Rate Limit Exceeded Response** (429):
```json
{
  "success": false,
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

---

## 🚨 Error Responses

### Standard Error Format
```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "field_name",
    "value": "invalid_value"
  },
  "timestamp": "2024-01-15T15:30:00Z"
}
```

### Common Error Codes
- `VALIDATION_ERROR`: Invalid request data
- `AUTHENTICATION_ERROR`: Invalid or missing credentials
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error
- `SERVICE_UNAVAILABLE`: External service down

---

## 📝 Response Standards

### Pagination
```json
{
  "success": true,
  "data": {
    "total": 150,
    "page": 1,
    "limit": 50,
    "total_pages": 3,
    "items": []
  }
}
```

### Date/Time Format
- All timestamps in ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`
- Timezone: UTC

### Number Formatting
- Prices: 2 decimal places
- Percentages: 2 decimal places
- Volume: Integer
- Large numbers: No commas (JSON standard)

---

## 🔐 Security Headers

All API responses include:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

---

## 📊 API Versioning

- Current version: `v1`
- Version in URL: `/api/v1/...`
- Backward compatibility maintained for 12 months
- Deprecation warnings in response headers:
```
X-API-Deprecation: This endpoint will be deprecated on 2025-01-01
X-API-Deprecated-By: /api/v2/cw/list
```
