# Lộ Trình Nghiên Cứu, Phân Tích & Bóc Tách Toàn Diện Ứng Dụng FinLens

Tài liệu này vạch ra các nhiệm vụ chi tiết để thực hiện nghiên cứu thực địa (reverse engineering), bóc tách dữ liệu và tìm hiểu sâu cơ chế hoạt động của toàn bộ ứng dụng FinLens (https://finlensquant.vn/).

---

## 📅 GIAI ĐOẠN 1: REVERSE ENGINEERING FRONTEND & UI/UX (Khảo Sát Giao Diện)

### [ ] Task 1.1: Khảo sát Cấu trúc Component & DOM
- **Mục tiêu**: Tìm hiểu cách thức dựng giao diện và các thư viện UI được sử dụng.
- **Chi tiết**:
  - Dùng Inspect Element kiểm tra framework sử dụng (React, Next.js, Vue, hay Nuxt).
  - Phân tích các class CSS để xác định hệ thống styling (Tailwind CSS, CSS Modules, hay Styled Components).
  - Xác định các thư viện đồ thị đang dùng (Highcharts, ECharts, Recharts, Chart.js, hay D3.js) cho Scatter Plot, Pareto Chart, Radar Chart, và Matrix Grid.

### [ ] Task 1.2: Phân Tích Luồng Trải Nghiệm (User Flow Mapping)
- **Mục tiêu**: Vẽ lại bản đồ điều hướng của toàn bộ hệ thống FinLens.
- **Chi tiết**:
  - Ghi lại các bước đăng ký/đăng nhập (Auth Flow).
  - Khảo sát chức năng phân quyền giữa các gói tài khoản (Demo, Client, Client Pro) xem việc chặn tính năng diễn ra ở Frontend (ẩn nút/hiển thị modal nâng cấp) hay trả về lỗi 403 ở Backend.
  - Vẽ sơ đồ chuyển trang (Trang chủ -> Dashboard -> DeepFinLens -> Sector Analysis).

---

## 📐 GIAI ĐOẠN 2: REVERSE ENGINEERING MÔ HÌNH TOÁN HỌC & ĐỊNH LƯỢNG (Quant Engine)

### [ ] Task 2.1: Giải Mã Thuật Toán Tính Toán "Opportunity Score" (DeepFinLens Matrix)
- **Mục tiêu**: Tìm ra công thức định lượng điểm cơ hội trong ô ma trận 10x10.
- **Chi tiết**:
  - Quan sát trục X (Maturity - Thời gian đáo hạn) và trục Y (Moneyness - Độ sâu giá thực hiện).
  - Thu thập dữ liệu điểm số (0 - 100) của các ô tương ứng với các trạng thái thị trường khác nhau.
  - Phân tích xem điểm số được tính bằng công thức tĩnh (tỷ lệ Delta, Volatility, Premium) hay được huấn luyện qua mô hình Machine Learning/Deep Learning (DeepFinLens Classification).

### [ ] Task 2.2: Phân Tích Phương Pháp Dự Báo Ngành (Sector OLS Projection)
- **Mục tiêu**: Tái tạo lại mô hình hồi quy dự báo xu hướng ngành.
- **Chi tiết**:
  - Thu thập dữ liệu đầu vào của mô hình OLS (ví dụ: chuỗi giá đóng cửa, thanh khoản ngành, hay chỉ số VNINDEX).
  - Xác định số phiên lịch sử được sử dụng để khớp đường hồi quy (Lookback window) và số phiên dự báo (Forecast window - ví dụ: 30 ngày).
  - Phân tích cách tính độ tin cậy (Confidence intervals) và chỉ số R-squared hiển thị trên biểu đồ.

---

## 🔌 GIAI ĐOẠN 3: REVERSE ENGINEERING HỆ THỐNG API & DATA FLOW (Kết Nối Dữ Liệu)

### [ ] Task 3.1: Chặn và Phân Tích Request HTTP (Interception)
- **Mục tiêu**: Lập danh mục tất cả API Gateway endpoints của FinLens.
- **Chi tiết**:
  - Sử dụng công cụ proxy (như Charles Proxy, Fiddler, hoặc Burp Suite) để bắt toàn bộ request HTTPS giữa Client và Backend.
  - Lập tài liệu Swagger/OpenAPI không chính thức cho FinLens API bao gồm:
    - URL Endpoint (ví dụ: `GET /api/v1/sector-rotation`, `POST /api/v1/matrix-filter`).
    - Headers (Authorization JWT, User-Agent, Referer).
    - Cấu trúc Payload (JSON parameters).
    - Cấu trúc Response.

### [ ] Task 3.2: Khảo Sát Kênh WebSocket (`wss://finlensquant.vn/ws`)
- **Mục tiêu**: Hiểu cấu trúc truyền tin thời gian thực.
- **Chi tiết**:
  - Ghi nhận thông điệp ping-pong để giữ kết nối.
  - Giải mã cơ chế gửi cập nhật giá chứng quyền trực tiếp (L2/L3 data stream).
  - Đánh giá băng thông và tần suất gửi dữ liệu (Frequency/Heartbeat rate).

---

## 💰 GIAI ĐOẠN 4: NGHIÊN CỨU LUỒNG THANH TOÁN (VietQR Integration)

### [ ] Task 4.1: Phân Tích Cơ Chế Khởi Tạo VietQR
- **Mục tiêu**: Xem cách thức ứng dụng tích hợp cổng thanh toán tự động VietQR.
- **Chi tiết**:
  - Kiểm tra xem API sinh mã VietQR là từ bên thứ ba (PayOS, VietQR.io, Casso) hay do FinLens tự build bằng cách mã hóa thông tin tài khoản ngân hàng + số tiền + nội dung chuyển khoản theo chuẩn EMVCo.

### [ ] Task 4.2: Cơ Chế Đồng Bộ Trạng Thái Giao Dịch (Callback/Webhook)
- **Mục tiêu**: Hiểu cách hệ thống nâng cấp tài khoản tức thì sau khi quét mã.
- **Chi tiết**:
  - Khảo sát xem Client dùng kỹ thuật Long Polling (gọi API liên tục để check trạng thái thanh toán) hay WebSocket push tín hiệu từ server sau khi nhận được webhook từ ngân hàng.
