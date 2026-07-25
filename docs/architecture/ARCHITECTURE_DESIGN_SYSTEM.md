# 🏛️ FINVISTA: ARCHITECTURE, DESIGN SYSTEM & DETAILED PAGE SPECIFICATIONS

> **Document Version**: 3.0  
> **Last Updated**: 2026-07-22  
> **Repository Target**: `Finvista (Finvista.pdf Specification)`

---

## 🎨 1. CORE DESIGN SYSTEM & COLOR PALETTE

To maintain absolute visual consistency across all 12 feature pages, all components **MUST** strictly adhere to the unified Finvista Dark Theme color tokens below. Do not introduce arbitrary inline hex colors.

### 🌟 Color Tokens Table

| Token Name | Hex Code | Usage Scope |
| :--- | :--- | :--- |
| **`--bg-root`** | `#0b0f19` | Deep charcoal dark navy root page background |
| **`--bg-card`** | `#131b2e` | Container background for panels, cards, and table boxes |
| **`--border-subtle`** | `#1e293b` | 1px solid border lines, table row dividers, input borders |
| **`--accent-primary`** | `#2563eb` | Active tab highlight, primary action buttons, links |
| **`--status-success`** | `#10b981` | Bullish indicators, BUY signals, profit P/L, SAFE ratings |
| **`--status-danger`** | `#ef4444` | Bearish indicators, SELL signals, loss P/L, DANGER ratings |
| **`--status-warning`** | `#f59e0b` | HOLD signals, caution alerts, GREY ratings |
| **`--text-main`** | `#ffffff` | Primary text headings and main values |
| **`--text-muted`** | `#94a3b8` | Subtitles, labels, secondary information |

---

## 🔌 2. BACKEND API & DATA CONTRACTS

All data displayed in the frontend must be dynamic and queried from the FastAPI Backend (`http://localhost:8008`):

### Key API Endpoints
1. **Market Underlyings & Stocks**: `GET /api/market/underlyings`
   - Queries `stock_history` PostgreSQL table (51,027+ real records).
   - Returns underlying stock quotes, sector groupings, and market index levels (`VNINDEX`, `VN30`, `HNXINDEX`, `UPCOM`).
2. **Covered Warrant Scanner**: `GET /api/warrants/opportunities`
   - Returns real-time G-Score rated Covered Warrants with Black-Scholes theoretical price, Delta ($\Delta$), Implied Volatility (IV %), and Premium (%).
3. **Credit Health & Altman Z-Score**: `GET /api/credit-health/{symbol}`
   - Computes financial distress probability, Altman Z-Score, Springate S-Score, Zmijewski X-Score, and CAMELS bank metrics.
4. **Creed Market Regime**: `GET /api/regime/market`
   - Evaluates HMM market regimes (`LONG_CW` / `BULLISH_VOL_EXPANSION`, `SKIP_CW` / `BEARISH_HIGH_VOL`, `NEUTRAL`).
5. **TradingView UDF Datafeed**: `GET /api/udf/history`
   - Serves historical daily candlestick (OHLCV) bars for Lightweight Charts.
6. **Paper Trading Portfolio**: `GET /api/portfolio`, `POST /api/portfolio/order`, `POST /api/portfolio/reset`
   - Executes real-time paper trading orders, computes NAV, cash, and P/L.

---

## 📐 3. FRONTEND NAVIGATION & UI RULES

1. **Sidebar Cleanliness**:
   - Sidebar contains 11 core navigation items (`Overview`, `Market`, `Scanner`, `Dashboard`, `Portfolio`, `Credit Health`, `Watchlist`, `Learning`, `News`, `Alerts`, `Products`).
   - `Settings` is accessed exclusively via the Top-Right User Avatar Profile Menu to avoid clutter.
2. **Dynamic Sub-Tabs**:
   - Sub-tabs must trigger real reactive filtering and re-rendering of views/tables rather than static mock toggles.
3. **TradingView Lightweight Chart Reactivity**:
   - Chart components must use `key={activeTab}` or `key={symbol}` so React remounts and re-fetches the correct UDF historical bars when switching indices or tickers.
4. **Interactive Action Buttons**:
   - All `MUA`, `BÁN HẾT`, `MUA THÊM`, `THEO DÕI`, `LÀM MỚI LIVE`, `RESET` buttons must invoke real API actions (`placeOrder()`, `localStorage`, `getOpportunities()`) and display feedback toasts.

---

## 🖥️ 4. EXHAUSTIVE PAGE-BY-PAGE SPECIFICATION DIRECTORY

Below is the complete functional and design specification for every single page in the Finvista Application:

### 📄 Trang 1: OVERVIEW (Tổng quan Thị trường & Danh mục)
* **Mục đích**: Trang trung tâm cung cấp góc nhìn toàn cảnh về thị trường chứng quyền Việt Nam, tín hiệu trạng thái Creed Market Regime và tóm tắt hiệu suất tài sản cá nhân.
* **Điều hướng**: Nhấp vào tab `Tổng quan` ở Sidebar hoặc Logo Finvista.
* **Các thẻ thông tin & Nút bấm**:
  * Thẻ Badge **Creed Market Regime**: Hiển thị trạng thái biến động thị trường (ví dụ: `BULLISH_VOL_EXPANSION (98%)`).
  * 4 Thẻ KPI: `Tổng tài sản`, `Lãi/Lỗ trong ngày`, `Lãi/Lỗ chưa thực hiện (%)`, `Sức mua khả dụng`.
  * Nút chuyển Tab Chỉ số: `VN-INDEX`, `VN30`, `CW-INDEX`, `Thế giới` (tự động đổi mã `SPX`).
  * Nút chọn Khung thời gian: `1D`, `1W`, `1M`, `3M`, `6M`, `YTD`, `1Y`, `5Y`.
  * Nút chuyển Tab Top Chứng quyền: `Tăng mạnh`, `Thanh khoản`, `Giảm mạnh`.
* **Biểu đồ tích hợp**:
  * Biểu đồ chính **TradingView Lightweight Chart**: Hiển thị đường giá nến nạp từ backend UDF API (`/api/udf/history`).
* **Bảng dữ liệu**: Bảng Cảnh báo cá nhân & Tin tức nổi bật.

---

### 📄 Trang 2: MARKET (Thị trường Cổ phiếu Cơ sở & CW)
* **Mục đích**: Tra cứu toàn bộ bảng giá realtime của các mã cổ phiếu cơ sở có chứng quyền và danh sách chứng quyền đang lưu hành.
* **Điều hướng**: Nhấp vào tab `Thị trường` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * 4 Thẻ Chỉ số chính: `VN-Index`, `HNX-Index`, `UPCOM-Index`, `VN30` (nạp trực tiếp từ PostgreSQL `stock_history`).
  * Thanh tìm kiếm Live: Lọc tức thì theo mã chứng quyền hoặc mã cổ phiếu (vd: `HDB`, `CVPB2404`).
  * Nút lọc Ngành nhanh: `Tất cả`, `Ngân hàng`, `Bất động sản`, `Thép`, `Công nghệ`, `Thực phẩm`.
  * Sub-nav Tabs: `Tổng quan`, `Chỉ số`, `Heatmap`, `Dòng tiền`, `Thanh khoản`, `Phái sinh`.
  * Nút `Xem chi tiết`: Mở trang định giá chuyên sâu cho từng mã.
* **Bảng dữ liệu**:
  * **Bảng 1**: DANH SÁCH CHỨNG QUYỀN HOẠT ĐỘNG (Mã CW, Mã CS, Tổ chức PH, Giá CW, Thay đổi %, Premium %, Delta, IV %, Giá thực hiện, Nút Action).
  * **Bảng 2**: BẢNG GIÁ CỔ PHIẾU CƠ SỞ DB REALTIME (Mã cổ phiếu, Tên công ty, Ngành, Giá hiện tại, Biến động %, Khối lượng GD, Số lượng CW lưu hành).

---

### 📄 Trang 3: SCANNER (Bộ lọc Chứng quyền & Tìm kiếm Cơ hội)
* **Mục đích**: Công cụ định lượng lọc chứng quyền tốt nhất thị trường dựa trên điểm số G-Score, Black-Scholes, Delta và Implied Volatility.
* **Điều hướng**: Nhấp vào tab `Scanner` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * Sub-tabs: `Cơ bản`, `Nâng cao`, `Yêu thích ★`.
  * Bộ trượt Slider: `Thời gian đáo hạn (ngày)`, `Premium tối đa (%)`, `Delta tối thiểu`, `Khối lượng giao dịch`.
  * Nút hành động trên từng hàng: Nút `MUA` (mở modal mua lệnh paper trading), Nút `THEO DÕI` (lưu vào Watchlist), Nút `Đặt lại`.
* **Biểu đồ tích hợp**: N/A (Tập trung tối đa vào bảng kết quả định lượng).
* **Bảng dữ liệu**: Bảng kết quả lọc chứng quyền chuẩn định lượng với xếp hạng G-Score và khuyến nghị Buy/Skip.

---

### 📄 Trang 4: DASHBOARD (Quản trị Danh mục & Phân tích Rủi ro)
* **Mục đích**: Phân tích chuyên sâu danh mục đầu tư, kiểm soát rủi ro đáo hạn 14 ngày và theo dõi sức khỏe tín dụng Altman Z-Score của các doanh nghiệp cơ sở.
* **Điều hướng**: Nhấp vào tab `Dashboard` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * Sub-tabs: `Tổng quan NAV`, `Hiệu suất danh mục`, `Rủi ro tín dụng Z-Score`, `Cảnh báo đáo hạn`.
  * Nút `Xuất báo cáo PDF`: Xuất file báo cáo định lượng danh mục chuẩn bị cho nhà đầu tư.
* **Biểu đồ tích hợp**:
  * Biểu đồ đường **NAV Growth & Benchmark Chart**: So sánh tăng trưởng danh mục cá nhân với VN-Index.
  * Biểu đồ tròn **Asset Allocation Pie Chart**: Phân bổ vốn theo chứng quyền và cổ phiếu.
* **Bảng dữ liệu**: Bảng xếp hạng Altman Z-Score & Danh sách chứng quyền sắp hết hạn trong 14 ngày.

---

### 📄 Trang 5: PORTFOLIO (Quản lý Vị thế & Đặt lệnh Mô phỏng Paper Trading)
* **Mục đích**: Thực hiện giao dịch mua/bán chứng quyền giả định (Paper Trading) và theo dõi Lãi/Lỗ thực tế (Unrealized & Realized P/L).
* **Điều hướng**: Nhấp vào tab `Portfolio` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * 4 Thẻ Tổng quan: `Tổng giá trị tài sản`, `Sức mua tiền mặt`, `Tổng lãi/lỗ chưa thực hiện`, `Số lượng vị thế đang mở`.
  * Form Đặt lệnh Paper Trading: Nhập `Mã CW`, `Số lượng`, `Giá đặt`, nút `MUA NGAY`.
  * Nút hành động nhanh trên bảng vị thế: Nút `MUA THÊM`, Nút `BÁN HẾT`, Nút `Reset danh mục ban đầu`.
* **Bảng dữ liệu**: Bảng danh sách các vị thế đang nắm giữ (Mã CW, Giá vốn, Giá hiện tại, Lãi/Lỗ %, Khối lượng, Nút Bán/Mua).

---

### 📄 Trang 6: CREDIT HEALTH (Phân tích Sức khỏe Tín dụng Altman Z-Score)
* **Mục đích**: Đánh giá rủi ro phá sản/kiệt quệ tài chính của doanh nghiệp phát hành cổ phiếu cơ sở bằng các mô hình định lượng tiên tiến.
* **Điều hướng**: Nhấp vào tab `Rủi ro tín dụng Z-Score` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * Ô nhập mã cổ phiếu cơ sở (vd: `HPG`, `FPT`, `VIC`, `VPB`) + Nút `Tra cứu`.
  * Thẻ KPI Rủi ro: `Mã cổ phiếu`, `Điểm Altman Z-Score / CAR`, `Vùng rủi ro (SAFE / WARNING / DANGER)`, `Xác suất rủi ro phá sản (%)`.
* **Bảng dữ liệu**:
  * Bảng chỉ số tài chính: Debt ratio, Current ratio, ROA, ROE, EBIT/Assets, ICR.
  * Bảng đối chiếu mô hình: Altman Z-Score, Springate S-Score, Zmijewski X-Score, CAMELS rating (đối với Ngân hàng).

---

### 📄 Trang 7: WATCHLIST (Danh mục Phụ theo dõi)
* **Mục đích**: Quản lý danh sách các mã chứng quyền và cổ phiếu cơ sở yêu thích cá nhân.
* **Điều hướng**: Nhấp vào tab `Watchlist` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * Ô thêm mã mới + Nút `Thêm vào danh mục`.
  * Nút `🗑️ Xóa` từng hàng để loại bỏ mã khỏi bộ nhớ `localStorage`.
* **Bảng dữ liệu**: Bảng danh sách theo dõi với biến động giá realtime, khối lượng và tín hiệu định giá.

---

### 📄 Trang 8: LEARNING (Trung tâm Đào tạo & Quiz Trắc nghiệm)
* **Mục đích**: Cung cấp kiến thức chuẩn định lượng về chứng quyền, các chỉ số Greeks (Delta, Gamma, Theta, Vega) và mô hình Black-Scholes.
* **Điều hướng**: Nhấp vào tab `Learning` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * Sub-tabs: `Khóa học`, `Video`, `Bài viết`, `Quiz hàng ngày`, `Mô phỏng`.
  * Nút học: `Bắt đầu`, `Xem lại`.
  * Widget Quiz trắc nghiệm tương tác: Nút chọn đáp án A/B/C/D + Nút `NỘP BÀI TRẢ LỜI`.
* **Bảng dữ liệu**: Danh sách khóa học & Tiến trình hoàn thành bài học (ProgressBar).

---

### 📄 Trang 9: NEWS (Tin tức Doanh nghiệp & Phân tích Tin tức)
* **Mục đích**: Cập nhật tin tức doanh nghiệp niêm yết từ Vietstock/SSI và đánh giá tác động tin tức đến giá cổ phiếu cơ sở.
* **Điều hướng**: Nhấp vào tab `Tin tức` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * Ô lọc tin tức theo mã cổ phiếu + Nút `Làm mới tin tức`.
* **Bảng dữ liệu**: Danh sách bài viết với tiêu đề, ngày đăng, nguồn tin, tóm tắt và link gốc.

---

### 📄 Trang 10: ALERTS (Hệ thống Cảnh báo Rủi ro & Giá)
* **Mục đích**: Quản lý các cảnh báo biến động giá, vi phạm ngưỡng Delta, đòn bẩy quá cao và cảnh báo đáo hạn 14 ngày.
* **Điều hướng**: Nhấp vào tab `Cảnh báo` ở Sidebar.
* **Các thẻ thông tin & Nút bấm**:
  * Nút `Tạo cảnh báo mới`, Nút `Bật/Tắt cảnh báo`.
* **Bảng dữ liệu**: Bảng danh sách cảnh báo đang kích hoạt và lịch sử thông báo.

---

### 📄 Trang 11: PRODUCTS (Gói cước & Nâng cấp Tài khoản)
* **Mục đích**: Giới thiệu các gói cước dịch vụ Finvista (Free, Pro, Institutional) và các tính năng cao cấp.
* **Điều hướng**: Nhấp vào tab `Sản phẩm` ở Sidebar hoặc Nút `Nâng cấp ngay` ở Sidebar Footer.
* **Các thẻ thông tin & Nút bấm**:
  * 3 Thẻ bảng giá gói cước + Nút `Đăng ký gói Pro / Enterprise`.

---

### 📄 Trang 12: WARRANT DETAIL (Trang Chi tiết Định giá Chứng quyền)
* **Mục đích**: Trang phân tích chuyên sâu nhất cho một mã chứng quyền cụ thể (màn hình khi nhấp vào bất kỳ mã CW nào).
* **Điều hướng**: Nhấp vào mã CW ở bất kỳ bảng dữ liệu nào hoặc tìm kiếm ở Header.
* **Các thẻ thông tin & Nút bấm**:
  * Thẻ thông tin chung: Giá hiện tại, Biến động, Tỷ lệ chuyển đổi, Giá thực hiện, Ngày đáo hạn, Tổ chức phát hành.
  * Thẻ chỉ số Greeks: Delta, Gamma, Theta, Vega, Implied Volatility (IV %).
  * Thẻ đánh giá Altman Z-Score của công ty cơ sở.
  * Nút `Đặt lệnh Mua`, Nút `Thêm vào Watchlist`.
* **Biểu đồ tích hợp**:
  * Biểu đồ nến TradingView Lightweight Chart dành riêng cho mã chứng quyền được chọn.

---

## 🚀 5. ĐOẠN LỆNH BUILD & DOCKER

To update both Frontend Nginx and FastAPI Backend containers in background mode:

```powershell
# 1. Build frontend distribution bundle
cd c:\Users\samvo\Downloads\Finvista\frontend
npm run build

# 2. Rebuild and restart Docker containers
cd c:\Users\samvo\Downloads\Finvista
docker compose up -d --build
```
