# FINLENS QUANT – LIVE ANALYSIS (3 Tasks)
> **Thực hiện**: 14/07/2026  
> **Phương pháp**: HTTP crawl toàn bộ public pages + web search  
> **Nguồn**: finlensquant.vn (live), YouTube @finlenshq (live), web search

---

## TASK 1: Hands-on Testing – Website Analysis (Public Pages)

### 1.1 Tech Stack Xác Nhận (Live Evidence)

| Layer | Technology | Evidence từ HTML thực tế |
|-------|-----------|--------------------------|
| Framework | **Next.js 13+ (App Router)** | `/_next/static/chunks/app/(marketing)/layout-...js`, route group pattern `app/(marketing)` và `app/(protected)` |
| CSS framework | **Tailwind CSS** | Class: `flex items-center gap-2.5 rounded-[10px]`, `bg-[#071426]`, `text-white/80` |
| UI Components | **Lucide React** | `<svg class="lucide lucide-arrow-right">`, `<svg class="lucide lucide-menu">` |
| Auth | **NextAuth.js** | Login URL: `/auth/login?callbackUrl=%2Fintro` |
| Theme | **Dark mode default** | `localStorage.getItem("finlens-theme") || "dark"` inline script |
| Language | **Vietnamese (vi-VN)** | `<html lang="vi-VN">`, hreflang tags |

### 1.2 Route Structure (Xác Nhận từ JSON-LD và HTML)

```
PUBLIC ROUTES:
/                          → Homepage
/ma-tran-dinh-luong       → Ma trận định lượng
/dong-tien-to-chuc        → Dòng tiền tổ chức
/sector-rotation           → Sector Rotation
/nghien-cuu               → Nghiên cứu
/huong-dan                → Hướng dẫn (Docs)
/huong-dan/pdf            → PDF hướng dẫn
/huong-dan/video          → Video hướng dẫn (YouTube embeds)
/pricing                  → Bảng giá
/copyright                → Bản quyền
/auth/login               → Đăng nhập
/auth/register            → Đăng ký

PROTECTED ROUTES (yêu cầu auth - từ JS chunk names):
/intro                    → Onboarding (callbackUrl default)
/dash                     → Main Dashboard
/dash/trading-chart       → Trading Chart
/dash/sector              → Sector Board
/dash/cashflow            → Cashflow
/dash/matrix              → Signal Matrix
/dash/volatility          → Volatility
/dash/multi-layer         → Multi-Layer
/dash/deepfinlens         → Deep FinLens
/dash/finlens-ai          → Finlens AI
/dash/manipulation        → Market Manipulation
/dash/market-watch        → Market Watch
/dash/social              → Social
```

### 1.3 Auth Flow (Confirmed)

- Redirect to `/intro` (onboarding) sau khi login lần đầu
- Redirect to `/dash` nếu đã quen
- Pattern: `/auth/login?callbackUrl=%2Fdash`
- **Frame embedding blocked**: Inline script chặn iframe embed (anti-scraping)
- **Custom chunk recovery**: Auto-reload khi ChunkLoadError (max 3 lần / 30s)

### 1.4 Navigation (Live)

**Desktop header**:
- Logo: "Finlens Quant StockApp"
- Badge: **"Định Lượng Liên Tầng Cơ Sở - PS - CW"** (3 thị trường: Cơ sở, Phái Sinh, Chứng Quyền)
- Nav: Sản phẩm | Khám phá | Bảng giá | Tài liệu
- CTA: "Dùng thử miễn phí" → /auth/login?callbackUrl=%2Fintro

**Footer**:
- Sản phẩm: Bảng thị trường, Ma trận định lượng, Sector rotation, Dòng tiền
- Social: Zalo, TikTok, Threads, LinkedIn, Email
- Book demo: `finlensstock@gmail.com`

### 1.5 Brand Identity (Confirmed từ Schema.org)

| Field | Value |
|-------|-------|
| Slogan | *"Đọc thị trường Việt Nam bằng dữ liệu, tín hiệu và dòng tiền"* |
| Founded | 2026 |
| Area served | Vietnam |
| Know about | Chứng khoán VN, Phân tích định lượng, Dòng tiền tổ chức, VNINDEX, VN30F1M, Xoay vòng ngành |

### 1.6 Performance Pattern

```javascript
// Dark mode – trước first paint:
localStorage.getItem("finlens-theme") || "dark"

// Performance detection – tắt animations tự động:
var shouldUseSafeMode = reducedMotion || coarsePointer || narrowViewport || lowBandwidth
// Toggle class: "finlens-performance-safe"

// Skeleton loading thay blank screen:
class="finlens-skeleton mx-auto h-12 w-full max-w-4xl rounded-[18px]"
```

### 1.7 Social Channels (Confirmed từ Footer HTML)

| Platform | Handle |
|----------|--------|
| Zalo | 0903256365 |
| TikTok | @finlensquant.stockapp |
| Threads | @finlens_stock |
| LinkedIn | finlens-vietnam-stocks-quantitative-analysis-system |
| Email | finlensstock@gmail.com |
| YouTube | @finlenshq |

---

## TASK 2: Pricing & Feature Analysis

> Pricing page client-side rendered (SPA). Data từ HTML meta + web research.

### 2.1 Pricing Plans

**Gói Demo** (Free trial):
- Thời hạn: **14 ngày** miễn phí
- Features: ~2/3 biểu đồ Overall Dashboard + partial Matrix Board
- Không cần credit card

**Gói Client**:
- Dành cho: Nhà đầu tư cá nhân
- Features: Full Dashboard + Matrix Board + Sector + Cashflow + hỗ trợ cơ bản
- Giá: Chưa xác nhận (SPA, cần auth xem)

**Gói Client Pro**:
- Dành cho: Power users / người cần khai thác sâu
- Giá: **2.999.000 VNĐ / 3 tháng** (~999.000 VNĐ/tháng)
- Features bổ sung:
  - Sector Extensions (full)
  - Volatility module
  - Matrix Advanced Search & Preset
  - Deep Analysis
  - Finlens AI (trợ lý phân tích đầy đủ)

**Confirmed từ meta description pricing page**:
> *"Finlens Quant giúp so sánh gói Demo, Client và Client Pro cho phân tích chứng khoán Việt Nam: dòng tiền tổ chức, độ rộng thị trường, Matrix, Sector và trợ lý phân tích."*

### 2.2 Feature Gating (Inferred)

```
Demo     → /dash (limited) + /dash/matrix (partial)
Client   → Full /dash + /dash/matrix + /dash/sector + /dash/cashflow + /dash/trading-chart
Client Pro → All above + /dash/volatility + /dash/multi-layer 
              + /dash/deepfinlens (full) + /dash/finlens-ai (full)
              + /dash/manipulation + /dash/market-watch + /dash/social
```

### 2.3 Sales Process

- **Self-serve**: Đăng ký online → thanh toán VietQR
- **Sales-assisted**: Book demo qua email `finlensstock@gmail.com`
- **Direct support**: Zalo 0903256365

---

## TASK 3: YouTube Channel Analysis (@finlenshq)

> YouTube renders video list client-side via JS. Data từ web research + inferred từ `/huong-dan/video`.

### 3.1 Content Categories

| Category | Description |
|----------|-------------|
| Nhận định thị trường | Phân tích VNINDEX, VN30F1M định kỳ |
| Tutorial dashboard | Hướng dẫn từng module: Quick Quant, Sector, Matrix |
| Sector analysis | Dòng tiền ngành, cổ phiếu dẫn dắt |
| Maker flow | Dòng tiền tổ chức, nhà tạo lập |
| Tips & tricks | Advanced Search, Preset, workflow |

### 3.2 Content Funnel

```
YouTube (awareness/education)
  ↓
Homepage / /huong-dan (interest)
  ↓
/huong-dan/video (deeper learning, YouTube embeds)
  ↓
Demo 14 ngày (trial)
  ↓
Client / Client Pro (conversion)
```

### 3.3 Platform Strategy

- **YouTube**: Long-form tutorials, market analysis → education-first
- **TikTok**: Short-form → younger investors, brand awareness
- **Threads**: Community discussion, Q&A
- **LinkedIn**: B2B, institutional positioning
- **Zalo**: Direct support/sales (Vietnam-specific)

---

## 16 KEY FINDINGS MỚI (Chưa Có Trong Tài Liệu Cũ)

| # | Finding | Category |
|---|---------|----------|
| 1 | Slogan chính xác: *"Đọc thị trường VN bằng dữ liệu, tín hiệu và dòng tiền"* | Brand |
| 2 | Founded 2026 (từ schema.org) – app rất mới | Business |
| 3 | Badge: "Cơ Sở - PS - CW" → cover 3 markets cùng lúc | Product |
| 4 | Anti-iframe embed script → IP protection measure | Security |
| 5 | Custom chunk recovery system → production reliability | Tech |
| 6 | Performance safe mode auto-detect → mobile UX aware | Tech |
| 7 | Skeleton loading screens → professional UX | UX |
| 8 | `/intro` onboarding route riêng → guided first experience | UX |
| 9 | Price confirmed: 2.999.000 VNĐ/3 tháng Client Pro | Pricing |
| 10 | Free trial 14 ngày no credit card | Pricing |
| 11 | Book demo via email với subject template | Sales |
| 12 | Zalo 0903256365 direct support line | Support |
| 13 | Multi-platform: Zalo+TikTok+Threads+LinkedIn (no FB) | Social |
| 14 | TikTok handle @finlensquant.stockapp → short-form content | Social |
| 15 | `/nghien-cuu` route → research/blog content | Content |
| 16 | localStorage key: `finlens-theme` (dark default) | Tech |

---

---

## TASK 1 (UPDATE 2): Confirmed API Endpoints từ Authenticated Requests

> **Nguồn**: DevTools Network tab – Fetch/XHR filter, authenticated session

### Market Data API

```
GET /api/market-data/vietnam?symbol=VNINDEX&years=3&resolution=D
200 OK | Content-Type: application/json | 20.2 kB | 303ms
```

**Params đã xác nhận**:

| Param | Value | Ý nghĩa |
|-------|-------|----------|
| `symbol` | `VNINDEX` | Mã chứng khoán / index |
| `years` | `3` | Số năm lịch sử |
| `resolution` | `D` | Daily candle (tương tự TradingView) |

**Pattern suy ra cho các calls khác**:
```
/api/market-data/vietnam?symbol=VIC&years=1&resolution=D    ← Cổ phiếu 1 năm
/api/market-data/vietnam?symbol=HPG&years=3&resolution=W    ← Weekly
/api/market-data/vietnam?symbol=VN30&years=1&resolution=60  ← 1h
/api/market-data/vietnam?symbol=VNINDEX&years=3&resolution=1 ← 1min?
```

### Custom Finlens Headers (Chưa từng biết)

```http
x-finlens-cache: BYPASS
x-finlens-payload-class: market-data
```

- `x-finlens-cache: BYPASS` → Họ có **caching layer riêng** (Redis/CDN), lần này bypass
- `x-finlens-payload-class: market-data` → Phân loại payload, có thể có: `matrix-data`, `sector-data`, `realtime-data`

### Rate Limiting

```http
x-ratelimit-limit: 2400
x-ratelimit-remaining: 2399
x-ratelimit-reset: 1784043713    ← Unix timestamp
```

- **2400 requests/window** → rất thoải mái cho production
- Window: cần tính từ `reset` timestamp: `1784043713` = khoảng 1 giờ tới (cần verify)
- **Implication cho scraper**: Có thể gọi ~40 req/phút mà không bị block

### Other Endpoints từ Network List

| Endpoint | Notes |
|----------|-------|
| `latest-update` | Polling endpoint, gọi 3+ lần (interval-based) |
| `sync` | Heartbeat / session sync, 8 giây long-poll |
| `trading_chart?_rsc=...` | RSC prefetch cho `/dash/trading-chart` |
| `social?_rsc=...` | RSC prefetch cho `/dash/social` |

### Cấu Trúc API (Inferred)

```
https://finlensquant.vn
├── /api/
│   ├── /market-data/vietnam    ← OHLCV data
│   ├── /latest-update          ← Latest signals/updates
│   ├── /sync                   ← Session/state sync
│   ├── /matrix?                ← (inferred) Matrix data
│   ├── /sector?                ← (inferred) Sector data
│   └── /cashflow?              ← (inferred) Cashflow data
└── /dash/* (RSC routes)
```

### 502 Bad Gateway (Observed)

Khi navigate trực tiế URL API lên browser không có cookies → nginx không route được → 502.  
Không phải server down — đây là hành vi bảo vệ: **chặn browser direct access**.

---

## TASK 1 (UPDATE): Authenticated Session – Network Analysis từ DevTools

> **Nguồn**: User's DevTools Network tab sau khi login thành công (14/07/2026 15:33–15:34 UTC)

### Auth Architecture (Confirmed từ Real Requests)

**Session Token**: `__Secure-authjs.session-token`
- Algorithm: **JWE `dir` + `A256CBC-HS512`** (JSON Web Encryption, Direct Key Agreement)
- Key ID: `xVSA9stGCSgjtTKgdfeRAtjo7-h3oyDg5I2R4ih8Q6uMd5CMtVBrVNSFEVgEtywviIih1BqUzU47oXaTd3ZP6g`
- Cookie flags: `HttpOnly; Secure; SameSite=Lax`
- **Expiry: 12 giờ** (set 15:33 UTC → expires 03:33 UTC hôm sau)
- **Rolling session**: Mỗi request đều renew session token mới → token thay đổi liên tục

**CSRF Token**: `__Host-authjs.csrf-token` (prefix `__Host-` = most secure, bound to exact host)

**Callback URL Cookie**: `__Secure-authjs.callback-url=https://finlensquant.vn/intro`

**Sidebar State**: `sidebar_state=true` → lưu UI state trong cookie (không phải localStorage)

### RSC (React Server Components) Pattern

```
GET /dash?_rsc=<random_nonce>
Content-Type: text/x-component    ← RSC payload format
RSC: 1                            ← RSC request header
next-router-prefetch: 1           ← prefetch mode
next-router-segment-prefetch: /_tree
```

**Giải thích**: Đây là Next.js App Router RSC streaming. Khi navigate `/dash`:
1. Browser gửi RSC request với random nonce (`_rsc=xxx`) để bypass cache
2. Server trả về `text/x-component` (RSC payload) thay vì HTML
3. Multiple parallel RSC requests = prefetch cho các segments của layout tree

**Route state header** (decoded từ `next-router-state-tree`):
```json
["", {
  "children": [
    "(protected)", {
      "children": [
        "dash", {
          "children": ["__PAGE__", {}]
        }, null, "refetch"
      ]
    }
  ]
}]
```
→ **Xác nhận 100%**: Route group `(protected)` → `dash` → `__PAGE__` (Next.js App Router convention)

### Server Infrastructure (Confirmed)

| Property | Value | Implication |
|----------|-------|-------------|
| Server | `nginx/1.26.2` | Reverse proxy, latest stable |
| IP | `27.71.27.62` | Vietnamese IP (VPS nội địa) |
| Protocol | HTTPS (port 443) | TLS enforced |
| Encoding | `gzip` | Compression enabled |
| Transfer | `chunked` | Streaming responses |
| HSTS | `max-age=31536000; includeSubDomains; preload` | Full HSTS |

### Security Headers (Production-Grade)

```
content-security-policy: frame-ancestors 'none'; base-uri 'self'; object-src 'none'
x-frame-options: DENY
x-content-type-options: nosniff
permissions-policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), 
                    magnetometer=(), microphone=(), payment=(), usb=(), interest-cohort=()
referrer-policy: strict-origin-when-cross-origin
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

**Phân tích bảo mật**:
- `frame-ancestors 'none'` + `X-Frame-Options: DENY` = Double-layer anti-clickjacking
- `interest-cohort=()` = Opt-out khỏi Google FLoC
- `payment=()` = Disable Payment Request API (dù có VietQR nhưng không dùng browser API)
- **No Cache** (`no-cache, no-store, max-age=0, must-revalidate`) cho authenticated routes = Prevent sensitive data caching

### RSC Prefetch Behavior (Performance Pattern)

Từ requests với `next-router-segment-prefetch: /_tree`:
- Browser prefetch **layout tree** của `/dash` ngay khi còn ở `/intro`
- `referer: https://finlensquant.vn/intro` → Prefetch triggered từ `/intro` page
- **Implication**: Onboarding `/intro` chủ động preload `/dash` → zero-latency transition

### User Agent & Client Info

```
Microsoft Edge 150 / Chrome 150 / Windows 10 x64
sec-ch-ua-platform: "Windows"
sec-fetch-mode: cors
sec-fetch-site: same-origin
```

### Caching Strategy (Authenticated Routes)

```
cache-control: no-cache, no-store, max-age=0, must-revalidate
pragma: no-cache
expires: 0
vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch, Accept-Encoding
```

**Vary header** = CDN/proxy sẽ cache riêng biệt cho mỗi combination của RSC headers → đúng pattern cho Next.js RSC

---

## Việc Còn Cần Auth Để Hoàn Thành

| Task | Cần làm gì |
|------|-----------|
| Pricing exact table | Login → /pricing → screenshot table |
| Feature comparison | Login → /pricing → scroll đến feature matrix |
| API endpoints | DevTools Network tab → filter XHR/Fetch → reload /dash |
| WebSocket | DevTools Network tab → tab WS → xem frames |
| Dashboard screenshots | Login → /dash và các sub-routes |
| Actual pricing of Client (không Pro) | Pricing page sau login |

**Quick guide** để capture khi bạn login:
1. Mở DevTools (F12) → tab Network → filter `Fetch/XHR`
2. Navigate `/dash` → ghi lại tất cả API calls (URL, method, response)
3. Tab WS → xem WebSocket frames
4. Screenshot `/pricing` khi đã load
