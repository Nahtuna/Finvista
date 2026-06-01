# 🚀 HƯỚNG DẪN KHỞI CHẠY NHANH FINVISTA (QUICK START)

Chào mừng bạn đến với **Hệ thống Định giá, Giao dịch Giả lập & Cảnh báo Sớm Chứng quyền Finvista (Finvista SaaS Engine)**.
Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường, cấu hình biến bảo mật và vận hành hệ thống một cách nhanh nhất qua trình CLI điều khiển trung tâm `run.py`.

---

## 📂 1. Cấu Trúc File & Vai Trò Lõi Hệ Thống

Dự án được tổ chức theo chuẩn **Clean Architecture** (Kiến trúc Sạch) giúp cô lập logic nghiệp vụ toán học, cơ sở dữ liệu và API giao tiếp:

| Đường dẫn tệp tin | Vai trò & Trách nhiệm trong Hệ Thống |
| :--- | :--- |
| **[run.py](run.py)** | **[Entrypoint Duy Nhất]** CLI điều khiển trung tâm. Tích hợp banner ASCII, menu điều hướng tiếng Việt để gọi tất cả các tính năng. |
| **[src/api/main.py](src/api/main.py)** | **[API Gateway]** Khởi chạy server FastAPI. Tích hợp Rate Limiting (`slowapi`), WebSockets thời gian thực, xác thực JWT và CORS. |
| **[src/common/database.py](src/common/database.py)** | **[ORM Persistence]** Quản trị cơ sở dữ liệu SQLite (`finvista.db`) bằng SQLAlchemy. Lưu trữ tài khoản, số dư NAV, vị thế và lịch sử giao dịch. |
| **[src/common/telegram_alerts.py](src/common/telegram_alerts.py)** | **[Webhook Alerts]** Động cơ đẩy thông báo HTML tự động về cơ hội `STRONG BUY` hoặc cảnh báo Theta đáo hạn (<14 ngày) qua Telegram. |
| **[src/cw_engine/pricing_core.py](src/cw_engine/pricing_core.py)** | **[Math Engine]** Công thức Black-Scholes-Merton, tính các Greeks lý thuyết ($\Delta, \Gamma, \Theta, \nu$) và trình giải ngược Newton-Raphson IV. |
| **[src/credit_risk/run_pipeline.py](src/credit_risk/run_pipeline.py)** | **[Credit Risk]** Pipeline 5 bước cào BCTC 1,447 doanh nghiệp niêm yết, tính Altman Z''-Score và nhãn rủi ro phá sản. |
| **[src/credit_risk/train_model.py](src/credit_risk/train_model.py)** | **[XGBoost ML]** Đọc dữ liệu, chia tập Train/Test theo chuỗi thời gian, huấn luyện mô hình XGBoost Classifier cảnh báo sớm kiệt quệ tài chính. |
| **[tests/](tests/)** | **[Test Suite]** 15/15 bài test tự động cho REST endpoints và lõi toán học Greeks (chạy qua `pytest`). |
| **[alembic/](alembic/)** | **[Migrations]** Tự động đồng bộ hóa cấu trúc Database schema mà không làm mất mát dữ liệu. |

---

## ⚙️ 2. Thiết Lập Môi Trường Lần Đầu

### Bước 1: Sao chép tệp cấu hình và kích hoạt bảo mật
Nhân bản file cấu hình mẫu `.env.example` thành tệp nội bộ `.env` để nạp các thông tin nhạy cảm:
```powershell
copy .env.example .env
```
Mở tệp `.env` vừa tạo và điền các khóa bí mật của bạn (ví dụ: `JWT_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` để nhận tin nhắn cảnh báo).

### Bước 2: Cài đặt thư viện phụ thuộc
Hệ thống sử dụng các thư viện Python gọn nhẹ nhưng mạnh mẽ. Tiến hành cài đặt qua:
```powershell
pip install -r requirements.txt
```

### Bước 3: Đồng bộ cơ sở dữ liệu ban đầu (Database Migration)
Sử dụng Alembic để tự động tạo cấu trúc bảng dữ liệu sạch:
```powershell
alembic upgrade head
```

---

## ⚡ 3. Hướng Dẫn Vận Hành Dự Án Qua CLI `run.py`

Mở terminal tại thư mục gốc và sử dụng các câu lệnh hợp nhất sau:

### Chức năng A: Khởi chạy API Gateway phục vụ Frontend
Khởi chạy API server cổng 8008 tích hợp đầy đủ WebSockets và Rate Limiting:
```powershell
python run.py api
```
*   *Tài liệu tương tác Swagger:* Truy cập đường dẫn [http://127.0.0.1:8008/docs](http://127.0.0.1:8008/docs).

### Chức năng B: Định giá chứng quyền thời gian thực & Cảnh báo Telegram
Quét toàn bộ thị trường CW, tính IV thực tế, Greeks lý thuyết và lọc cơ hội đầu tư:
```powershell
# Chạy quét thị trường theo chiến thuật Balanced
python run.py scan --strategy balanced

# Gom nhóm theo Cổ phiếu cơ sở và xuất báo cáo CSV ra data/
python run.py scan --group-by cpcs --all
```

### Chức năng C: Phân tích chênh lệch biến động IV vs HV lịch sử
Giải ngược IV lịch sử 10 ngày gần nhất và so sánh với biến động thực tế HV của cổ phiếu cơ sở:
```powershell
python run.py history --symbol CACB2510 --days 10
```

### Chức năng D: Bot giao dịch giả lập tự động (Paper Trading)
Quản trị vị thế, kiểm soát chốt lời cắt lỗ HOSE thời gian thực:
```powershell
# Quét danh mục và tự động thực thi tín hiệu chốt lời (+20%), cắt lỗ (-15%)
python run.py trade --scan

# Xem tài sản ròng NAV, số dư tiền mặt và vị thế mở của bạn
python run.py trade --portfolio
```

### Chức năng E: Pipeline chấm điểm tín dụng 1,447 Doanh nghiệp & Train XGBoost
```powershell
# Chạy pipeline 5 bước thu thập BCTC và gán nhãn Altman Z''
python run.py credit

# Huấn luyện mô hình học máy XGBoost dự báo Danger Zone
python run.py credit --train
```

---
*Tài liệu vận hành nhanh được số hóa và chuẩn hóa tại UPGen Deutsches Haus Tower.*
