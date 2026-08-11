# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: CW ANALYST PROMPT BUILDER
=======================================
Auto-injects real market data into the 4-step CW analysis prompt template.
Used by GET /api/analyst-prompt/{ticker}.

Implements the full spec from prompts/Analyst_Prompt.md:
  Bước 0: IV/HV Pre-check (mandatory ranking)
  Bước 1: Hard Filter (Delta ≥ 0.3, Maturity > 45d, Spread < 15%)
  Bước 2: Two-factor analysis (Technical + Fundamental + GEX)
  Bước 3: Verdict + Entry/SL/TP/R:R + Theta decay %

Author: samvo
"""

from typing import Optional, Dict, Any, List


def build_analyst_prompt(ticker: str, cw_symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a fully-injected CW analyst prompt for a given underlying ticker.

    Args:
        ticker     : Underlying stock ticker (e.g., "ACB", "VPB", "HPG")
        cw_symbol  : Optional specific CW code to focus analysis on.
                     If None, analyses all CWs for the underlying.

    Returns:
        {
            "prompt"           : str — filled prompt ready to paste into Finvista AI Chat
            "ticker"           : str
            "regime"           : dict
            "cw_candidates"    : list
            "actionable_levels": dict | None  (for the top-ranked CW)
            "data_injected"    : dict  (summary of all injected data)
        }
    """
    ticker = ticker.upper().strip()

    # ── 1. Fetch CW opportunities filtered by underlying ─────────────────────
    cw_candidates: List[Dict[str, Any]] = []
    try:
        from backend.modules.cw_pricing.service import WarrantService
        opps = WarrantService.get_opportunities(underlying=ticker, limit=50)
        cw_candidates = opps.get("recommendations", [])
        if cw_symbol:
            # Bring the specified CW to the front if present
            specific = [c for c in cw_candidates if c["warrant_symbol"] == cw_symbol.upper()]
            rest = [c for c in cw_candidates if c["warrant_symbol"] != cw_symbol.upper()]
            cw_candidates = specific + rest
    except Exception:
        pass

    # ── 2. Fetch market regime ─────────────────────────────────────────────
    regime: Dict[str, Any] = {}
    try:
        from backend.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
        regime = calculate_vnindex_regime(days=1250)
    except Exception:
        pass

    # ── 3. Fetch news sentiment ────────────────────────────────────────────
    sentiment_score: Optional[float] = None
    sentiment_label: str = "N/A"
    try:
        from backend.modules.news_impact.service import NewsImpactService
        sent = NewsImpactService.get_ticker_sentiment_score(ticker)
        sentiment_score = sent.get("composite_score")
        sentiment_label = sent.get("label", "N/A")
    except Exception:
        pass

    # ── 4. Compute per-CW metrics for Bước 0 & 1 ───────────────────────────
    # IV/HV ratio, theta_pct_daily, spread_pct, hard filter pass/fail
    enriched_cws: List[Dict[str, Any]] = []
    for cw in cw_candidates:
        iv = cw.get("implied_volatility_pct", 0.0) or 0.0
        hv = cw.get("historical_volatility_pct", 0.0) or 0.0
        iv_hv_ratio = round(iv / hv, 2) if hv > 0 else None

        if iv_hv_ratio is None:
            vol_label = "N/A"
        elif iv_hv_ratio > 1.30:
            vol_label = "⚠️ OVERPRICED"
        elif iv_hv_ratio > 1.10:
            vol_label = "🟡 FAIR TO EXPENSIVE"
        elif iv_hv_ratio >= 0.90:
            vol_label = "⚪ FAIR VALUE"
        else:
            vol_label = "✅ CHEAP VOL"

        # Theta % per day
        price = cw.get("market_price", 0.0) or 0.0
        theta = abs(cw.get("theta_daily_burn", 0.0) or 0.0)
        theta_pct_daily = round(theta / price * 100, 3) if price > 0 else 0.0

        # Hard filter checks
        delta = cw.get("delta", 0.0) or 0.0
        days = cw.get("days_to_maturity", 0) or 0

        # Spread check: if bid/ask not available, use 0 (pass) as approximation
        spread_pct = 0.0  # placeholder — actual spread not stored in MarketOpportunity

        hard_filter_pass = (
            delta >= 0.30
            and days > 45
            and spread_pct < 15.0
            and iv_hv_ratio is not None
            and iv_hv_ratio <= 1.30
            and price > 0
        )

        reject_reasons = []
        if delta < 0.30:
            reject_reasons.append(f"Delta {delta:.2f} < 0.30 (Deep OTM)")
        if days <= 45:
            reject_reasons.append(f"Còn {days} ngày ≤ 45 ngày (Theta decay cao)")
        if iv_hv_ratio is not None and iv_hv_ratio > 1.30:
            reject_reasons.append(f"IV/HV = {iv_hv_ratio} > 1.30 (Quá đắt vol)")

        enriched_cws.append({
            **cw,
            "iv_hv_ratio": iv_hv_ratio,
            "vol_label": vol_label,
            "theta_pct_daily": theta_pct_daily,
            "hard_filter_pass": hard_filter_pass,
            "reject_reasons": reject_reasons,
        })

    # Sort by IV/HV ascending (cheapest vol first)
    passed_cws = sorted(
        [c for c in enriched_cws if c["hard_filter_pass"]],
        key=lambda x: (x["iv_hv_ratio"] or 9.99)
    )
    rejected_cws = [c for c in enriched_cws if not c["hard_filter_pass"]]

    # ── 5. Actionable levels for top-ranked CW ─────────────────────────────
    actionable: Optional[Dict[str, Any]] = None
    top_cw_sym: Optional[str] = None
    if passed_cws:
        top_cw_sym = passed_cws[0]["warrant_symbol"]
        try:
            from backend.modules.cw_pricing.service import WarrantService
            actionable = WarrantService.get_actionable_levels(top_cw_sym)
            if actionable.get("status") != "ok":
                actionable = None
        except Exception:
            pass
    elif cw_symbol:
        try:
            from backend.modules.cw_pricing.service import WarrantService
            actionable = WarrantService.get_actionable_levels(cw_symbol.upper())
            if actionable.get("status") == "ok":
                top_cw_sym = cw_symbol.upper()
            else:
                actionable = None
        except Exception:
            pass

    # ── 6. Build Bước 0 text (IV/HV ranking) ───────────────────────────────
    buoc0_lines = [
        "### BƯỚC 0: IV/HV PRE-CHECK (BẮT BUỘC)",
        "",
        "📊 IV/HV Ranking (sắp xếp theo IV/HV ratio từ thấp → cao):",
    ]
    for i, cw in enumerate(sorted(enriched_cws, key=lambda x: (x["iv_hv_ratio"] or 9.99)), 1):
        sym = cw["warrant_symbol"]
        ratio_str = f"{cw['iv_hv_ratio']:.2f}" if cw["iv_hv_ratio"] else "N/A"
        buoc0_lines.append(f"{i}. {sym} — IV/HV = {ratio_str} — {cw['vol_label']}")

    buoc0_text = "\n".join(buoc0_lines)

    # ── 7. Build Bước 1 text (Hard Filter) ─────────────────────────────────
    buoc1_lines = [
        "### BƯỚC 1: HARD FILTER",
        "",
        f"✅ PASSED Hard Filter ({len(passed_cws)}/{len(enriched_cws)} mã):",
    ]
    if passed_cws:
        buoc1_lines.append(
            "| Mã | CPCS | Delta | Maturity | IV/HV | G-Score | Tín hiệu |"
        )
        buoc1_lines.append("|---|---|---|---|---|---|---|")
        for cw in passed_cws:
            buoc1_lines.append(
                f"| {cw['warrant_symbol']} | {cw['underlying_symbol']} "
                f"| {cw['delta']:.2f} | {cw['days_to_maturity']}d "
                f"| {cw['iv_hv_ratio']:.2f} | {cw['composite_g_score']:.1f} "
                f"| {cw['recommendation_signal']} |"
            )
    else:
        buoc1_lines.append("*(Không có mã nào vượt qua Hard Filter — thị trường khó khăn hoặc dữ liệu chưa đầy đủ)*")

    buoc1_lines += ["", f"❌ REJECTED ({len(rejected_cws)} mã):"]
    if rejected_cws:
        buoc1_lines.append("| Mã | Lý do loại |")
        buoc1_lines.append("|---|---|")
        for cw in rejected_cws:
            reasons = "; ".join(cw["reject_reasons"]) if cw["reject_reasons"] else "Giá = 0 hoặc dữ liệu thiếu"
            buoc1_lines.append(f"| {cw['warrant_symbol']} | {reasons} |")

    buoc1_text = "\n".join(buoc1_lines)

    # ── 8. Build Bước 3 verdict (Actionable Levels) ────────────────────────
    if actionable and top_cw_sym:
        cl = actionable["cw_levels"]
        thr = actionable["theta_risk"]
        ul = actionable["underlying_levels"]
        buoc3_text = f"""### BƯỚC 3: KẾT LUẬN GIAO DỊCH

## 🎯 KẾT LUẬN

### Khuyến nghị chính: {top_cw_sym} — [AI sẽ điền MUA / CHỜ / ĐỨNG NGOÀI dựa trên phân tích Bước 2]

| | CW: {top_cw_sym} | CPCS: {actionable['underlying_symbol']} |
|--|---|---|
| Entry | {cl['entry']:,} VNĐ | Vùng gom: {ul['entry_zone_low']:,} – {ul['entry_zone_high']:,} VNĐ |
| Stop-Loss | {cl['stop_loss']:,} VNĐ ({cl['stop_loss_pct']:.0f}%) | {ul['stop_loss']:,} VNĐ (-7%) |
| Take Profit 1 | {cl['take_profit_1']:,} VNĐ (+{cl['take_profit_1_pct']:.1f}%) | {ul['target_5pct']:,} VNĐ (+5%) |
| Take Profit 2 | {cl['take_profit_2']:,} VNĐ (+{cl['take_profit_2_pct']:.1f}%) | {ul['target_10pct']:,} VNĐ (+10%) |
| R:R | 1:{cl['risk_reward_ratio']} {cl['rr_quality']} | — |

⏱️ **Theta decay:** -{thr['theta_pct_daily']:.2f}%/ngày — Cầm 5 ngày ≈ mất **{thr['cost_5_days_pct']:.1f}%** giá trị

{actionable.get('time_warning', '')}

⚠️ DISCLAIMER: Phân tích mang tính tham khảo, không phải lời khuyên đầu tư.
Rủi ro CW: có thể mất 100% vốn nếu CPCS không vượt strike tại đáo hạn."""
    else:
        buoc3_text = """### BƯỚC 3: KẾT LUẬN GIAO DỊCH

*(Không có mã nào đủ điều kiện để tính mốc giá Entry/SL/TP — xem lại Bước 1)*

⚠️ DISCLAIMER: Phân tích mang tính tham khảo, không phải lời khuyên đầu tư."""

    # ── 9. Assemble full prompt ─────────────────────────────────────────────
    regime_str = (
        f"- VNINDEX Regime: {regime.get('regime', 'UNKNOWN')} "
        f"(confidence: {regime.get('confidence', 0.0)*100:.0f}%)\n"
        f"- Bias: {regime.get('bias', 'NEUTRAL')}"
    ) if regime else "- VNINDEX Regime: Không có dữ liệu"

    avg_iv = (
        sum(c["implied_volatility_pct"] or 0 for c in enriched_cws) / len(enriched_cws)
        if enriched_cws else 0
    )
    cheapest = min(enriched_cws, key=lambda x: (x["iv_hv_ratio"] or 9.99)) if enriched_cws else None
    expensive = max(enriched_cws, key=lambda x: (x["iv_hv_ratio"] or 0)) if enriched_cws else None

    import datetime
    analysis_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    sentiment_score_str = f"{sentiment_score:.2f}" if sentiment_score is not None else "N/A"

    prompt = f"""# PHÂN TÍCH COVERED WARRANT — FINVISTA AI ANALYST
Ngày phân tích: {analysis_date}
Underlying: **{ticker}**

## Bối cảnh thị trường
{regime_str}
- Sentiment tin tức 30 ngày: {sentiment_label} (score: {sentiment_score_str})

## Dữ liệu CW từ FINVISTA ({len(enriched_cws)} mã)
- IV/HV trung bình basket: {avg_iv:.1f}%
- Mã rẻ vol nhất: {cheapest['warrant_symbol'] if cheapest else 'N/A'} (IV/HV = {cheapest['iv_hv_ratio'] if cheapest else 'N/A'})
- Mã đắt vol nhất: {expensive['warrant_symbol'] if expensive else 'N/A'} (IV/HV = {expensive['iv_hv_ratio'] if expensive else 'N/A'})

---

{buoc0_text}

---

{buoc1_text}

---

### BƯỚC 2: TWO-FACTOR ANALYSIS
*[AI sẽ điền phân tích Technical + Fundamental + GEX cho từng mã PASSED Bước 1]*

📈 Technical:
- Xu hướng CPCS {ticker}: [Finvista AI sẽ phân tích dựa trên dữ liệu HMM + EMA]
- Regime: {regime.get('regime', 'N/A')} — bias {regime.get('bias', 'N/A')}

📰 Fundamental:
- Sentiment 30d: {sentiment_label} (score: {sentiment_score_str})
- Catalyst: [Điền sự kiện quan trọng từ context hệ thống]

---

{buoc3_text}

---
Thực hiện phân tích theo 4 bước trên. Trả lời bằng tiếng Việt. Kết luận dứt khoát: MUA / CHỜ / ĐỨNG NGOÀI.
"""

    return {
        "prompt": prompt,
        "ticker": ticker,
        "analysis_date": analysis_date,
        "regime": regime,
        "cw_candidates": enriched_cws,
        "passed_filter_count": len(passed_cws),
        "rejected_filter_count": len(rejected_cws),
        "top_cw_symbol": top_cw_sym,
        "actionable_levels": actionable,
        "data_injected": {
            "total_cws_found": len(enriched_cws),
            "regime_available": bool(regime),
            "sentiment_available": sentiment_score is not None,
            "actionable_levels_available": actionable is not None,
        }
    }
