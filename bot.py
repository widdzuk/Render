import time
import requests
import os

# === CONFIG ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # Your Telegram numeric chat ID

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, data=payload)
    print(r.text)

# === MAIN LOOP ===
send_message("✅ Bot started! You’ll get signals every 2 hours.")
while True:
    # Example signal — replace with real strategy later
    send_message("🧪 TEST SIGNAL – ETH\n🎯 Target: $3,050\n📉 Stop: $2,890")
    time.sleep(2 * 60 * 60)  # wait 2 hours