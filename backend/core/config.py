# -*- coding: utf-8 -*-
"""
Config module - paths, settings, environment variables.
"""

import os
from dotenv import load_dotenv
import pandas as pd

# Pandas display settings
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 125)
pd.set_option('display.max_colwidth', 30)
pd.set_option('display.unicode.east_asian_width', True)

load_dotenv()

# Directory structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
DATA_DIR = os.path.join(BASE_DIR, "data", "raw", "financial_distress")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Subdirectories
_SUBDIRS = {
    "CREDIT_RISK_DIR": os.path.join(ARTIFACTS_DIR, "credit_risk"),
    "CW_PRICING_DIR": os.path.join(ARTIFACTS_DIR, "cw_pricing"),
    "REGIME_ANALYSIS_DIR": os.path.join(ARTIFACTS_DIR, "regime_analysis"),
    "RAW_DATA_DIR": os.path.join(DATA_DIR, "raw"),
    "PROCESSED_DATA_DIR": os.path.join(DATA_DIR, "processed"),
    "FINAL_DATA_DIR": os.path.join(DATA_DIR, "final")
}

# Add to namespace
for key, path in _SUBDIRS.items():
    globals()[key] = path

# Ensure directories exist
for path in [ARTIFACTS_DIR, DATA_DIR, LOG_DIR] + list(_SUBDIRS.values()):
    os.makedirs(path, exist_ok=True)

# Model artifacts
MODELS_DIR = ARTIFACTS_DIR  # backward-compatible
BEST_DISTRESS_MODEL = os.path.join(_SUBDIRS["CREDIT_RISK_DIR"], "best_distress_model.pkl")
SCALER_ARTIFACT = os.path.join(_SUBDIRS["CREDIT_RISK_DIR"], "scaler.pkl")
FEATURE_NAMES_ARTIFACT = os.path.join(_SUBDIRS["CREDIT_RISK_DIR"], "feature_names.pkl")
THRESHOLD_CONFIG = os.path.join(_SUBDIRS["CREDIT_RISK_DIR"], "threshold_config.json")
BEST_MODEL_PARAMS = os.path.join(_SUBDIRS["CREDIT_RISK_DIR"], "best_model_params.json")
SHAP_FEATURE_IMPORTANCE = os.path.join(_SUBDIRS["CREDIT_RISK_DIR"], "shap_feature_importance.json")

ML_PRICING_MODEL = os.path.join(_SUBDIRS["CW_PRICING_DIR"], "ml_pricing_model.pkl")
ML_HYBRID_VOL_MODEL = os.path.join(_SUBDIRS["CW_PRICING_DIR"], "ml_hybrid_vol_model.pkl")

XGBOOST_REGIME_DIR = _SUBDIRS["REGIME_ANALYSIS_DIR"]

# Regime System Configuration
REGIME_PERFORMANCE_MODE = os.getenv("REGIME_PERFORMANCE_MODE", "HYBRID")  # FAST, HYBRID, FULL
REGIME_CACHE_ENABLED = os.getenv("REGIME_CACHE_ENABLED", "true").lower() == "true"
REGIME_ASYNC_ENABLED = os.getenv("REGIME_ASYNC_ENABLED", "true").lower() == "true"
REGIME_TTL_SECONDS = int(os.getenv("REGIME_TTL_SECONDS", "600"))  # 10 minutes default

# Data files
COMPANIES_LIST_FILE = os.path.join(DATA_DIR, "companies_list.json")
FILTERED_COMPANIES_FILE = os.path.join(DATA_DIR, "filtered_companies.json")
RAW_FINANCIALS_FILE = os.path.join(_SUBDIRS["RAW_DATA_DIR"], "raw_financials.json")
CLEANED_FINANCIALS_FILE = os.path.join(_SUBDIRS["PROCESSED_DATA_DIR"], "cleaned_financials.csv")
FEATURES_FILE = os.path.join(_SUBDIRS["PROCESSED_DATA_DIR"], "financial_features.csv")
LABELED_DATA_FILE = os.path.join(_SUBDIRS["PROCESSED_DATA_DIR"], "labeled_financial_data.csv")
FINAL_DATASET_FILE = os.path.join(_SUBDIRS["FINAL_DATA_DIR"], "financial_distress_dataset.csv")

# Pipeline configuration
TARGET_EXCHANGES = ["HOSE", "HNX", "UPCOM"]
START_YEAR = 2018
END_YEAR = 2026
TICKER_GROUP = "ALL"
USE_MOCK = False

# Crawling settings
CRAWL_CHECKPOINT_INTERVAL = 25
MAX_RETRIES = 3
MIN_DELAY = 1.0
MAX_DELAY = 2.5

# Excluded financial sectors
EXCLUDED_SECTORS = [
    "Ngân hàng", "Chứng khoán", "Bảo hiểm", "Quỹ đầu tư", "Công ty tài chính", "Tài chính khác",
    "Banking", "Securities", "Insurance", "Investment Funds", "Financial Services"
]