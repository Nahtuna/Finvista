# 🔄 FINVISTA DATA FLOW ARCHITECTURE

## 📊 VẤN ĐỀ HIỆN TẠI

### 1. Data Flow Rời Rạc
- **Mỗi trang fetch data riêng biệt:**
  - HomePage: `getOpportunities`, `getPortfolio`, `getUnderlyingMarket`, `getMarketRegime`, `getFireantArticles`
  - WatchlistPage: `getOpportunities` riêng
  - OpportunitiesPage: `getOpportunities`, `getUnderlyingMarket` riêng
  - WarrantDetailPage: `getOpportunities`, `getUnderlyingMarket` riêng
  - PortfolioPage: `getPortfolio` riêng
  - MarketPage: `getUnderlyingMarket`, `getOpportunities`, `getMarketRegime` riêng

### 2. Không Có Central Data Store
- Mỗi component có `useState` riêng
- Không có global state management
- Data không được chia sẻ giữa các trang

### 3. Cache Logic Không Đồng Bộ
- `market_cache.py` tồn tại nhưng không được sử dụng đồng bộ
- Cache logic chỉ áp dụng cho một số endpoint
- Không có cache invalidation strategy

### 4. Scheduler Không Được Chạy
- `scheduler.py` tồn tại với các job đã cấu hình
- Nhưng có thể không được khởi động
- Data cũ trong DB (market_opportunities: 2026-06-29, stock_history: 2026-06-26)

### 5. Data Không Đồng Bộ
- Chỗ này data hôm nay, chỗ kia data hôm qua
- Không có version control cho data
- Không có data freshness indicator

---

## 🎯 KIẾN TRÚC MỚI ĐỀ XUẤT

### 1. Central Data Store (Global State)

```
┌─────────────────────────────────────────────────────────┐
│                    Central Data Store                     │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ Market Data  │ Portfolio    │ User State   │ Cache  ││
│  │ (Realtime)   │ (Persistent)  │ (Session)    │ (TTL)  ││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
    HomePage          PortfolioPage        WatchlistPage
    OpportunitiesPage  WarrantDetailPage     MarketPage
```

**Benefits:**
- Single source of truth
- Data được chia sẻ giữa các trang
- Automatic synchronization
- Cache invalidation centralized

### 2. Data Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                        │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ Components   │ Hooks        │ Context      │ Utils  ││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘
                         ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ Routes       │ Middleware   │ Validation   │ Cache  ││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                          │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ Market Svc   │ Portfolio Svc│ Model Svc    │ Cache  ││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                            │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ Database     │ External API │ File Storage │ Memory ││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘
```

### 3. Cache Strategy

```
┌─────────────────────────────────────────────────────────┐
│                   Cache Hierarchy                         │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ L1: Memory   │ L2: Redis    │ L3: Database │ L4:    ││
│  │ (5s)         │ (1m)         │ (5m)         │ External││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘
```

**Cache Rules:**
- **Realtime data (trong phiên):** L1 Memory (5s TTL)
- **Near-realtime data (sau phiên):** L2 Redis (1m TTL)
- **Historical data:** L3 Database (5m TTL)
- **External API:** L4 với rate limiting

---

## ⏰ SCHEDULER QUY TRÌNH CHẠY DATA

### 1. Trading Hours (Giờ Giao Dịch)

```
┌─────────────────────────────────────────────────────────┐
│                  PHIÊN SÁNG (09:00 - 11:30)              │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ 08:45        │ 09:00-11:30  │ 11:30-11:45  │ 11:45  ││
│  │ Pre-market   │ Trading      │ Break         │ End    ││
│  │ Cache Reset  │ Realtime     │ Cache         │ Cache  ││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  PHIÊN CHIỀU (13:00 - 15:00)              │
│  ┌──────────────┬──────────────┬──────────────┬────────┐│
│  │ 12:45        │ 13:00-15:00  │ 15:00-15:15  │ 15:15  ││
│  │ Pre-market   │ Trading      │ Post-market   │ EOD    ││
│  │ Cache Reset  │ Realtime     │ ATC Sync      │ Sync   ││
│  └──────────────┴──────────────┴──────────────┴────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2. Scheduler Jobs (Theo Giờ Việt Nam UTC+7)

#### A. Pre-Market Jobs (Trước Phiên)

| Time        | Job                          | Frequency | Description                          |
|-------------|------------------------------|-----------|--------------------------------------|
| 08:45       | Cache Reset                  | Daily     | Reset cache chuẩn bị phiên mới        |
| 08:50       | Market Indices Update        | Daily     | Update VNINDEX, VN30, HNXINDEX       |
| 08:55       | Macro Data Update            | Daily     | Update USD/VND, Gold, VIX, Oil       |

#### B. Intraday Jobs (Trong Phiên)

| Time        | Job                          | Frequency | Description                          |
|-------------|------------------------------|-----------|--------------------------------------|
| 09:00-11:30 | CW Pricing Scan             | 15m       | BSM, Greeks, G-Score calculation     |
| 09:00-11:30 | Market Data Refresh         | 30s       | Realtime bid/ask, prices            |
| 09:00-11:30 | Portfolio Update             | 1m        | Update portfolio P&L                 |

#### C. Inter-Session Jobs (Nghỉ Trưa)

| Time        | Job                          | Frequency | Description                          |
|-------------|------------------------------|-----------|--------------------------------------|
| 11:45       | Session Cache Save           | Daily     | Save cache cuối phiên sáng            |
| 12:45       | Cache Reset                  | Daily     | Reset cache chuẩn bị phiên chiều     |

#### D. Afternoon Session (Phiên Chiều)

| Time        | Job                          | Frequency | Description                          |
|-------------|------------------------------|-----------|--------------------------------------|
| 13:00-15:00 | CW Pricing Scan             | 15m       | BSM, Greeks, G-Score calculation     |
| 13:00-15:00 | Market Data Refresh         | 30s       | Realtime bid/ask, prices            |
| 13:00-15:00 | Portfolio Update             | 1m        | Update portfolio P&L                 |

#### E. Post-Market Jobs (Sau Phiên)

| Time        | Job                          | Frequency | Description                          |
|-------------|------------------------------|-----------|--------------------------------------|
| 15:15       | ATC/EOD Sync                 | Daily     | Sync giá chốt phiên STOCK + CW       |
| 15:30       | Market Indices Update        | Daily     | Update VNINDEX, VN30, HNXINDEX       |
| 16:00       | Derivatives Update           | Daily     | Update VN30F1M basis, OI, flow      |
| 16:30       | Macro Data Update            | Daily     | Update USD/VND, Gold, VIX, Oil       |
| 17:00       | US Indices Update            | Daily     | Update S&P 500, NASDAQ               |
| 17:30       | Model Refresh                | Daily     | Refresh ML models (GARCH, Merton...)  |

#### F. Off-Hours Jobs (Ngoài Giờ Giao Dịch)

| Time        | Job                          | Frequency | Description                          |
|-------------|------------------------------|-----------|--------------------------------------|
| 02:00 CN    | News Scrape                  | Weekly    | Scrape tin tức incremental            |
| 03:00 CN    | Model Training               | Weekly    | Train/retrain ML models              |
| 04:00 T2-CN | Data Validation             | Daily     | Validate data integrity              |
| 05:00 T2-CN | Backup Database             | Daily     | Backup database                      |

### 3. Data Freshness TTL

| Data Type               | Intraday TTL | EOD TTL | Off-Hours TTL |
|-------------------------|--------------|---------|---------------|
| Market Prices           | 30s          | 5m      | 1h            |
| CW Opportunities        | 1m           | 15m     | 2h            |
| Portfolio P&L           | 1m           | 15m     | 2h            |
| Market Indices          | 1m           | 30m     | 4h            |
| Macro Data              | 5m           | 1h      | 6h            |
| Model Outputs           | 15m          | 1h      | 24h           |
| Historical Data         | N/A          | 1d      | 7d            |

---

## 🔧 IMPLEMENTATION PLAN

### Phase 1: Central Data Store (Priority: HIGH)

**1.1 Create Global Context**
```javascript
// src/app/DataContext.jsx
export const DataContext = createContext({
  marketData: null,
  portfolioData: null,
  userData: null,
  refreshData: () => {},
  dataFreshness: {}
});
```

**1.2 Create Data Provider**
```javascript
// src/app/DataProvider.jsx
export function DataProvider({ children }) {
  const [marketData, setMarketData] = useState(null);
  const [portfolioData, setPortfolioData] = useState(null);
  const [dataFreshness, setDataFreshness] = useState({});
  
  const refreshData = useCallback(async (type = 'all') => {
    // Refresh logic with cache invalidation
  }, []);
  
  return (
    <DataContext.Provider value={{ marketData, portfolioData, refreshData, dataFreshness }}>
      {children}
    </DataContext.Provider>
  );
}
```

**1.3 Update Components to Use Context**
- Remove individual `useState` for data
- Use `useContext(DataContext)`
- Remove duplicate API calls

### Phase 2: Cache Layer (Priority: HIGH)

**2.1 Implement Redis Cache**
```python
# src/infra/cache.py
class RedisCache:
    def get(self, key: str, ttl: int = None)
    def set(self, key: str, value: Any, ttl: int)
    def invalidate(self, pattern: str)
```

**2.2 Add Cache Middleware**
```python
# src/api/middleware/cache.py
@cache_response(ttl=30)  # 30s for realtime data
async def get_market_data():
    pass
```

**2.3 Cache Invalidation Strategy**
- Time-based invalidation (TTL)
- Event-based invalidation (data updates)
- Manual invalidation (admin trigger)

### Phase 3: Enhanced Scheduler (Priority: HIGH)

**3.1 Update Scheduler Configuration**
```python
# src/api/scheduler.py
SCHEDULE_CONFIG = {
    "pre_market": {
        "08:45": "cache_reset",
        "08:50": "market_indices",
        "08:55": "macro_data"
    },
    "intraday_morning": {
        "09:00-11:30": {
            "cw_pricing": "15m",
            "market_data": "30s",
            "portfolio": "1m"
        }
    },
    # ... rest of config
}
```

**3.2 Add Scheduler Health Check**
```python
@router.get("/api/scheduler/status")
def get_scheduler_status():
    return {
        "running": True,
        "last_run": {...},
        "next_run": {...},
        "jobs_status": {...}
    }
```

**3.3 Add Manual Trigger**
```python
@router.post("/api/scheduler/trigger/{job_name}")
def trigger_job(job_name: str):
    # Trigger specific job immediately
```

### Phase 4: Data Freshness Monitoring (Priority: MEDIUM)

**4.1 Add Data Freshness Indicator**
```javascript
// Display data age in UI
<DataFreshnessIndicator 
  type="market" 
  lastUpdate={dataFreshness.market} 
/>
```

**4.2 Add Data Validation**
```python
# Validate data integrity
def validate_data_freshness():
    # Check if data is stale
    # Alert if data is too old
```

**4.3 Add Alerts**
- Alert when data is stale (> 1 hour old)
- Alert when scheduler is not running
- Alert when data validation fails

### Phase 5: WebSocket for Realtime (Priority: MEDIUM)

**5.1 Implement WebSocket**
```python
# src/api/websocket.py
@router.websocket("/ws/market")
async def market websocket(websocket: WebSocket):
    # Push realtime updates
```

**5.2 Frontend WebSocket Client**
```javascript
// Subscribe to realtime updates
useWebSocket('ws://localhost:8000/ws/market', {
  onMessage: (data) => updateMarketData(data)
});
```

---

## 📋 CHECKLIST IMPLEMENTATION

### Immediate (Week 1)
- [ ] Create DataContext and DataProvider
- [ ] Update HomePage to use DataContext
- [ ] Update OpportunitiesPage to use DataContext
- [ ] Update PortfolioPage to use DataContext
- [ ] Add data freshness indicator

### Short-term (Week 2-3)
- [ ] Implement Redis cache layer
- [ ] Add cache middleware to API routes
- [ ] Update scheduler configuration
- [ ] Add scheduler health check endpoint
- [ ] Add manual job trigger endpoint

### Medium-term (Week 4-6)
- [ ] Implement WebSocket for realtime updates
- [ ] Add data validation logic
- [ ] Add stale data alerts
- [ ] Update all components to use DataContext
- [ ] Remove duplicate API calls

### Long-term (Week 7+)
- [ ] Implement data versioning
- [ ] Add data rollback capability
- [ ] Implement advanced caching strategies
- [ ] Add performance monitoring
- [ ] Add analytics for data usage

---

## 🎯 SUCCESS METRICS

### Data Synchronization
- **Target:** < 5s data sync across all pages
- **Current:** Unknown (no measurement)
- **Metric:** Time between data update and UI refresh

### Data Freshness
- **Target:** < 1min data age during trading hours
- **Current:** Up to 1 month old data
- **Metric:** Average data age across all endpoints

### Cache Hit Rate
- **Target:** > 80% cache hit rate
- **Current:** Unknown (no cache monitoring)
- **Metric:** Cache hits / total requests

### Scheduler Reliability
- **Target:** 99.9% scheduler uptime
- **Current:** Unknown (scheduler may not be running)
- **Metric:** Scheduler uptime percentage

---

## 📚 REFERENCE

### Files to Modify
- `src/app/DataContext.jsx` (NEW)
- `src/app/DataProvider.jsx` (NEW)
- `src/infra/cache.py` (NEW)
- `src/api/scheduler.py` (UPDATE)
- `src/api/middleware/cache.py` (NEW)
- `frontend/src/features/home/HomePage.jsx` (UPDATE)
- `frontend/src/features/opportunities/OpportunitiesPage.jsx` (UPDATE)
- `frontend/src/features/portfolio/PortfolioPage.jsx` (UPDATE)
- `frontend/src/features/watchlist/WatchlistPage.jsx` (UPDATE)
- `frontend/src/features/market/MarketPage.jsx` (UPDATE)

### Files to Reference
- `src/infra/market_cache.py` (existing cache logic)
- `src/api/scheduler.py` (existing scheduler)
- `frontend/src/api.js` (existing API calls)

---

## 🚀 NEXT STEPS

1. **Review and approve architecture** - Get stakeholder approval
2. **Start Phase 1 implementation** - Central Data Store
3. **Test data synchronization** - Verify sync across pages
4. **Implement cache layer** - Phase 2
5. **Update scheduler** - Phase 3
6. **Add monitoring** - Phase 4
7. **Implement WebSocket** - Phase 5
8. **Continuous monitoring** - Track success metrics
