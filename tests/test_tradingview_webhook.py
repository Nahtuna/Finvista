# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_tradingview_webhook_regime():
    # 1. Send BEARISH Webhook Signal from TradingView
    payload_bear = {
        "ticker": "VNINDEX",
        "regime": "BEAR",
        "bias": "SKIP_CW",
        "source": "TradingView Creed Master Grid Audit Test"
    }
    response = client.post("/api/regime/webhook/tradingview", json=payload_bear)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["active_regime"]["regime"] == "BEARISH_HIGH_VOL"
    assert data["active_regime"]["bias"] == "SKIP_CW"

    # 2. Check /api/regime/market reflects the Webhook signal
    mkt_res = client.get("/api/regime/market")
    assert mkt_res.status_code == 200
    mkt_data = mkt_res.json()
    assert mkt_data["regime"] == "BEARISH_HIGH_VOL"
    assert mkt_data["bias"] == "SKIP_CW"
    assert mkt_data["source"] == "TradingView Creed Master Grid Audit Test"

    # 3. Send BULLISH Webhook Signal from TradingView
    payload_bull = {
        "ticker": "VNINDEX",
        "regime": "BULL",
        "bias": "LONG_CW",
        "source": "TradingView Creed Master Grid Audit Test"
    }
    response_bull = client.post("/api/regime/webhook/tradingview", json=payload_bull)
    assert response_bull.status_code == 200

    mkt_res_bull = client.get("/api/regime/market")
    assert mkt_res_bull.json()["regime"] == "BULLISH_VOL_EXPANSION"
    assert mkt_res_bull.json()["bias"] == "LONG_CW"
