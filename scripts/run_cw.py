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
from src.cw_engine.run_analysis import main

if __name__ == "__main__":
    main()
