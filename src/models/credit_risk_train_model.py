# -*- coding: utf-8 -*-
"""
🏁 Finvista Corporate Credit Risk & Financial Distress Model Comparator & Exporter
========================================================================
Entry point: loads data, trains candidate models, evaluates, and exports artifacts.

Author: samvo
"""

from src.common.utils import logger
from src.models.credit_risk_evaluator import evaluate_and_export
from src.models.credit_risk_preprocessor import prepare_train_test_split
from src.models.credit_risk_trainer import train_all_models


def train_prediction_model():
    logger.info("==========================================================")
    logger.info("🏁 INITIALIZING ADVANCED MULTI-MODEL ML COMPARATIVE ENGINE")
    logger.info("==========================================================")

    prepared = prepare_train_test_split()
    if prepared is None:
        return

    models = train_all_models(prepared)
    if not models:
        logger.error("❌ No models were trained successfully.")
        return

    evaluate_and_export(models, prepared)
    logger.info("==========================================================")


def main():
    train_prediction_model()


if __name__ == "__main__":
    main()
