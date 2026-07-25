# 🎨 FINVISTA - BLUEPRINT & SPECIFICATION KỸ THUẬT CHI TIẾT (ĐỒNG BỘ 100% FINVISTA.PDF)

> **Tài liệu này chuẩn hóa toàn bộ 12 trang chức năng của Finvista khớp 100% với giao diện, hình ảnh mô phỏng và các ghi chú điều chỉnh trực tiếp trong file `Finvista.pdf`.**

---

## 🧭 CẤU TRÚC ĐIỀU HƯỚNG CHÍNH (SIDEBAR & GLOBAL BAR)
*   **Logo**: Finvista Gradient (Teal `#008b7a` - Red `#d94a6f`), Slogan *"Quantitative Edge. Smarter Decisions."*.
*   **Menu 11 Thẻ Chức Năng**:
    1. 📊 **Tổng quan (Overview)**
    2. 📈 **Thị trường (Market)**
    3. 🔍 **Scanner**
    4. 🖥️ **Dashboard**
    5. 💼 **Portfolio**
    6. ⭐ **Watchlist**
    7. 📚 **Learning**
    8. 📰 **Tin tức (News)**
    9. 🔔 **Alerts**
    10. 📦 **Sản phẩm (Products)**
    11. ⚙️ **Settings**
*   **Trạng thái thị trường**: Đèn hiệu chỉ thị xanh/đỏ (Đang mở cửa / Đóng cửa lúc 15:00) kèm đồng hồ đếm ngược.
*   **Profile Bar**: Avatar, Tên người dùng (`Nguyễn Tuấn Anh`), Badge `Premium`, Nút chuyển đổi Light/Dark mode, Chuông thông báo.

---

## 1. TỔNG QUAN (OVERVIEW PAGE)
*   **Khối KPI Tài Sản (Overview Header)**:
    *   **Tổng tài sản (NAV)**: `1,254,320,000 VND` (+24,560,000 / +1.99%).
    *   **Lãi/Lỗ hôm nay**: `24,560,000 VND` (+1.99%).
    *   **Lãi/Lỗ chưa thực hiện**: `86,750,000 VND` (+7.45%).
    *   **Sức mua khả dụng (Cash)**: `320,450,000 VND` kèm icon nạp tiền.
    *   **Hiệu suất danh mục (1M)**: `+7.45%` (+86,750,000 VND).
*   **Chỉ số & Biến động Thời gian thực (Interactive Chart)**:
    *   Tabs: `VN-INDEX`, `VN30`, `CW-INDEX`, `Thế giới`.
    *   Biểu đồ đường nến thời gian thực VN-INDEX (`1,245.32` điểm) kèm thanh timeframe: 1D, 1W, 1M, 3M, 6M, YTD, 1Y, 5Y.
*   **Bản đồ thị trường & Dòng tiền**:
    *   Thanh phân bổ dòng tiền ngành (Ngân hàng, Bất động sản, Thực phẩm, Chứng khoán, Thép, Công nghiệp).
    *   Biểu đồ cột Dòng tiền (Tổng quan, Nước ngoài, Tự doanh).
*   **Khối bên phải (Right Column)**:
    *   **Top chứng quyền**: Tabs (Tăng mạnh, Thanh khoản, Giảm mạnh). Danh sách các mã CVPB2404, CVMWG2401, CVRE2402, CVHM2403, CVFPT2401.
    *   **Cảnh báo của tôi**: Danh sách cảnh báo giá (Giá > 1,250, VN-INDEX < 1,240, IV Index > 70).
    *   **Tin tức nổi bật**: Cập nhật tin nóng từ thị trường & doanh nghiệp.
*   **Cơ hội hôm nay cho bạn (Recommendation Cards)**:
    *   Các thẻ mã CW nổi bật: `CVPB2404` (G-Score: 85, Động lượng tích cực, Định giá hấp dẫn), `CVMWG2401` (G-Score: 78), `CVFPT2401` (G-Score: 72), `CVTCB2402` (G-Score: 65).

---

## 2. THỊ TRƯỜNG (MARKET PAGE)
*   **Tabs chức năng**: `[Tổng quan]`, `[Chỉ số]`, `[Heatmap]`, `[Dòng tiền]`, `[Thanh khoản]`, `[Phái sinh]`, `[Thế giới]`.
*   **2.1 Tổng quan Thị trường**:
    *   4 thẻ chỉ số chính: **VN-Index** (`1,245.32`), **HNX-Index** (`234.56`), **UPCOM-Index** (`98.76`), **VN30** (`1,312.45`).
    *   Biểu đồ VN-INDEX thời gian thực.
    *   Thanh khoản thị trường (Giá trị khớp lệnh `15,820 tỷ`, Thỏa thuận `2,720 tỷ`).
    *   Thống kê Dòng tiền NĐT ngoại: Mua `1,880 tỷ`, Bán `1,260 tỷ` (Ròng `+620 tỷ`).
    *   Tỷ lệ Tăng/Giảm (Tăng: 386, Giảm: 136, Không đổi: 91).
    *   Biến động mạnh (Tăng mạnh: 65, Giảm mạnh: 22, Biến động > 3%: 97).
    *   Từ khóa nổi bật: `ngân hàng`, `bất động sản`, `dòng tiền`, `lãi suất`, `FLO`, `thanh khoản`, `chứng khoán`.
*   **2.2 Chỉ số Thị trường (Phân loại Trong nước & Thế giới)**:
    *   *Trong nước*: VN-INDEX, VN30, HNX-INDEX hiển thị đồ thị K-line thời gian thực từ API UDF. *(Đã loại bỏ CW Index)*.
    *   *Thế giới*: Nhúng TradingView Widget chính thức cho DOW JONES (`TVC:DJI`), S&P 500 (`TVC:SPX`), NASDAQ (`TVC:IXIC`).

---

## 3. SCANNER (TÌM KIẾM CƠ HỘI CHỨNG QUYỀN)
*   **Tabs lọc**: `[Cơ bản]`, `[Nâng cao]`, `[Yêu thích]`.
*   **3.1 Bộ lọc Nâng cao (Advanced Filter)**:
    *   Dropdown: Loại chứng quyền, T.Cơ sở, Tổ chức phát hành, Sàn.
    *   Range Sliders:
        *   Định giá (Premium/Parity): `0% - 20%`
        *   Delta: `0.3 - 1.0`
        *   Thời gian đáo hạn: `10 - 180 ngày`
        *   Thanh khoản (GTGD/ngày): `> 1 tỷ`
        *   Implied Volatility (IV): `0% - 60%`
    *   Checkbox Tín hiệu: `Định giá thấp (Undervalued)`, `Đà tăng mạnh`, `Thanh khoản cao`, `Rủi ro cao`.
*   **3.2 Bảng Kết Quả G-Score**:
    *   Sắp xếp theo **Điểm G-Score** từ cao xuống thấp (Ví dụ: CVPB2404 - 92 điểm, CHPG2405 - 88 điểm, CVE2403 - 85 điểm).
    *   Cột dữ liệu: Mã CW, Mã cơ sở, Giá hiện tại, Premium %, Delta, IV %, GTGD, Tín hiệu (Giá hấp dẫn, Động lượng tăng, Thanh khoản tốt), Thao tác `[MUA]` / `[RỦI RO]`.

---

## 4. DASHBOARD (BẢNG ĐIỀU KHIỂN & QUẢN TRỊ RỦI RO)
> 📌 **ĐIỀU CHỈNH CHÍNH THEO GHI CHÚ TRONG PDF (Trang 7)**:
> 1. **BỎ HOÀN TOÀN khối 4.1 (Tổng quan danh mục trùng lặp)**.
> 2. **SẮP XẾP THỨ TỰ**: Khối **Phân bổ tài sản** phải xếp TRƯỚC khối **Hiệu suất danh mục**.

*   **Bố cục giao diện hiển thị**:
    1. **CẢNH BÁO RỦI RO (Risk Alert Banner - Trên cùng)**: Thẻ viền đỏ cảnh báo *"Danh mục của bạn đang có 2 mã rủi ro cao. Xem chi tiết >"*.
    2. **PHÂN BỔ TÀI SẢN (Asset Allocation - Hiển thị TRƯỚC)**: Biểu đồ tròn Doughnut Chart thể hiện tỷ trọng vốn:
        *   Chứng quyền: `58%`
        *   Cổ phiếu: `25%`
        *   Tiền mặt: `12%`
        *   Khác: `5%`
    3. **HIỆU SUẤT DANH MỤC (Portfolio Performance - Hiển thị SAU)**: Tăng trưởng NAV `+12.54%` kèm Line Chart so sánh với chỉ số VN-INDEX theo thời gian (1D, 1W, 1M, 3M, 6M, YTD, 1Y, ALL).
    4. **TOP ĐÓNG GÓP LÃI/LỖ**: CVPB2401 (`+4.2 tr`), CHPQ2405 (`+3.1 tr`), HPQ (`+2.0 tr`), CVRE2402 (`-1.2 tr`), CMSN2402 (`-0.6 tr`).
    5. **KHỐI THỐNG KÊ**: Tổng giá trị `128,540,000đ`, Lãi/lỗ chưa thực hiện `+12,540,000đ`, Tỷ suất sinh lời `+12.54%`, Tiền mặt `24,300,000đ`.
    6. **PHÂN BỔ THEO NGÀNH**: Ngân hàng (`40%`), Bất động sản (`25%`), Thép (`13%`), Chứng khoán (`10%`), Khác (`10%`).

---

## 5. PORTFOLIO (QUẢN LÝ GIAO DỊCH & DANH MỤC)
> 📌 **ĐIỀU CHỈNH CHÍNH THEO GHI CHÚ TRONG PDF (Trang 10)**:
> **LOẠI BỎ HOÀN TOÀN đồ thị "Phân bổ theo chứng khoán cơ sở"** trong tab Lịch sử giao dịch để tránh rối mắt.

*   **5.1 Danh mục nắm giữ (Active Holdings)**:
    *   Bảng theo dõi: Mã CW, Mã cơ sở, Loại (Call), Số lượng, Giá mua TB, Giá hiện tại, Giá trị thị trường, Lãi/Lỗ (VND & %), Delta, Premium, Ngày đáo hạn, Trạng thái T+2.5, Nút `[BÁN]`.
*   **5.2 Lịch sử giao dịch (Transaction Logs)**:
    *   Bảng log sạch sẽ: Thời gian, Mã lệnh, Mã CW, Loại (Mua/Bán), Giá đặt, Giá khớp TB, SL đặt, SL khớp, Khớp %, Trạng thái (Khớp toàn bộ / Khớp một phần / Đã hủy).
    *   Phân bổ trạng thái lệnh: Khớp toàn bộ (`76.1%`), Khớp một phần (`16.5%`), Đã hủy (`7.4%`).
    *   Thống kê tốc độ khớp lệnh & lý do hủy lệnh.
*   **5.3 Phân tích Danh mục & Rủi ro**:
    *   Chỉ số hiệu quả: Sharpe Ratio (`1.42`), Sortino Ratio (`2.18`), Max Drawdown (`-8.35%`), Beta (`0.78`), Alpha (`12.54%`).
    *   Phân tích Rủi ro Value at Risk (VaR): VaR 95% (`-2.35%`), VaR 99% (`-3.89%`).

---

## 6. WATCHLIST (DANH SÁCH THEO DÕI)
*   Tabs: `[Chứng khoán cơ sở]` và `[Chứng quyền]`.
*   Cột dữ liệu: Mã CK/CW, Tên tài sản, Giá hiện tại, Thay đổi, % Thay đổi, Xu hướng Sparkline, Khối lượng, Giá trị, Ghi chú theo dõi.

---

## 7. LEARNING (TRUNG TÂM HỌC ĐẦU TƯ & ĐỊNH GIÁ)
*   Tabs: `[Khóa học]`, `[Video]`, `[Bài viết]`, `[Quiz]`, `[Mô phỏng]`.
*   **Khóa học nổi bật**: Hiểu về Chứng quyền, Greeks & Ứng dụng, Định giá Option Black-Scholes, Quản trị rủi ro. Progress bar tiến trình học tập (`65%`).
*   **Trình định giá Greeks Solver (Mô phỏng Black-Scholes)**:
    *   Máy tính toán BSM cho giá lý thuyết và 5 chỉ số Greeks ($\Delta, \Gamma, \mathcal{V}, \Theta, \rho$).
*   **Quiz hàng ngày & Kịch bản mô phỏng giao dịch (Paper Trading Simulation)**.

---

## 8. NEWS (TIN TỨC TÍCH HỢP AI SENTIMENT)
*   Tabs: `[Tất cả]`, `[Thị trường]`, `[Doanh nghiệp]`, `[Vĩ mô]`, `[Phân tích]`.
*   **Layout 2 cột**:
    *   Cột trái: Danh sách tin tức thời gian thực từ FireAnt/vnstock.
    *   Cột phải: 
        *   **AI Sentiment Gauge**: Biểu đồ đo cảm xúc thị trường (`68/100` - Tích cực).
        *   **Từ khóa nổi bật**: `ngân hàng`, `thép`, `bất động sản`, `lãi suất`, `dầu khí`, `chứng khoán`.
        *   Top tin tích cực & tin tiêu cực tác động đến giá CPCS.

---

## 9. ALERTS (CẢNH BÁO GIÁ ĐỘNG)
*   Cài đặt điều kiện cảnh báo cho CW và CPCS (Chạm giá, Biến động Delta, Implied Volatility vượt ngưỡng).
*   Quản lý danh sách cảnh báo (Bật/Tắt công tắc Toggle).
*   Đồng bộ thông báo qua Web App, Email và Telegram Bot.

---

## 10. PRODUCTS (SẢN PHẨM & NÂNG CẤP PREMIUM)
*   Bảng so sánh gói Free vs Premium.
*   Quyền lợi Premium: Mở khóa bộ quét Ma trận 10x10, Greeks Solver không giới hạn, Cảnh báo Telegram tức thì, AI Sentiment News.

---

## 11. CHI TIẾT MÃ CHỨNG QUYỀN (WARRANT DETAIL PAGE)
*   **4.1 Tổng quan**:
    *   Giá hiện tại (`1,210đ`), % Tăng/Giảm (`+10.93%`).
    *   **Biểu đồ Candlestick K-Line**: *Đã chuẩn hóa đơn vị giá lịch sử về VND đồng nhất (chia 1000 nếu > 20.0) để đồ thị nến chạy mượt mà, không bị âm hay phẳng lỳ.*
    *   Biểu đồ Payoff sinh lời/lỗ tại ngày đáo hạn.
    *   Bảng chỉ số Greeks hiện tại ($\Delta: 0.62, \Gamma: 0.018, \Theta: -4.21, \mathcal{V}: 0.35, \rho: 0.07$).
*   **4.2 Định giá BSM**:
    *   Giá lý thuyết Black-Scholes (`1,450đ` vs Giá thị trường `1,210đ` -> Định giá thấp `+19.83%`).
    *   So sánh 4 mô hình định giá: Black-Scholes, Binomial (CRR), Monte Carlo, Parity.
*   **4.3 Greeks Detail**:
    *   Bảng & Đồ thị đường thể hiện sự thay đổi của Greeks theo biến động giá cổ phiếu cơ sở.
*   **4.4 Biểu đồ kỹ thuật**:
    *   Tích hợp chỉ báo RSI (14), MACD (12, 26, 9) và dải Bollinger Bands.

---

## 12. SETTINGS (CÀI ĐẶT HỆ THỐNG)
*   Tabs menu dọc: `Tài khoản`, `Bảo mật`, `Thông báo`, `Giao diện`, `Ngôn ngữ`, `Liên kết tài khoản`, `Về Finvista`.
*   Tùy chọn Chế độ giao diện (Tối / Sáng / Tự động), Tùy chỉnh màu sắc chủ đề, Tốc độ tương tác biểu đồ, Đăng xuất tất cả thiết bị.

---
