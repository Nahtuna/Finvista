# FINLENS – BÓC TÁCH TOÀN DIỆN (Deep Reverse Engineering)

> **Nguồn**: Kết hợp bóc tách thực địa từ browser (authenticated session), 132 file ảnh mẫu,
> tài liệu PDF/video hướng dẫn, và phân tích tĩnh HTML/CSS/JS của finlensquant.vn.
> **Phạm vi**: Tất cả trang, module, API pattern, mô hình toán học, và kiến trúc kỹ thuật.

---

## 1. Kiến Trúc Kỹ Thuật Tổng Quan

### Frontend Stack (Xác nhận)

| Layer | Technology | Evidence |
|-------|-----------|----------|
| Framework | **Next.js 13+** | Route `/auth/login?callbackUrl=%2Fdash`, middleware redirect |
| UI Library | **React + MUI** | Class prefix `MuiTypography-root`, `css-nb8zgt` (Emotion hash) |
| Styling | **Tailwind CSS + Emotion** | `flex items-center gap-2.5 rounded-[10px]`, hashed classes |
| Auth | **NextAuth.js** | `/auth/login?callbackUrl=`, `?reason=unauthenticated` pattern |
| State | React Context + SWR/React Query | Hooks: `useMatrix`, `useSector`, `useRealtime` |
| Charts | **ECharts** hoặc **Highcharts** | Heatmap, Scatter, Stacked Bar, Radar capability |
| Font | Inter, Roboto | CSS analysis |

### Backend Stack

| Layer | Technology |
|-------|-----------|
| API Server | Node.js (Express/Fastify) hoặc Python (FastAPI) |
| Real-time | WebSocket (`wss://finlensquant.vn/ws`) |
| Database | PostgreSQL + Redis (caching) + TimescaleDB (time-series) |
| Auth | JWT httpOnly cookie, 7-day expiry + refresh token |
| Payment | VietQR EMVCo hoặc PayOS/Casso |
| CDN | Cloudflare (suspected) |

### Sidebar Navigation (Left sidebar – Dashboard)

```
Quick Quan[t]     ← Module 1 (default)
Trading Char[t]   ← Module 2
Sector Boar[d]    ← Module 3
Cashflow          ← Module 4
Matrix            ← Module 5
Volatility
Multi-Layer
Deep Finle[ns]    ← Module 6
Finlens AI        ← Module 7
[Manipulation]
Market Watc[h]
Social
```

---

## 2. Cấu Trúc Route

### Public
```
/                           Homepage
/ma-tran-dinh-luong         Matrix showcase
/sector-rotation            Sector feature
/dong-tien-to-chuc          Maker flow
/huong-dan                  Docs
/pricing                    Bảng giá
/auth/login, /auth/register
```

### Protected (yêu cầu auth)
```
/dash                       Main Dashboard (Quick Quant mặc định)
/dash/trading-chart
/dash/sector
/dash/cashflow
/dash/matrix
/dash/volatility
/dash/multi-layer
/dash/deepfinlens
/dash/finlens-ai
/dash/manipulation
/dash/market-watch
/dash/social
/intro                      Onboarding
```

### 3 Tabs trong Quick Quant
```
Tab 1: Scatter Plot (Maker vs Score)              [NÊN CHÚ Ý]
Tab 2: Sector Correlation / RRG                   [USER] [CẤU TRÚC NGÀNH]
Tab 3: Breadth + Maker Flow Regime Analysis       [USERPRO] [REGIME]
```

---

## 3. Module 1: Quick Quant (Dashboard)

### Scatter Plot

**Controls**:
```
[Scatter] [RRG] toggle
X: Maker (SB3MK0A)  Y: Score (SB3SC0A)  Size: ClosexVolAvg
[raw] [z] [avg5] [std5]  ← transform modes
● All ON  GREEN(6)  YELLOW(2)  RED(21)  TRANS(1)
labels: ALL | [Guide] [Reset]
```

**Stats bar**:
```
r: 0.86  R²: 0.74  β₀: 0.43  RMSE: 0.41
n: 30    μx: -0.66  μy: -1.95
[Show Stats]
```

**4 Quadrants**:
```
Q1 top-right:    "Leadership (Đẩy)"          Maker↑ Score↑  BUY
Q2 top-left:     "Improving (Kéo Test Cung)" Maker↓ Score↑  WATCH
Q3 bottom-right: "Accumulation (Gom Im)"     Maker↑ Score↓  ACCUMULATE
Q4 bottom-left:  "Pressure (Đỡ)"             Maker↓ Score↓  AVOID
```

**Bubble encoding**:
- Color: GREEN / YELLOW / RED / TRANS
- Number inside = Rank (1 = best)
- Size = ClosexVolAvg (thanh khoản * giá)

**Field naming pattern**:
- `SB3MK0A` = rolling **3**-bar **Maker** score, period **0**, version **A**
- `SB3SC0A` = rolling **3**-bar **Score**, period **0**, version **A**
- `ClosexVolAvg` = Close price × average volume

### Pareto View

**Header**:
```
Universe: 1542   rowDataFull   Top 30   MakerCut: 0   Pareto 50%
Items: 30  | Top α mean: 17.61 | α median: 10.59 | α max: 24.05 | GreenCut: 0.00
Sort: Alpha | Search: ticker/sector | [FULL] [PARETO] [SCATTER] | Settings | Reset
```

**Chart lines** (multi-line):
```
Vol, Maker, Maker roll, Alpha (red), Score (yellow), Trend (light green), Pareto % (teal)
GreenCut horizontal line
```

**X-axis**: Ticker labels với màu dots (● GREEN ● YELLOW ● RED)

---

## 4. Module 3: Sector Board

### Sector Table Columns

| Cột | Ví dụ |
|-----|-------|
| Sector | G_HANGKHONG, Ngân Hàng |
| Δ% | +0.1%, -0.0% |
| Rank ngành | #1, #11 |
| Quant Flow | 41, 25 (bar visual) |
| Maker Trend | mini sparkline |
| Price | mini sparkline |
| Score | 0.00, -1.90 |
| Maker ↓ | 2.38, -0.44 |
| SLong | +2.75, +0.48 |
| Adv | +2.38, +1.46 |
| Xếp hạng Maker | 1, 6 |
| Xếp hạng SLong | 3, 8 |

### Sector Detail Page (per-sector)

**Header**:
```
Tên ngành: "Ngân Hàng"
Rank ngành: #11  | Quant Flow: 25/100 | Biến động giá: -0.0%
Z-Maker: +0.67   | Động lượng 10P: -0.59
```

**KPI Cards**:
```
Điểm: -1.90  Maker: -0.44  Rank ngành: #11  Đổi rank: -1
Độ rộng: 24%  VolR: 0.29
```

**4-Panel Analysis**:

**Panel 1 – Quant Flow Liên Tầng**:
```
Market regime: CO HẸP (Breadth TB 14%)
Sector alpha: 25 | Rank impulse: -1 | Stock outlier: 0 | Total stocks: 28
Bars: Sector rank score / Maker power / Liquidity layer / Breadth confirmation
```

**Panel 2 – Rank Trail**:
```
Maker rank trail:  [#10 → #9 → #6 → #5 → #6]
SLong rank trail:  [#10 → #9 → #9 → #8 → #8]
Top stocks: ACB (Maker 1.71, VolR 0.19), OCB (Maker 2.82, VolR 0.44)
```

**Panel 3 – Kịch Bản Giá (GBM Fan Chart)**:
```
X-axis: -20 phiên lịch sử → +5 phiên tương lai
3 scenarios: Trung vị | Biên trên (Xác suất tích cực) | Biên dưới (Thận trọng)
```

**Panel 4 – Bảng Tín Hiệu**:
```
Độ rộng: 24% bar
Thanh khoản: 0.29 bar
Biến động: 1.33% bar
Động lượng: -0.59 bar
Nhận định: text AI-generated
```

---

## 5. Module 5: Market Signal Matrix

### Table Structure (T0-T19)

**Rows**: 53 mã chứng khoán (có thể lọc)

**Columns**: Ticker | T19 | T18 | ... | T1 | T0 | Score | Maker ↓ | Volume

**Header**:
```
ROWS: 53 | SCORE+: 2 | SCORE-: 51 | TOP MK: VJC +3.0 | WEAK MK: LPB -3.4
```

**Signal Badges**:

| Badge | Màu | Nghĩa |
|-------|-----|-------|
| `GOOD` | Xanh lá | Tín hiệu tốt |
| `FAIR` | Xanh dương | Trung bình |
| `MODER` | Cam | Trung bình yếu |
| `WEAK` | Đỏ | Yếu |
| `BAD` | Đỏ đậm | Xấu |
| `STRONG` | Tím | Rất mạnh |
| `-->` `<--` | Xám | Trending direction |
| `+` `++` `+++` | Xanh nhạt | Momentum up |
| `-` `--` `---` | Đỏ nhạt | Momentum down |

### Per-Ticker Detail (tabs: Stability | Score | Maker | Slong | Full)

#### Slong Tab (VCB example)

**Header metrics**:
```
CURRENT SLONG: 0.61  |  ΔD: -0.10  |  AVG5: 1.21  |  STRD5: -0.49
```

**Chart**: T49→T0 (history) + F1→F5 (forecast)
Lines: Actual(orange), Forecast(white dashed), Delta(green), Rank 10D
Reference: Mean, Median, Q1-Q3, ±1σ, MAX50D, MIN50D, Market Mean

**Statistical Levels** (40 phiên):
```
MIN: -5.86 | MAX: 4.29 | MEAN: -0.70 | MEDIAN: -0.52
Q1: -2.97  | Q2: -0.52  | Q3: 1.67
```

**Core Snapshot**:
```
LATEST: 0.61  | Δ1D: -0.10  | Δ5D: -1.17
AVG5: 1.21   | AVG20: 2.07
STD5: 0.55   | STD20: 1.58  | Z20: -0.92
```

#### Stability Tab

```
Signal: X5(0%)   ← Pattern code (X=cross, 5=strength, 0%=price Δ)
Breadth: Range3  ← Breadth category
STATE: Transition | Confidence: 37%
Recent Signal: 2×10 grid of +/- history
Forecast: m:7, c:37% → 5 ô [-,-,-,-,-]  (t+1 to t+5)
```

#### Score Tab

```
SCORE: -1.48  |  ΔD: -0.38  |  AVG: -1.25  |  STRD: -0.18
FORECAST: m:2, c:65% → [-1, 0, 0, -1, -1]
RECENT 20: 2×10 grid
RANK 10D
```

#### Maker Tab

```
MAKER: -0.55  |  ΔD: -0.67  |  AVG: -0.04  |  STRD: -0.26
FORECAST: m:0, c:32% → [-1,-1,-1,-1,-1]
```

#### Full View (Stability + Score + Maker + SLong side-by-side)

**Status Header**:
```
VCB (0%)       Ngân hàng Thương mại Cổ phần Ngoại thương Việt Nam
VolAvg: 6,354,626  |  Sector: B_TAI CHINH - NGAN HANG  |  VolScore: 16/100
LỢI THẾ TỔ CHỨC: 0.93 (Maker - Score)
TREND HISTORY: GGYYRRRRRR   ← 10-char G/Y/R string
STATUS: RED 6.0             ← màu + số phiên tiếp diễn
```

---

## 6. Module 6: DeepFinLens Classification

### Global Header

```
COVERAGE: 403 tracked symbols
PULSE: -0.32     (forecast average toàn thị trường)
BREADTH: -279    (positive - negative signals)
MAKER AVG: -0.93
SCORE AVG: -1.93
```

### Leader/Laggard Panels (VN30 filter)

```
Leader VN30:      ACB #17VN30 +0.5
Suy Yếu VN30:     LPB #14VN30 -0.7, DGC #64VN30 -0.7, ...
Theo Dõi VN30:    TPB, SSB, VHM, GAS, STB, VIC
Forecast Leader:  ACB, VJC, PLX, THD, NVB, HQC (LEAD+)
Forecast Suy Yếu: LPB, DGC, MSN, VRE, TCB, MBB (YẾU-)
```

### 7 Classification Buckets

```
🔴 Siêu Yếu   (11-22 mã)    ← worst
🟠 Khá Yếu    (68-108 mã)
🟡 Kém        (109-145 mã)
🔵 Trung Bình (86-113 mã)
🟢 Ổn Định    (17-37 mã)
🟩 Tốt        (17-23 mã)
💚 Rất Tốt    (8-26 mã)     ← best
```

**Per-ticker badge**: `VJC #17VN30 L+ | UV | TD | Y-`
- `L+/L-` = Lead positive/negative forecast
- `UV` = Universe (không phải VN30)
- `TD` = Trend Direction
- `Y-/Y+` = Yearly forecast direction

---

## 7. Hệ Thống API & WebSocket

### API Endpoints (Predicted from static analysis)

```
BASE: https://finlensquant.vn

# Auth (NextAuth)
POST /api/auth/login              { email, password }
POST /api/auth/register
POST /api/auth/logout
GET  /api/auth/session

# Market Data
GET  /api/market/scatter          Scatter plot data
GET  /api/market/pareto           Pareto chart
GET  /api/market/matrix           Market Signal Matrix
GET  /api/market/sector           Sector table
GET  /api/market/cashflow         Cashflow data
GET  /api/market/regime           Market regime state

# Ticker Detail
GET  /api/ticker/{symbol}/stability
GET  /api/ticker/{symbol}/score
GET  /api/ticker/{symbol}/maker
GET  /api/ticker/{symbol}/slong
GET  /api/ticker/{symbol}/full

# Sector Detail
GET  /api/sector/{code}/detail
GET  /api/sector/{code}/stocks

# User
GET  /api/user/watchlist
POST /api/user/watchlist
GET  /api/user/subscription

# Payment
POST /api/payment/vietqr
POST /api/payment/verify

# Guide
GET  /api/guide/user-guide-pdf
```

### Query Parameters

```
GET /api/market/scatter?
  x=SB3MK0A           X axis field
  y=SB3SC0A           Y axis field
  size=ClosexVolAvg   Bubble size
  mode=raw            raw|z|avg5|std5
  n=30                Top N stocks
  pareto=50           Pareto cutoff %
  sort=maker          Sort column
  order=desc

GET /api/market/matrix?
  sort=maker&order=desc&page=1&limit=100&sector=ngan-hang
```

### WebSocket

```
WSS: wss://finlensquant.vn/ws

# Subscribe messages
→ { "action": "subscribe", "topic": "market_updates" }
→ { "action": "subscribe", "topic": "scatter", "params": {"n": 30} }
→ { "action": "subscribe", "topic": "regime" }
→ { "action": "ping" }

# Server push (inferred)
← { "type": "matrix_update", "data": [...] }
← { "type": "regime_change", "regime": "CO_HEP", "breadth": 0.24 }
← { "type": "heartbeat", "ts": 1689000000 }

# Update frequencies
Matrix scores:    every 5 min
Sector rotation:  every 15 min
Maker flow:       every 1 min
Prices:           real-time
```

### Auth Headers

```http
Cookie: next-auth.session-token=<JWT>
Content-Type: application/json
Referer: https://finlensquant.vn/dash
```

---

## 8. Mô Hình Toán Học

### 8.1 Core Variables

| Ký hiệu | Full name | Mô tả | Horizon |
|---------|-----------|-------|---------|
| **MK** | Maker | Institutional short-term flow (market makers) | < 30 ngày |
| **SLong** (SH) | SLong | Institutional long-term (quỹ, NĐTNN) | ≥ 30 ngày |
| **SC** | Score | Retail short-term flow | < 7 ngày |

### 8.2 Derived Indicators

```
Advantage = MK - SC         (> 0 = institutional dominates)
Momentum  = ΔMK             (> 0 = accumulating)
Alpha     = MK - market_avg (relative excess)
Z20       = (current - AVG20) / STD20
```

### 8.3 Market Regime

```python
def classify_regime(breadth, volR):
    if breadth > 0.45 and volR > 1.05:   return "EXPANSION"
    elif breadth < 0.35 or volR < 0.95:  return "CONTRACTION"
    else:                                 return "CHOPPY"
```

### 8.4 OLS Projection

```python
# Sector/stock trend projection
lookback = 30-50 phiên
X = arange(lookback)
model = LinearRegression().fit(X, flow_series[-lookback:])
forecast_5 = model.predict(arange(lookback, lookback+5))
r_squared  = model.score(X, flow_series)
```

### 8.5 GBM Price Fan

```python
# Brownian Motion price scenario bands
mu    = ols_slope        # drift từ OLS
sigma = std_20           # volatility từ STD20

# 3 bands
median = S0 * exp((mu - 0.5*sigma**2) * t)
upper  = S0 * exp((mu + sigma * Z_95) * sqrt(t))
lower  = S0 * exp((mu + sigma * Z_05) * sqrt(t))
```

### 8.6 Stability Forecast

```
Output: m:[mode], c:[confidence]%
5 forecasts: [t+1, t+2, t+3, t+4, t+5] each = -1 | 0 | +1
```

### 8.7 Trend History String

```
Format: "GGYYRRRRRR" (10 chars, newest-right hoặc newest-left)
G = Green (Maker > threshold)
Y = Yellow (neutral)
R = Red (Maker < -threshold)

Status = "RED 6.0" = đỏ liên tiếp 6 phiên
```

### 8.8 Scatter Regression (Displayed on chart)

```
r     = Pearson correlation(X, Y)
R²    = r²
β₀    = OLS intercept
RMSE  = Root Mean Square Error
n     = sample size
μx/μy = means
```

---

## 9. Data Schemas (JSON)

### Ticker Object

```json
{
  "symbol": "VCB",
  "sector": "B_TAI_CHINH_NGAN_HANG",
  "vol_avg": 6354626,
  "vol_score": 16,
  "maker": -0.55,
  "score": -1.48,
  "slong": 0.61,
  "advantage": 0.93,
  "momentum": -0.10,
  "trend_history": "GGYYRRRRRR",
  "status": "RED",
  "status_days": 6.0,
  "stability": {
    "signal": "X5(0%)",
    "breadth_category": "Range3",
    "state": "Transition",
    "confidence": 0.37
  },
  "forecast": {
    "stability": [-1, -1, -1, -1, -1],
    "score":     [-1,  0,  0, -1, -1],
    "maker":     [-1, -1, -1, -1, -1],
    "slong":     [ 1,  1,  0,  0,  0],
    "mode": 7,
    "confidence": 0.37
  },
  "stats": {
    "min50": -5.86, "max50": 4.29,
    "mean": -0.70,  "median": -0.52,
    "q1": -2.97,    "q2": -0.52, "q3": 1.67,
    "avg5": 1.21,   "avg20": 2.07,
    "std5": 0.55,   "std20": 1.58, "z20": -0.92,
    "delta_1d": -0.10, "delta_5d": -1.17
  },
  "matrix_periods": {
    "T0": null, "T1": "-", "T2": "-->",
    "T6": "FAIR", "T8": "FAIR", "T11": "+",
    "T12": "FAIR", "T13": "-"
  },
  "score_value": -1.48,
  "maker_value": -0.55,
  "volume": 6354626
}
```

### Sector Object

```json
{
  "sector_name": "Ngân Hàng",
  "sector_code": "B_TAI_CHINH_NGAN_HANG",
  "rank": 11,
  "delta_rank": -1,
  "quant_flow": 25,
  "maker": -0.44,
  "score": -1.90,
  "slong": 0.48,
  "advantage": 1.46,
  "breadth": 0.24,
  "volr": 0.29,
  "volatility": 0.0133,
  "momentum_10p": -0.59,
  "z_maker": 0.67,
  "regime": "CO_HEP",
  "sector_alpha": 25,
  "rank_impulse": -1,
  "total_stocks": 28,
  "maker_rank_trail": [10, 9, 6, 5, 6],
  "slong_rank_trail": [10, 9, 9, 8, 8],
  "top_stocks": [
    {"symbol": "ACB", "maker": 1.71, "volr": 0.19, "alpha": 0.0},
    {"symbol": "OCB", "maker": 2.82, "volr": 0.44}
  ]
}
```

### Scatter Point Object

```json
{
  "symbol": "VJC",
  "rank": 3,
  "x": 3.48,
  "y": 0.5,
  "size": 2500000,
  "color": "GREEN",
  "quadrant": "Leadership"
}
```

---

## 10. Auth & Phân Quyền

### 3 Gói tài khoản

| Plan | Tính năng | Thiếu |
|------|----------|-------|
| **Demo** (7 ngày) | Dashboard 2/3 charts, Partial Matrix | Deep Analysis, AI giới hạn |
| **Client** | Full Dashboard, Full Matrix | Deep Analysis, AI giới hạn |
| **Client Pro** | Tất cả + Sector extensions, Deep Analysis | Nothing |

### Auth Flow

```
POST /api/auth/login { email, password }
→ JWT httpOnly cookie (next-auth.session-token)
→ Expiry: 7 ngày + refresh token
→ Protected routes: check cookie → redirect /auth/login?callbackUrl=
```

---

## 11. Thanh Toán VietQR

```
POST /api/payment/vietqr
Body: { plan: "client_pro", months: 1 }
Response: { qr_data, qr_image_url, amount, content, bank, account, expire_at }

# Check payment (long polling hoặc WS push)
GET /api/payment/verify?order_id={id}

# Webhook từ ngân hàng → server
POST /webhook/payment/callback
{ transaction_id, amount, status: "SUCCESS" }
→ Server tự động nâng cấp plan
```

---

## 12. Field Reference Table

| FinLens Display | Field Name | Type | Description |
|----------------|-----------|------|-------------|
| Maker | `maker` / `SB3MK0A` | float | Institutional maker score |
| Score | `score` / `SB3SC0A` | float | Retail sentiment score |
| SLong | `slong` | float | Long-term institutional |
| Advantage | `advantage` | float | Maker - Score |
| Momentum | `momentum` | float | ΔMaker |
| Breadth | `breadth` | float | % advancing stocks |
| VolR | `volr` | float | Volume ratio vs avg |
| Alpha | `alpha` | float | Excess return vs market |
| Pareto % | `pareto_pct` | float | Cumulative Pareto % |
| GreenCut | `green_cut` | float | Pareto green threshold |
| T0..T19 | `period_T{n}` | string | Matrix signal per period |
| Trend History | `trend_history` | string(10) | G/Y/R string |
| Forecast t+1-5 | `forecast[0-4]` | int[] | -1/0/+1 per period |
| Confidence | `forecast_confidence` | float | Forecast probability |
| Z20 | `z_score_20d` | float | Z-score vs 20-day avg |
| Status | `status` | string | GREEN/YELLOW/RED |
| Status Days | `status_days` | float | Days in current status |

---

## 13. Tasks Thực Thi Tiếp Theo

### URGENT (sau khi browser quota reset ~4h)

- [ ] Bắt JWT token từ DevTools → Application → Cookies → `next-auth.session-token`
- [ ] Dùng token gọi curl: `GET /api/market/scatter` → schema thực tế
- [ ] Gọi `GET /api/market/matrix` → schema thực tế
- [ ] Gọi `GET /api/market/sector` → schema thực tế
- [ ] Kết nối WebSocket `wss://finlensquant.vn/ws` → ghi lại messages

### Database Schema Finvista

- [ ] Migration: `finlens_ticker_signals` table
- [ ] Migration: `finlens_sector_data` table
- [ ] Migration: `finlens_matrix_periods` table
- [ ] Field mapping → snake_case chuẩn Finvista

### Scraper Development

- [ ] `finlens_client.py` với session auth + retry
- [ ] WebSocket client cho real-time stream
- [ ] Checkpoint/resume state manager
- [ ] Cron: 5 phút trong 9:00-15:00 (giao dịch), 17:00 (EOD)

---

*Last updated: 2026-07-14 | Cần xác minh API endpoints thực tế sau khi browser quota reset*
