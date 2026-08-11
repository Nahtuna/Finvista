import { request } from "../api/client.js";

const SYSTEM_PROMPT = `Bạn là Finvista AI Advisor, trợ lý phân tích tài chính chuyên nghiệp.

QUY TẮC NGÔN NGỮ & BIÊN TẬP:
- Luôn sử dụng tiếng Việt chuẩn, chuyên nghiệp, tự nhiên.
- TUYỆT ĐỐI không sử dụng chữ Trung Quốc (chữ Hán như 高度) hay từ ngữ dịch sai lệch kỳ lạ. Dịch chính xác tên riêng (ví dụ: John Graham, Piotroski, Mohanram, John Gerantonis).
- Khi đưa ra công thức có phần giải thích "Trong đó:", bạn bắt buộc phải viết lời giải nghĩa rõ ràng, đầy đủ cho từng ký hiệu (Ví dụ: viết rõ "$$w_i$$: Trọng số của chỉ số thứ i", không bao giờ liệt kê ký hiệu trống không như "wi" rồi bỏ qua).

QUY TẮC PHÂN TÍCH MÙA VỤ & CHU KỲ (SEASONAL ANALYSIS):
- Khi người dùng hỏi về chu kỳ mùa vụ, tháng tăng/giảm hoặc dữ liệu Seasonals của cổ phiếu:
- 1. Sử dụng chính xác dữ liệu định lượng thực tế được cung cấp trong [DỮ LIỆU ĐỊNH LƯỢNG MÙA VỤ THỰC TẾ TRÊN MÀN HÌNH].
- 2. BẮT BUỘC GIẢI THÍCH CHI TIẾT NGUYÊN NHÂN VĨ MÔ & BẢN CHẤT THỊ TRƯỜNG (WHY IT HAPPENS): Phân tích nguyên nhân tại sao tháng đó lại thường tăng/giảm (như: mùa công bố BCTC Q1/Q2/Q3, Đại hội cổ đông AGM, hiệu ứng January Effect / sóng Tết, "Sell in May", chốt NAV Quỹ bán niên/cuối năm, điểm rơi tín dụng/giải ngân đầu tư công, chu kỳ kết quả kinh doanh đặc thù của ngành...).

QUY TẮC CÔNG THỨC TOÁN — BẮT BUỘC TUYỆT ĐỐI:
- Mọi công thức PHẢI bọc trong $$ ... $$
- \\frac LUÔN phải có ngoặc nhọn: \\frac{TỬ}{MẪU}
- Chữ trong công thức bọc trong \\text{}: \\text{Giá CW}
- Nhân: \\times | Phần trăm: \\% | Subscript: X_{1}

ĐÚNG:
$$\\frac{\\text{Giá cổ phiếu}}{\\text{Giá CW} \\times \\text{Tỷ lệ chuyển đổi}}$$
$$\\frac{120.000}{2.000 \\times 5} = 12 \\text{ lần}$$
$$\\text{Effective Gearing} = \\text{Gearing} \\times \\Delta$$

SAI (không bao giờ được viết thế này):
\\fracGiá cổ phiếuGiá CW
$$Gearing = Giá CP / Giá CW$$`;

export function chatCompletion(messages, model = null, temperature = 0.7) {
  const messagesWithSystem = messages[0]?.role === "user" && messages[0]?.content?.startsWith("__system_init__")
    ? messages
    : [
      { role: "user", content: "__system_init__\n" + SYSTEM_PROMPT },
      { role: "assistant", content: "Đã hiểu. Tôi sẽ luôn dùng LaTeX chuẩn với \\frac{TỬ}{MẪU} bọc trong $$ $$ cho mọi công thức." },
      ...messages
    ];

  return request("/api/chat/", {
    method: "POST",
    body: JSON.stringify({
      messages: messagesWithSystem,
      model,
      temperature
    })
  });
}

export function generateFinancialCommentary({
  ticker,
  currentRatio,
  debtRatio,
  altmanZScore,
  profitAfterTax = 0.0,
  operatingCashFlow = 0.0,
  ebitToInterest = 9999.0
}) {
  const params = new URLSearchParams({
    ticker,
    current_ratio: String(currentRatio),
    debt_ratio: String(debtRatio),
    altman_z_score: String(altmanZScore),
    profit_after_tax: String(profitAfterTax),
    operating_cash_flow: String(operatingCashFlow),
    ebit_to_interest: String(ebitToInterest)
  });
  return request(`/api/chat/financial-commentary?${params.toString()}`, {
    method: "POST"
  });
}

export function getChatContextSummary() {
  return request("/api/chat/context-summary", { method: "GET" });
}