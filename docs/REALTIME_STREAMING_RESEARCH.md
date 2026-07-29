# Realtime Streaming Research for Vietnam Stock Market

## Overview
Document này tổng hợp nghiên cứu về các nguồn data realtime streaming cho thị trường chứng khoán Việt Nam (HOSE, HNX, UPCOM) để tích hợp vào Finvista.

---

## 1. Official Broker APIs

### 1.1 SSI FastConnect Data

**Type:** WebSocket Streaming + HTTP REST

**WebSocket URL:** 
- Python/.Net: `wss://fc-datahub.ssi.com.vn/v2.0`
- Node.js: `wss://fc-datahub.ssi.com.vn/v2.0`
- Java: `https://fc-datahub.ssi.com.vn/`

**Data Types:**
- **F**: Securities status (trạng thái giao dịch)
- **X**: Best bid/ask (HOSE: 3 levels, HNX/UPCOM/DER: 10 levels)
- **B**:Realtime OHLCV (Open, High, Low, Close, Volume by tick)
- **R**: Foreign room (room nước ngoài)
- **MI**: Index data (VN-Index, VN30, HNX-Index)

**Subscription Format:**
```
F:ALL          # All securities status
X:SSI          # Best bid/ask for SSI
B:SSI-VN30     # OHLCV for SSI and VN30
MI:VN30        # Index data for VN30
MI:ALL         # All indexes
```

**Sample Output (X-Quote):**
```json
{
  "Rtype": "X",
  "MarketID": "HOSE",
  "TradingDate": "28072026",
  "Time": "091500",
  "Symbol": "SSI",
  "Floor": 1,
  "RefPrice": 22.5,
  "Open": 22.8,
  "Close": 22.9,
  "High": 23.0,
  "Low": 22.7,
  "Avg": 22.85,
  "PriorVal": 22.3,
  "LastPrice": 22.9,
  "Change": 0.6,
  "RatioChange": 2.67,
  "EstMatchedPrice": 22.85,
  "LastVol": 100,
  "TotalVal": 1500000,
  "TotalVol": 65000,
  "BidPrice1": 22.85,
  "BidVol1": 500,
  "AskPrice1": 22.9,
  "AskVol1": 300
}
```

**Pros:**
- Official broker API, reliable
- Comprehensive data types
- Real-time streaming
- Good documentation

**Cons:**
- Requires API key/account with SSI
- May have usage limits
- Commercial service (likely paid)

**Documentation:** https://guide.ssi.com.vn/ssi-products/fastconnect-data/streaming-data

---

### 1.2 DNSE Lightspeed API

**Type:** WebSocket Streaming

**Topics (MQTT-style):**
- `MARKET_INDEX`: Chỉ số thị trường
- `STOCK_INFO`: Giá cổ phiếu
- `TOP_PRICE`: Bid/Offer (sổ lệnh)
- `TRADING_SESSION`: Trạng thái phiên
- `OHLC`: Nến giá
- `TICK`: Tick data

**Subscription Format:**
```
plaintext/quotes/stock/SI/{symbol}     # Stock info
plaintext/quotes/stock/TP/{symbol}     # Top price (bid/ask)
plaintext/quotes/index/MI/{marketID}   # Market index
plaintext/quotes/{type}/OHLC/{resolution}/{symbol}  # OHLC
```

**Sample Output (Stock Info):**
```json
{
  "symbol": "SSI",
  "exchangeCode": "HSX",
  "price": 22.9,
  "change": 0.6,
  "percentChange": 2.67,
  "volume": 65000,
  "high": 23.0,
  "low": 22.7,
  "open": 22.8,
  "reference": 22.3
}
```

**Pros:**
- Real-time WebSocket
- Structured JSON format
- Good documentation

**Cons:**
- Requires DNSE account
- Commercial service
- Less widely used than SSI

**Documentation:** https://hdsd.dnse.com.vn/san-pham-dich-vu/lightspeed-api-truoc-krx/

---

## 2. Third-Party Data Providers

### 2.1 Kun Data (StockerAPI)

**Type:** WebSocket + HTTP REST

**Website:** https://kun.pro/stocks-en.html
**Docs:** https://kun.pro/docs-en.html

**Capabilities:**
- Real-time WebSocket API for live prices
- Historical OHLCV/candlestick data
- Snapshot data for watchlists, rankings
- Coverage: HOSE, HNX

**Integration Pattern:**
1. Use HTTP for initialization and historical backfill
2. Use snapshot endpoint for batched market views
3. Use WebSocket for live updates after page load

**Authentication:** Token-based (Bearer token for HTTP, token query for WebSocket)

**Supported Exchanges:**
- HOSE
- HNX

**Pros:**
- Designed for developers
- Clear documentation
- WebSocket + HTTP hybrid approach
- Good for broker dashboards, watchlists, quant tools

**Cons:**
- Commercial service (paid)
- Requires API key
- May have rate limits

**GitHub:** https://github.com/StockerAPI/vietnam-stock-market-api

---

### 2.2 vnstock (vnstock-hq)

**Type:** Python Library with WebSocket Streaming

**GitHub:** https://github.com/vnstock-hq/vnstock-agent-guide

**Streaming Data Types (Standard Schema):**
- `stock`: Giá cổ phiếu cơ sở (real-time match data)
- `stockps`: Giá phái sinh
- `board`: Sổ lệnh cổ phiếu (3 bước giá)
- `boardps`: Sổ lệnh phái sinh (10 bước giá)
- `index`: Chỉ số thị trường
- `aggregatemarket`: Tổng hợp toàn thị trường
- `aggregateforeigngroup`: GDNN theo nhóm
- `spt`: Giao dịch thỏa thuận

**Sample Output (stock):**
```json
{
  "time": "2026-03-20 09:10:14",
  "symbol": "PVS",
  "id": 3220,
  "price": 42.3,
  "volume": 10,
  "price_change": 0.60,
  "percent_change": 1.40,
  "total_volume": 4280,
  "high_price": 43.1,
  "low_price": 42.2,
  "open_price": 43.0,
  "average_price": 42.72,
  "ceiling_price": "i",
  "side": "B",
  "session_id": "1773972279123"
}
```

**Pros:**
- Open-source Python library
- Standard schema (inspired by FIX/Bloomberg)
- Comprehensive data types
- Good documentation
- Free to use

**Cons:**
- May rely on scraping (not official API)
- Rate limits from data sources
- Requires maintenance

**Documentation:** https://github.com/vnstock-hq/vnstock-agent-guide/blob/main/docs/vnstock_pipeline/07-streaming-data-schemas.md

---

### 2.3 VietstockUpdater

**Type:** Desktop Application + Data Feed

**Data Types:**
- **EOD**: End-of-day data (Daily, Weekly, Monthly)
- **INTRADAY Ticker**: Real-time ticker data, cập nhật mỗi phút
- **INTRADAY 5-minute**: Data 5 phút (dùng cho backtesting)

**Coverage:**
- Vietnam stocks and ETFs
- Futures contracts and CW
- Vietnam stock indices
- International markets (EOD only)
- Gold, Forex, Commodities (EOD only)

**Pros:**
- Comprehensive data coverage
- Real-time intraday ticker
- Automatic update
- Stable and fast

**Cons:**
- Desktop application (not API)
- Paid service (699,000 VND/6 months)
- Designed for MetaStock, AmiBroker (not programmatic access)
- INTRADAY Ticker updates every minute (not true real-time)

**Website:** https://dichvu.vietstock.vn/san-pham/vietstockupdater

---

### 2.4 FireAnt

**Type:** Excel Platform + Metakit Software

**Data Types:**
- Real-time intraday data
- EOD data
- Financial data
- Corporate information

**Products:**
- **Excel Platform**: Real-time data in Excel
- **Metakit**: Data feed for MetaStock, AmiBroker, MetaTrader

**Pros:**
- Real-time intraday updates
- Comprehensive data
- Automatic updates

**Cons:**
- No public API for programmatic access
- Desktop software focus
- Commercial service
- Requires FireAnt account

**Website:** https://corporate.fireant.vn

---

## 3. Comparison Summary

| Provider | Type | WebSocket | Free | API Access | Coverage | Latency |
|----------|------|-----------|------|------------|----------|---------|
| **SSI FastConnect** | Official Broker | ✅ | ❌ | ✅ | HOSE, HNX, UPCOM, DER | Real-time |
| **DNSE Lightspeed** | Official Broker | ✅ | ❌ | ✅ | HOSE, HNX, UPCOM | Real-time |
| **Kun Data** | Third-Party | ✅ | ❌ | ✅ | HOSE, HNX | Real-time |
| **vnstock** | Open-Source Lib | ✅ | ✅ | ✅ | HOSE, HNX, UPCOM | Near real-time |
| **VietstockUpdater** | Desktop App | ❌ | ❌ | ❌ | All markets | 1-minute |
| **FireAnt** | Desktop Software | ❌ | ❌ | ❌ | All markets | Real-time |

---

## 4. Recommended Implementation Options

### Option 1: vnstock (Recommended for MVP)

**Why:**
- Free and open-source
- Python library, easy to integrate
- Standard schema, good documentation
- Active community

**Implementation Steps:**
1. Install vnstock library
2. Integrate WebSocket streaming into FastAPI backend
3. Broadcast updates via existing WebSocket manager
4. Store real-time data in Redis for caching
5. Update frontend to consume WebSocket events

**Estimated Effort:** 2-3 weeks

---

### Option 2: SSI FastConnect (Recommended for Production)

**Why:**
- Official broker API, reliable
- True real-time streaming
- Comprehensive data types
- Professional support

**Implementation Steps:**
1. Register for SSI FastConnect account
2. Obtain API credentials
3. Implement WebSocket client in Python
4. Integrate with existing FastAPI backend
5. Handle reconnection, error handling
6. Broadcast via WebSocket manager

**Estimated Effort:** 3-4 weeks

**Cost:** Commercial (contact SSI for pricing)

---

### Option 3: Kun Data (Alternative for Production)

**Why:**
- Designed for developers
- Good documentation
- WebSocket + HTTP hybrid
- Reasonable pricing

**Implementation Steps:**
1. Register for Kun Data account
2. Obtain API token
3. Implement HTTP client for initialization
4. Implement WebSocket client for streaming
5. Integrate with FastAPI backend
6. Handle authentication, rate limits

**Estimated Effort:** 3-4 weeks

**Cost:** Commercial (check https://kun.pro for pricing)

---

## 5. Technical Architecture

### Proposed Architecture for Finvista

```
┌─────────────────┐
│   Data Source   │
│  (SSI/vnstock)  │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│  FastAPI Backend│
│  - WebSocket    │
│  - Redis Cache  │
│  - Data Store   │
└────────┬────────┘
         │ WebSocket Broadcast
         ▼
┌─────────────────┐
│   Frontend      │
│  - React App    │
│  - WebSocket    │
│  - Real-time UI │
└─────────────────┘
```

### Key Components:

1. **WebSocket Client (Backend)**
   - Connect to data source (SSI/vnstock)
   - Handle reconnection logic
   - Parse incoming messages
   - Store in Redis cache

2. **Data Processing**
   - Normalize data format
   - Calculate derived metrics
   - Apply business logic

3. **WebSocket Broadcast**
   - Use existing `ConnectionManager`
   - Broadcast to connected clients
   - Filter by subscription (symbol, market)

4. **Frontend Integration**
   - Connect to backend WebSocket
   - Subscribe to relevant data
   - Update UI in real-time
   - Handle connection states

---

## 6. Implementation Checklist

### Phase 1: Research & Setup (Week 1)
- [ ] Choose data provider (vnstock for MVP, SSI for production)
- [ ] Register for API access (if needed)
- [ ] Set up development environment
- [ ] Test WebSocket connection
- [ ] Document data schema

### Phase 2: Backend Integration (Week 2-3)
- [ ] Implement WebSocket client
- [ ] Add Redis caching layer
- [ ] Implement data normalization
- [ ] Add error handling & reconnection
- [ ] Integrate with existing WebSocket manager
- [ ] Add logging & monitoring

### Phase 3: Frontend Integration (Week 3-4)
- [ ] Update WebSocket connection logic
- [ ] Add subscription management
- [ ] Implement real-time UI updates
- [ ] Add connection status indicators
- [ ] Handle offline/fallback scenarios
- [ ] Optimize performance

### Phase 4: Testing & Deployment (Week 4-5)
- [ ] Unit tests for WebSocket client
- [ ] Integration tests
- [ ] Load testing
- [ ] User acceptance testing
- [ ] Deploy to staging
- [ ] Deploy to production

---

## 7. Cost Analysis

| Provider | Setup Cost | Monthly Cost | Notes |
|----------|------------|--------------|-------|
| vnstock | $0 | $0 | Free, open-source |
| SSI FastConnect | TBD | TBD | Contact SSI for pricing |
| Kun Data | TBD | TBD | Check https://kun.pro |
| VietstockUpdater | 699,000 VND | 699,000 VND/6 months | Desktop app, not API |
| FireAnt | TBD | TBD | Contact FireAnt |

---

## 8. Risks & Mitigation

### Risk 1: API Rate Limits
**Mitigation:** Implement caching, use Redis, batch requests

### Risk 2: Connection Instability
**Mitigation:** Implement reconnection logic, fallback to HTTP polling

### Risk 3: Data Quality Issues
**Mitigation:** Validate data, cross-check with multiple sources

### Risk 4: Cost Overruns
**Mitigation:** Start with free option (vnstock), monitor usage, scale up as needed

### Risk 5: Regulatory Changes
**Mitigation:** Keep updated with provider terms, have backup data sources

---

## 9. Next Steps

1. **Decision:** Choose data provider for MVP (recommend vnstock)
2. **Prototype:** Build simple WebSocket client to test data flow
3. **Architecture Review:** Review with team, get feedback
4. **Implementation:** Start with Phase 1 tasks
5. **Monitoring:** Set up metrics to track data quality, latency

---

## 10. References

- SSI FastConnect: https://guide.ssi.com.vn/ssi-products/fastconnect-data/streaming-data
- DNSE Lightspeed: https://hdsd.dnse.com.vn/san-pham-dich-vu/lightspeed-api-truoc-krx/
- Kun Data: https://kun.pro/stocks-en.html
- vnstock: https://github.com/vnstock-hq/vnstock-agent-guide
- VietstockUpdater: https://dichvu.vietstock.vn/san-pham/vietstockupdater
- FireAnt: https://corporate.fireant.vn

---

**Last Updated:** 2026-07-28
**Next Review:** 2026-08-28
