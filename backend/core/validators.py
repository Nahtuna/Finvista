# -*- coding: utf-8 -*-
"""
Data Validation Module - financial data, API responses, user inputs.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal
import re


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


class DataValidator:
    """Base validator class with common validation methods."""
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> None:
        """Validate that a required field is present and not empty."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"Field '{field_name}' is required", field_name, value)
    
    @staticmethod
    def validate_type(value: Any, expected_type: type, field_name: str) -> None:
        """Validate that a value is of the expected type."""
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"Field '{field_name}' must be of type {expected_type.__name__}, got {type(value).__name__}",
                field_name, value
            )
    
    @staticmethod
    def validate_range(value: Union[int, float, Decimal], min_val: Optional[Union[int, float, Decimal]] = None,
                      max_val: Optional[Union[int, float, Decimal]] = None, field_name: str = "value") -> None:
        """Validate that a numeric value is within a specified range."""
        if min_val is not None and value < min_val:
            raise ValidationError(f"Field '{field_name}' must be >= {min_val}, got {value}", field_name, value)
        if max_val is not None and value > max_val:
            raise ValidationError(f"Field '{field_name}' must be <= {max_val}, got {value}", field_name, value)
    
    @staticmethod
    def validate_string_length(value: str, min_length: Optional[int] = None, max_length: Optional[int] = None,
                            field_name: str = "string") -> None:
        """Validate string length constraints."""
        length = len(value)
        if min_length is not None and length < min_length:
            raise ValidationError(f"Field '{field_name}' must be at least {min_length} characters", field_name, value)
        if max_length is not None and length > max_length:
            raise ValidationError(f"Field '{field_name}' must be at most {max_length} characters", field_name, value)
    
    @staticmethod
    def validate_regex(value: str, pattern: str, field_name: str = "string") -> None:
        """Validate that a string matches a regex pattern."""
        if not re.match(pattern, value):
            raise ValidationError(f"Field '{field_name}' does not match required pattern", field_name, value)
    
    @staticmethod
    def validate_date(value: Union[str, date, datetime], field_name: str = "date") -> datetime:
        """Validate and convert a date value."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                raise ValidationError(f"Field '{field_name}' must be a valid ISO date string", field_name, value)
        raise ValidationError(f"Field '{field_name}' must be a date or datetime", field_name, value)


class FinancialValidator(DataValidator):
    """Validator for financial data and market instruments."""
    
    TICKER_PATTERN = r'^[A-Z]{3}\d*$'
    WARRANT_PATTERN = r'^[A-Z]{3}\d{4}$'
    
    GREEKS_RANGES = {
        "delta": (-1, 1),
        "gamma": (0, 1),
        "vega": (0, 10),
        "theta": (-10, 10),
        "rho": (-10, 10)
    }
    
    @staticmethod
    def validate_ticker(ticker: str, field_name: str = "ticker") -> None:
        """Validate Vietnamese stock ticker format."""
        DataValidator.validate_required(ticker, field_name)
        DataValidator.validate_string_length(ticker, min_length=3, max_length=10, field_name=field_name)
        DataValidator.validate_regex(ticker, FinancialValidator.TICKER_PATTERN, field_name)
    
    @staticmethod
    def validate_warrant_symbol(symbol: str, field_name: str = "symbol") -> None:
        """Validate warrant symbol format."""
        DataValidator.validate_required(symbol, field_name)
        DataValidator.validate_regex(symbol, FinancialValidator.WARRANT_PATTERN, field_name)
    
    @staticmethod
    def validate_price(price: Union[int, float, Decimal], field_name: str = "price") -> None:
        """Validate that price is positive and reasonable."""
        DataValidator.validate_type(price, (int, float, Decimal), field_name)
        DataValidator.validate_range(price, min_val=0.01, max_val=1000000, field_name=field_name)
    
    @staticmethod
    def validate_volume(volume: Union[int, float], field_name: str = "volume") -> None:
        """Validate that volume is non-negative."""
        DataValidator.validate_type(volume, (int, float), field_name)
        DataValidator.validate_range(volume, min_val=0, field_name=field_name)
    
    @staticmethod
    def validate_percentage(value: Union[int, float, Decimal], field_name: str = "percentage") -> None:
        """Validate that a value is a valid percentage (0-100)."""
        DataValidator.validate_type(value, (int, float, Decimal), field_name)
        DataValidator.validate_range(value, min_val=0, max_val=100, field_name=field_name)
    
    @staticmethod
    def validate_greeks(greeks: Dict[str, float], field_name: str = "greeks") -> None:
        """Validate options Greeks values."""
        for greek_name, (min_val, max_val) in FinancialValidator.GREEKS_RANGES.items():
            if greek_name in greeks:
                value = greeks[greek_name]
                DataValidator.validate_type(value, (int, float), f"{field_name}.{greek_name}")
                DataValidator.validate_range(value, min_val=min_val, max_val=max_val, field_name=f"{field_name}.{greek_name}")
    
    @staticmethod
    def validate_credit_score(score: Union[int, float], field_name: str = "credit_score") -> None:
        """Validate credit risk score (0-1 or 0-100)."""
        DataValidator.validate_type(score, (int, float), field_name)
        if 0 <= score <= 1:
            DataValidator.validate_range(score, 0, 1, field_name)
        else:
            DataValidator.validate_range(score, 0, 100, field_name)
    
    @staticmethod
    def validate_ohlcv(data: Dict[str, Any], field_name: str = "ohlcv") -> None:
        """Validate OHLCV candlestick data."""
        required_fields = ["open", "high", "low", "close", "volume"]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field '{field}' in OHLCV data", field_name, data)
        
        # Validate price relationships: high >= max(open, close) and low <= min(open, close)
        FinancialValidator.validate_price(data["open"], f"{field_name}.open")
        FinancialValidator.validate_price(data["high"], f"{field_name}.high")
        FinancialValidator.validate_price(data["low"], f"{field_name}.low")
        FinancialValidator.validate_price(data["close"], f"{field_name}.close")
        FinancialValidator.validate_volume(data["volume"], f"{field_name}.volume")
        
        if data["high"] < max(data["open"], data["close"]):
            raise ValidationError(f"High price must be >= max(open, close)", f"{field_name}.high", data["high"])
        if data["low"] > min(data["open"], data["close"]):
            raise ValidationError(f"Low price must be <= min(open, close)", f"{field_name}.low", data["low"])
    
    @staticmethod
    def validate_market_opportunity(data: Dict[str, Any], field_name: str = "opportunity") -> None:
        """Validate market opportunity data structure."""
        required_fields = ["symbol", "underlying", "score", "signal"]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field '{field}' in opportunity data", field_name, data)
        
        FinancialValidator.validate_warrant_symbol(data["symbol"], f"{field_name}.symbol")
        FinancialValidator.validate_ticker(data["underlying"], f"{field_name}.underlying")
        FinancialValidator.validate_percentage(data["score"], f"{field_name}.score")


class APIValidator(DataValidator):
    """Validator for API request/response data."""
    
    @staticmethod
    def validate_pagination_params(offset: int, limit: int, max_limit: int = 100) -> None:
        """Validate pagination parameters."""
        DataValidator.validate_range(offset, min_val=0, field_name="offset")
        DataValidator.validate_range(limit, min_val=1, max_val=max_limit, field_name="limit")
    
    @staticmethod
    def validate_sort_params(sort_by: str, valid_fields: List[str], field_name: str = "sort_by") -> None:
        """Validate sort parameter against valid fields."""
        if sort_by not in valid_fields:
            raise ValidationError(
                f"Invalid sort field '{sort_by}'. Valid fields: {', '.join(valid_fields)}",
                field_name, sort_by
            )