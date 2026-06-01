# 🏆 FINVISTA: NỀN TẢNG ĐỊNH GIÁ & QUẢN TRỊ RỦI RO CHỨNG QUYỀN
> **Quantitative Covered Warrant Core Engine (Vietnamese Financial Markets)**  
> Trụ sở nghiên cứu: **UPGen Deutsches Haus Tower, Quận 1, TP. Hồ Chí Minh**

---

## 🌟 Tổng Quan Dự Án

**Finvista** là một giải pháp toán học tài chính tinh gọn giúp định giá và quản trị rủi ro cho **Chứng quyền có bảo đảm (Covered Warrants - CW)** tại Việt Nam.

Nền tảng loại bỏ sự phức tạp cồng kềnh bằng cách tích hợp toàn bộ giải thuật định lượng lõi vào một kiến trúc **Siêu tối giản & Mô-đun hóa (Modular Architecture)** gồm đúng **4 tệp khởi chạy thực chiến** ở thư mục gốc và thư viện lõi cô lập trong `src/`:

1.  **`run_cw.py`**: Quét lọc toàn thị trường, xếp hạng cơ hội đầu tư bằng Greeks ($\Delta, \Gamma, \Theta, \nu$), xác suất ITM, và tự động gửi cảnh báo HTML chất lượng cao qua Telegram Bot.
2.  **`run_cw_history.py`**: Trình phân tích biến động lịch sử, tự động giải ngược IV (Implied Volatility) theo thời gian và đối chiếu với HV (Historical Volatility) của cổ phiếu cơ sở để phát hiện Volatility Arbitrage (lệch giá biến động). Vẽ biểu đồ ASCII trực tiếp trên Terminal.
3.  **`run_paper_trader.py`**: Siêu bot giao dịch giả lập thời gian thực. Tuân thủ 100% luật HOSE (phí giao dịch, chu kỳ thanh toán T+2.5, lô tối thiểu 100 CW). Hỗ trợ chế độ chạy vòng lặp liên tục tự động canh lệnh 24/7.
4.  **`run_credit_risk.py`**: Pipeline thu thập BCTC của 1,447 doanh nghiệp niêm yết trên 3 sàn, tính toán điểm Altman Z''-Score và huấn luyện mô hình XGBoost để cảnh báo sớm rủi ro phá sản của cổ phiếu cơ sở.

---

## 📂 Kiến Trúc Dự Án Hiện Tại

```
vnstock-main/
├── data/                             📂 THƯ MỤC DỮ LIỆU CỤC BỘ (Không commit Git)
│   ├── excel_cw_report.csv           ├─ Tệp báo cáo phân tích CW đầy đủ dạng CSV
│   ├── paper_portfolio.json          ├─ Số dư tiền mặt, danh mục & nhật ký paper trade
│   ├── telegram_config.json          ├─ Cấu hình Bot Telegram & Chat ID cá nhân
│   └── underlying_hv_cache.json      └─ Cache biến động lịch sử (HV) chống Rate Limit
├── src/                              🧠 THƯ MỤC CHỨA TOÀN BỘ LÕI THUẬT TOÁN
│   ├── cw_engine/                    ├─ Module Chứng Quyền (BSM, IV Solver, Paper Trader)
│   └── credit_risk/                  └─ Module Chấm điểm kiệt quệ tài chính (Altman Z, XGBoost)
├── tools/                            📂 THƯ MỤC CÔNG CỤ PHỤ TRỢ & TIỆN ÍCH
│   ├── detect_chat_id.py             ├─ Tiện ích dò Chat ID Telegram
│   ├── setup_api.py                  ├─ Tiện ích thiết lập API và Tokens
│   ├── read_pdf.py                   ├─ Tiện ích trích xuất nội dung từ PDF
│   └── inspect_images.py             └─ Tiện ích phân tích metadata hình ảnh slide
├── run_cw.py                         🚀 [1] Phân tích định giá CW & cảnh báo Telegram
├── run_cw_history.py                 📈 [2] Phân tích lịch sử Volatility IV vs HV
├── run_paper_trader.py               🏆 [3] Trình quản lý tài khoản & quét lệnh giả lập
├── run_credit_risk.py                🔍 [4] Pipeline quét kiệt quệ tài chính 1,447 doanh nghiệp
├── ROADMAP.md                        🎯 BẢN ĐỒ PHÁT TRIỂN & GAP ANALYSIS (Finvista PDF)
├── QUICK_START.md                    ⚡ HƯỚNG DẪN KHỞI CHẠY NHANH CÁC LỆNH
├── README.md                         📖 HƯỚNG DẪN SỬ DỤNG
├── requirements.txt                  ⚙️ Danh sách thư viện phụ thuộc cực nhẹ
└── LICENSE                           ⚙️ Giấy phép phần mềm MIT
```

---

## ⚡ Hướng Dẫn Sử Dụng Nhanh

### 1. Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```

---

### 2. Định Giá Chứng Quyền & Cảnh Báo Telegram (`run_cw.py`)
Nạp dữ liệu thời gian thực từ VCI API, tính toán Greeks lý thuyết và xếp hạng điểm đầu tư theo khẩu vị của bạn:

*   **Chế độ Cân Bằng (Mặc định):**
    ```bash
    python run_cw.py --strategy balanced
    ```
*   **Chế độ An Toàn (Tránh xa các mã sắp đáo hạn, ưu tiên tính thanh khoản):**
    ```bash
    python run_cw.py --strategy safe
    ```
*   **Chế độ Đầu Cơ (Ưu tiên đòn bẩy cao, tối đa hóa tỷ suất sinh lời):**
    ```bash
    python run_cw.py --strategy aggressive
    ```
*   **Xem bảng phân tích so sánh gom nhóm (Ví dụ gom nhóm theo Cổ phiếu cơ sở):**
    ```bash
    python run_cw.py --group-by cpcs --all
    ```
*   **Mô phỏng ma trận Lãi/Lỗ 2 chiều (P/L Scenario Matrix):**
    ```bash
    python run_cw.py --simulate CACB2510
    ```

---

### 3. Nghiên Cứu Lịch Sử Biến Động IV vs HV (`run_cw_history.py`)
Dò quét dữ liệu lịch sử từ vnstock để phân tích đường cong biến động (Volatility Smile) và gán nhãn định giá ĐẮT/RẺ:
```bash
python run_cw_history.py --symbol CACB2510 --days 10
```
*Hệ thống tự động giải ngược IV lịch sử Session-by-Session, đối chiếu HV rolling 40 phiên, in biểu đồ xu hướng dạng ký tự ASCII tuyệt đẹp và xuất báo cáo CSV ra thư mục dữ liệu.*

---

### 4. Giả Lập Giao Dịch Thực Chiến HOSE (`run_paper_trader.py`)
Mô phỏng tài khoản vốn 100 Triệu VND thực tế, tự động hóa toàn bộ quy trình khớp lệnh và kiểm soát rủi ro:

*   **Xem bảng điều khiển tài sản & trạng thái vị thế (Dashboard):**
    ```bash
    python run_paper_trader.py --portfolio
    ```
*   **Quét tín hiệu thị trường và thực hiện lệnh tức thời (Mon-Fri trong giờ giao dịch):**
    ```bash
    python run_paper_trader.py --scan
    ```
*   **Ép quét giao dịch ngoài giờ (Sử dụng giá khớp cuối ngày gần nhất):**
    ```bash
    python run_paper_trader.py --scan --force
    ```
*   **Khởi chạy Bot giao dịch tự động liên tục (Cứ mỗi 5 phút quét giá live, cắt lỗ/chốt lời và đặt lệnh):**
    ```bash
    python run_paper_trader.py --scan --loop 300
    ```
*   **Reset tài khoản demo về 100 Triệu VND ban đầu:**
    ```bash
    python run_paper_trader.py --reset
    ```

---

### 5. Pipeline Cảnh Báo Phá Sản Doanh nghiệp Cơ Sở (`run_credit_risk.py`)
Bảo vệ danh mục đầu tư bằng cách cào dữ liệu BCTC và dự báo điểm tín dụng của toàn thị trường:

*   **Chạy Pipeline cào dữ liệu BCTC & tự động gán nhãn rủi ro:**
    ```bash
    python run_credit_risk.py
    ```
*   **Huấn luyện mô hình Machine Learning XGBoost Classifier:**
    ```bash
    python run_credit_risk.py --train
    ```

---

## 🧠 Sơ Đồ Quy Trình Phân Tích 5 Bước

```
  📥 BƯỚC 1: LẤY DỮ LIỆU
     Live Ingest từ VCI API: Strike, Ratio, Maturity, Last Bid/Ask, Underlying Price.
        │
        ▼
  📈 BƯỚC 2: GIẢI NGƯỢC IV
     Dùng thuật toán Newton-Raphson dò tìm Implied Volatility từ giá thị trường.
        │
        ▼
  📊 BƯỚC 3: TÍNH TOÁN GREEKS
     Tính Delta (đã chia tỷ lệ), Gamma, Theta (suy hao/ngày) và Vega nhạy cảm.
        │
        ▼
  🎯 BƯỚC 4: CHẤM ĐIỂM CHIẾN THUẬT
     Tích hợp Điểm Sức khỏe Doanh nghiệp FA (XGBoost Classifier) và xếp hạng theo Profile đầu tư.
        │
        ▼
  🏆 BƯỚC 5: RA QUYẾT ĐỊNH
     Lọc bỏ rủi ro đáo hạn ngắn (<15 ngày) -> Ra khuyến nghị STRONG BUY / BUY / SKIP.
```

---

## 🎯 Bản Đồ Phát Triển (ROADMAP)
Hãy xem chi tiết tệp [ROADMAP.md](ROADMAP.md) ở thư mục gốc để nắm được:
*   **Gap Analysis:** Đánh giá chi tiết sự tương thích giữa Hồ sơ nghiên cứu khả thi dự án **Finvista (PDF)** và mã nguồn thực tế.
*   **Định hướng tương lai:** Lộ trình 4 giai đoạn phát triển lên Web App thời gian thực, tích hợp chuông cảnh báo Telegram/Zalo, và cào đường cong lãi suất Kho bạc Nhà nước thực tế.
