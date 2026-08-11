# -*- coding: utf-8 -*-
"""
Rule-based Sentiment Analysis for News Impact
Thay thế AI để giảm phụ thuộc
Keywords from lotusmarket (70+ financial Vietnamese keywords)
"""

import re
from typing import Dict, List
import unicodedata

def remove_vietnamese_accents(text):
    """Remove Vietnamese accents for better keyword matching"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    return text

def split_into_sentences(text):
    """Split text into sentences"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

class RuleBasedSentimentAnalyzer:
    """Phân tích sentiment tin tức bằng rule-based keywords (lotusmarket-based)"""
    
    def __init__(self):
        # Keywords tích cực với weight (từ lotusmarket + financial domain)
        self.positive_keywords = {
            # High weight keywords (strong positive) - từ lotusmarket
            r'tang truong': 2.0, r'tang manh': 2.0, r'tang vot': 2.5, r'bung no': 2.5,
            r'dot pha': 2.0, r'ky luc': 2.0, r'but pha': 2.5, r'phuc hoi': 1.5,
            r'hoi phuc': 1.5, r'khoi sac': 2.0, r'lac quan': 2.0, r'tich cuc': 2.0,
            r'thuon loi': 1.5, r'trien vong': 1.5, r'co hoi': 1.5, r'thang hoa': 2.5,
            r'lai': 1.5, r'lai lon': 2.0, r'loi nhuan': 2.0, r'co tuc': 1.5,
            r'chia co tuc': 2.0, r'vuot ky vong': 2.0, r'mua rong': 1.5,
            r'dong tien': 1.0, r'hap dan': 1.5, r'xanh': 1.5, r'xanh ruc': 2.0,
            r'ruc ro': 2.0, r'lan toa': 1.5, r'soi dong': 1.5, r'nang hang': 2.0,
            r'vuot dinh': 2.0, r'tang tran': 2.0,
            
            # Financial keywords bổ sung
            r'doanh thu tang': 2.5, r'lai rong tang': 2.5, r'kinh doanh co loi': 2.5,
            r'tang von': 2.0, r'thanh khoan': 2.0, r'thuc hien': 2.0,
            
            # Base keywords
            r'tang': 1.0, r'khon luong': 1.0, r'tot': 1.0, r'tien bo': 1.0,
            r'phe duyet': 1.0, r'dau tu': 1.0, r'mo rong': 1.0, r'trien khai': 1.0,
            r'van hanh': 1.0, r'hop tac': 1.0, r'sap nhap': 1.0, r'mua lai': 1.0,
            r'gianh duoc': 1.0, r'ky ket': 1.0, r'cai thien': 1.0, r'phuc hoi': 1.0,
            r'dat': 1.0, r'hieu qua': 1.0, r'toi uu': 1.0,
            r'cash flow': 1.0, r'don bay': 1.0, r'co cau von': 1.0, r'tai chinh': 1.0,
            
            # English keywords
            r'up': 1.0, r'rise': 1.0, r'grow': 1.0, r'growth': 2.0, r'gain': 1.0,
            r'profit': 2.0, r'profitable': 2.0, r'success': 1.0, r'strong': 1.0,
            r'positive': 1.0, r'improve': 1.0, r'expand': 1.0, r'boost': 1.0,
            r'record': 2.0, r'breakthrough': 2.0, r'launch': 1.0, r'partner': 1.0,
            r'partnership': 1.0, r'acquire': 1.0, r'acquisition': 1.0, r'investment': 1.0,
            r'revenue': 2.0, r'increase': 1.0, r'exceed': 2.0, r'beat': 2.0,
            r'outperform': 2.0, r'dividend': 2.0, r'shareholder': 1.0,
            r'revenue up': 2.0, r'profit up': 2.0, r'profit growth': 2.0, r'earnings': 2.0,
            r'margin': 1.0, r'cash flow': 1.0, r'liquidity': 1.0, r'leverage': 1.0,
            r'capital structure': 1.0, r'bullish': 1.0, r'tang gia': 1.0, r'khang cu': 1.0,
            r'ho tro': 1.0, r'breakout': 1.0, r'uptrend': 1.0, r'momentum': 1.0,
            r'accumulation': 1.0, r'institutional': 1.0
        }
        
        # Keywords tiêu cực với weight (từ lotusmarket + financial domain)
        self.negative_keywords = {
            # High weight keywords (strong negative) - từ lotusmarket
            r'giam': 1.5, r'giam manh': 2.0, r'giam sau': 2.5, r'giam soc': 2.5,
            r'lao doc': 2.5, r'rot': 2.0, r'rot manh': 2.5, r'sut': 2.0,
            r'sut giam': 2.0, r'sap do': 2.5, r'ban thao': 2.5, r'thao chay': 2.5,
            r'hoang loan': 2.5, r'lo ngai': 1.5, r'bi quan': 2.0, r'tieu cuc': 2.0,
            r'roi ro': 1.5, r'lo': 1.5, r'thua lo': 2.0, r'pha san': 2.5,
            r'no xau': 2.0, r'dong cua': 1.5, r'dinh chi': 2.0, r'canh bao': 1.5,
            r'giam san': 2.5, r'do san': 2.0, r'ban rong': 1.5, r'rut von': 2.0,
            
            # Financial keywords bổ sung
            r'khung hoang': 3.0, r'that bai': 3.0, r'giai the': 3.0, r'vo no': 3.0,
            r'thua lo': 3.0, r'lo rong': 3.0, r'lo luy ke': 3.0, r'no xau': 3.0,
            r'canh bao': 2.0, r'bien dong': 2.0, r'risk': 2.0, r'roi ro': 2.0,
            r'phat': 2.0, r'vi pham': 2.0, r'that chap': 2.0, r'qua han': 2.0,
            r'doanh thu giam': 3.0, r'amortization': 2.0,
            r'ap luc tai chinh': 2.0, r'giam no': 2.0,
            
            # Context-specific negative keywords
            r'bi loai': 2.5, r'loai khoi': 2.5, r'bi xoa': 2.5, r'bo': 2.0,
            r'giam danh muc': 2.0, r'loai khoi index': 2.5, r'bi loai khoi': 2.5,
            
            # Base keywords
            r'tuot doc': 1.0, r' yeu kem': 1.0, r'kho khan': 1.0, r'xau': 1.0,
            r'thao go': 1.0, r'thanh ly': 1.0, r'bán': 1.0, r'cat giam': 1.0,
            r'toi uu': 1.0, r'thuong mai hoa': 1.0, r'xa hang': 1.0,
            r'giam gia': 1.0, r'doi tra': 1.0, r'gia mac': 1.0, r'tieu huy': 1.0,
            r'thanh toan': 1.0, r'co phieu': 1.0, r'phi tra no': 1.0,
            
            # English keywords
            r'down': 1.0, r'fall': 1.0, r'drop': 1.0, r'decline': 1.0, r'decrease': 1.0,
            r'loss': 2.0, r'losses': 2.0, r'fail': 1.0, r'failure': 1.0, r'weak': 1.0,
            r'negative': 1.0, r'worse': 1.0, r'poor': 1.0, r'warning': 2.0, r'warn': 2.0,
            r'violation': 2.0, r'penalty': 2.0, r'fine': 2.0, r'sanction': 2.0,
            r'default': 2.0, r'bankruptcy': 2.0, r'debt': 1.0, r'bad debt': 2.0,
            r'overdue': 1.0, r'revenue down': 2.0, r'profit down': 2.0,
            r'profit decline': 2.0, r'margin': 1.0, r'finance pressure': 2.0,
            r'debt issue': 2.0, r'bearish': 1.0, r'giam gia': 1.0, r'sell-off': 1.0,
            r'dump': 1.0, r'correction': 1.0, r'downtrend': 1.0, r'distribution': 1.0,
            r'retail panic': 1.0
        }
        
        # Keywords trung lập với weight
        self.neutral_keywords = {
            r'giu nguyen': 2.0, r'on dinh': 2.0, r'duy tri': 2.0, r'khong doi': 2.0,
            r'thang': 2.0, r'tang lai suat': 2.0, r'lai suat': 2.0, r'ky han': 2.0,
            r'thong bao': 1.0, r'cong bo': 1.0, r'quyet dinh': 1.0, r'chinh sach': 1.0,
            r'hoat dong': 1.0, r'to chuc': 1.0, r'hop': 1.0, r'duyet': 1.0, r'ky ket': 1.0,
            r'thoa thuan': 1.0, r'cam ket': 1.0, r'ke hoach': 1.0, r'trien khai': 1.0,
            r'thong tin': 1.0, r'bao cao': 1.0, r'cong bo': 1.0, r'ra mat': 1.0,
            r'maintain': 1.0, r'stable': 1.0, r'keep': 1.0, r'unchanged': 1.0,
            r'announce': 1.0, r'report': 1.0, r'decision': 1.0, r'policy': 1.0,
            r'plan': 1.0, r'implement': 1.0, r'information': 1.0, r'release': 1.0,
            r'launch': 1.0, r'interest rate': 2.0, r'deposit': 2.0,
            
            # Context-specific neutral keywords
            r'trai phieu': 2.0, r'phat hanh trai phieu': 2.0, r'dang ky giao dich': 2.0,
            r'esop': 2.0, r'phat hanh co phieu': 2.0, r'chao ban': 2.0,
            r'nghiet quyet': 2.0, r'hdqt': 2.0, r'phat co tuc': 2.0,
            r'kiem toan': 2.0, r'bao cao tai chinh': 2.0, r'bctc': 2.0
        }
        
        # Negation words (đảo ngược sentiment)
        self.negation_words = [
            r'khong', r'ko', r'khong co', r'khong duoc', r'khong nhan',
            r'khong lap', r'khong dat', r'that bai', r'fail', r'bi loai',
            r'bi tu choi', r'troi len', r'ngung',
            r'not', r'no', r'without', r'fail to', r'unable'
        ]
        
        # Context-aware rules
        self.context_rules = {
            # Bond issuance is usually neutral/positive, not negative
            'bond_positive': [
                r'phat hanh trai phieu', r'phat hanh bond', r'issuance',
                r'phat hanh thanh cong', r'dang ky giao dịch'
            ],
            # Being removed from index/ETF is negative
            'index_removal': [
                r'bi loai khoi', r'loai khoi index', r'loai khoi etf',
                r'bi xoa khoi', r'bo khoi', r'giam danh muc'
            ],
            # ESOP can be neutral (employee benefit)
            'esop_neutral': [
                r'esop', r'phat hanh esop', r'co phieu uu dai'
            ],
            # Dividend issuance is neutral (standard corporate action)
            'dividend_neutral': [
                r'phat hanh co phieu tra co tuc', r'tra co tuc', r'chia co tuc',
                r'co tuc bang co phieu', r'co tuc dong'
            ]
        }
    
    def analyze_sentiment(self, title: str, summary: str = "") -> str:
        """
        Phân tích sentiment từ tiêu đề và tóm tắt tin tức với weighted keywords
        Xử lý text dài bằng cách chia thành câu và phân tích từng câu
        
        Returns: "POSITIVE", "NEGATIVE", hoặc "NEUTRAL"
        """
        # Combine title and summary
        full_text = f"{title} {summary}"
        
        # Remove Vietnamese accents for better matching
        text_no_accents = remove_vietnamese_accents(full_text).lower()
        
        # Split into sentences for better analysis of long text
        sentences = split_into_sentences(text_no_accents)
        
        # If no sentences or very short, analyze as single block
        if not sentences or len(sentences) <= 1:
            return self._analyze_text_block(text_no_accents)
        
        # Analyze each sentence separately
        sentence_sentiments = []
        for sentence in sentences:
            sentiment = self._analyze_text_block(sentence)
            sentence_sentiments.append(sentiment)
        
        # Aggregate sentence sentiments
        pos_count = sentence_sentiments.count("POSITIVE")
        neg_count = sentence_sentiments.count("NEGATIVE")
        neu_count = sentence_sentiments.count("NEUTRAL")
        
        # Give more weight to title (first sentence usually title)
        if sentence_sentiments:
            title_sentiment = sentence_sentiments[0]
            pos_count += 1 if title_sentiment == "POSITIVE" else 0
            neg_count += 1 if title_sentiment == "NEGATIVE" else 0
            neu_count += 1 if title_sentiment == "NEUTRAL" else 0
        
        # Final decision
        if pos_count > neg_count and pos_count > neu_count:
            return "POSITIVE"
        elif neg_count > pos_count and neg_count > neu_count:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    def _analyze_text_block(self, text: str) -> str:
        """Analyze a single text block (sentence or short text) with context-aware rules"""
        positive_score = 0
        negative_score = 0
        neutral_score = 0
        
        # Check for context-specific rules first
        # Bond issuance -> NEUTRAL (not negative)
        if any(pattern in text for pattern in self.context_rules['bond_positive']):
            return "NEUTRAL"
        
        # Index/ETF removal -> NEGATIVE
        if any(pattern in text for pattern in self.context_rules['index_removal']):
            return "NEGATIVE"
        
        # ESOP -> NEUTRAL
        if any(pattern in text for pattern in self.context_rules['esop_neutral']):
            return "NEUTRAL"
        
        # Dividend issuance -> NEUTRAL
        if any(pattern in text for pattern in self.context_rules['dividend_neutral']):
            return "NEUTRAL"
        
        # Check for negation
        has_negation = any(neg_word in text for neg_word in self.negation_words)
        
        # Đếm keywords với weight
        for keyword, weight in self.positive_keywords.items():
            matches = len(re.findall(keyword, text))
            if has_negation:
                # Invert sentiment if negation present
                negative_score += matches * weight
            else:
                positive_score += matches * weight
        
        for keyword, weight in self.negative_keywords.items():
            matches = len(re.findall(keyword, text))
            if has_negation:
                # Invert sentiment if negation present
                positive_score += matches * weight
            else:
                negative_score += matches * weight
        
        for keyword, weight in self.neutral_keywords.items():
            matches = len(re.findall(keyword, text))
            neutral_score += matches * weight
        
        # Quyết định sentiment với threshold
        if positive_score > negative_score + 1:  # Need clear advantage
            return "POSITIVE"
        elif negative_score > positive_score + 1:
            return "NEGATIVE"
        else:
            return "NEUTRAL"

# Singleton instance
_analyzer_instance = None

def get_sentiment_analyzer() -> RuleBasedSentimentAnalyzer:
    """Get singleton instance of sentiment analyzer"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = RuleBasedSentimentAnalyzer()
    return _analyzer_instance
