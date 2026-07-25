# ⚙️ Hướng Dẫn Cấu Hình Biến Môi Trường (Environment Variables)

Dự án **Finvista** sử dụng file `.env` nằm ở thư mục gốc để nạp các cấu hình và API key cần thiết khi khởi chạy. Dưới đây là chi tiết ý nghĩa và cách lấy các biến này.

---

## 💾 1. Cấu Hình Cơ Sở Dữ Liệu (Database)

*   `DATABASE_URL`: Đường dẫn kết nối CSDL (PostgreSQL). Dự án được thiết kế tương thích với Supabase.
    *   *Định dạng:* `postgresql://<user>:<password>@<host>:<port>/<dbname>`
    *   *Cách lấy:* Truy cập Supabase Dashboard ➔ Project Settings ➔ Database ➔ Connection String (URI).

---

## 🔒 2. Bảo Mật & Xác Thực (Security & Auth)

*   `JWT_SECRET_KEY`: Khóa bí mật dùng để mã hóa mã thông báo JWT bảo mật cho API.
    *   *Yêu cầu:* Nên là một chuỗi ngẫu nhiên có độ dài tối thiểu 32 ký tự (ví dụ tạo nhanh bằng lệnh: `openssl rand -hex 32`).
*   `JWT_ALGORITHM`: Thuật toán mã hóa JWT. Mặc định là `HS256`.
*   `ACCESS_TOKEN_EXPIRE_MINUTES`: Thời gian hết hạn của token truy cập tính bằng phút. Mặc định là `1440` (24 giờ).

---

## 📢 3. Cảnh Báo Telegram Webhook (Telegram Alerts)

*   `TELEGRAM_ALERTS_ENABLED`: Bật/tắt tính năng đẩy cảnh báo tín hiệu chứng quyền tự động về Telegram. Nhận giá trị `true` hoặc `false`.
*   `TELEGRAM_BOT_TOKEN`: Mã token của Bot Telegram do BotFather cung cấp khi bạn tạo bot.
*   `TELEGRAM_CHAT_ID`: ID của chat room hoặc group/channel nhận tin nhắn cảnh báo.

---

## 🤖 4. Cấu Hình AI (Large Language Models)

Dự án tích hợp OpenRouter để gọi các mô hình AI phục vụ cho hội đồng AI phân tích (AI Committee).

*   `OPENROUTER_API_KEY`: API key của OpenRouter để gọi các mô hình LLM.
*   `OPENROUTER_BATCH_MODEL`: Model LLM sử dụng cho các tác vụ xử lý hàng loạt (ví dụ: `openrouter/free` hoặc `google/gemini-2.5-flash`).
*   `OPENROUTER_DEEP_MODEL`: Model LLM mạnh mẽ hơn cho phân tích sâu (ví dụ: `google/gemini-2.5-pro`).

---

## 📊 5. Cấu Hình Thu Thập Dữ Liệu (ETL & Scrapers)

Để cào dữ liệu lịch sử giá, tin tức và báo cáo tài chính:

*   `VNSTOCK_API_KEY`: API Key sử dụng cho thư viện `vnstock` để tải thông tin thị trường chứng khoán Việt Nam.
*   `FIREANT_TOKEN`: Token xác thực tài khoản FireAnt dùng để cào các bài phân tích, tin tức phục vụ RAG.
    *   *Cách lấy:* Đăng nhập vào [fireant.vn](https://fireant.vn) trên trình duyệt ➔ Nhấn `F12` ➔ Tab `Network` ➔ Chọn một request bất kỳ ➔ Tìm header `Authorization` và sao chép phần chuỗi token (không cần chữ `Bearer ` ở trước).

---

## ⚡ 6. Cấu Hình Khác (ML, Caching)

*   `REDIS_ENABLED`: Bật (`true`) hoặc tắt (`false`) lớp cache Redis.
*   `REDIS_URL`: Địa chỉ máy chủ Redis (mặc định: `redis://localhost:6379/0`).
*   `FINVISTA_TUNE`: Bật/tắt quá trình tối ưu hóa siêu tham số (Hyperparameter tuning) cho Machine Learning.
*   `FINVISTA_USE_SMOTE`: Bật (`1`) hoặc tắt (`0`) thuật toán SMOTE để cân bằng tập dữ liệu huấn luyện.
