# 🤝 Hướng Dẫn Đóng Góp & Phát Triển Dự Án (Contributing Guide)

Tài liệu này hướng dẫn các developer (và AI) quy trình thiết lập môi trường, phát triển tính năng mới, viết tests và đóng góp mã nguồn vào dự án **Finvista**.

---

## 🛠️ 1. Setup Môi Trường Phát Triển Local

Dự án sử dụng Python 3.9+ và node/npm cho frontend. Bạn nên sử dụng `virtualenv` hoặc `venv` để cô lập môi trường.

### Backend Setup
1. **Khởi tạo và kích hoạt môi trường ảo:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1   # Trên Windows
   source .venv/bin/activate    # Trên macOS/Linux
   ```
2. **Cài đặt dependencies:**
   ```powershell
   pip install -r requirements.txt
   pip install -e .[dev]
   ```
3. **Cấu hình biến môi trường:**
   Sao chép `.env.example` thành `.env` và điền đầy đủ các thông tin bí mật.

### Database Migrations (Alembic)
Khi thay đổi schema database của SQLAlchemy, bạn cần tạo migration:
```powershell
# Tạo file migration tự động phát hiện thay đổi
alembic revision --autogenerate -m "description_of_change"

# Nâng cấp database local lên phiên bản mới nhất
alembic upgrade head
```

---

## 🧪 2. Viết & Chạy Tests

Tất cả các tính năng hoặc bug fix mới đều **bắt buộc** phải đi kèm với unit tests hoặc integration tests.

### Chạy Test Suite
Sử dụng `pytest` để thực thi toàn bộ test:
```powershell
pytest
```

### Yêu cầu viết test:
*   Đặt file test trong thư mục `tests/` và đặt tên dạng `test_*.py`.
*   Mock các network requests hoặc API bên ngoài (như gọi sang Gemini API hoặc cào dữ liệu từ SSI).
*   Đảm bảo test coverage cho các logic nghiệp vụ quan trọng tối thiểu đạt **80%**.

---

## 🌿 3. Git Workflow & Quy Tắc Đóng Góp

Để đảm bảo lịch sử Git sạch và dễ theo dõi, dự án tuân theo các quy tắc sau:

### Git Branching Model
*   **`main`**: Nhánh production, luôn ổn định và sẵn sàng deploy.
*   **`develop`**: Nhánh tích hợp chính.
*   **`feature/*`**: Các nhánh phát triển tính năng mới (ví dụ: `feature/vietqr-webhook`).
*   **`bugfix/*`** hoặc **`hotfix/*`**: Nhánh sửa lỗi.

### Commit Messages Standard
Dự án áp dụng chuẩn **Conventional Commits**:
*   `feat: <mô tả ngắn>`: Thêm tính năng mới.
*   `fix: <mô tả ngắn>`: Sửa bug.
*   `docs: <mô tả ngắn>`: Cập nhật tài liệu.
*   `style: <mô tả ngắn>`: Thay đổi format, linting (không ảnh hưởng logic code).
*   `refactor: <mô tả ngắn>`: Tái cấu trúc mã nguồn.
*   `test: <mô tả ngắn>`: Thêm hoặc sửa tests.

---

## 🐍 4. Tiêu Chuẩn Coding (Coding Standards)

Hãy đọc kỹ chi tiết tiêu chuẩn code cho cả Backend và Frontend tại:
➔ **[05_coding_standards.md](file:///c:/Users/samvo/Downloads/Finvista/docs/reverse_engineering/app-spec-context/05_coding_standards.md)**

Một số điểm cốt lõi:
1.  **Type Hints**: Bắt buộc đối với toàn bộ tham số đầu vào và kiểu trả về của function.
2.  **Docstrings**: Viết docstrings theo chuẩn Google Style cho tất cả classes và public functions.
3.  **Naming**:
    *   Python variables & functions: `snake_case`
    *   Python classes: `PascalCase`
    *   URLs: `kebab-case` (ví dụ: `/api/v1/cw-market-data`)
