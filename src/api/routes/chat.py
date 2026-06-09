# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI CHAT ENDPOINT
==============================
AI-powered financial chat assistant using Gemini integration.

Author: samvo
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import os

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict] = None


@router.post("/", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    AI-powered financial chat assistant.
    
    Supports:
    - General financial questions
    - Covered Warrant analysis
    - Credit risk explanations
    - Trading strategy discussions
    """
    try:
        from src.common.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        # Convert Pydantic models to dicts
        messages_dict = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        response = ai_client.chat(
            messages=messages_dict,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not response:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty response"
            )
        
        return ChatResponse(
            response=response,
            model=request.model or ai_client.default_model
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat completion failed: {str(e)}"
        )


@router.post("/financial-commentary")
async def generate_financial_commentary(
    ticker: str,
    current_ratio: float,
    debt_ratio: float,
    altman_z_score: float,
    profit_after_tax: float = 0.0,
    operating_cash_flow: float = 0.0,
    ebit_to_interest: float = 9999.0
):
    """
    Generate AI-powered financial commentary for distressed companies.
    
    This endpoint provides the same functionality used in Telegram alerts
    but accessible via REST API.
    """
    try:
        from src.common.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        commentary = ai_client.generate_financial_commentary(
            ticker=ticker,
            current_ratio=current_ratio,
            debt_ratio=debt_ratio,
            altman_z_score=altman_z_score,
            profit_after_tax=profit_after_tax,
            operating_cash_flow=operating_cash_flow,
            ebit_to_interest=ebit_to_interest
        )
        
        if not commentary:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty commentary"
            )
        
        return {
            "ticker": ticker,
            "commentary": commentary,
            "model": ai_client.default_model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Financial commentary generation failed: {str(e)}"
        )


@router.post("/trading-signal-commentary")
async def generate_trading_signal_commentary(
    cw_code: str,
    signal: str,
    g_score: float,
    price: float,
    leverage: float,
    days_to_expiry: int,
    price_change_pct: float
):
    """
    Generate AI-powered commentary for CW trading signals.
    
    This endpoint provides AI analysis for trading signals
    used in the quantitative trading system.
    """
    try:
        from src.common.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        commentary = ai_client.generate_trading_signal_commentary(
            cw_code=cw_code,
            signal=signal,
            g_score=g_score,
            price=price,
            leverage=leverage,
            days_to_expiry=days_to_expiry,
            price_change_pct=price_change_pct
        )
        
        if not commentary:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty commentary"
            )
        
        return {
            "cw_code": cw_code,
            "signal": signal,
            "commentary": commentary,
            "model": ai_client.default_model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Trading signal commentary generation failed: {str(e)}"
        )
