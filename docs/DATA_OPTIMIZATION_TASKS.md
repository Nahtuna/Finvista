# Data Optimization & Freshness Tasks

## Overview
Document này liệt kê tất cả các task cần thực hiện để tối ưu hóa data, đảm bảo data luôn mới nhất, loại bỏ mock data, và chạy model định kỳ.

---

## 0. COMPLETED TASKS (Phase 1 - DataContext Implementation)

### 0.1 Central Data Store Implementation ✅ COMPLETED
**Status:** Completed 2026-07-28

**Implemented:**
- Created `DataContext.jsx` with React Context API for centralized data management
- Updated `App.jsx` to wrap application with `DataProvider`
- Refactored all pages to use `useData` hook instead of independent API calls:
  - ✅ HomePage - uses marketData, portfolioData, opportunitiesData, regimeData, newsData
  - ✅ OpportunitiesPage - uses opportunitiesData
  - ✅ PortfolioPage - uses portfolioData
  - ✅ WatchlistPage - uses opportunitiesData
  - ✅ MarketPage - uses marketData, opportunitiesData, regimeData
  - ✅ WarrantDetailPage - uses opportunitiesData, marketData
  - ✅ DashboardPage - uses portfolioData

**Benefits:**
- Eliminated redundant API calls across components
- Centralized data fetching logic
- Consistent data freshness tracking
- Simplified error handling

### 0.2 Authentication Error Handling ✅ COMPLETED
**Status:** Completed 2026-07-28

**Implemented:**
- Modified `client.js` to return `null` for 401 auth errors instead of throwing
- Updated `DataContext.jsx` to handle auth errors gracefully in both `refreshAllData()` and `refreshDataType()`
- Added conditional rendering in HomePage to show portfolio section only when authenticated
- Added `showPortfolioSection` flag to control portfolio UI display

**Benefits:**
- App no longer crashes when user is not authenticated
- Portfolio data gracefully skipped when auth fails
- Other data (market, opportunities, regime, news) still loads normally
- User-friendly "Login to view portfolio" message

### 0.3 UI Theme Fixes ✅ COMPLETED
**Status:** Completed 2026-07-28

**Implemented:**
- Fixed light mode background to be actually light (white backgrounds)
- Added CSS overrides for `.app-shell.color-light` in `theme.css`
- Ensured all components (topbar, cards, buttons, inputs, tables) have proper light mode styling
- Fixed HomePage loading state error by adding missing `loading` state variable

**Benefits:**
- Light mode now displays correctly with white backgrounds
- Consistent theming across all components
- No more dark backgrounds in light mode

### 0.4 File Cleanup ✅ COMPLETED
**Status:** Completed 2026-07-28

**Cleaned:**
- Removed 23 `__pycache__` directories
- Removed 43 `.pyc` compiled Python files
- Attempted to remove `logs/pipeline.log` (file in use by another process)

**Benefits:**
- Reduced repository size
- Cleaner codebase
- Removed unnecessary build artifacts

---

## 1. DATA SOURCES & CURRENT STATUS

### 1.1 Market Indices
| Symbol | Source | Latest Date | Auto-Update | Status | Current Display |
|--------|--------|-------------|-------------|---------|-----------------|
| VNINDEX | vnstock API | 2026-07-27 | ✅ 16:00 daily | ⚠️ OLD | 1,669.01 (27/7) - 1 day old |
| VN30 | vnstock API | 2026-07-27 | ✅ 16:00 daily | ⚠️ OLD | 1,806.5 (27/7) - 1 day old |
| HNXINDEX | Database | 2026-07-27 | ❌ No auto-update | ⚠️ OLD | 269.35 (27/7) - 1 day old |
| UPCOM | Fallback/DB | N/A | ❌ Not available | ❌ MOCK | 125.07 - MOCK DATA! |
| SPX (S&P 500) | yfinance | 2026-07-28 | ✅ 17:30 daily | ✅ FRESH | 5,560.8 (28/7) - Today |
| NDX (NASDAQ) | yfinance | 2026-07-28 | ✅ 17:30 daily | ✅ FRESH | 17,872.4 (28/7) - Today |

**CRITICAL ISSUES (28/7/2026):**
- VN indices data is 1 day old (27/7/2026) - Today is 28/7/2026
- UPCOM showing 125.07 is MOCK/FALLBACK data - No real data in DB
- US indices (SPX, NDX) are fresh (28/7/2026)
- Scheduler ran but VN indices not updated to 28/7/2026

### 1.2 Covered Warrant Data
| Data Type | Source | Latest Date | Auto-Update | Status |
|-----------|--------|-------------|-------------|---------|
| CW Prices (OHLCV) | SSI Scraper | 2026-07-27 | ✅ ATC sync | OK |
| CW Opportunities | BSM Engine | Realtime | ✅ 15-min scan | OK |
| CW Greeks | BSM Engine | Realtime | ✅ 15-min scan | OK |

**Issues:**
- Một số CW cũ (CACB2401, CACB2501) data cũ (2024-2025)
- Cần backfill data cho các CW đã niêm yết nhưng thiếu lịch sử

### 1.3 Underlying Stock Data
| Data Type | Source | Latest Date | Auto-Update | Status |
|-----------|--------|-------------|-------------|---------|
| Stock Prices | SSI Scraper | 2026-07-27 | ✅ ATC sync | OK |
| Stock Fundamentals | Annual Reports | Varies | ❌ Manual | ⚠️ Needs automation |
| Credit Health Scores | ML Model | Varies | ❌ Manual | ⚠️ Needs automation |

**Issues:**
- Fundamentals data không có auto-update
- Credit health scores cần re-train định kỳ

### 1.4 Macro Data
| Indicator | Source | Latest Date | Auto-Update | Status | Current Display |
|-----------|--------|-------------|-------------|---------|-----------------|
| USD/VND | Macro scraper | 2026-07-27 | ✅ 16:30 daily | ⚠️ OLD | 25,450 (27/7) - 1 day old |
| Gold Price | Macro scraper | 2026-07-27 | ✅ 16:30 daily | ⚠️ OLD | 88.50M (27/7) - 1 day old |
| VIX | Macro scraper | 2026-07-27 | ✅ 16:30 daily | ⚠️ OLD | Need verification |
| Brent Oil | Yahoo Finance | 2026-07-28 | ❌ Manual | ✅ FRESH | $88.07 (28/7) - Today |

**CRITICAL ISSUES (28/7/2026):**
- Macro data (USD/VND, Gold) is 1 day old (27/7/2026)
- Some macro showing "-" in UI (correct behavior when unavailable)
- Brent Oil showing fresh data from Yahoo Finance
- Need to verify macro scheduler execution

---

## 2. MISSING DATA GAPS

### 2.1 Critical Missing Data
1. **UPCOM Index**
   - Status: ❌ No data source
   - Impact: Market overview incomplete
   - Solution: Find alternative data source (yfinance: `^UPCOM`, HNX API, or scraping)
   - Priority: HIGH

2. **Historical CW Data for Old Warrants**
   - Status: ⚠️ Partial (CACB2401: 2024-06-17, CACB2501: 2025-07-24)
   - Impact: Cannot analyze historical performance
   - Solution: Backfill from SSI historical data or alternative sources
   - Priority: MEDIUM

3. **Stock Fundamentals Auto-Update**
   - Status: ❌ Manual only
   - Impact: Credit health scores outdated
   - Solution: Auto-scrape from quarterly reports
   - Priority: HIGH

### 2.2 Secondary Missing Data
1. **Derivatives Data (VN30F1M)**
   - Status: ✅ Available but needs verification
   - Impact: Basis analysis
   - Solution: Verify auto-update scheduler
   - Priority: LOW

2. **News Data**
   - Status: ✅ Available (Fireant)
   - Impact: News sentiment analysis
   - Solution: Keep current, verify freshness
   - Priority: LOW

---

## 3. REDUNDANT DATA

### 3.1 Duplicate Data Sources
1. **Market Indices**
   - Database: `StockHistoricalPrice` table
   - Cache: `market_data_snapshot.json`
   - Issue: Cache may be stale
   - Solution: Remove cache, always query DB
   - Priority: MEDIUM

2. **CW Opportunities**
   - Database: Multiple tables (cw_opportunities, warrants)
   - Cache: Excel export
   - Issue: Potential inconsistency
   - Solution: Single source of truth (DB)
   - Priority: MEDIUM

### 3.2 Unused Data
1. **Paper Trading Data**
   - Status: ✅ Active but may have unused fields
   - Solution: Audit and clean up
   - Priority: LOW

---

## 4. MOCK DATA TO REMOVE

### 4.1 Fallback Values (Keep but Document)
These are acceptable fallbacks when data unavailable:
- `service.py` line 1174: Fallback map for indices (VNINDEX, VN30, HNXINDEX, UPCOM, SPX, NDX)
- `TradingViewLightweightChart.jsx`: Fallback bars generation

**Action:** Keep but ensure these are only used when API fails, not as primary data source.

### 4.2 Hardcoded Values to Replace
1. **Sector Heatmap Data** (`HomePage.jsx` line 596-608)
   - Status: Hardcoded sector performance
   - Solution: Calculate from real stock data
   - Priority: HIGH

2. **Default Credit Health Profiles**
   - Status: Predefined profiles for banks
   - Solution: Use real fundamentals data
   - Priority: MEDIUM

---

## 5. DATA FRESHNESS TASKS

### 5.1 CRITICAL - Immediate Tasks (Today 28/7/2026)
1. **Update VN Indices to Today (28/7/2026)**
   - Current: VNINDEX, VN30, HNXINDEX showing 27/7/2026 data
   - Required: Update to 28/7/2026 data
   - Action: Run backfill_indices.py manually or trigger scheduler
   - Priority: CRITICAL
   - Command: `python scripts/data_pipelines/backfill_indices.py`

2. **Remove UPCOM Mock Data**
   - Current: Showing 125.07 (mock/fallback value)
   - Required: Replace with "-" when no data available
   - Action: Update service.py to return "-" for UPCOM instead of fallback
   - Priority: CRITICAL
   - File: `src/modules/cw_pricing/service.py` line 1174

3. **Verify Scheduler Execution**
   - Issue: Scheduler ran but indices not updated to 28/7
   - Required: Debug why 16:00 daily indices update didn't work
   - Action: Check scheduler logs, verify vnstock API availability
   - Priority: CRITICAL

### 5.2 Immediate Tasks (This Week)
1. **Fix HNXINDEX Auto-Update**
   - Add HNXINDEX to scheduler job
   - Use yfinance: `^HNX` or HNX API
   - Update `scheduler.py` line 127-137
   - Priority: HIGH

2. **Add UPCOM Data Source**
   - Research available data sources
   - Implement scraper or API integration
   - Add to scheduler
   - Priority: HIGH

3. **Fix yfinance Dependency**
   - Resolve websockets.asyncio import error
   - Test US indices fetch
   - Ensure scheduler runs successfully
   - Priority: HIGH

4. **Backfill Historical CW Data**
   - Identify CW with incomplete history
   - Run backfill script for missing periods
   - Verify data quality
   - Priority: MEDIUM

### 5.2 Short-Term Tasks (This Month)
1. **Automate Stock Fundamentals Update**
   - Create quarterly report scraper
   - Update credit health scores automatically
   - Add to scheduler (quarterly)
   - Priority: HIGH

2. **Replace Hardcoded Sector Data**
   - Calculate sector performance from real data
   - Update HomePage.jsx
   - Remove hardcoded values
   - Priority: HIGH

3. **Optimize Data Caching**
   - Remove stale cache files
   - Implement proper cache invalidation
   - Ensure always fresh data
   - Priority: MEDIUM

### 5.3 Long-Term Tasks (This Quarter)
1. **Data Quality Dashboard**
   - Create monitoring dashboard
   - Track data freshness across all sources
   - Alert on stale data
   - Priority: MEDIUM

2. **Historical Data Archive**
   - Archive old data efficiently
   - Implement data retention policy
   - Optimize database performance
   - Priority: LOW

---

## 6. MODEL TRAINING TASKS

### 6.1 Credit Health Model
1. **Retrain XGBoost Model**
   - Current: May be outdated
   - Frequency: Quarterly
   - Data needed: Latest fundamentals
   - Priority: HIGH

2. **Update Distress Score Models**
   - Altman Z-Score: Keep current formula
   - Springate S-Score: Keep current formula
   - Zmijewski X-Score: Keep current formula
   - Action: Verify formulas are up-to-date
   - Priority: LOW

### 6.2 Market Regime Model
1. **HMM Regime Detection**
   - Current: Running but needs verification
   - Frequency: Weekly retraining
   - Data needed: VNINDEX historical
   - Priority: MEDIUM

2. **Creed Trend Analysis**
   - Current: Running in background
   - Frequency: Daily update
   - Data needed: Market indices
   - Priority: LOW

### 6.3 ML Pipeline Tasks
1. **Automate Model Retraining**
   - Create scheduler job for model retraining
   - Add to `scheduler.py`
   - Priority: HIGH

2. **Model Performance Monitoring**
   - Track model accuracy over time
   - Alert on performance degradation
   - Priority: MEDIUM

---

## 7. INFRASTRUCTURE IMPROVEMENTS

### 7.1 Scheduler Optimization
1. **Current Schedule Review**
   ```
   09:00-14:45: CW scan (15-min) ✅
   15:15: ATC sync ✅
   16:00: Indices update (VNINDEX, VN30 only) ⚠️
   16:30: Macro update ✅
   17:00: Derivatives update ✅
   17:30: US indices update ✅
   Sunday 02:00: Weekly news ✅
   ```

2. **Needed Additions**
   - Add HNXINDEX to 16:00 job
   - Add UPCOM when data source available
   - Add quarterly fundamentals update
   - Add quarterly model retraining

### 7.2 Error Handling
1. **Scheduler Failure Recovery**
   - Add retry logic for failed jobs
   - Alert on consecutive failures
   - Priority: HIGH

2. **Data Validation**
   - Validate data before inserting to DB
   - Reject invalid/outdated data
   - Priority: MEDIUM

### 7.3 Monitoring
1. **Data Freshness Monitoring**
   - Track last update time for each data source
   - Alert if data > 24 hours old
   - Priority: HIGH

2. **Job Execution Monitoring**
   - Log all scheduler job executions
   - Track success/failure rates
   - Priority: MEDIUM

---

## 8. DISPLAY IMPROVEMENTS

### 8.1 Missing Data Display
1. **Replace Mock Data with "-"**
   - Review all components for hardcoded values
   - Replace with "-" when data unavailable
   - Add loading states
   - Priority: HIGH

2. **Data Freshness Indicators**
   - Show last update time on UI
   - Color-code freshness (green < 1h, yellow < 24h, red > 24h)
   - Priority: MEDIUM

### 8.2 Error States
1. **API Failure Handling**
   - Show user-friendly error messages
   - Provide retry buttons
   - Fallback to cached data with warning
   - Priority: HIGH

---

## 9. PRIORITY MATRIX

| Task | Priority | Effort | Impact | Timeline | Status |
|------|----------|--------|--------|----------|--------|
| **Update VN indices to 28/7/2026** | CRITICAL | Low | High | TODAY | ⚠️ Pending |
| **Remove UPCOM mock data** | CRITICAL | Low | High | TODAY | ⚠️ Pending |
| **Verify scheduler execution** | CRITICAL | Medium | High | TODAY | ⚠️ Pending |
| **Update macro data to 28/7/2026** | CRITICAL | Low | High | TODAY | ⚠️ Pending |
| Fix HNXINDEX auto-update | HIGH | Low | High | This week | Pending |
| Add UPCOM data source | HIGH | Medium | High | This month | Pending |
| Fix yfinance dependency | HIGH | Low | High | This week | Pending |
| Automate fundamentals update | HIGH | High | High | This month | Pending |
| Replace hardcoded sector data | HIGH | Medium | Medium | This month | Pending |
| Backfill historical CW data | MEDIUM | Medium | Medium | This month | Pending |
| Optimize data caching | MEDIUM | Low | Medium | This month | Pending |
| Automate model retraining | HIGH | High | High | This quarter | Pending |
| Data quality dashboard | MEDIUM | High | Medium | This quarter | Pending |
| Historical data archive | LOW | Medium | Low | Next quarter | Pending |

---

## 10. SUCCESS METRICS

### 10.1 Data Freshness
- All market indices: < 24 hours old
- CW prices: < 1 hour old during trading hours
- Fundamentals: < 3 months old
- Model predictions: < 1 month old

### 10.2 Data Completeness
- All active CW: Complete historical data
- All indices: No gaps in last 5 years
- All stocks: Complete fundamentals

### 10.3 System Reliability
- Scheduler success rate: > 99%
- API uptime: > 99.9%
- Data validation: 100% pass rate

---

## 11. IMPLEMENTATION CHECKLIST

### TODAY (28/7/2026) - CRITICAL
- [x] Implement DataContext for centralized data management
- [x] Handle 401 authentication errors gracefully
- [x] Fix light mode background styling
- [x] Fix HomePage loading state errors
- [x] Clean up temporary files (__pycache__, .pyc)
- [ ] Run backfill_indices.py to update VN indices to 28/7
- [ ] Update service.py to return "-" for UPCOM instead of mock data
- [ ] Check scheduler logs for indices update failure
- [ ] Run macro scraper to update USD/VND and Gold to 28/7
- [ ] Verify all data freshness in UI after updates

### Week 1
- [ ] Fix yfinance dependency issue
- [ ] Add HNXINDEX to scheduler
- [ ] Test US indices fetch
- [ ] Verify all indices data freshness

### Week 2-3
- [ ] Research UPCOM data source
- [ ] Implement UPCOM scraper/API
- [ ] Backfill missing CW historical data
- [ ] Replace hardcoded sector data

### Week 4
- [ ] Automate fundamentals update
- [ ] Implement quarterly model retraining
- [ ] Optimize data caching
- [ ] Add data freshness monitoring

### Month 2-3
- [ ] Build data quality dashboard
- [ ] Implement error handling improvements
- [ ] Add historical data archive
- [ ] Complete all display improvements

---

## 12. NOTES

- **Never use mock data** - Always show "-" when data unavailable
- **Single source of truth** - Database is the only reliable source
- **Cache invalidation** - Always force refresh when user requests
- **Error transparency** - Show users when data is unavailable
- **Performance vs Freshness** - Prioritize freshness over performance for financial data

---

**Last Updated:** 2026-07-28
**Next Review:** 2026-08-28
