# 04. Features Flow - FinLens Clone

## 📋 Overview

Tài liệu này chi tiết hóa luồng đi của từng tính năng theo format **User Story + Acceptance Criteria** để AI có thể implement chính xác logic và UX.

---

## 🔐 Authentication Module

### Feature: User Registration

**User Story**: Là một user mới, tôi muốn đăng ký tài khoản để sử dụng các tính năng cơ bản của FinLens.

**Acceptance Criteria**:
- [ ] User nhập email, username, password (min 8 ký tự, bao gồm chữ hoa, chữ thường, số)
- [ ] Hệ thống validate email format và username uniqueness
- [ ] Password được hash bằng bcrypt trước khi lưu vào database
- [ ] Tài khoản mặc định có subscription_tier = "demo"
- [ ] Gửi email verification link sau khi đăng ký thành công
- [ ] Trả về JWT access token và refresh token
- [ ] Log registration event cho monitoring

**Luồng xử lý (Logic)**:
```
1. User nhập thông tin → Frontend validate
2. POST /api/v1/auth/register → Backend validate
3. Check email/username uniqueness trong database
4. Hash password → Insert vào users table
5. Generate JWT tokens → Return response
6. Send verification email → Async task
7. Log event → api_logs table
```

**API Endpoint**: `POST /api/v1/auth/register`

**Edge Cases**:
- Email đã tồn tại → Return 400 với message "Email already exists"
- Username đã tồn tại → Return 400 với message "Username already exists"
- Password không đủ mạnh → Return 400 với validation errors
- Email service down → Queue email, không block registration

---

### Feature: User Login

**User Story**: Là một user đã đăng ký, tôi muốn đăng nhập để truy cập các tính năng theo subscription tier của mình.

**Acceptance Criteria**:
- [ ] User nhập email và password
- [ ] Hệ thống verify credentials và generate JWT tokens
- [ ] Access token expires sau 15 phút, refresh token sau 7 ngày
- [ ] Tokens được lưu trong httpOnly cookie (security)
- [ ] Return user profile với subscription tier
- [ ] Log login event với IP và user agent

**Luồng xử lý (Logic)**:
```
1. User nhập credentials → Frontend validate
2. POST /api/v1/auth/login → Backend verify
3. Hash input password → Compare với database
4. Generate access_token (15min) + refresh_token (7days)
5. Set httpOnly cookies → Return response
6. Log login event → api_logs table
7. Update last_login_at trong users table
```

**API Endpoint**: `POST /api/v1/auth/login`

**Edge Cases**:
- Sai password → Return 401 với message "Invalid credentials"
- Tài khoản không active → Return 403 với message "Account inactive"
- Quá nhiều lần login failed → Rate limit + CAPTCHA
- Token generation failed → Return 500 với log error

---

### Feature: Token Refresh

**User Story**: Là một user đang sử dụng app, tôi muốn access token được tự động refresh để không bị logout giữa chừng.

**Acceptance Criteria**:
- [ ] Frontend gọi refresh API trước khi access token expired
- [ ] Backend verify refresh token validity
- [ ] Generate new access token
- [ ] Invalidate old refresh token (rotation)
- [ ] Return new access token

**Luồng xử lý (Logic)**:
```
1. Frontend detect token即将过期 (13min)
2. POST /api/v1/auth/refresh với refresh_token
3. Backend verify refresh_token signature + expiry
4. Generate new access_token
5. Invalidate old refresh_token → Generate new refresh_token
6. Return new tokens
```

**API Endpoint**: `POST /api/v1/auth/refresh`

**Edge Cases**:
- Refresh token expired → Return 401, redirect to login
- Refresh token revoked → Return 401, redirect to login
- Refresh token reused → Detect attack, revoke all tokens

---

## 📊 Dashboard Module

### Feature: CW Scatter Plot Visualization

**User Story**: Là một trader, tôi muốn xem scatter plot phân bổ CW theo Delta vs Premium để nhanh chóng nhận diện cơ hội.

**Acceptance Criteria**:
- [ ] Scatter plot hiển thị tất cả CW đang active
- [ ] X-axis: Delta (0-1), Y-axis: Premium (%)
- [ ] Size of bubble: Volume trading
- [ ] Color: Opportunity score (heatmap: đỏ → vàng → xanh)
- [ ] Hover tooltip: Hiển thị chi tiết CW (symbol, price, Greeks)
- [ ] Click vào bubble: Mở modal chi tiết CW
- [ ] Filter: Theo underlying, issuer, days to maturity
- [ ] Real-time update: WebSocket stream mỗi 5 giây

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/cw/dashboard
2. Backend query cw_market_data + cw_analytics (latest)
3. Calculate x (delta), y (premium_pct), size (volume), color (opportunity_score)
4. Return scatter_data array
5. Frontend render với D3.js scatter plot
6. WebSocket subscribe → Real-time updates
7. User filter → Re-fetch với query params
```

**API Endpoint**: `GET /api/v1/cw/dashboard`

**WebSocket Channel**: `cw_prices`

**Edge Cases**:
- Không có data → Hiển thị empty state với message
- WebSocket disconnect → Fallback to polling (30s)
- Too many points (>500) → Implement pagination or clustering
- Mobile view → Simplified chart hoặc hide

---

### Feature: CW Pareto Chart Analysis

**User Story**: Là một trader, tôi muốn xem Pareto chart để xác định top 20% CW mang lại 80% lợi nhuận tiềm năng.

**Acceptance Criteria**:
- [ ] Pareto chart hiển thị CW theo expected return
- [ ] X-axis: CW symbols, Y-axis: Expected return (%)
- [ ] Line chart: Cumulative return
- [ ] Highlight: Top 20% CW với màu khác
- [ ] Tooltip: Hiển thị exact return và cumulative % 
- [ ] Sort: Theo expected return descending
- [ ] Filter: Theo strategy (balanced, safe, aggressive)

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/cw/dashboard?strategy=balanced
2. Backend calculate expected_return = theoretical_price / current_price - 1
3. Sort by expected_return DESC
4. Calculate cumulative_return
5. Identify top 20% cutoff
6. Return pareto_data array
7. Frontend render với Recharts mixed chart (bar + line)
```

**API Endpoint**: `GET /api/v1/cw/dashboard`

**Edge Cases**:
- Negative expected returns → Hiển thị nhưng color khác
- Missing theoretical_price → Skip CW hoặc calculate fallback
- Large dataset (>100 CW) → Show top 50 only

---

## 🌊 DeepFinLens Module

### Feature: Matrix Visualization (10x10)

**User Story**: Là một trader chuyên nghiệp, tôi muốn xem ma trận 10x10 để phân tích cơ hội theo regime (maturity vs moneyness).

**Acceptance Criteria**:
- [ ] Matrix grid 10x10 cells
- [ ] X-axis: Maturity buckets (1-10, 1 = sắp đáo hạn, 10 = dài hạn)
- [ ] Y-axis: Moneyness buckets (1-10, 1 = deep OTM, 10 = deep ITM)
- [ ] Cell color: Opportunity score (gradient)
- [ ] Cell content: CW count, avg score, recommendation
- [ ] Click vào cell: Mở modal hiển thị CW list trong cell
- [ ] Filter: Theo regime (bull, bear, sideways)
- [ ] Trend indicators: 3D, 7D, 30D trend arrows
- [ ] Auto-refresh: Mỗi 5 phút

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/deepfinlens/matrix
2. Backend query cw_analytics + cw_info
3. Calculate maturity_bucket = floor(days_to_maturity / 30) + 1 (max 10)
4. Calculate moneyness_bucket = floor((current_price / strike_price) * 10) (max 10)
5. Group by (maturity_bucket, moneyness_bucket)
6. Calculate avg metrics per cell
7. Determine recommendation based on avg_score + stability
8. Return matrix array (100 cells)
9. Frontend render grid với React-Flow hoặc custom CSS grid
```

**API Endpoint**: `GET /api/v1/deepfinlens/matrix`

**Edge Cases**:
- Empty cells → Hiển thị với màu xám, "No data"
- Extreme values → Clamp color scale để tránh misleading
- Mobile view → Scrollable hoặc simplified view

---

### Feature: Matrix Cell Detail

**User Story**: Là một trader chuyên nghiệp, tôi muốn xem chi tiết các CW trong một ô ma trận để ra quyết định cụ thể.

**Acceptance Criteria**:
- [ ] Modal hiển thị list CW trong cell
- [ ] Table columns: Symbol, Underlying, Delta, Premium, Score, Signal
- [ ] Sortable: Theo bất kỳ column nào
- [ ] Filter: Theo decision signal (buy, sell, hold)
- [ ] Click row: Mở CW detail modal
- [ ] Export: CSV export của table

**Luồng xử lý (Logic)**:
```
1. User click cell → GET /api/v1/deepfinlens/matrix/{maturity}/{moneyness}
2. Backend query CWs trong bucket cụ thể
3. Calculate detailed metrics cho mỗi CW
4. Return cw_list array
5. Frontend render table với sortable columns
6. User sort/filter → Client-side hoặc re-fetch API
```

**API Endpoint**: `GET /api/v1/deepfinlens/matrix/{maturity_bucket}/{moneyness_bucket}`

**Edge Cases**:
- Cell có quá nhiều CW (>50) → Pagination
- No CWs in cell → Hiển lý "No CWs in this range"

---

### Feature: DeepFinLens Classification

**User Story**: Là một trader chuyên nghiệp, tôi muốn xem phân loại CW theo DeepFinLens để hiểu pattern của từng loại.

**Acceptance Criteria**:
- [ ] Classification theo category (high_delta_low_premium, etc.)
- [ ] Subcategory detail (aggressive_growth, conservative, etc.)
- [ ] Confidence score cho mỗi classification
- [ ] Key factors contributing to classification
- [ ] Filter theo category
- [ ] Visual representation: Radar chart hoặc Sankey diagram

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/deepfinlens/classification
2. Backend ML model classify mỗi CW
3. Determine category dựa trên delta, premium, volatility, liquidity
4. Calculate confidence score
5. Extract key features (SHAP values hoặc feature importance)
6. Return classification array
7. Frontend render với visualization
```

**API Endpoint**: `GET /api/v1/deepfinlens/classification`

**Edge Cases**:
- Low confidence (<0.6) → Mark as "uncertain"
- ML model down → Fallback to rule-based classification

---

## 🏢 Sector Analysis Module

### Feature: Sector Ranking Table

**User Story**: Là một trader, tôi muốn xem bảng xếp hạng ngành để xác định dòng tiền đang chảy vào đâu.

**Acceptance Criteria**:
- [ ] Table hiển thị tất cả sectors
- [ ] Columns: Rank, Sector Name, Avg Change %, Total Turnover, Net Cash Flow, Rank Score
- [ ] Sortable: Theo bất kỳ column nào
- [ ] Color coding: Top 3 xanh, bottom 3 đỏ
- [ ] Click row: Mở sector detail modal
- [ ] Auto-refresh: Mỗi 10 phút

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/sectors
2. Backend query stock_market_data grouped by sector
3. Calculate avg_change_pct, total_turnover per sector
4. Calculate net_cash_flow từ foreign_buy/sell
5. Calculate rank_score = weighted sum của metrics
6. Sort by rank_score DESC
7. Return sector array
8. Frontend render table với sorting
```

**API Endpoint**: `GET /api/v1/sectors`

**Edge Cases**:
- Sector không có data → Hiển lý "N/A" hoặc hide
- Data delay → Hiển lý last updated timestamp

---

### Feature: Sector Cashflow Analysis

**User Story**: Là một trader, tôi muốn xem phân tích dòng tiền ngành để dự đoán xu hướng sector rotation.

**Acceptance Criteria**:
- [ ] Cashflow overview chart: Bar chart net cash flow per sector
- [ ] Cashflow trend: Line chart 7D, 30D trend
- [ ] Flow ratio: Net flow / Total flow
- [ ] Flow direction: Inflow (xanh) / Outflow (đỏ)
- [ ] Top inflow/outflow stocks trong sector

**Luồng xử lý (Logic)**:
```
1. User click sector → GET /api/v1/sectors/{sector_name}
2. Backend query historical cashflow data (7D, 30D)
3. Calculate trend line (linear regression)
4. Identify top inflow/outflow stocks
5. Return sector detail with cashflow data
6. Frontend render charts với Recharts
```

**API Endpoint**: `GET /api/v1/sectors/{sector_name}`

**Edge Cases**:
- Insufficient historical data → Show available data only
- Extreme values → Clamp chart scale

---

### Feature: OLS Projection

**User Story**: Là một trader, tôi muốn xem OLS projection để dự báo xu hướng ngành ngắn hạn.

**Acceptance Criteria**:
- [ ] OLS line trên historical price chart
- [ ] R-squared value để đánh giá fit
- [ ] Forecast points: 7D, 30D projections
- [ ] Confidence interval band
- [ ] Trend strength indicator (strong, moderate, weak)

**Luồng xử lý (Logic)**:
```
1. User click sector → GET /api/v1/sectors/{sector_name}
2. Backend query historical sector index data (60 days)
3. Fit OLS regression: y = mx + b
4. Calculate R-squared
5. Forecast 7D, 30D using regression line
6. Calculate confidence interval (95%)
7. Return projection data
8. Frontend render chart với regression line + forecast points
```

**API Endpoint**: `GET /api/v1/sectors/{sector_name}`

**Edge Cases**:
- Low R-squared (<0.5) → Display warning "Low confidence"
- Insufficient data → Fallback to simple moving average

---

## 👛 Portfolio Management Module

### Feature: Portfolio Creation

**User Story**: Là một user, tôi muốn tạo portfolio để theo dõi danh mục CW của mình.

**Acceptance Criteria**:
- [ ] User nhập portfolio name, description, initial capital
- [ ] Initial capital default: 100,000,000 VND
- [ ] Validation: Name required, capital > 0
- [ ] Portfolio mặc định active
- [ ] Return portfolio ID cho tracking

**Luồng xử lý (Logic)**:
```
1. User nhập thông tin → Frontend validate
2. POST /api/v1/portfolio → Backend validate
3. Insert vào user_portfolios table
4. Calculate current_capital = initial_capital
5. Return portfolio object với ID
6. Frontend redirect đến portfolio detail
```

**API Endpoint**: `POST /api/v1/portfolio`

**Edge Cases**:
- User exceeded portfolio limit (max 5) → Return 400 với message
- Invalid capital amount → Return 400 validation error

---

### Feature: Position Entry

**User Story**: Là một trader, tôi muốn thêm position vào portfolio để theo dõi lợi nhuận/loss.

**Acceptance Criteria**:
- [ ] User chọn CW, nhập quantity, entry price
- [ ] Optional: Strategy notes, entry reason
- [ ] Validation: Quantity > 0, price > 0
- [ ] Calculate total_value = quantity * price
- [ ] Check sufficient capital (current_capital >= total_value)
- [ ] Deduct from portfolio capital
- [ ] Create position record với is_active = true

**Luồng xử lý (Logic)**:
```
1. User nhập position info → Frontend validate
2. POST /api/v1/portfolio/{id}/position → Backend validate
3. Check portfolio current_capital >= total_value
4. Insert vào portfolio_positions table
5. Insert vào portfolio_transactions table (buy)
6. Update portfolio current_capital -= total_value
7. Return position object
8. Frontend update portfolio UI
```

**API Endpoint**: `POST /api/v1/portfolio/{portfolio_id}/position`

**Edge Cases**:
- Insufficient capital → Return 400 với message "Insufficient capital"
- CW not found → Return 404
- Invalid quantity/price → Return 400 validation error

---

### Feature: Position Exit

**User Story**: Là một trader, tôi muốn đóng position để thực hiện lợi nhuận hoặc cắt lỗ.

**Acceptance Criteria**:
- [ ] User chọn position, nhập exit quantity, exit price
- [ ] Support partial exit (quantity < original quantity)
- [ ] Calculate realized_pnl = (exit_price - entry_price) * quantity
- [ ] Add realized_pnl to portfolio capital
- [ ] Update position: remaining_quantity, is_active (if full exit)
- [ ] Create transaction record (sell)
- [ ] Log exit reason

**Luồng xử lý (Logic)**:
```
1. User nhập exit info → Frontend validate
2. PUT /api/v1/portfolio/{id}/position/{pos_id} → Backend validate
3. Calculate realized_pnl
4. Update portfolio current_capital += realized_pnl
5. Update position: remaining_quantity -= exit_quantity
6. If remaining_quantity == 0 → is_active = false, exit_date = NOW
7. Insert vào portfolio_transactions (sell)
8. Return updated position
9. Frontend update portfolio UI
```

**API Endpoint**: `PUT /api/v1/portfolio/{portfolio_id}/position/{position_id}`

**Edge Cases**:
- Exit quantity > remaining_quantity → Return 400 validation error
- Position already closed → Return 400 error
- Negative PnL → Allow but display in red

---

### Feature: Portfolio Performance Tracking

**User Story**: Là một user, tôi muốn xem performance summary của portfolio để đánh giá hiệu quả trading.

**Acceptance Criteria**:
- [ ] Summary cards: Total capital, Total return %, Win rate, Active positions
- [ ] PnL chart: Historical portfolio value over time
- [ ] Position table: All positions with status (active/closed)
- [ ] Performance metrics: Sharpe ratio, Max drawdown, Profit factor
- [ ] Export: CSV export của positions

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/portfolio/{id}
2. Backend query portfolio_positions + portfolio_transactions
3. Calculate unrealized_pnl cho active positions (current_price - entry_price)
4. Calculate realized_pln từ closed positions
5. Calculate total_return = (current_capital - initial_capital) / initial_capital
6. Calculate win_rate = winning_positions / total_positions
7. Query historical portfolio NAV data
8. Return portfolio summary + positions array
9. Frontend render summary cards + charts
```

**API Endpoint**: `GET /api/v1/portfolio/{portfolio_id}`

**Edge Cases**:
- No positions yet → Show empty state
- Missing current price data → Use last known price

---

## 💰 Subscription Module

### Feature: Plan Selection

**User Story**: Là một user demo, tôi muốn xem các gói subscription để chọn nâng cấp.

**Acceptance Criteria**:
- [ ] Display 3 plans: Demo, Client, Client Pro
- [ ] Show features comparison table
- [ ] Show pricing per month
- [ ] Highlight recommended plan (Client)
- [ ] Click "Select" → Redirect to checkout

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/subscription/plans
2. Backend return plans array với features
3. Frontend render pricing cards
4. User click "Select" → Store selected plan in state
5. Redirect to checkout page
```

**API Endpoint**: `GET /api/v1/subscription/plans`

**Edge Cases**:
- User already has active subscription → Show current plan + upgrade option
- Promotional pricing → Display special offer

---

### Feature: VietQR Checkout

**User Story**: Là một user, tôi muốn thanh toán qua VietQR để nâng cấp subscription nhanh chóng.

**Acceptance Criteria**:
- [ ] Generate VietQR code với correct amount
- [ ] QR code expires sau 15 phút
- [ ] Display payment instructions
- [ ] Auto-check payment status every 10 seconds
- [ ] On success → Auto-redirect to success page
- [ ] On timeout → Show retry option

**Luồng xử lý (Logic)**:
```
1. User confirm payment → POST /api/v1/subscription/checkout
2. Backend create subscription_payments record (status: pending)
3. Generate VietQR code via VietQR API
4. Return payment_id + qr_code_url + expiry
5. Frontend display QR + countdown timer
6. Start polling: GET /api/v1/subscription/status every 10s
7. Backend check payment status via VietQR API
8. On payment success → Update subscription_tier, expires_at
9. Stop polling, redirect to success page
```

**API Endpoints**:
- `POST /api/v1/subscription/checkout`
- `GET /api/v1/subscription/status`

**Edge Cases**:
- VietQR API down → Show error + retry option
- Payment timeout → Allow retry with new QR
- Payment failed → Show error message + support contact

---

### Feature: Subscription Status Check

**User Story**: Là một user, tôi muốn xem subscription status hiện tại để biết khi nào hết hạn.

**Acceptance Criteria**:
- [ ] Display current tier (Demo/Client/Client Pro)
- [ ] Show expiry date
- [ ] Show days remaining
- [ ] Show active features list
- [ ] Show upgrade option if not Pro

**Luồng xử lý (Logic)**:
```
1. Component mount → GET /api/v1/subscription/status
2. Backend query users table + subscription_payments
3. Determine current tier dựa trên latest successful payment
4. Calculate days_remaining = expires_at - NOW()
5. Map features theo tier
6. Return subscription status
7. Frontend render status card
```

**API Endpoint**: `GET /api/v1/subscription/status`

**Edge Cases**:
- Subscription expired → Show "Expired" + renew option
- No subscription → Show "Demo" + upgrade option

---

## 🤖 AI Analysis Module

### Feature: AI Trading Decision

**User Story**: Là một trader, tôi muốn nhận AI recommendation cho một CW cụ thể để hỗ trợ ra quyết định.

**Acceptance Criteria**:
- [ ] User chọn CW → Request AI analysis
- [ ] AI analyze: Delta, Premium, Volatility, Regime, Underlying trend
- [ ] Return decision: buy/sell/hold/neutral
- [ ] Return consensus score (0-1)
- [ ] Return confidence level
- [ ] Return rationale summary (2-3 sentences)
- [ ] Return key factors với weights
- [ ] Display recommendation với color coding (green=buy, red=sell)

**Luồng xử lý (Logic)**:
```
1. User select CW → POST /api/v1/ai/analyze
2. Backend query cw_analytics + regime_data + stock_market_data
3. Extract features: delta, premium, iv, regime, underlying_trend
4. AI model (Gemini) analyze features
5. Generate decision + consensus_score + rationale
6. Store analysis in ai_analysis_memory table
7. Return analysis result
8. Frontend render recommendation card
```

**API Endpoint**: `POST /api/v1/ai/analyze`

**Edge Cases**:
- AI model down → Fallback to rule-based decision
- Insufficient data → Return "insufficient_data" error
- Low confidence (<0.5) → Display warning

---

### Feature: AI Memory Tracking

**User Story**: Là một trader, tôi muốn xem lịch sử AI recommendations để đánh giá accuracy.

**Acceptance Criteria**:
- [ ] Display history of AI analyses for a CW
- [ ] Show: timestamp, decision, consensus_score, is_correct
- [ ] Show actual outcome (profit loss) if available
- [ ] Calculate accuracy rate
- [ ] Filter by date range, decision type

**Luồng xử lý (Logic)**:
```
1. User select CW → GET /api/v1/ai/memory/{symbol}
2. Backend query ai_analysis_memory table
3. Filter by symbol, order by timestamp DESC
4. Calculate accuracy = correct_predictions / total_predictions
5. Return memory array + accuracy stats
6. Frontend render history table
```

**API Endpoint**: `GET /api/v1/ai/memory/{symbol}`

**Edge Cases**:
- No history → Show empty state
- Outcome not yet determined → Display "Pending"

---

## 📊 Real-time Data Module

### Feature: WebSocket Connection

**User Story**: Là một user, tôi muốn nhận real-time updates để không phải refresh trang.

**Acceptance Criteria**:
- [ ] Auto-connect WebSocket on app load (if authenticated)
- [ ] Subscribe to channels: cw_prices, market_data, signals
- [ ] Handle connection errors with auto-reconnect
- [ ] Handle message parsing and validation
- [ ] Update UI state on message receive
- [ ] Show connection status indicator (green=connected, red=disconnected)

**Luồng xử lý (Logic)**:
```
1. App mount → Check authentication
2. If authenticated → Connect to wss://api/v1/ws?token={access_token}
3. Send subscribe message: {"action": "subscribe", "channels": ["cw_prices", "market_data"]}
4. Listen for messages → Parse JSON
5. Update Redux/Zustand state
6. Handle onclose → Attempt reconnect (exponential backoff)
7. Handle onerror → Log error + show notification
```

**WebSocket Endpoint**: `wss://api/v1/ws`

**Edge Cases**:
- Token expired → Re-authenticate + reconnect
- Network disconnect → Auto-reconnect with backoff
- Invalid message format → Log error + ignore

---

### Feature: Real-time CW Price Updates

**User Story**: Là một trader, tôi muốn thấy giá CW update real-time để nắm bắt cơ hội.

**Acceptance Criteria**:
- [ ] Receive price updates via WebSocket every 5 seconds
- [ ] Update scatter plot bubbles with new prices
- [ ] Flash animation on price change
- [ ] Update opportunity scores if significant change
- [ ] Show last update timestamp

**Luồng xử lý (Logic)**:
```
1. WebSocket receive cw_prices message
2. Parse message: {symbol, price, change_pct, volume, timestamp}
3. Update state: cw_prices[symbol] = new_data
4. Recalculate opportunity_score if price changed > 2%
5. Trigger re-render of affected components
6. Show visual indicator (flash/color change)
```

**WebSocket Channel**: `cw_prices`

**Edge Cases**:
- Stale data (timestamp > 30s) → Ignore
- Duplicate messages → Deduplicate by timestamp
- Missing fields → Use last known values

---

## 🚨 Error Handling & Edge Cases

### Common Error States

**Network Error**:
- Display friendly error message
- Show retry button
- Log error for debugging
- Fallback to cached data if available

**Loading State**:
- Show skeleton loaders
- Display progress indicators for long operations
- Cancelable operations

**Empty State**:
- Show friendly empty state message
- Provide call-to-action (e.g., "Create your first portfolio")
- Illustration or icon

**Permission Denied**:
- Check subscription tier
- Show upgrade prompt for premium features
- Graceful degradation (show limited data)

**Data Validation Errors**:
- Display field-specific error messages
- Highlight invalid fields
- Provide examples of correct format

### Rate Limiting

**When Rate Limited**:
- Show "Too many requests" message
- Display countdown timer to retry
- Implement exponential backoff for retries
- Queue non-critical requests

---

## 📱 Responsive Design

### Mobile Adaptations

**Dashboard**:
- Simplified scatter plot (hide tooltips on touch)
- Horizontal scroll for Pareto chart
- Bottom navigation bar

**DeepFinLens Matrix**:
- Scrollable matrix container
- Simplified cell content
- Landscape mode recommendation

**Portfolio**:
- Card-based layout instead of table
- Swipe actions for position management
- Collapsible sections

**Forms**:
- Full-width inputs
- Larger touch targets (44px min)
- Auto-focus on first field
- Numeric keypads for number inputs

---

## ♿ Accessibility

**WCAG 2.1 AA Compliance**:
- Keyboard navigation for all interactive elements
- ARIA labels for screen readers
- Color contrast ratio ≥ 4.5:1
- Focus indicators visible
- Error messages associated with form fields
- Skip to main content link
- Responsive text scaling

---

## 🔄 State Management

**Global State (Zustand)**:
- `authStore`: User data, tokens, subscription
- `marketDataStore`: CW prices, market indices
- `portfolioStore`: User portfolios, positions
- `uiStore`: Theme, language, preferences

**Local State (React useState)**:
- Form inputs
- Modal open/close
- Temporary filters
- Component-specific UI state

**Server State (React Query)**:
- API responses with caching
- Automatic refetching
- Optimistic updates
- Error/retry handling
