# -*- coding: utf-8 -*-
"""Background periodic market scan scheduler."""

import threading
import time
from datetime import datetime

from src.cw_engine.run_analysis import run_quant_pipeline_programmatic


def start_periodic_scheduler() -> None:
    def scheduler_loop():
        time.sleep(10)
        print("🕒 [Scheduler Thread] Starting periodic market scanning background loop...")
        while True:
            try:
                now = datetime.now()
                is_weekday = now.weekday() < 5
                time_str = now.strftime("%H:%M:%S")
                in_morning = "09:00:00" <= time_str <= "11:30:00"
                in_afternoon = "13:00:00" <= time_str <= "14:45:00"

                if is_weekday and (in_morning or in_afternoon):
                    print(
                        "🕒 [Scheduler Thread] HOSE Market is open. "
                        "Executing scheduled quantitative scan..."
                    )
                    run_quant_pipeline_programmatic(strategy="balanced")
                    print(
                        "🕒 [Scheduler Thread] Scheduled quantitative scan completed and persisted."
                    )
                    time.sleep(900)
                else:
                    time.sleep(300)
            except Exception as e:
                print(f"⚠️ [Scheduler Thread] Error in loop: {e}")
                time.sleep(60)

    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
