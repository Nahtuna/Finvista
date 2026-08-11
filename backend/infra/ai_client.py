# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI CLIENT UTILITY
================================
Unified AI client for Gemini integration using gemini-web2api.
Supports both free web API and official Google AI API.
Supports Vision multipart (text + image) via OpenRouter / OpenAI API.

Author: samvo
"""

import base64
import os
import subprocess
import socket
import time
import sys
import hashlib
from typing import Optional, List, Dict, Any, Union
from openai import OpenAI
from dotenv import load_dotenv
from backend.core.utils import initialize_console_setup

# Initialize console setup (UTF-8 encoding and proxy sanitization)
initialize_console_setup()

load_dotenv()

class AIClient:
    """Unified AI client for Gemini integration with Vision support."""
    
    # Module-specific port mapping for separate proxy instances
    MODULE_PORTS = {
        "chat": int(os.getenv("AI_PROXY_CHAT_PORT", "8081")),           # Chat Assistant (người dùng)
        "news_impact": int(os.getenv("AI_PROXY_NEWS_IMPACT_PORT", "8082")),    # News Impact Analysis
        "annual_reports": int(os.getenv("AI_PROXY_ANNUAL_REPORTS_PORT", "8083")),  # Annual Reports Analysis
        "ai_committee": int(os.getenv("AI_PROXY_AI_COMMITTEE_PORT", "8084")),   # AI Committee Trading
        "credit_risk": int(os.getenv("AI_PROXY_CREDIT_RISK_PORT", "8085")),    # Credit Risk Analysis
        "market_overview": int(os.getenv("AI_PROXY_MARKET_OVERVIEW_PORT", "8086")), # Market Overview
        "default": int(os.getenv("AI_PROXY_CHAT_PORT", "8081"))        # Fallback
    }
    
    def __init__(self, module_name: str = "default", auto_start_proxy: bool = True):
        self.module_name = module_name
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Caching configuration
        self.cache = {}
        self.cache_ttl = int(os.getenv("AI_CACHE_TTL", "3600"))  # Default 1 hour TTL
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_cache_size = int(os.getenv("AI_CACHE_MAX_SIZE", "1000"))  # Max 1000 cached responses
        
        # Prioritize OpenRouter if API key is present and configured
        if self.openrouter_api_key and not self.openrouter_api_key.startswith("YOUR_") and "sk-or-v1" in self.openrouter_api_key:
            self.use_web_api = False
            self.base_url = "https://openrouter.ai/api/v1"
            self.default_model = "google/gemini-2.5-flash"
            self.vision_model = "google/gemini-2.5-flash"   # hỗ trợ vision
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.openrouter_api_key
            )
            print(f"AIClient [{module_name}]: Connected via OpenRouter API Gateway (Vision enabled).")
        else:
            self.use_web_api = True
            self.ai_host = "localhost"
            # Get module-specific port
            self.port = self.MODULE_PORTS.get(module_name, self.MODULE_PORTS["default"])
            self.base_url = f"http://localhost:{self.port}/v1"
            self.default_model = "gemini-3.5-flash"
            self.vision_model = "gemini-3.5-flash"
            if auto_start_proxy:
                self._ensure_proxy_running()
            self.client = OpenAI(
                base_url=self.base_url,
                api_key="sk-web-api"
            )
            print(f"AIClient [{module_name}]: Connected via local Web-to-API Proxy (port {self.port}).")
    
    def _is_port_open(self, port: int, host: Optional[str] = None) -> bool:
        """Check if a local port is already open."""
        target_host = host or "localhost"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            return s.connect_ex((target_host, port)) == 0

    def _ensure_proxy_running(self):
        """Automatically starts the gemini_web2api proxy if not running."""
        if self._is_port_open(self.port, "localhost"):
            return # Already running
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        proxy_script = os.path.join(base_dir, "scripts", "maintenance", "gemini_web2api.py")
        if not os.path.exists(proxy_script):
            print(f"Warning: AI Proxy script not found at {proxy_script}")
            return

        print(f"Starting Gemini AI Proxy on port {self.port} for module {self.module_name}...")
        try:
            subprocess.Popen(
                [sys.executable, proxy_script, "--port", str(self.port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            time.sleep(2)
            if self._is_port_open(self.port, "localhost"):
                print(f"Gemini AI Proxy started successfully on port {self.port}.")
            else:
                print(f"Warning: Gemini AI Proxy is taking longer than expected to start on port {self.port}.")
        except Exception as e:
            print(f"Error: Failed to start AI Proxy on port {self.port}: {e}")
    
    def _get_cache_key(self, messages: List[Dict[str, Any]], model: str = None) -> str:
        """Generate cache key from messages and model."""
        content = str(messages[-1]["content"]) if messages else ""
        model_key = model or self.default_model
        cache_input = f"{self.module_name}:{model_key}:{content}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get response from cache if valid."""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # Check TTL
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                self.cache_hits += 1
                return cached_data["response"]
            else:
                # Expired, remove from cache
                del self.cache[cache_key]
        self.cache_misses += 1
        return None
    
    def _set_cache(self, cache_key: str, response: str):
        """Cache response with timestamp."""
        # Evict old entries if cache is full (simple LRU)
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry (first added)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size
        }
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        image_base64: Optional[str] = None,
        image_media_type: str = "image/png",
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """
        Send a chat request. Optionally attach an image for Vision analysis.
        
        Args:
            messages: Conversation history (role/content dicts)
            image_base64: Base64-encoded image string (no data URI prefix)
            image_media_type: MIME type of the image (default: image/png)
            use_cache: Whether to use caching (default: True)
        """
        try:
            max_tokens = kwargs.get("max_tokens") or 2048
            model = kwargs.get("model") or self.default_model
            
            # Generate cache key (only for text requests, not vision)
            cache_key = None
            if use_cache and not image_base64:
                cache_key = self._get_cache_key(messages, model)
                cached_response = self._get_from_cache(cache_key)
                if cached_response:
                    return cached_response
            
            # If image is provided, convert the last user message to multipart Vision format
            if image_base64:
                processed_messages = []
                for i, msg in enumerate(messages):
                    if msg["role"] == "user" and i == len(messages) - 1:
                        # Build multipart content block
                        text_content = msg.get("content", "")
                        content_parts: List[Dict[str, Any]] = [
                            {"type": "text", "text": text_content}
                        ]
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_media_type};base64,{image_base64}"
                            }
                        })
                        processed_messages.append({"role": "user", "content": content_parts})
                    else:
                        processed_messages.append(msg)
                model = kwargs.get("model") or self.vision_model
            else:
                processed_messages = messages
            
            response = self.client.chat.completions.create(
                model=model,
                messages=processed_messages,
                max_tokens=max_tokens,
                timeout=60.0
            )
            response_content = response.choices[0].message.content
            
            # Cache the response if caching is enabled and not a vision request
            if use_cache and cache_key and not image_base64:
                self._set_cache(cache_key, response_content)
            
            return response_content
        except Exception as e:
            error_msg = str(e)
            try:
                if "Connection error" in error_msg or "ConnectError" in error_msg:
                    print("⚠️ [AI Client] Connection Error: Unable to reach AI proxy/gateway.")
                elif "429" in error_msg or "Too Many Requests" in error_msg:
                    # Print once or concisely to avoid log spamming
                    if not hasattr(self, "_last_429_time") or time.time() - self._last_429_time > 60:
                        self._last_429_time = time.time()
                        print("⚠️ [AI Client] Rate limit exceeded (429). Falling back to rule-based sentiment.")
                else:
                    print(f"AI Client Error: {error_msg}")
            except Exception:
                pass
            return ""
    
    def _generate_rule_based_financial_commentary(self, ticker: str, **kwargs) -> str:
        z_score = kwargs.get("altman_z_score", 0.0)
        curr_ratio = kwargs.get("current_ratio", 1.0)
        debt_ratio = kwargs.get("debt_ratio", 0.0)
        pat = kwargs.get("profit_after_tax", 0.0)
        ocf = kwargs.get("operating_cash_flow", 0.0)
        
        # Format values to billion VND
        pat_bn = pat / 1e9
        ocf_bn = ocf / 1e9
        
        if z_score < 1.1:
            status = "nằm trong Vùng Nguy Hiểm (Danger Zone) với rủi ro kiệt quệ tài chính cao"
        elif z_score <= 2.6:
            status = "nằm trong Vùng Cảnh Báo (Grey Zone) với sức khỏe tài chính ở mức trung bình"
        else:
            status = "nằm trong Vùng An Toàn (Green Zone) với nền tảng tài chính lành mạnh"
            
        comment = f"Doanh nghiệp {ticker} hiện {status} (Altman Z-Score đạt {z_score:.2f}). "
        
        if debt_ratio > 0.6:
            comment += f"Tỷ lệ nợ ở mức tương đối cao ({debt_ratio*100:.1f}%), có thể gây áp lực lên chi phí lãi vay. "
        else:
            comment += f"Cơ cấu nguồn vốn khá an toàn với tỷ lệ nợ duy trì ở mức {debt_ratio*100:.1f}%. "
            
        if curr_ratio < 1.0:
            comment += f"Khả năng thanh toán ngắn hạn gặp áp lực lớn khi Current Ratio chỉ đạt {curr_ratio:.2f}. "
        else:
            comment += f"Khả năng thanh toán ngắn hạn được đảm bảo với hệ số thanh toán hiện thời đạt {curr_ratio:.2f}. "
            
        if pat_bn < 0:
            comment += f"Hoạt động kinh doanh gặp thách thức khi ghi nhận lỗ ròng {abs(pat_bn):.1f} tỷ VND trong kỳ."
        else:
            comment += f"Hoạt động kinh doanh ghi nhận mức lãi sau thuế {pat_bn:.1f} tỷ VND cùng dòng tiền HĐKD đạt {ocf_bn:.1f} tỷ VND."
            
        return comment

    def generate_financial_commentary(self, ticker: str, **kwargs) -> str:
        if self.use_web_api:
            return self._generate_rule_based_financial_commentary(ticker, **kwargs)
            
        z_score = kwargs.get("altman_z_score", 0.0)
        curr_ratio = kwargs.get("current_ratio", 1.0)
        debt_ratio = kwargs.get("debt_ratio", 0.0)
        pat = kwargs.get("profit_after_tax", 0.0)
        ocf = kwargs.get("operating_cash_flow", 0.0)
        ebit_to_int = kwargs.get("ebit_to_interest", 9999.0)
        
        prompt = (
            f"Phân tích ngắn gọn sức khỏe tài chính cho mã {ticker}.\n"
            f"- Altman Z-Score: {z_score:.2f}\n"
            f"- Tỷ lệ thanh toán hiện thời (Current Ratio): {curr_ratio:.2f}\n"
            f"- Tỷ lệ nợ (Debt Ratio): {debt_ratio:.2f}\n"
            f"- Lợi nhuận sau thuế: {pat/1e9:.2f} tỷ VND\n"
            f"- Dòng tiền HĐKD: {ocf/1e9:.2f} tỷ VND\n"
            f"- Khả năng trả lãi (ICR): {ebit_to_int:.2f}\n"
            f"Hãy viết nhận xét tài chính ngắn gọn khoảng 3-4 câu bằng tiếng Việt."
        )
        response = self.chat([{"role": "user", "content": prompt}], model="google/gemini-2.5-flash")
        if not response:
            return self._generate_rule_based_financial_commentary(ticker, **kwargs)
        return response
    
    def generate_trading_signal_commentary(self, cw_code: str, signal: str, **kwargs) -> str:
        return f"Tín hiệu {signal} cho {cw_code}. Cần theo dõi thêm."

    def analyze_chart_vision(self, image_base64: str, question: str = "Phân tích biểu đồ này.") -> str:
        """
        Analyze a chart image using Gemini Vision.
        
        Args:
            image_base64: Base64 encoded image (without data URI prefix)
            question: Analysis question to ask about the chart
        """
        messages = [{"role": "user", "content": question}]
        return self.chat(messages, image_base64=image_base64)

_ai_clients: Dict[str, Optional[AIClient]] = {}

def get_ai_client(module_name: str = "default", auto_start_proxy: bool = True) -> AIClient:
    """Get or create AI client for a specific module."""
    if module_name not in _ai_clients or _ai_clients[module_name] is None:
        _ai_clients[module_name] = AIClient(module_name=module_name, auto_start_proxy=auto_start_proxy)
    return _ai_clients[module_name]
