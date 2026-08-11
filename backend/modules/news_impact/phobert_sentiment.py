# -*- coding: utf-8 -*-
"""
PhoBERT-based Sentiment Analysis for News Impact
Dùng model NLP tiếng Việt chuyên nghiệp thay cho AI
"""

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PhoBERTSentimentAnalyzer:
    """Phân tích sentiment tin tức bằng PhoBERT (model NLP tiếng Việt)"""
    
    def __init__(self):
        self.model_name = "vinai/phobert-base-v2"
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()
    
    def _load_model(self):
        """Load PhoBERT model"""
        try:
            logger.info(f"Loading PhoBERT model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info("PhoBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load PhoBERT model: {e}")
            # Fallback sang rule-based nếu không load được model
            self.model = None
            self.tokenizer = None
    
    def analyze_sentiment(self, title: str, summary: str = "") -> str:
        """
        Phân tích sentiment từ tiêu đề và tóm tắt tin tức bằng PhoBERT
        
        Returns: "POSITIVE", "NEGATIVE", hoặc "NEUTRAL"
        """
        if self.model is None or self.tokenizer is None:
            # Fallback sang rule-based nếu model không available
            from backend.modules.news_impact.rule_based_sentiment import get_sentiment_analyzer
            analyzer = get_sentiment_analyzer()
            return analyzer.analyze_sentiment(title, summary)
        
        try:
            # Combine title and summary
            text = f"{title}. {summary}" if summary else title
            
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                predictions = torch.softmax(logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=-1).item()
            
            # Map class to sentiment (assumes 3 classes: NEGATIVE, NEUTRAL, POSITIVE)
            sentiment_map = {0: "NEGATIVE", 1: "NEUTRAL", 2: "POSITIVE"}
            return sentiment_map.get(predicted_class, "NEUTRAL")
            
        except Exception as e:
            logger.error(f"PhoBERT prediction failed: {e}, falling back to rule-based")
            from backend.modules.news_impact.rule_based_sentiment import get_sentiment_analyzer
            analyzer = get_sentiment_analyzer()
            return analyzer.analyze_sentiment(title, summary)
    
    def batch_analyze(self, news_items: List[Dict]) -> List[Dict]:
        """
        Phân tích sentiment batch cho nhiều tin tức
        
        Args:
            news_items: List of dicts with 'title' and 'summary' keys
            
        Returns:
            List of dicts with original data + 'sentiment' key
        """
        results = []
        for item in news_items:
            title = item.get('title', '')
            summary = item.get('summary', '')
            sentiment = self.analyze_sentiment(title, summary)
            
            result = item.copy()
            result['sentiment'] = sentiment
            results.append(result)
        
        return results

# Singleton instance
_phobert_analyzer = None

def get_phobert_analyzer() -> PhoBERTSentimentAnalyzer:
    """Get singleton PhoBERT analyzer instance"""
    global _phobert_analyzer
    if _phobert_analyzer is None:
        _phobert_analyzer = PhoBERTSentimentAnalyzer()
    return _phobert_analyzer
