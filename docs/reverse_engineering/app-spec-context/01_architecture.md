# 01. System Overview - FinLens Clone Specification

## 📋 Mục Tiêu Hệ Thống

**FinLens Clone** là nền tảng phân tích tài chính định lượng chuyên nghiệp dành cho thị trường chứng quyền Việt Nam, cung cấp các công cụ trực quan hóa dữ liệu và phân tích chuyên sâu để hỗ trợ nhà đầu tư ra quyết định giao dịch.

### Đối tượng sử dụng
- **Nhà đầu tư cá nhân**: Cần công cụ phân tích CW chuyên sâu
- **Trader chuyên nghiệp**: Cần tín hiệu giao dịch thời gian thực  
- **Quỹ đầu tư**: Cần phân tích rủi ro và tối ưu danh mục
- **Nhà phân tích tài chính**: Cần công cụ backtest và research

### Giá trị cốt lõi
- **Dashboard trực quan**: Scatter plot, Pareto chart phân bổ CW
- **DeepFinLens Matrix**: Ma trận 10x10 phân tích cơ hội theo regime
- **Sector Analysis**: Phân tích dòng tiền ngành và OLS projection
- **Real-time signals**: Cảnh báo giao dịch qua WebSocket

---

## 🏗️ Techstack Đề Xuất

### Frontend Stack
```yaml
Framework: Next.js 14+ (App Router)
Language: TypeScript
Styling: TailwindCSS
State Management: Zustand / React Context
Data Visualization: 
  - D3.js (cho custom charts)
  - Recharts (cho standard charts)
  - React-Flow (cho matrix visualization)
HTTP Client: Axios
Real-time: WebSocket Client
```

### Backend Stack
```yaml
Framework: FastAPI
Language: Python 3.11+
Database: PostgreSQL (Supabase)
ORM: SQLAlchemy
Authentication: JWT + OAuth2
WebSocket: FastAPI WebSocket
Task Queue: Celery + Redis
API Documentation: OpenAPI/Swagger
```

### Infrastructure Stack
```yaml
Hosting: 
  - Frontend: Vercel
  - Backend: Render.com / Railway
Database: Supabase PostgreSQL
CDN: Cloudflare
Monitoring: Sentry + Prometheus
CI/CD: GitHub Actions
```

### ML/AI Stack
```yaml
ML Framework: scikit-learn, XGBoost
Quant Libraries: 
  - scipy (tính toán scientific)
  - numpy (matrix operations)
  - pandas (data manipulation)
Option Pricing: 
  - Black-Scholes implementation
  - SABR volatility surface
  - Monte Carlo simulation
```

---

## 🔄 Luồng Đi Tổng Thể (High-Level Flow)

```
┌─────────────────────────────────────────────────────────────┐
│                     USER LAYER                              │
├─────────────────────────────────────────────────────────────┤
│  Browser (Next.js) → Mobile App (React Native)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP/WebSocket
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   API GATEWAY LAYER                         │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Routes → Auth Middleware → Rate Limiting           │
│  WebSocket Manager → Request Validation                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   BUSINESS LOGIC LAYER                      │
├─────────────────────────────────────────────────────────────┤
│  CW Pricing Engine │ Regime Analysis │ Credit Risk          │
│  Portfolio Optimizer │ AI Committee │ Trading Engine         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL │ Redis Cache │ Market Data APIs                 │
│  ML Models (.pkl) │ Historical Data Storage                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧩 Các Module Chính

### 1. **Dashboard Module**
- **Scatter Plot Visualization**: Phân bổ CW theo Delta vs Premium
- **Pareto Chart Analysis**: Phân tích 80/20 cơ hội
- **Real-time CW Monitoring**: Cập nhật giá live
- **Color-coded Signals**: Xanh (mua), Đỏ (bán), Vàng (giữ)

### 2. **DeepFinLens Module**
- **Matrix Visualization**: Ma trận 10x10 (Maturity vs Moneyness)
- **Stability Analysis**: Phân tích độ ổn định regime
- **Trend Projection**: Dự báo xu hướng giá
- **Multi-dimensional Radar Chart**: Đa chiều chỉ số
- **Automatic Descriptions**: AI tóm tắt tín hiệu

### 3. **Sector Analysis Module**
- **Sector Ranking Table**: Bảng xếp hạng ngành
- **Cashflow Analysis**: Phân tích dòng tiền ngành
- **OLS Projection**: Dự báo OLS
- **Sector Comparison**: So sánh giữa các ngành

### 4. **User Management Module**
- **Authentication**: Đăng ký/Đăng nhập
- **Subscription Management**: Demo/Client/Client Pro
- **Payment Integration**: VietQR
- **Profile Management**: Quản lý thông tin

### 5. **Data Pipeline Module**
- **Market Data Scraping**: Cào dữ liệu từ SSI/Vietstock
- **News Processing**: Xử lý tin tức doanh nghiệp
- **Historical Data Backfill**: Điền dữ liệu lịch sử
- **Real-time Updates**: WebSocket stream

---

## 🔐 Authentication & Authorization

### User Roles
```yaml
Demo:
  - Access: Dashboard (limited features)
  - Data: Delayed 15 minutes
  - Signals: Basic signals only
  
Client:
  - Access: All modules except DeepFinLens
  - Data: Real-time
  - Signals: All signals
  
Client Pro:
  - Access: All modules including DeepFinLens
  - Data: Real-time + historical
  - Signals: All signals + AI recommendations
  - API Access: REST API key
```

### Auth Flow
```
1. User đăng ký → Email verification
2. Login → JWT token issued (access + refresh)
3. Token stored in httpOnly cookie
4. Each request includes Bearer token
5. Token refresh every 15 minutes
6. Logout → Token invalidation
```

---

## 📊 Data Flow Architecture

### Real-time Data Flow
```
Market Sources (SSI/Vietstock)
    ↓
WebSocket Stream
    ↓
Redis Cache (TTL: 5 seconds)
    ↓
WebSocket Broadcast → Connected Clients
    ↓
Frontend State Update → Re-render Charts
```

### Historical Data Flow
```
Scheduled Jobs (Celery)
    ↓
Data Scraping & Processing
    ↓
PostgreSQL Bulk Insert
    ↓
Materialized Views Refresh
    ↓
API Query Optimization
```

---

## 🎯 Non-Functional Requirements

### Performance
- **API Response Time**: < 200ms (p95)
- **WebSocket Latency**: < 100ms
- **Page Load Time**: < 2 seconds
- **Chart Render Time**: < 500ms

### Scalability
- **Concurrent Users**: 1,000+ (initial)
- **Data Volume**: 10,000+ CW symbols
- **Historical Data**: 5+ years
- **API Requests**: 10,000+ per day

### Security
- **Data Encryption**: TLS 1.3
- **Password Hashing**: bcrypt
- **SQL Injection Prevention**: ORM parameterized queries
- **XSS Protection**: Content Security Policy
- **Rate Limiting**: 100 req/min per user

### Reliability
- **Uptime**: 99.5%+
- **Data Backup**: Daily automated backups
- **Error Monitoring**: Sentry integration
- **Health Checks**: /health endpoint

---

## 🚀 Deployment Architecture

### Development Environment
```yaml
Frontend: localhost:3000 (Next.js dev server)
Backend: localhost:8000 (FastAPI with auto-reload)
Database: PostgreSQL (Docker container)
Redis: Docker container
```

### Production Environment
```yaml
Frontend: Vercel (automatic deployments)
Backend: Render.com (auto-scaling)
Database: Supabase (managed PostgreSQL)
CDN: Cloudflare (global edge caching)
Monitoring: Sentry + Vercel Analytics
```

---

## 📈 Monitoring & Observability

### Metrics to Track
- **User Engagement**: DAU/MAU, session duration
- **System Performance**: API latency, error rates
- **Business Metrics**: Conversion rate, churn rate
- **Data Quality**: Scraping success rate, data freshness

### Alerting Rules
- **API Error Rate** > 5% → PagerDuty alert
- **Database Connection Pool** > 80% → Warning
- **WebSocket Disconnections** > 10% → Investigation
- **Data Scraping Failure** → Immediate alert

---

## 🔄 Development Phases

### Phase 1: MVP (4-6 weeks)
- Basic Dashboard with static data
- User authentication
- CW pricing engine
- Basic charts (Scatter, Pareto)

### Phase 2: Core Features (6-8 weeks)
- Real-time WebSocket integration
- DeepFinLens Matrix
- Sector Analysis
- Subscription management

### Phase 3: Advanced Features (8-10 weeks)
- AI Committee integration
- Portfolio optimization
- Advanced backtesting
- Mobile app (React Native)

### Phase 4: Scale & Optimize (Ongoing)
- Performance optimization
- Additional data sources
- ML model improvements
- Internationalization
