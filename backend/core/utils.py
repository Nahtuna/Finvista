# -*- coding: utf-8 -*-
"""
Core utility module - logging, file I/O, checkpoint management.
"""

import os
import sys
import json
import logging
import time
import random
import pandas as pd
from typing import Any, Dict, List
from backend.core import config

# Force UTF-8 encoding for stdout/stderr on Windows to handle emoji characters
def reconfigure_console():
    """Force UTF-8 encoding for stdout/stderr on Windows to handle emoji characters."""
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

def sanitize_proxies():
    """Sanitize proxy variables to prevent httpx IPv6 loopback crash (::1)."""
    for var in ["no_proxy", "NO_PROXY"]:
        if var in os.environ:
            parts = [p.strip() for p in os.environ[var].split(",")]
            cleaned = [p for p in parts if "::1" not in p]
            os.environ[var] = ",".join(cleaned)

def initialize_console_setup():
    """Initialize console setup (called from entry points)."""
    reconfigure_console()
    sanitize_proxies()



class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that safely ignores closed stream errors during server reloads."""
    def emit(self, record):
        try:
            super().emit(record)
        except (ValueError, OSError):
            pass

class SafeFileHandler(logging.FileHandler):
    """FileHandler that safely ignores closed file errors during server reloads."""
    def emit(self, record):
        try:
            super().emit(record)
        except (ValueError, OSError):
            pass

class CustomFormatter(logging.Formatter):
    """Custom log formatter: '14:21:50 | INFO  | Message'."""
    def format(self, record):
        log_time = time.strftime("%H:%M:%S", time.localtime(record.created))
        return f"{log_time} | {record.levelname:<5} | {record.getMessage()}"


def get_logger(name: str = "financial_distress") -> logging.Logger:
    """Configures and returns a custom formatted logger with thread-safe handler management."""
    logger = logging.getLogger(name)
    
    # Remove any closed handlers from this logger, root logger, and all registered loggers to prevent "I/O operation on closed file" errors
    all_loggers = [logging.getLogger(), logger]
    for l_name in list(logging.Logger.manager.loggerDict.keys()):
        all_loggers.append(logging.getLogger(l_name))

    for curr_logger in all_loggers:
        for handler in curr_logger.handlers[:]:
            try:
                if hasattr(handler, 'stream') and hasattr(handler.stream, 'closed'):
                    if handler.stream.closed:
                        curr_logger.removeHandler(handler)
                        try:
                            handler.close()
                        except Exception:
                            pass
            except Exception:
                curr_logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
    
    # Add handlers if none exist or all were removed
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Prevent duplicate logs from root logger
        
        # Console handler with UTF-8 encoding for emoji support
        try:
            ch = SafeStreamHandler()
            if hasattr(ch.stream, 'reconfigure'):
                ch.stream.reconfigure(encoding='utf-8', errors='replace')
            ch.setFormatter(CustomFormatter())
            logger.addHandler(ch)
        except Exception:
            # Fallback to default stream handler
            ch = SafeStreamHandler()
            ch.setFormatter(CustomFormatter())
            logger.addHandler(ch)
        
        # File handler with UTF-8 encoding (optional - can fail gracefully)
        try:
            file_log_path = os.path.join(config.LOG_DIR, "pipeline.log")
            fh = SafeFileHandler(file_log_path, encoding="utf-8")
            fh.setFormatter(CustomFormatter())
            logger.addHandler(fh)
        except Exception as e:
            # If file handler fails, at least we have console logging
            logger.warning(f"Could not create file handler: {e}")
    
    return logger


logger = get_logger()


def _ensure_dir(file_path: str):
    """Ensure parent directory exists."""
    if file_path:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)


def load_json(file_path: str) -> Any:
    """Safely loads a JSON file."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return None


def save_json(data: Any, file_path: str) -> bool:
    """Safely saves data to a JSON file."""
    try:
        _ensure_dir(file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False


def load_csv(file_path: str) -> pd.DataFrame:
    """Safely loads a CSV file."""
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8")
    except Exception as e:
        logger.error(f"Error loading CSV from {file_path}: {e}")
        return pd.DataFrame()


def save_csv(df: pd.DataFrame, file_path: str) -> bool:
    """Safely saves a pandas DataFrame to a CSV file."""
    try:
        _ensure_dir(file_path)
        df.to_csv(file_path, index=False, encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Error saving CSV to {file_path}: {e}")
        return False


def random_sleep(min_sec: float = 1.0, max_sec: float = 2.5):
    """Sleeps for a random duration to prevent API blocking."""
    time.sleep(random.uniform(min_sec, max_sec))


class CheckpointManager:
    """Manages crawl state to allow resuming from failures."""
    
    DEFAULT_STATE = {
        "last_processed_index": 0,
        "completed_tickers": [],
        "failed_tickers": {}
    }
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load checkpoint state or return default."""
        state = load_json(self.checkpoint_file)
        return state if state else self.DEFAULT_STATE.copy()
    
    def save(self, index: int, ticker: str, status: str = "success", error_msg: str = ""):
        """Save checkpoint state."""
        self.state["last_processed_index"] = index
        
        if status == "success":
            if ticker not in self.state["completed_tickers"]:
                self.state["completed_tickers"].append(ticker)
            self.state["failed_tickers"].pop(ticker, None)
        else:
            self.state["failed_tickers"][ticker] = {
                "error": error_msg,
                "timestamp": time.time(),
                "attempts": self.state["failed_tickers"].get(ticker, {}).get("attempts", 0) + 1
            }
        save_json(self.state, self.checkpoint_file)
    
    def get_progress(self) -> int:
        return self.state["last_processed_index"]
    
    def get_completed(self) -> List[str]:
        return self.state["completed_tickers"]
    
    def get_failed(self) -> Dict[str, Any]:
        return self.state["failed_tickers"]
