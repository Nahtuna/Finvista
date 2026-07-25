# Finvista Documentation

## 📚 Cấu Trúc Tài Liệu

```
docs/
├── architecture/          # Thiết kế hệ thống & kiến trúc
├── guides/               # Hướng dẫn sử dụng & API
├── research/             # Nghiên cứu & roadmap
├── reference/            # Tài liệu tham khảo (FinLens analysis)
├── reverse_engineering/  # Đặc tả & phân tích kỹ thuật hệ thống FinLens
└── archive/              # Tài liệu cũ/lưu trữ
```

---

## 🏗️ architecture/

Thiết kế kiến trúc hệ thống Finvista:

- `decision_making_pipeline.md` - Pipeline ra quyết định
- `golden_modern_architecture.md` - Kiến trúc modern chuẩn
- `modern_data_stack_architecture.md` - Stack dữ liệu hiện đại
- `saas_architecture_blueprint.md` - Blueprint kiến trúc SaaS

---

## 📖 guides/

Hướng dẫn sử dụng cho người dùng và developer:

- `user_guide.md` - Hướng dẫn sử dụng tổng quan
- `quick_start.md` - Bắt đầu nhanh
- `api_documentation.md` - Tài liệu API
- `cw_metrics_handbook.md` - Cẩm nang chỉ số chứng quyền
- `telegram_webhook_setup.md` - Cài đặt Telegram webhook
- `contributing.md` - Hướng dẫn đóng góp & phát triển dự án
- `environment_variables.md` - Hướng dẫn cấu hình biến môi trường

---

## 🔬 research/

Nghiên cứu, phân tích và roadmap phát triển:

- `roadmap.md` - Roadmap phát triển chính
- `financial_distress_roadmap.md` - Roadmap phân tích distress
- `modern_market_research.md` - Nghiên cứu thị trường hiện đại
- `ai_data_enhancement_summary.md` - Tóm tắt nâng cấp dữ liệu AI
- `credit_distress_audit.md` - Audit credit distress
- `rccr_conformal_risk_framework.md` - Framework rủi ro conformal
- `unified_integration_plan.md` - Kế hoạch tích hợp thống nhất
- `finlens_app_analysis_tasks.md` - Tasks phân tích app FinLens
- `finlens_scraper_tasks.md` - Tasks scraper FinLens
- `modern_data_requirements.md` - Yêu cầu dữ liệu hiện đại
- `roadmap_realtime.md` - Roadmap real-time
- `ref/` - Tài liệu tham chiếu (28 items)

---

## 🛠️ reverse_engineering/

Đặc tả và tài liệu kỹ thuật thu thập được từ quá trình phân tích ứng dụng FinLens:

- `app-spec-context/`
  - `00_AI_IMPLEMENTATION_GUIDE.md` - Hướng dẫn nạp đặc tả cho AI phát triển clone
  - `01_architecture.md` - Kiến trúc hệ thống
  - `02_database_schema.md` - Thiết kế CSDL chi tiết
  - `03_api_endpoints.md` - Các endpoints và WebSockets API
  - `04_features_flow.md` - Luồng hoạt động của các tính năng
  - `05_coding_standards.md` - Tiêu chuẩn code (Python, React/TS, SQL)

---

## 📚 reference/

Tài liệu tham khảo và phân tích từ các nguồn khác:

- `finlens_analysis.md` - Phân tích chi tiết app FinLens
- `finlens_media/` - Media files (ảnh, video, PDF) từ FinLens (132 files)

---

## 🗄️ archive/

Tài liệu cũ, ít dùng hoặc đã thay thế:

- `finlens_legacy/` - Tài liệu FinLens cũ
  - `FINLENS_BOCTACH_HOANTOAN.md` - Phân tích hoàn chỉnh FinLens
  - `FINLENS_LIVE_ANALYSIS.md` - Live analysis FinLens

---

## 🚀 Quick Start

1. **New to Finvista?** → Xem `guides/quick_start.md`
2. **Developer?** → Xem `guides/contributing.md` và `guides/api_documentation.md`
3. **Architecture?** → Xem `architecture/saas_architecture_blueprint.md`
4. **Research?** → Xem `research/roadmap.md`
5. **Reference?** → Xem `reference/finlens_analysis.md`
6. **Reverse Engineering?** → Xem `reverse_engineering/app-spec-context/00_AI_IMPLEMENTATION_GUIDE.md`

---

## 📝 Notes

- Tất cả file đều được giữ nguyên, chỉ reorganize cấu trúc và chuẩn hóa tên file viết thường
- Thư mục đặc tả kỹ thuật `reverse_engineering/` được tích hợp chính thức vào tài liệu
- File media từ FinLens được gom vào `reference/finlens_media/`
- File cũ ít dùng được chuyển vào `archive/`
- Cấu trúc mới giúp dễ tìm kiếm và quản lý hơn

