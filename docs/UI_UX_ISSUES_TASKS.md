# UI/UX Issues & Improvement Tasks

## Overview
Document này liệt kê tất cả các vấn đề UI/UX hiện tại trong Finvista app và các task cần thực hiện để cải thiện trải nghiệm người dùng.

---

## 1. MARKET PAGE ISSUES

### 1.1 Stock Table Information Overlap
**Issue:** Bảng cổ phiếu cơ sở có thông tin trùng lặp và không tối ưu

**Current Problems:**
- Credit health info hiển thị trong bảng cổ phiếu gây overlap
- Thông tin "Sức khỏe Tài chính" hiển thị ngắn gọn (ví dụ: "AN TOÀN (3.00)")
- Không có chi tiết về các chỉ số tài chính

**Current Display:**
```
Mã cổ phiếu | Tên công ty | Ngành | Giá hiện tại | Biến động | Sức khỏe Tài chính | Khối lượng GD | Số lượng CW
ACB         | Ngân hàng... | Ngân hàng | 22.300 đ | +0.00% | AN TOÀN (3.00) | 375,809,380 | 20 mã CW
```

**Required Changes:**
- Xóa cột "Sức khỏe Tài chính" khỏi bảng cổ phiếu
- Thay bằng nút "Chi tiết" hoặc icon để xem thông tin chi tiết
- Khi click, hiển thị modal hoặc expand row với đầy đủ chỉ số:
  - Altman Z-Score
  - Springate S-Score
  - Zmijewski X-Score
  - Debt ratio, Liquidity, ROA, ROE
  - Các chỉ số tài chính khác

**Priority:** HIGH
**Effort:** MEDIUM
**File:** `frontend/src/features/market/MarketPage.jsx`

---

## 2. CREDIT HEALTH PAGE ISSUES

### 2.1 Page Redundancy
**Issue:** Trang Credit Health hiện tại trùng lặp với thông tin trong trang chi tiết CW

**Current Problems:**
- Credit health hiển thị riêng trang nhưng cũng có trong CW detail
- Dữ liệu giống nhau gây redundancy
- User phải navigate qua nhiều trang để xem thông tin

**Required Changes:**
- **Xóa trang Credit Health** (navigation item)
- Di chuyển credit health info vào:
  - **Trang chi tiết CW** (tab "Sức khỏe Credit CS") - đã có
  - **Modal popup** khi click vào cổ phiếu trong bảng
  - **Tooltip** khi hover over credit health indicator

**Priority:** HIGH
**Effort:** LOW
**Files:**
- `frontend/src/app/config.js` - Remove Credit Health navigation
- `frontend/src/app/AppShell.jsx` - Remove Credit Health route

### 2.2 Indicators Should Be Detailed
**Issue:** Các chỉ số hiện tại chỉ hiển thị ngắn gọn, thiếu chi tiết

**Current Display:**
```
Altman Z-score: 2.40
Risk zone: WARNING (GREY)
Risk probability: 31.0%
```

**Required Changes:**
- Hiển thị chi tiết từng chỉ số với:
  - **Giải thích ý nghĩa** (ví dụ: "Altman Z-Score > 2.99 = Safe, 1.81-2.99 = Grey Zone, < 1.81 = Distressed")
  - **Xu hướng lịch sử** (chart thay đổi theo thời gian)
  - **So sánh với ngành** (so sánh với trung bình ngành)
  - **Recommendation** dựa trên chỉ số

**Priority:** MEDIUM
**Effort:** HIGH
**File:** `frontend/src/features/warrant-detail/WarrantDetailPage.jsx`

---

## 3. WATCHLIST PAGE ISSUES

### 3.1 Buttons Not Working
**Issue:** Các nút trong Watchlist không hoạt động

**Current Problems:**
- Nút "CKCS" (Cổ phiếu cơ sở) không hoạt động
- Nút "Chứng quyền" không hoạt động
- Nút "So sánh" vẫn hiển thị nhưng không có chức năng

**Required Changes:**
- **Xóa nút "So sánh"** - Chưa có chức năng
- **Làm hoạt động nút "CKCS"**:
  - Filter watchlist để chỉ hiển thị cổ phiếu cơ sở
  - Hoặc navigate đến trang cổ phiếu cơ sở
- **Làm hoạt động nút "Chứng quyền"**:
  - Filter watchlist để chỉ hiển thị CW
  - Hoặc navigate đến trang CW scanner

**Priority:** HIGH
**Effort:** MEDIUM
**File:** `frontend/src/features/watchlist/WatchlistPage.jsx`

### 3.2 Missing Functionality
**Issue:** Watchlist thiếu các chức năng cơ bản

**Required Features:**
- Thêm/xóa mã khỏi watchlist
- Sắp xếp theo các tiêu chí (giá, % thay đổi, volume)
- Export watchlist
- Import watchlist
- Group watchlist (ví dụ: "CW tiềm năng", "Cổ phiếu blue chip")

**Priority:** MEDIUM
**Effort:** HIGH
**File:** `frontend/src/features/watchlist/WatchlistPage.jsx`

---

## 4. LEARNING PAGE ISSUES

### 4.1 Mock Data
**Issue:** Trang Learning đang hiển thị mock data

**Current Problems:**
- Dữ liệu không phải thật
- Các nút không hoạt động
- Không có nội dung trong các units

**Required Changes:**
- **Xóa mock data** - Thay bằng "-" khi không có data
- **Hoặc implement thật**:
  - Tạo nội dung học tập thật về:
    - Covered Warrants cơ bản
    - Black-Scholes model
    - Greeks (Delta, Gamma, Theta, Vega)
    - Credit health analysis
    - Market regime analysis
  - Thêm progress tracking
  - Th_add quizzes/tests

**Priority:** MEDIUM
**Effort:** VERY HIGH (nếu implement thật) hoặc LOW (nếu xóa mock data)
**File:** `frontend/src/features/learning/LearningPage.jsx`

### 4.2 Buttons Not Working
**Issue:** Các nút trong Learning page không hoạt động

**Required Changes:**
- Làm hoạt động các nút navigation giữa units
- Implement progress tracking
- Add completion status cho từng unit

**Priority:** MEDIUM
**Effort:** HIGH
**File:** `frontend/src/features/learning/LearningPage.jsx`

---

## 5. NEWS PAGE ISSUES

### 5.1 Cannot Click to See Overview
**Issue:** Không thể click vào news để xem tổng quan chi tiết

**Current Problems:**
- News items chỉ hiển thị list
- Không có modal hoặc detail view khi click
- Không thể đọc nội dung đầy đủ

**Required Changes:**
- **Add click handler** cho news items
- **Hiển thị modal** với:
  - Tiêu đề đầy đủ
  - Nội dung bài viết
  - Ngày đăng
  - Nguồn
  - Related tickers
  - Share buttons
- **Hoặc navigate** đến trang detail news

**Priority:** HIGH
**Effort:** MEDIUM
**File:** `frontend/src/features/news/NewsPage.jsx`

### 5.2 Missing Features
**Issue:** News page thiếu các chức năng cơ bản

**Required Features:**
- Filter by ticker/symbol
- Filter by date range
- Filter by category (Kinh tế, Tài chính, Thế giới, etc.)
- Search functionality
- Bookmark/save news
- Share news

**Priority:** MEDIUM
**Effort:** HIGH
**File:** `frontend/src/features/news/NewsPage.jsx`

---

## 6. ALERTS PAGE ISSUES

### 6.1 Mock Data
**Issue:** Trang Alerts đang hiển thị mock data

**Current Problems:**
- Dữ liệu không phải thật
- Alerts không hoạt động thực tế
- Không có alert notification system

**Required Changes:**
- **Xóa mock data** - Thay bằng "-" khi không có alerts
- **Hoặc implement thật**:
  - Alert system dựa trên:
    - Price alerts (giá đạt target)
    - Greeks alerts (Delta, Gamma thay đổi)
    - Credit health alerts (Altman Z-Score thay đổi)
    - Market regime alerts (chuyển regime)
  - Notification system (toast, bell icon)
  - Alert history
  - Alert configuration (set custom alerts)

**Priority:** MEDIUM
**Effort:** VERY HIGH (nếu implement thật) hoặc LOW (nếu xóa mock data)
**File:** `frontend/src/features/alerts/AlertsPage.jsx`

### 6.2 Missing Notification System
**Issue:** Không có hệ thống notification

**Required Features:**
- Bell icon trong header với badge count
- Toast notifications cho alerts
- Alert center để xem tất cả alerts
- Mark as read/unread
- Delete alerts
- Alert settings

**Priority:** MEDIUM
**Effort:** HIGH
**File:** `frontend/src/app/AppShell.jsx` (header), `frontend/src/features/alerts/AlertsPage.jsx`

---

## 7. GENERAL UI/UX ISSUES

### 7.1 Missing Landing Page
**Issue:** Không có landing page cho Finvista

**Current State:**
- App không có landing page/welcome page
- User đi thẳng vào dashboard khi mở app
- Không có introduction về Finvista
- Không có onboarding cho new users
- Không có showcase về features

**Required Changes:**
- **Tạo Landing Page component:**
  - Hero section với tagline "Quantitative Edge, Smarter Decisions"
  - Feature highlights (Market Scanner, CW Analytics, Credit Health, etc.)
  - Quick start guide
  - Call-to-action buttons
  - Screenshots/demo của app
  - Testimonials (optional)
  - Pricing/Plans (optional)
- **Add routing:**
  - Route `/` hoặc `/landing` cho landing page
  - Option để skip landing page cho returning users
- **Onboarding flow:**
  - First-time users see landing page
  - Returning users go directly to dashboard
  - "Tour" feature để giới thiệu app features

**Priority:** MEDIUM
**Effort:** HIGH
**Files:**
- `frontend/src/features/landing/LandingPage.jsx` - Create new
- `frontend/src/app/AppShell.jsx` - Add routing
- `frontend/src/app/config.js` - Add navigation

### 7.2 Color Scheme Inconsistency
**Issue:** Bảng màu chưa đồng bộ trên toàn bộ app

**Current Problems:**
- Màu sắc không nhất quán giữa các pages
- Dark/light mode không đồng bộ
- Button colors khác nhau giữa các sections
- Status colors (green/red/yellow) không consistent
- Background colors không uniform

**Examples of Inconsistency:**
- Nút "Làm mới" màu xanh (#059669) ở một số chỗ, màu khác ở chỗ khác
- Card background colors khác nhau giữa pages
- Text colors không consistent
- Border colors không uniform

**Required Changes:**
- **Tạo centralized color theme system:**
  - Define primary colors (success, warning, error, info)
  - Define background colors (card, sub-bg, main-bg)
  - Define text colors (primary, secondary, muted)
  - Define border colors
  - Define button colors (primary, secondary, danger, success)
- **Apply theme system consistently:**
  - Use `useThemeTokens()` hook across all components
  - Ensure dark/light mode works consistently
  - Standardize status colors (green = success, red = danger, yellow = warning)
  - Standardize button styles
- **Create design tokens:**
  - Store in `frontend/src/app/theme.js` hoặc `frontend/src/app/config.js`
  - Export as constants
  - Use throughout app

**Priority:** HIGH
**Effort:** MEDIUM
**Files:**
- `frontend/src/app/useThemeTokens.js` - Enhance with more tokens
- `frontend/src/app/theme.js` - Create if not exists
- All component files - Apply consistent theme

### 7.3 Data Freshness Indicators
**Issue:** Không có indicator cho data freshness

**Required Changes:**
- Thêm timestamp "Last updated" cho từng section
- Color-code freshness:
  - Green: < 1 hour old
  - Yellow: < 24 hours old
  - Red: > 24 hours old
- Hiển thị loading state khi data đang fetch

**Priority:** HIGH
**Effort:** MEDIUM
**Files:** Tất cả pages

### 7.3 Error States
**Issue:** Không có error states rõ ràng

**Required Changes:**
- Hiển thị user-friendly error messages
- Provide retry buttons
- Fallback to cached data với warning
- Show loading skeletons

**Priority:** HIGH
**Effort:** MEDIUM
**Files:** Tất cả pages

### 7.4 Responsive Design
**Issue:** UI có thể không responsive tốt trên mobile

**Required Changes:**
- Test trên các screen sizes
- Fix layout issues trên mobile
- Optimize touch targets
- Improve mobile navigation

**Priority:** MEDIUM
**Effort:** HIGH
**Files:** Tất cả components

---

## 8. REALTIME STREAMING IMPLEMENTATION

### 8.1 Research & Setup
**Issue:** Hiện tại Finvista chỉ có data từ DB được refresh mỗi 5 giây, không phải realtime streaming từ sàn

**Current State:**
- Data được cào từ các nguồn bên ngoài và lưu vào DB
- Nút "Realtime Auto (5s)" chỉ refresh lại data từ DB mỗi 5 giây
- Không có WebSocket streaming từ sàn (HOSE, HNX)
- Không có giá intraday realtime

**Required Changes:**
- **Tích hợp vnstock library** (free, open-source) cho MVP
- **Implement WebSocket client** để nhận data realtime
- **Broadcast data** qua existing WebSocket manager
- **Store real-time data** trong Redis cache
- **Update frontend** để consume WebSocket events
- **Add connection status indicators** (connected/disconnected)
- **Handle reconnection logic** khi mất kết nối

**Priority:** HIGH
**Effort:** HIGH (2-3 weeks)
**Files:**
- `src/infra/vnstock_client.py` - Create new WebSocket client
- `src/api/websocket.py` - Enhance to broadcast realtime data
- `frontend/src/features/home/HomePage.jsx` - Update to consume realtime data
- `frontend/src/features/market/MarketPage.jsx` - Add realtime price updates
- `requirements.txt` - Add vnstock dependency

**Implementation Phases:**

**Phase 1: Research & Setup (Week 1)**
- [ ] Install vnstock library (`pip install vnstock`)
- [ ] Test WebSocket connection with vnstock
- [ ] Document data schema from vnstock
- [ ] Set up Redis cache layer
- [ ] Create vnstock client module

**Phase 2: Backend Integration (Week 2-3)**
- [ ] Implement WebSocket client for vnstock
- [ ] Add data normalization logic
- [ ] Implement Redis caching for real-time data
- [ ] Add error handling & reconnection logic
- [ ] Integrate with existing WebSocket manager
- [ ] Add logging & monitoring
- [ ] Test data flow end-to-end

**Phase 3: Frontend Integration (Week 3-4)**
- [ ] Update WebSocket connection logic in frontend
- [ ] Add subscription management (subscribe to specific symbols)
- [ ] Implement real-time UI updates for stock prices
- [ ] Add connection status indicators (green dot when connected)
- [ ] Handle offline/fallback scenarios (switch to HTTP polling)
- [ ] Optimize performance (debounce updates, batch rendering)

**Phase 4: Testing & Deployment (Week 4-5)**
- [ ] Unit tests for WebSocket client
- [ ] Integration tests for data flow
- [ ] Load testing with multiple symbols
- [ ] User acceptance testing
- [ ] Deploy to staging environment
- [ ] Monitor data quality & latency
- [ ] Deploy to production

**Data Types to Support:**
- `stock`: Giá cổ phiếu cơ sở (real-time match data)
- `board`: Sổ lệnh (bid/ask 3 bước giá)
- `index`: Chỉ số thị trường (VN-Index, VN30, HNX-Index)

**Fallback Strategy:**
- Nếu WebSocket mất kết nối → switch to HTTP polling (30s interval)
- Nếu vnstock không hoạt động → fallback to existing DB refresh (5s interval)
- Hiển thị warning message cho user khi không có realtime data

**Documentation:** `docs/REALTIME_STREAMING_RESEARCH.md`

---

## 8. INTELLIGENT DATA SYNCHRONIZATION SYSTEM

### 8.1 Automated Data Freshness Monitor & Incremental Updater
**Issue:** Hiện tại data trong DB cũ (lag ~1 tháng), cần chạy thủ công scraper để cập nhật. Không có hệ thống tự động kiểm tra và cập nhật data thiếu.

**Current Problems:**
- Data VNINDEX cũ nhất: 2026-06-26 (lag ~1 tháng)
- Data cổ phiếu cũ nhất: 2026-06-23 (lag ~1 tháng)
- Không có scheduler tự động kiểm tra data freshness
- Không có incremental update (chỉ cào lại toàn bộ)
- ML models không được retrain khi data mới có
- Các biểu đồ/regime analysis dùng data cũ

**Required Changes:**
- **Tạo Data Freshness Monitor Service:**
  - Kiểm tra daily data cho VNINDEX, cổ phiếu, CW
  - Kiểm tra intraday data cho session hiện tại
  - Kiểm tra news data (tính freshness theo giờ)
  - Kiểm tra corporate events data
  - Return danh sách data thiếu với priority

- **Implement Incremental Scraper:**
  - Chỉ cào data từ ngày cuối cùng có trong DB
  - Chỉ cào tin mới hơn tin cuối đã có (dùng link làm dedup key)
  - Chỉ cào corporate events mới
  - Batch processing theo nhóm (VNINDEX, stocks, CW, news)

- **ML Model Auto-Retrain Trigger:**
  - Re-train HMM regime model khi có data mới (weekly)
  - Re-train news impact ML model khi có tin mới (daily)
  - Re-train credit risk model khi có BCTC mới (quarterly)
  - Cache model results để tránh re-train không cần thiết

- **Scheduler/Orchestrator:**
  - Chạy data freshness check mỗi 1 giờ
  - Chạy incremental scraper khi phát hiện data thiếu
  - Chạy ML retrain theo schedule (weekly/daily/quarterly)
  - Log tất cả hoạt động để monitoring
  - Alert khi scraper fail quá nhiều lần

- **API Endpoint cho Manual Trigger:**
  - `/api/admin/sync/check` - Kiểm tra data freshness
  - `/api/admin/sync/run` - Chạy incremental sync
  - `/api/admin/sync/status` - Xem trạng thái sync
  - `/api/admin/ml/retrain` - Manual retrain ML models

**Priority:** HIGH
**Effort:** VERY HIGH (4-6 weeks)
**Files:**
- `src/infra/data_freshness_monitor.py` - Create new
- `src/infra/incremental_scraper.py` - Create new
- `src/infra/scheduler.py` - Create new
- `src/api/routes/admin.py` - Add sync endpoints
- `src/modules/regime_analysis/service.py` - Add auto-retrain logic
- `src/modules/news_impact/service.py` - Add auto-retrain logic

**Implementation Phases:**

**Phase 1: Data Freshness Monitor (Week 1-2)**
- [ ] Create `DataFreshnessMonitor` class
- [ ] Implement check for VNINDEX daily data
- [ ] Implement check for stock daily data
- [ ] Implement check for CW daily data
- [ ] Implement check for intraday session data
- [ ] Implement check for news freshness
- [ ] Implement check for corporate events
- [ ] Add API endpoint `/api/admin/sync/check`
- [ ] Return missing data report with priority

**Phase 2: Incremental Scraper (Week 2-4)**
- [ ] Create `IncrementalScraper` class
- [ ] Implement incremental fetch for VNINDEX (from last date)
- [ ] Implement incremental fetch for stocks (from last date)
- [ ] Implement incremental fetch for CW (from last date)
- [ ] Implement incremental news fetch (from last link)
- [ ] Implement incremental events fetch (from last date)
- [ ] Add batch processing logic
- [ ] Add error handling & retry logic
- [ ] Add progress tracking & logging

**Phase 3: ML Auto-Retrain (Week 4-5)**
- [ ] Implement HMM regime auto-retrain (weekly)
- [ ] Implement news impact ML auto-retrain (daily)
- [ ] Implement credit risk model auto-retrain (quarterly)
- [ ] Add model versioning
- [ ] Add model performance tracking
- [ ] Add rollback mechanism nếu model tệ hơn

**Phase 4: Scheduler & Orchestrator (Week 5-6)**
- [ ] Create scheduler using APScheduler or similar
- [ ] Schedule data freshness check (hourly)
- [ ] Schedule incremental sync (when needed)
- [ ] Schedule ML retrain (weekly/daily/quarterly)
- [ ] Add monitoring dashboard
- [ ] Add alert system (Telegram/Email)
- [ ] Add manual trigger endpoints
- [ ] Test full end-to-end flow

**Data Freshness Rules:**
- **VNINDEX**: Cần data đến ngày làm việc gần nhất
- **Stocks**: Cần data đến ngày làm việc gần nhất
- **CW**: Cần data đến ngày làm việc gần nhất
- **Intraday**: Cần data session hiện tại (nếu trong giờ giao dịch)
- **News**: Cần tin trong 24h gần nhất
- **Events**: Cần events trong 7 ngày gần nhất

**Fallback Strategy:**
- Nếu primary scraper fail → try secondary source
- Nếu all sources fail → alert admin
- Nếu data quá cũ (>7 days) → alert admin
- Nếu ML retrain fail → use previous model version

**Success Metrics:**
- Data freshness < 1 day cho daily data
- Data freshness < 1 hour cho intraday data
- ML models retrained theo schedule
- Zero manual intervention required
- All charts use updated data

---

## 9. PRIORITY MATRIX

| Issue | Priority | Effort | Impact | Timeline |
|-------|----------|--------|--------|----------|
| **Fix color scheme inconsistency** | HIGH | Medium | High | This week |
| **Remove Credit Health page** | HIGH | Low | High | This week |
| **Fix stock table overlap** | HIGH | Medium | High | This week |
| **Fix Watchlist buttons** | HIGH | Medium | Medium | This week |
| **Fix News click to overview** | HIGH | Medium | High | This week |
| **Remove Learning mock data** | MEDIUM | Low | Medium | This week |
| **Remove Alerts mock data** | MEDIUM | Low | Medium | This week |
| **Implement intelligent data sync system** | HIGH | Very High | Very High | This month |
| **Implement realtime streaming (vnstock)** | HIGH | High | Very High | This month |
| **Create landing page** | MEDIUM | High | High | This month |
| **Make indicators detailed** | MEDIUM | High | High | This month |
| **Add data freshness indicators** | HIGH | Medium | High | This month |
| **Improve error states** | HIGH | Medium | High | This month |
| **Implement real Learning content** | LOW | Very High | Low | Next quarter |
| **Implement real Alerts system** | LOW | Very High | Low | Next quarter |
| **Add Watchlist features** | MEDIUM | High | Medium | This month |
| **Add News features** | MEDIUM | High | Medium | This month |
| **Improve responsive design** | MEDIUM | High | Medium | This month |

---

## 9. IMPLEMENTATION CHECKLIST

### Week 1 (This Week)
- [ ] Create centralized color theme system in theme.js
- [ ] Apply consistent colors across all components
- [ ] Remove Credit Health navigation item from config.js
- [ ] Remove Credit Health route from AppShell.jsx
- [ ] Remove "Sức khỏe Tài chính" column from stock table
- [ ] Add "Chi tiết" button/icon to stock table
- [ ] Fix Watchlist buttons (CKCS, Chứng quyền)
- [ ] Remove "So sánh" button from Watchlist
- [ ] Add click handler to news items
- [ ] Remove mock data from Learning page (replace with "-")
- [ ] Remove mock data from Alerts page (replace with "-")

### Week 2-4 (Realtime Streaming Implementation)
- [ ] Install vnstock library
- [ ] Test WebSocket connection with vnstock
- [ ] Set up Redis cache layer
- [ ] Create vnstock client module
- [ ] Implement WebSocket client for vnstock
- [ ] Add data normalization logic
- [ ] Implement Redis caching for real-time data
- [ ] Add error handling & reconnection logic
- [ ] Integrate with existing WebSocket manager
- [ ] Update frontend WebSocket connection logic
- [ ] Add subscription management
- [ ] Implement real-time UI updates for stock prices
- [ ] Add connection status indicators
- [ ] Handle offline/fallback scenarios
- [ ] Test data flow end-to-end

### Week 2-3
- [ ] Create landing page component
- [ ] Add routing for landing page
- [ ] Implement detailed credit health modal/tooltip
- [ ] Add data freshness indicators to all pages
- [ ] Improve error states across all pages
- [ ] Add basic Watchlist features (add/remove, sort)
- [ ] Add basic News features (filter, search)
- [ ] Test responsive design on mobile

### Month 2-3
- [ ] Implement real Learning content (optional)
- [ ] Implement real Alerts system (optional)
- [ ] Add advanced Watchlist features
- [ ] Add advanced News features
- [ ] Complete responsive design improvements

---

## 10. SUCCESS METRICS

### 10.1 User Experience
- Zero mock data in production
- All buttons functional
- Clear navigation flow
- Fast page loads (< 2s)
- Mobile-friendly interface

### 10.2 Data Transparency
- All data sources clearly labeled
- Freshness indicators visible
- Error states user-friendly
- No confusing overlaps

### 10.3 Feature Completeness
- All navigation items functional
- All buttons have clear purpose
- No dead-end pages
- Consistent UI patterns

---

## 11. NOTES

- **Mock data policy:** Never show mock data in production - use "-" when data unavailable
- **Button functionality:** Every button must have a clear purpose and working handler
- **Navigation:** Remove pages/features that are not implemented
- **User feedback:** Show loading states, error messages, and success confirmations
- **Progressive enhancement:** Start with basic functionality, add advanced features later

---

## 12. SCREENSHOT REFERENCES

### Market Page - Stock Table Overlap
- Issue: Credit health column causing information overlap
- Solution: Remove column, add detail button

### Credit Health Page - Redundancy
- Issue: Separate page duplicates CW detail info
- Solution: Remove page, integrate into CW detail

### Watchlist Page - Non-functional Buttons
- Issue: CKCS, Chứng quyền, So sánh buttons not working
- Solution: Fix or remove non-functional buttons

### Learning Page - Mock Data
- Issue: Showing mock data, buttons not working
- Solution: Remove mock data or implement real content

### News Page - No Detail View
- Issue: Cannot click to see news overview
- Solution: Add modal or detail page

### Alerts Page - Mock Data
- Issue: Showing mock alerts
- Solution: Remove mock data or implement real alert system

---

**Last Updated:** 2026-07-28
**Next Review:** 2026-08-28
