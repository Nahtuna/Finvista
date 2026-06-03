# -*- coding: utf-8 -*-
"""
🚨 Finvista Corporate Credit Risk & Financial Distress Pipeline Entrypoint
========================================================================
Usage:
  python run_credit_risk.py          (Runs the full 5-tier ingestion and labeling pipeline)
  python run_credit_risk.py --train  (Trains the XGBoost Early Warning ML Model)

Author: samvo
"""

import sys
import os
import argparse

# Ensure project root is on PYTHONPATH when running as a script (python scripts/run_credit_risk.py ...)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Reconfigure stdout and stderr to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Finvista Financial Distress & Credit Risk Engine")
    parser.add_argument('--train', '-t', action='store_true',
                        help="Train the XGBoost Credit Risk Early Warning Model using Out-of-Time split")
    parser.add_argument('--evaluate', '-e', action='store_true',
                        help="Run full-market quantitative credit health assessment on all 1,447 listed companies")
    args = parser.parse_args()

    if args.train:
        from src.models.credit_risk_train_model import train_prediction_model
        train_prediction_model()
    elif args.evaluate:
        from src.models.credit_risk_evaluate_market import evaluate_market_health
        evaluate_market_health()
    else:
        from src.etl.credit_pipeline import run_full_pipeline
        run_full_pipeline()

if __name__ == "__main__":
    main()
