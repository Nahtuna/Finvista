import pytest
from unittest.mock import patch, MagicMock
from src.modules.cw_pricing.prompts.analyst_prompt import build_analyst_prompt

def test_build_analyst_prompt():
    mock_opps = {
        "status": "ok",
        "recommendations": [
            {
                "warrant_symbol": "CHPG2301",
                "underlying_symbol": "HPG",
                "issuer": "SSI",
                "market_price": 1200.0,
                "price_change_pct": 1.5,
                "implied_volatility_pct": 45.0,
                "historical_volatility_pct": 35.0,
                "delta": 0.45,
                "theta_daily_burn": -10.0,
                "days_to_maturity": 60,
                "composite_g_score": 85.0,
                "recommendation_signal": "BUY"
            }
        ]
    }

    mock_market_regime = {"regime": "BULLISH_LOW_VOL", "confidence": 0.85, "bias": "LONG_CW"}

    # WarrantService and NewsImpactService are lazy-imported inside the function,
    # so patch at their source modules, not at analyst_prompt.
    with patch("src.modules.cw_pricing.service.WarrantService.get_opportunities", return_value=mock_opps), \
         patch("src.modules.cw_pricing.service.WarrantService.get_actionable_levels", return_value={"status": "error"}), \
         patch("src.modules.regime_analysis.indicators.hmm_regime.calculate_vnindex_regime", return_value=mock_market_regime), \
         patch("src.modules.news_impact.service.NewsImpactService.get_ticker_sentiment_score", return_value={"composite_score": 0.25, "label": "POSITIVE"}):

        res = build_analyst_prompt("HPG")
        assert "prompt" in res
        assert "data_injected" in res
        assert res["ticker"] == "HPG"
        assert len(res["cw_candidates"]) == 1
        assert res["cw_candidates"][0]["warrant_symbol"] == "CHPG2301"
        assert "CHPG2301" in res["prompt"]
