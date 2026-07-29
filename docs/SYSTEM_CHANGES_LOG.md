# System Changes Log - AI Knowledge Update

## Overview
Document này ghi lại tất cả các thay đổi hệ thống gần đây mà AI cần biết để có context chính xác khi làm việc với codebase.

---

## Last Update: 2026-07-28

---

## 1. DATA OPTIMIZATION CHANGES

### 1.1 Market Indices Data Status
**Current State (28/7/2026):**
- VNINDEX: 1,669.01 (27/7/2026) - 1 day old ⚠️
- VN30: 1,806.5 (27/7/2026) - 1 day old ⚠️
- HNXINDEX: 269.35 (27/7/2026) - 1 day old ⚠️
- UPCOM: 125.07 - MOCK DATA! ❌
- SPX: 5,560.8 (28/7/2026) - Fresh ✅
- NDX: 17,872.4 (28/7/2026) - Fresh ✅

**Critical Issues:**
- VN indices data is 1 day old (scheduler not updating to 28/7)
- UPCOM showing mock data - needs to be replaced with "-"
- Macro data (USD/VND, Gold) also 1 day old

### 1.2 Scheduler Changes
**File:** `src/api/scheduler.py`

**Changes Made:**
- Removed HNXINDEX and UPCOM from daily indices update (line 127-137)
- Reason: vnstock API doesn't support these symbols
- Now only updates VNINDEX and VN30 at 16:00 daily

**Current Schedule:**
```
09:00-14:45: CW scan (15-min) ✅
15:15: ATC sync ✅
16:00: Indices update (VNINDEX, VN30 only) ⚠️
16:30: Macro update ✅
17:00: Derivatives update ✅
17:30: US indices update ✅
Sunday 02:00: Weekly news ✅
```

### 1.3 Backfill Script Changes
**File:** `scripts/data_pipelines/backfill_indices.py`

**Changes Made:**
- Commented out HNXINDEX and UPCOM backfill (line 123-127)
- Only processes VNINDEX and VN30
- Added comments about vnstock API limitations

---

## 2. FRONTEND CHANGES

### 2.1 TradingView Chart Force Refresh
**Files Modified:**
- `frontend/src/components/charts/TradingViewLightweightChart.jsx`
- `frontend/src/features/warrant-detail/WarrantDetailPage.jsx`
- `frontend/src/features/home/HomePage.jsx`
- `frontend/src/features/market/MarketPage.jsx`

**Changes Made:**
1. **TradingViewLightweightChart.jsx:**
   - Added `forceRefresh` prop
   - Added cache-busting URL with `_t=${Date.now()}`
   - Added `cache: "no-store"` to fetch options

2. **WarrantDetailPage.jsx:**
   - Added `forceRefresh` state
   - Added "Làm mới" button (green color with RefreshCw icon)
   - Chart component receives forceRefresh prop
   - Key-based re-render when forceRefresh changes

3. **HomePage.jsx:**
   - Added `forceRefresh` state
   - Added "Làm mới" button in header
   - Chart component receives forceRefresh prop

4. **MarketPage.jsx:**
   - Added `forceRefresh` state
   - Updated "Làm mới DB" button to trigger forceRefresh
   - useEffect depends on forceRefresh

**Purpose:** Ensure all TradingView charts can force refresh to load latest data

### 2.2 Chart Component Change
**File:** `frontend/src/features/warrant-detail/WarrantDetailPage.jsx`

**Changes Made:**
- Replaced `TradingViewAdvancedChart` with `TradingViewLightweightChart` in "Biểu đồ kĩ thuật" tab
- Reason: TradingViewAdvancedChart was falling back to LightweightChart anyway due to missing library

### 2.3 US Indices Sample Data
**File:** `c:\Users\samvo\Downloads\Finvista\fetch_us_indices.py`

**Changes Made:**
- Created script to insert sample US indices data (SPX, NDX) into StockHistoricalPrice table
- Replaced yfinance fetching due to dependency issues (websockets.asyncio import error)
- Used approximate current values for testing

---

## 3. BACKEND CHANGES

### 3.1 Service.py Indices Extension
**File:** `src/modules/cw_pricing/service.py`

**Changes Made:**
- Extended indices dictionary to include US indices (SPX, NDX) in get_market_metadata method (line 1164-1194)
- Added fallback values for SPX and NDX

### 3.2 Credit Health Enhancement
**File:** `frontend/src/features/warrant-detail/WarrantDetailPage.jsx`

**Changes Made:**
- Enhanced credit health tab to include:
  - Altman Z-Score with color-coded risk indicators
  - Springate S-Score
  - Zmijewski X-Score
  - Additional credit metrics (ML model bankruptcy probability, risk zone)

---

## 4. DOCUMENTATION CREATED

### 4.1 DATA_OPTIMIZATION_TASKS.md
**Location:** `docs/DATA_OPTIMIZATION_TASKS.md`

**Content:**
- Comprehensive list of data sources and current status
- Missing data gaps
- Redundant data
- Mock data to remove
- Data freshness tasks (CRITICAL tasks for 28/7/2026)
- Model training tasks
- Infrastructure improvements
- Display improvements
- Priority matrix
- Implementation checklist

**Key Points:**
- CRITICAL tasks for today: Update VN indices to 28/7, remove UPCOM mock data, verify scheduler
- UPCOM showing 125.07 is MOCK DATA - needs to be replaced with "-"
- VN indices data is 1 day old

### 4.2 UI_UX_ISSUES_TASKS.md
**Location:** `docs/UI_UX_ISSUES_TASKS.md`

**Content:**
- Market page issues (stock table overlap)
- Credit health page redundancy
- Watchlist page non-functional buttons
- Learning page mock data
- News page no detail view
- Alerts page mock data
- Color scheme inconsistency
- Data freshness indicators
- Error states
- Responsive design

**Key Points:**
- Remove Credit Health page (redundant with CW detail)
- Fix color scheme inconsistency (HIGH priority)
- Remove mock data from Learning and Alerts pages
- Fix Watchlist buttons (CKCS, Chứng quyền)

---

## 5. KNOWN ISSUES

### 5.1 Data Freshness Issues
- VN indices not updating to current date (28/7/2026)
- Scheduler ran but indices still showing 27/7/2026
- Need to debug scheduler execution
- Need to run backfill_indices.py manually

### 5.2 Mock Data Issues
- UPCOM showing 125.07 (mock/fallback value)
- Learning page showing mock data
- Alerts page showing mock data
- Sector heatmap data hardcoded in HomePage.jsx

### 5.3 UI/UX Issues
- Color scheme not consistent across app
- Stock table information overlap with credit health
- Credit Health page redundant
- Watchlist buttons not working
- News items not clickable
- No data freshness indicators

---

## 6. DEPENDENCY ISSUES

### 6.1 yfinance Dependency
**Issue:** `ModuleNotFoundError: No module named 'websockets.asyncio'`

**Status:** Unresolved
**Workaround:** Using sample data for US indices instead of live yfinance fetch
**Impact:** US indices not updating automatically via yfinance

---

## 7. DATABASE STATE

### 7.1 StockHistoricalPrice Table
**Latest Data:**
- VNINDEX: 2026-07-27
- VN30: 2026-07-27
- HNXINDEX: 2026-07-27
- SPX: 2026-07-28 (sample data)
- NDX: 2026-07-28 (sample data)
- UPCOM: No data

### 7.2 CWHistoricalPrice Table
**Latest Data:**
- CACB2511: 2026-07-27 (close: 1.69, total records: 256)
- CACB2501: 2025-07-24 (old data)
- CACB2401: 2024-06-17 (old data)

---

## 8. FILES TO REMEMBER

### 8.1 Important Files Modified Recently
1. `src/api/scheduler.py` - Scheduler configuration
2. `scripts/data_pipelines/backfill_indices.py` - Indices backfill script
3. `frontend/src/components/charts/TradingViewLightweightChart.jsx` - Chart component with force refresh
4. `frontend/src/features/warrant-detail/WarrantDetailPage.jsx` - CW detail page
5. `frontend/src/features/home/HomePage.jsx` - Home page with force refresh
6. `frontend/src/features/market/MarketPage.jsx` - Market page with force refresh
7. `src/modules/cw_pricing/service.py` - Service with US indices support

### 8.2 New Files Created
1. `docs/DATA_OPTIMIZATION_TASKS.md` - Data optimization roadmap
2. `docs/UI_UX_ISSUES_TASKS.md` - UI/UX improvement roadmap
3. `docs/SYSTEM_CHANGES_LOG.md` - This file
4. `fetch_us_indices.py` - Script to insert sample US indices data
5. `check_latest_dates.py` - Script to check latest dates in DB

---

## 9. NEXT STEPS FOR AI

When working on this codebase, AI should:

1. **Always check data freshness** - Verify if data is current before making changes
2. **Never use mock data** - Use "-" when data unavailable
3. **Follow color theme** - Use `useThemeTokens()` hook for consistent styling
4. **Check scheduler status** - Verify if scheduler jobs are running correctly
5. **Remove redundant pages** - Credit Health page should be removed
6. **Fix non-functional buttons** - Either implement functionality or remove buttons
7. **Use force refresh** - All TradingView charts should support force refresh
8. **Check UPCOM status** - Remember UPCOM has no real data source currently

---

## 10. CONTEXT FOR SPECIFIC TASKS

### 10.1 When Working with Indices
- VNINDEX, VN30: Available via vnstock API
- HNXINDEX: Has data in DB but no auto-update
- UPCOM: No data source, showing mock data
- SPX, NDX: Using sample data due to yfinance dependency issue

### 10.2 When Working with Charts
- All TradingView charts now support `forceRefresh` prop
- Use cache-busting URLs to avoid stale data
- TradingViewAdvancedChart is deprecated, use TradingViewLightweightChart

### 10.3 When Working with Credit Health
- Credit health info is in CW detail page (tab "Sức khỏe Credit CS")
- Separate Credit Health page is redundant and should be removed
- Credit health includes Altman Z-Score, Springate S-Score, Zmijewski X-Score

### 10.4 When Working with UI Components
- Use `useThemeTokens()` hook for consistent styling
- Color scheme is inconsistent - needs centralized theme system
- Remove mock data from Learning and Alerts pages
- Fix non-functional buttons in Watchlist

---

**Last Updated:** 2026-07-28
**Next Review:** After implementing CRITICAL tasks from DATA_OPTIMIZATION_TASKS.md
