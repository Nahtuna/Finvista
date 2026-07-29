# -*- coding: utf-8 -*-
"""
Data Validation Module
=======================
Provides validation logic for financial data, API responses, and user inputs.
Ensures data integrity, type safety, and business rule compliance.
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
                field_name,
                value
            )
    
    @staticmethod
    def validate_range(
        value: Union[int, float, Decimal],
        min_val: Optional[Union[int, float, Decimal]] = None,
        max_val: Optional[Union[int, float, Decimal]] = None,
        field_name: str = "value"
    ) -> None:
        """Validate that a numeric value is within a specified range."""
        if min_val is not None and value < min_val:
            raise ValidationError(
                f"Field '{field_name}' must be >= {min_val}, got {value}",
                field_name,
                value
            )
        if max_val is not None and value > max_val:
            raise ValidationError(
                f"Field '{field_name}' must be <= {max_val}, got {value}",
                field_name,
                value
            )
    
    @staticmethod
    def validate_string_length(
        value: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        field_name: str = "string"
    ) -> None:
        """Validate string length constraints."""
        length = len(value)
        if min_length is not None and length < min_length:
            raise ValidationError(
                f"Field '{field_name}' must be at least {min_length} characters, got {length}",
                field_name,
                value
            )
        if max_length is not None and length > max_length:
            raise ValidationError(
                f"Field '{field_name}' must be at most {max_length} characters, got {length}",
                field_name,
                value
            )
    
    @staticmethod
    def validate_regex(value: str, pattern: str, field_name: str = "string") -> None:
        """Validate that a string matches a regex pattern."""
        if not re.match(pattern, value):
            raise ValidationError(
                f"Field '{field_name}' does not match required pattern",
                field_name,
                value
            )
    
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
                raise ValidationError(
                    f"Field '{field_name}' must be a valid ISO date string (YYYY-MM-DD)",
                    field_name,
                    value
                )
        raise ValidationError(
            f"Field '{field_name}' must be a date or datetime",
            field_name,
            value
        )


class FinancialValidator(DataValidator):
    """Validator for financial data and market instruments."""
    
    # Vietnamese ticker pattern: 3 uppercase letters + optional suffix
    TICKER_PATTERN = r'^[A-Z]{3}\d*$'
    
    # Warrant symbol pattern: e.g., CACB2511, FPT2412
    WARRANT_PATTERN = r'^[A-Z]{3}\d{4}$'
    
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
    def validate_percentage(
        value: Union[int, float, Decimal],
        field_name: str = "percentage"
    ) -> None:
        """Validate that a value is a valid percentage (0-100)."""
        DataValidator.validate_type(value, (int, float, Decimal), field_name)
        DataValidator.validate_range(value, min_val=0, max_val=100, field_name=field_name)
    
    @staticmethod
    def validate_greeks(greeks: Dict[str, float], field_name: str = "greeks") -> None:
        """Validate options Greeks values."""
        valid_greeks = ["delta", "gamma", "vega", "theta", "rho"]
        
        for greek_name in valid_greeks:
            if greek_name in greeks:
                value = greeks[greek_name]
                DataValidator.validate_type(value, (int, float), f"{field_name}.{greek_name}")
                
                # Delta: -1 to 1
                if greek_name == "delta":
                    DataValidator.validate_range(value, min_val=-1, max_val=1, f"{field_name}.{greek_name}")
                # Gamma: 0 to 1
                elif greek_name == "gamma":
                    DataValidator.validate_range(value, min_val=0, max_val=1, f"{field_name}.{greek_name}")
                # Theta: typically negative, but allow reasonable range
                elif greek_name == "theta":
                    DataValidator.validate_range(value, min_val=-10, max_val=10, f"{field_name}.{greek_name}")
    
    @staticmethod
    def validate_credit_score(score: Union[int, float], field_name: str = "credit_score") -> None:
        """Validate credit risk score (typically 0-100 or 0-1)."""
        DataValidator.validate_type(score, (int, float), field_name)
        if 0 <= score <= 1:
            # Normalized score (0-1)
            DataValidator.validate_range(score, min_val=0, max_val=1, field_name)
        else:
            # Raw score (0-100)
            DataValidator.validate_range(score, min_val=0, max_val=100, field_name)
    
    @staticmethod
    def validate_ohlcv(data: Dict[str, Any], field_name: str = "ohlcv") -> None:
        """Validate OHLCV candlestick data."""
        required_fields = ["open", "high", "low", "close", "volume"]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field '{field}' in OHLCV data", field_name, data)
        
        # Validate price relationships
        open_price = data["open"]
        high_price = data["high"]
        low_price = data["low"]
        close_price = data["close"]
        
        FinancialValidator.validate_price(open_price, f"{field_name}.open")
        FinancialValidator.validate_price(high_price, f"{field_name}.high")
        FinancialValidator.validate_price(low_price, f"{field_name}.low")
        FinancialValidator.validate_price(close_price, f"{field_name}.close")
        FinancialValidator.validate_volume(data["volume"], f"{field_name}.volume")
        
        # Validate high >= low
        if high_price < low_price:
            raise ValidationError(
                f"High price ({high_price}) must be >= low price ({low_price})",
                f"{field_name}.high",
                high_price
            )
        
        # Validate high/low contain open/close
        if high_price < open_price or high_price < close_price:
            raise ValidationError(
                f"High price ({high_price}) must be >= open ({open_price}) and close ({close_price})",
                f"{field_name}.high",
                high_price
            )
        
        if low_price > open_price or low_price > close_price:
            raise ValidationError(
                f"Low price ({low_price}) must be <= open ({open_price}) and close ({close_price})",
                f"{field_name}.low",
                low_price
            )


class APIValidator(DataValidator):
    """Validator for API requests and responses."""
    
    @staticmethod
    def validate_pagination(
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        max_page_size: int = 100
    ) -> tuple[int, int]:
        """Validate and normalize pagination parameters."""
        if page is None:
            page = 1
        else:
            DataValidator.validate_type(page, int, "page")
            DataValidator.validate_range(page, min_val=1, field_name="page")
        
        if page_size is None:
            page_size = 20
        else:
            DataValidator.validate_type(page_size, int, "page_size")
            DataValidator.validate_range(page_size, min_val=1, max_val=max_page_size, field_name="page_size")
        
        return page, page_size
    
    @staticmethod
    def validate_sort_field(
        sort_field: str,
        allowed_fields: List[str],
        field_name: str = "sort_field"
    ) -> None:
        """Validate that sort field is in allowed list."""
        if sort_field not in allowed_fields:
            raise ValidationError(
                f"Invalid sort field '{sort_field}'. Allowed fields: {', '.join(allowed_fields)}",
                field_name,
                sort_field
            )
    
    @staticmethod
    def validate_sort_order(sort_order: str, field_name: str = "sort_order") -> None:
        """Validate sort order (asc/desc)."""
        allowed_orders = ["asc", "desc"]
        if sort_order not in allowed_orders:
            raise ValidationError(
                f"Invalid sort order '{sort_order}'. Allowed: {', '.join(allowed_orders)}",
                field_name,
                sort_order
            )
    
    @staticmethod
    def validate_date_range(
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        field_prefix: str = "date"
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """Validate date range parameters."""
        validated_start = None
        validated_end = None
        
        if start_date is not None:
            validated_start = DataValidator.validate_date(start_date, f"{field_prefix}_start")
        
        if end_date is not None:
            validated_end = DataValidator.validate_date(end_date, f"{field_prefix}_end")
        
        # Validate that start_date <= end_date
        if validated_start and validated_end and validated_start > validated_end:
            raise ValidationError(
                f"Start date ({validated_start}) must be <= end date ({validated_end})",
                f"{field_prefix}_range",
                f"{start_date} - {end_date}"
            )
        
        return validated_start, validated_end


class DataFreshnessValidator:
    """Validator for data freshness and staleness checks."""
    
    @staticmethod
    def validate_freshness(
        timestamp: Union[str, datetime],
        max_age_seconds: int,
        field_name: str = "timestamp"
    ) -> bool:
        """
        Check if data is fresh enough based on timestamp.
        
        Args:
            timestamp: Data timestamp
            max_age_seconds: Maximum allowed age in seconds
            field_name: Field name for error reporting
        
        Returns:
            True if data is fresh, False otherwise
        
        Raises:
            ValidationError: If timestamp is invalid
        """
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                raise ValidationError(
                    f"Invalid timestamp format: {timestamp}",
                    field_name,
                    timestamp
                )
        
        if not isinstance(timestamp, datetime):
            raise ValidationError(
                f"Timestamp must be datetime or ISO string",
                field_name,
                timestamp
            )
        
        age_seconds = (datetime.now() - timestamp).total_seconds()
        return age_seconds <= max_age_seconds
    
    @staticmethod
    def get_freshness_status(
        timestamp: Union[str, datetime],
        thresholds: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """
        Get detailed freshness status with age and status level.
        
        Args:
            timestamp: Data timestamp
            thresholds: Custom thresholds in seconds (default: fresh=60, stale=300)
        
        Returns:
            Dict with age, status, and is_fresh flag
        """
        if thresholds is None:
            thresholds = {
                "fresh": 60,      # 1 minute
                "stale": 300,    # 5 minutes
                "expired": 3600  # 1 hour
            }
        
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        age_seconds = (datetime.now() - timestamp).total_seconds()
        
        if age_seconds <= thresholds["fresh"]:
            status = "fresh"
        elif age_seconds <= thresholds["stale"]:
            status = "stale"
        elif age_seconds <= thresholds["expired"]:
            status = "warning"
        else:
            status = "expired"
        
        return {
            "timestamp": timestamp.isoformat(),
            "age_seconds": age_seconds,
            "age_human": f"{age_seconds:.0f}s",
            "status": status,
            "is_fresh": age_seconds <= thresholds["fresh"],
            "thresholds": thresholds
        }


def validate_request_data(data: Dict[str, Any], validator_class: type) -> List[str]:
    """
    Validate request data using a validator class.
    
    Args:
        data: Request data dictionary
        validator_class: Validator class to use
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    validator = validator_class()
    
    # This is a generic wrapper - specific implementations should override
    # or use specific validation methods
    try:
        if hasattr(validator, 'validate'):
            validator.validate(data)
    except ValidationError as e:
        errors.append(f"{e.field}: {e.message}" if e.field else e.message)
    
    return errors
