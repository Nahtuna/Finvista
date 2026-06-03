# -*- coding: utf-8 -*-
"""Dataset loading, feature selection, and train/test preprocessing."""

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.common import config
from src.common.utils import load_csv, logger

DEFAULT_THRESHOLD = 0.5
TARGET_RECALL = 0.65
USE_LAGGED_LABEL = True
LEAKAGE_FEATURES = {
    "ebit_to_interest",
    "icr",
    "current_ratio",
    "total_equity",
    "springate_distressed",
    "zmijewski_distressed",
}


@dataclass
class PreparedDataset:
    df: pd.DataFrame
    feature_cols: list
    target_col: str
    split_year: int
    train_years: np.ndarray
    X_train_scaled: pd.DataFrame
    X_test_scaled: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    scaler: StandardScaler
    scale_pos_weight: float


def prepare_train_test_split(split_year: int = 2022) -> Optional[PreparedDataset]:
    """Load dataset, build features, and return scaled train/test matrices."""
    dataset_file = config.FINAL_DATASET_FILE
    if not os.path.exists(dataset_file):
        logger.error(f"❌ Final dataset not found: {dataset_file}")
        logger.info("💡 Please run: python run_pipeline.py first to generate the dataset.")
        return None

    df = load_csv(dataset_file)
    if df.empty:
        logger.error("❌ Final training dataset is empty!")
        return None
    
    # ------------------------------------------------------------------
    # LAGGED LABEL MODE: load _lagged dataset for proper T → T+1 setup
    # ------------------------------------------------------------------
    if USE_LAGGED_LABEL:
        lagged_file = dataset_file.replace(".csv", "_lagged.csv")
        if os.path.exists(lagged_file):
            df = load_csv(lagged_file)
            target_col = "distress_label_next_year"
            logger.info("✅ LAGGED MODE: features(T) → distress_label(T+1) — No data leakage")
        else:
            logger.warning("⚠️ Lagged dataset not found. Run pipeline first. Falling back to same-year label.")
            target_col = "distress_label"
    else:
        target_col = "distress_label"
        logger.info("⚠️ SAME-YEAR MODE: features(T) → distress_label(T) — Data leakage present")
        
    # Ensure year column is treated as integer
    df["year"] = df["year"].astype(int)
    
    train_mask = df["year"] <= split_year
    test_mask = df["year"] > split_year
    
    # Define features and target
    exclude_cols = {"ticker", "company_name", "year", "exchange", "industry",
                    "distress_label", "distress_label_next_year"}
    if USE_LAGGED_LABEL:
        exclude_cols |= LEAKAGE_FEATURES
        logger.info(f"🚫 Excluded {len(LEAKAGE_FEATURES)} leakage features: {sorted(LEAKAGE_FEATURES)}")
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, target_col]
    train_years = df.loc[train_mask, "year"].to_numpy()
    
    X_test = df.loc[test_mask, feature_cols]
    y_test = df.loc[test_mask, target_col]
    
    logger.info(f"📊 Dataset successfully prepared:")
    logger.info(f"   * Total unique features      : {len(feature_cols)}")
    logger.info(f"   * Train Set (Years <= {split_year}): {len(X_train)} records")
    logger.info(f"   * Test Set (Years > {split_year}) : {len(X_test)} records")
    
    distress_rate_train = np.mean(y_train)
    distress_rate_test = np.mean(y_test)
    logger.info(f"   * Distress Rate in Train Set : {distress_rate_train:.2%}")
    logger.info(f"   * Distress Rate in Test Set  : {distress_rate_test:.2%}")
    
    if len(X_train) == 0 or len(X_test) == 0:
        logger.error("❌ Not enough records in Train or Test set! Make sure data spans multiple years.")
        return None

    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_cols)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=feature_cols)

    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
    logger.info(f"⚖️ Calculated Class Balance Factor: {scale_pos_weight:.2f}")

    return PreparedDataset(
        df=df,
        feature_cols=feature_cols,
        target_col=target_col,
        split_year=split_year,
        train_years=train_years,
        X_train_scaled=X_train_scaled,
        X_test_scaled=X_test_scaled,
        y_train=y_train,
        y_test=y_test,
        scaler=scaler,
        scale_pos_weight=scale_pos_weight,
    )
