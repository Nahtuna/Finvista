# -*- coding: utf-8 -*-
"""
🎯 FINVISTA: TELEGRAM CHAT ID AUTO-DETECTOR
======================================================
Listens to Telegram updates to auto-discover your personal Chat ID,
writes it into data/telegram_config.json, and activates alerts automatically.

Author: samvo
"""

import sys
import os
import json
import time
import requests

# Force UTF-8 for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CONFIG_PATH = os.path.join("data", "telegram_config.json")

def main():
    print("=" * 70)
    print(" 🎯 FINVISTA CHAT ID AUTOMATIC DETECTOR")
    print("=" * 70)
    
    if not os.path.exists(CONFIG_PATH):
        print("❌ Configuration file data/telegram_config.json not found.")
        return
        
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    token = config.get("telegram_bot_token", "").strip()
    if not token or "YOUR_TELEGRAM" in token:
        print("❌ Bot Token is missing in telegram_config.json.")
        return
        
    print(f"🤖 Bot Token detected: {token[:15]}...{token[-10:]}")
    print("\n👉 BƯỚC CẦN LÀM:")
    print("   1. Mở Telegram trên điện thoại/máy tính của bạn.")
    print("   2. Truy cập link bot: https://t.me/Finvista_bot")
    print("   3. Nhấn nút [START] (hoặc gõ bất kỳ tin nhắn nào như 'hello' và gửi đi).")
    print("\n📡 Đang lắng nghe phản hồi từ Telegram API (Nhấn Ctrl+C để hủy)...")
    
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    offset = 0
    detected = False
    
    start_time = time.time()
    while not detected:
        # Check timeout after 5 minutes
        if time.time() - start_time > 300:
            print("\n⏰ Quá thời gian chờ (5 phút). Hãy đảm bảo bạn đã nhấn START trên bot và thử lại.")
            break
            
        try:
            resp = requests.get(url, params={"offset": offset, "timeout": 5}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("result", [])
                for update in results:
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if message:
                        chat = message.get("chat")
                        from_user = message.get("from", {})
                        if chat:
                            chat_id = chat.get("id")
                            first_name = from_user.get("first_name", "User")
                            username = from_user.get("username", "")
                            
                            print(f"\n🎉 PHÁT HIỆN THÀNH CÔNG THÔNG TIN:")
                            print(f"   - Tên người dùng: {first_name} (@{username})")
                            print(f"   - Telegram Chat ID: {chat_id}")
                            
                            # Write back to config and enable alerts
                            config["telegram_chat_id"] = str(chat_id)
                            config["enable_alerts"] = True
                            
                            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                json.dump(config, f, indent=4, ensure_ascii=False)
                                
                            print(f"\n💾 Đã lưu cấu hình Chat ID và bật alerts tự động vào {CONFIG_PATH}!")
                            print("🚀 Hệ thống Finvista đã sẵn sàng hoạt động với Telegram Alerts 100%!")
                            detected = True
                            break
            else:
                print(f"⚠️ Telegram API returned error: {resp.status_code}")
        except Exception as e:
            pass
            
        if not detected:
            print(".", end="", flush=True)
            time.sleep(1.5)

if __name__ == "__main__":
    main()
