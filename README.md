# 🏆 FINVISTA: NỀN TẢNG ĐỊNH GIÁ & QUẢN TRỊ RỦI RO CHỨNG QUYỀN (SAAS PRO)

<p align="center">
  <a href="https://github.com/Nahtuna/Finvista">
    <img src="https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/SQLAlchemy-D31900?style=for-the-badge&logo=python&logoColor=white" alt="SQLAlchemy">
    <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/JWT_Auth-Isolated-orange?style=flat-square&logo=json-web-tokens&logoColor=white" alt="JWT">
  <img src="https://img.shields.io/badge/Realtime-WebSockets-brightgreen?style=flat-square" alt="WebSockets">
  <img src="https://img.shields.io/badge/Rate_Limiting-Active-red?style=flat-square" alt="Rate Limiting">
  <img src="https://img.shields.io/badge/Tests-15%2F15%20Passed-success?style=flat-square&logo=pytest&logoColor=white" alt="Tests">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License">
</p>

> **Quantitative Covered Warrant Core Engine & Enterprise API Gateway (Vietnamese Financial Markets)**  
> Trụ sở nghiên cứu: **UPGen Deutsches Haus Tower, Quận 1, TP. Hồ Chí Minh**


---

## 🌟 Tổng Quan Dự Án

**Finvista** là giải pháp toán học tài chính tinh gọn và bảo mật cao giúp định giá, phát hiện cơ hội giao dịch lệch giá biến động (Volatility Arbitrage) và quản trị rủi ro cho **Chứng quyền có bảo đảm (Covered Warrants - CW)** tại Việt Nam.

Nền tảng đã được tái cấu trúc hoàn chỉnh theo chuẩn **Kiến trúc Sạch (Clean Architecture)** với một cổng điều khiển trung tâm duy nhất `run.py` tại thư mục gốc, hệ thống lưu trữ bền vững SQLite bằng ORM SQLAlchemy, xác thực người dùng bảo mật cao JWT, cổng API Gateway tích hợp WebSockets thời gian thực và Rate Limiting bảo vệ máy chủ.

---

## 📂 Kiến Trúc Dự Án Hoàn Chỉnh (Clean Architecture)

```
Finvista/
├── alembic/                         📂 FILE MIGRATION CỦA DATABASE (Đồng bộ Schema tự động)
├── data/                            📂 THƯ MỤC DỮ LIỆU CỤC BỘ (Không commit Git)
│   ├── finvista.db                  ├─ Cơ sở dữ liệu SQLite chính của hệ thống SaaS
│   └── underlying_hv_cache.json     └─ Cache biến động lịch sử (HV) chống Rate Limit
├── docs/                            📂 TÀI LIỆU NGHIÊN CỨU & SLIDE DỰ ÁN
├── scripts/                         📂 CÁC KỊCH BẢN KHỞI CHẠY LẺ (Đã di chuyển vào đây)
│   ├── run_cw.py                    ├─ Phân tích định giá CW & cảnh báo Telegram
│   ├── run_cw_history.py            ├─ Phân tích lịch sử Volatility IV vs HV
│   ├── run_paper_trader.py          ├─ Bot paper trade tự động hóa
│   └── run_credit_risk.py           └─ Pipeline chấm điểm tín dụng Altman Z & XGBoost
├── src/                             🧠 THƯ MỤC MÃ NGUỒN CHÍNH
│   ├── api/                         ├─ API Gateway (main.py, WebSockets, Rate Limiting, CORS)
│   ├── common/                      ├─ Cơ sở hạ tầng (config, database.py ORM, telegram_alerts)
│   ├── credit_risk/                 ├─ Mô hình & Pipeline kiệt quệ tài chính XGBoost
│   └── cw_engine/                   └─ Toán học định giá BSM, Greeks & Trình giải Newton-Raphson
├── tests/                           🧪 BỘ KIỂM THỬ TỰ ĐỘNG (pytest 15/15 cases thành công 100%)
├── tools/                           📂 TIỆN ÍCH HỖ TRỢ (Setup API, Dò Chat ID Telegram)
├── run.py                           🏆 TRÌNH ĐIỀU KHIỂN TRUNG TÂM (CLI - ENTRYPOINT DUY NHẤT)
├── .env.example                     ⚙️ Tệp cấu hình môi trường mẫu cho Nhà phát triển
├── requirements.txt                 ⚙️ Danh sách thư viện phụ thuộc cực nhẹ
└── LICENSE                          ⚙️ Giấy phép phần mềm MIT
```

---

## ⚙️ Cấu Hình Môi Trường (.env)

Hệ thống quản lý thông tin nhạy cảm qua tệp `.env` tại thư mục gốc. Trước khi khởi chạy, hãy sao chép tệp mẫu và điền thông tin thực tế:
```bash
cp .env.example .env
```
Các biến cấu hình chính hỗ trợ nạp động bao gồm:
*   `DATABASE_URL`: Đường dẫn SQLite (mặc định) hoặc PostgreSQL/MySQL khi deploy production.
*   `JWT_SECRET_KEY`: Khóa mã hóa bảo mật tài khoản đa người dùng.
*   `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: Credentials để đẩy cảnh báo thị trường thời gian thực.

---

## ⚡ Hướng Dẫn Vận Hành Qua Trình Điều Khiển Trung Tâm (`run.py`)

Tất cả các chức năng của hệ thống được hợp nhất về trình CLI chuyên nghiệp tại thư mục gốc. Bạn chỉ cần chạy thông qua `python run.py`.

### 1. Khởi chạy API Gateway & WebSocket Server
Khởi chạy cổng API Gateway phục vụ SaaS đa người dùng, tích hợp Rate Limiting và WebSocket stream dữ liệu:
```bash
python run.py api
```
*   **REST API Swagger:** Truy cập [http://127.0.0.1:8008/docs](http://127.0.0.1:8008/docs) để xem tài liệu tương tác đầy đủ.
*   **WebSocket Endpoint:** `ws://127.0.0.1:8008/api/ws` (dùng để stream NAV danh mục và trạng thái quét thị trường thời gian thực).

---

### 2. Định Giá Chứng Quyền & Cảnh Báo Telegram
Nạp dữ liệu từ Vietcap API, giải ngược IV, tính Greeks lý thuyết và đẩy cảnh báo tức thời:
```bash
# Quét thị trường với chiến thuật Mặc định (Balanced)
python run.py scan --strategy balanced

# Quét thị trường với chiến thuật An Toàn (Safe)
python run.py scan --strategy safe

# Quét thị trường với chiến thuật Aggressive (Đòn bẩy cao)
python run.py scan --strategy aggressive

# Gom nhóm cơ hội theo Cổ phiếu cơ sở (CPCS)
python run.py scan --group-by cpcs --all
```

---

### 3. Nghiên Cứu Lịch Sử Biến Động IV vs HV
Phân tích đường cong biến động lịch sử, phát hiện lệch giá biến động (Volatility Arbitrage) và in biểu đồ ASCII:
```bash
python run.py history --symbol CACB2510 --days 10
```

---

### 4. Giả Lập Giao Dịch Thực Chiến HOSE (Paper Trading)
Mô phỏng tài khoản vốn 100 Triệu VND, khớp lệnh theo đúng luật HOSE, tự động chốt lời/cắt lỗ:
```bash
# Xem bảng điều khiển tài sản & vị thế nắm giữ của tài khoản hiện tại
python run.py trade --portfolio

# Quét tín hiệu thị trường và thực thi lệnh (Cắt lỗ -15%, Chốt lời +20%)
python run.py trade --scan

# Chạy bot tự động hóa quét lệnh liên tục 5 phút một lần
python run.py trade --scan --loop 300

# Reset tài khoản demo về 100 Triệu VND ban đầu
python run.py trade --reset
```

---

### 5. Pipeline Chấm Điểm & Huấn Luyện Tín Dụng XGBoost
Cào dữ liệu BCTC, dự báo Altman Z''-Score và huấn luyện mô hình XGBoost cảnh báo rủi ro vỡ nợ doanh nghiệp:
```bash
# Chạy pipeline 5 bước cào dữ liệu & tự động gán nhãn rủi ro
python run.py credit

# Huấn luyện mô hình Machine Learning XGBoost Classifier với dữ liệu đã cào
python run.py credit --train
```

---

## 🧪 Bộ Kiểm Thử Tự Động (Test Suite)

Hệ thống được đảm bảo tính ổn định tuyệt đối nhờ bộ suite kiểm thử tích hợp REST API và kiểm thử đơn vị logic toán học. Chạy kiểm thử tức thời qua:
```bash
python -m pytest -s
```
*Kết quả kiểm thử đạt tỉ lệ thành công 100% (15/15 cases passed), bảo chứng cho chất lượng backend sẵn sàng đưa vào vận hành thực tế.*

---

## 🎯 Lộ Trình Giai Đoạn Frontend (ROADMAP)
Hãy xem chi tiết tệp [ROADMAP.md](ROADMAP.md) ở thư mục gốc để nắm được:
*   **Gap Analysis:** Đánh giá độ khớp giữa hồ sơ thiết kế khả thi **Finvista (PDF)** và mã nguồn thực tế.
*   **Giai đoạn 5 (Active):** Kế hoạch xây dựng giao diện ReactJS + TailwindCSS tương tác đồ thị và bảng nhiệt 2D Scenario P/L Heatmap chuyên nghiệp.
