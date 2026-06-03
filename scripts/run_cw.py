# -*- coding: utf-8 -*-
"""
🏆 Finvista Covered Warrant Pricing & Greeks Analysis Quick-Launch Entrypoint
========================================================================
Usage:
  python run_cw.py --strategy balanced --limit 15
  python run_cw.py --simulate CACB2510

Author: samvo
"""

import sys
import os

# Ensure project root is on PYTHONPATH when running as a script (python scripts/run_cw.py ...)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    print("⏳ Đang khởi động engine chứng quyền (nạp thư viện, có thể mất 20–30 giây)...", flush=True)
    from src.cw_engine.run_analysis import main

    main()
