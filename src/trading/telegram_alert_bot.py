# -*- coding: utf-8 -*-
"""
🚀 FINVISTA REAL-TIME SCANNER BOT
======================================================
Tự động quét toàn bộ thị trường Chứng quyền và cập nhật
mỗi 5 phút một lần.

Usage:
  python scripts/run_realtime_bot.py
"""

import time
import os
import subprocess
from datetime import datetime

def clear_screen():
    # Xóa trắng terminal để cập nhật bảng giá mới cho gọn
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    interval_minutes = 5
    interval_seconds = interval_minutes * 60
    
    # Bạn có thể đổi thành "--all" nếu muốn in TOÀN BỘ 200+ mã ra terminal.
    # Hiện tại để không bị rối mắt, nó sẽ đánh giá CẢ THỊ TRƯỜNG nhưng chỉ in TOP 15 mã ngon nhất.
    # Toàn bộ 200+ mã vẫn được lưu đầy đủ vào file Excel (data/excel_cw_report.csv).
    command = ["python", "scripts/run_cw.py", "--all"] 
    
    # Nếu muốn in hết ra màn hình thì dùng dòng này:
    # command = ["python", "scripts/run_cw.py", "--all"]

    print(f"🚀 Kích hoạt Radar Real-time: Quét thị trường mỗi {interval_minutes} phút...")
    
    try:
        while True:
            clear_screen()
            now_str = datetime.now().strftime('%H:%M:%S')
            print(f"================================================================")
            print(f" 📡 LẦN QUÉT GẦN NHẤT: {now_str} (Tự động cập nhật sau {interval_minutes} phút)")
            print(f"================================================================")
            
            # Gọi tiến trình phân tích
            subprocess.run(command)
            
            print(f"\n⏳ Đã cập nhật xong! Hệ thống đang chờ {interval_minutes} phút cho nhịp quét tiếp theo...")
            print("🛑 (Bấm Ctrl + C để thoát khỏi chế độ Radar liên tục)")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Đã tắt Radar Real-time. Hẹn gặp lại!")

if __name__ == "__main__":
    main()
