# Danh Sách Nhiệm Vụ Bóc Tách Dữ Liệu FinLens (finlensquant.vn)

Tài liệu này chi tiết hóa các bước thực thi để bóc tách dữ liệu chứng quyền (Covered Warrants) và các chỉ số định lượng từ hệ thống FinLens.

---

## 📅 Giai Đoạn 1: Reverse Engineering & Khảo Sát API (Phân Tích)

### [ ] Task 1.1: Khảo sát Tĩnh & Động
- **Mục tiêu**: Xác định cách thức trang web tải dữ liệu.
- **Chi tiết**:
  - Kiểm tra xem dữ liệu được render từ Server (SSR) hay gọi API từ Client (SPA).
  - Thu thập toàn bộ danh sách HTTP API endpoints (ví dụ: `/api/v1/sectors`, `/api/v1/matrix`, `/api/v1/cw/active`).
  - Ghi nhận cấu trúc payload yêu cầu và phản hồi (JSON schema).

### [ ] Task 1.2: Phân Tích WebSocket Stream (`wss://finlensquant.vn/ws`)
- **Mục tiêu**: Giải mã luồng dữ liệu thời gian thực.
- **Chi tiết**:
  - Ghi lại bản tin handshake ban đầu.
  - Xác định cấu trúc bản tin đăng ký nhận dữ liệu (Subscribe): ví dụ: `{"action": "subscribe", "topic": "cw_tickers"}`.
  - Phân tích bản tin trả về (Heartbeat, Ticker Updates, Scatter Plot positions).

### [ ] Task 1.3: Đánh giá Rào Cản Kỹ Thuật (Anti-Bot & Authentication)
- **Mục tiêu**: Đảm bảo scraper không bị chặn và hoạt động ổn định.
- **Chi tiết**:
  - Kiểm tra xem trang web có sử dụng Cloudflare, Incapsula hoặc các giải pháp WAF khác không.
  - Phân tích cơ chế sinh Token/Session: cookie, Bearer JWT, hoặc custom headers.
  - Xác định giới hạn tần suất gọi tin (Rate Limit) của server đối với 1 IP.

---

## 🛠️ Giai Đoạn 2: Thiết Kế Database Schema & Mapping Dữ Liệu

### [ ] Task 2.1: Thiết Kế Database Tables cho FinLens Data
- **Mục tiêu**: Lưu trữ dữ liệu bóc tách một cách khoa học.
- **Chi tiết**:
  - Tạo bảng `finlens_cw_signals` (lưu trữ Delta, Premium, Moneyness, Maturity, Volume, Scatter X/Y).
  - Tạo bảng `finlens_regime_matrix` (lưu trữ ma trận 10x10, Opportunity Score, Stability Score).
  - Tạo bảng `finlens_sector_analysis` (lưu xếp hạng ngành, dòng tiền, OLS projection).
  - Viết file migration bằng Alembic trong thư mục `alembic/versions/`.

### [ ] Task 2.2: Mapping Mã Chứng Quyền & Phân Loại Ngành
- **Mục tiêu**: Đồng bộ dữ liệu bóc tách với hệ thống dữ liệu hiện tại của Finvista.
- **Chi tiết**:
  - Áp dụng các quy tắc lọc ngành (loại bỏ ngân hàng/tài chính đối với luồng doanh nghiệp thường và áp dụng CAMEL cho ngân hàng nếu cần).
  - Chuẩn hóa tên trường của FinLens về dạng snake_case tương thích với codebase.

---

## 💻 Giai Đoạn 3: Phát Triển Ingestion Engine (Scraper)

### [ ] Task 3.1: Xây Dựng Core Scraper Client (`finlens_client.py`)
- **Mục tiêu**: Triển khai logic gọi API/WS kiên cường.
- **Chi tiết**:
  - Sử dụng thư viện `requests` cho HTTP APIs và `websockets` (hoặc `aiohttp`) cho WebSocket streams.
  - Triển khai cơ chế Retry với Exponential Backoff & Jitter (độ trễ ngẫu nhiên) để tránh bị phát hiện là bot.
  - Tích hợp Proxy Rotation nếu hệ thống yêu cầu cào với tần suất cao.

### [ ] Task 3.2: Module Lưu Trạng Thế (State & Checkpoint Manager)
- **Mục tiêu**: Đảm bảo tính chịu lỗi (Fault Tolerance).
- **Chi tiết**:
  - Lưu checkpoint cuối cùng thành công vào file JSON hoặc Redis.
  - Ghi nhận các lỗi (failed tickers, failed endpoints) vào log file để chạy quét bù (fallback run).

---

## 🧪 Giai Đoạn 4: Kiểm Thử & Tự Động Hóa

### [ ] Task 4.1: Viết Unit Tests & Integration Tests
- **Mục tiêu**: Đảm bảo code chạy đúng khi cấu trúc trang web thay đổi.
- **Chi tiết**:
  - Viết mock-tests cho các phản hồi API của FinLens.
  - Tạo test case chạy thử luồng cào thực tế trong môi trường sandbox (`tests/modules/cw_pricing/test_finlens_scraper.py`).

### [ ] Task 4.2: Tích hợp Lập Lịch & Giám Sát (Cron Jobs & Alerts)
- **Mục tiêu**: Đưa hệ thống vào vận hành tự động.
- **Chi tiết**:
  - Cấu hình cron job chạy scraper định kỳ (ví dụ: mỗi 5 phút trong phiên giao dịch từ 9:00 - 15:00 cho WebSocket/Scatter data, và 1 lần vào lúc 17:00 cho Sector/Cashflow data).
  - Thiết lập Telegram/Email Alert webhook khi scraper gặp lỗi liên tiếp hoặc cấu trúc API của FinLens thay đổi (Schema Drift).
