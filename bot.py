import time
import requests
import os
import numpy as np

# === CONFIG ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # Your Telegram numeric chat ID

def send_message(text: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=payload)
        print("Sent message:", r.text)
    except Exception as e:
        print("Error sending message:", e)

# === Indicator functions ===
def fetch_candles(coin_id, vs="usd", days=2):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs, "days": days, "interval": "hourly"}
    r = requests.get(url, params=params)
    data = r.json()["prices"]
    closes = [p[1] for p in data]
    closes = closes[::2]  # downsample to 2h
    return closes[-50:]

def ema(values, period):
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    a = np.convolve(values, weights, mode='full')[:len(values)]
    a[:period] = a[period]
    return a

def rsi(values, period=14):
    deltas = np.diff(values)
    seed = deltas[:period+1]
    up = seed[seed>=0].sum()/period
    down = -seed[seed<0].sum()/period
    rs = up/down if down != 0 else 0
    rsi = np.zeros_like(values)
    rsi[:period] = 100. - 100./(1.+rs)
    for i in range(period, len(values)):
        delta = deltas[i-1]
        upval = delta if delta > 0 else 0.
        downval = -delta if delta < 0 else 0.
        up = (up*(period-1)+upval)/period
        down = (down*(period-1)+downval)/period
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1.+rs)
    return rsi

# === Coins to monitor ===
COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "fetch-ai": "FET"
}

# === MAIN LOOP ===
send_message("✅ Bot started with RSI+EMA logic. Scanning every 2 hours...")

while True:
    for cg_id, symbol in COINS.items():
        try:
            closes = fetch_candles(cg_id)
            if len(closes) < 22:
                continue
            ema9 = ema(closes, 9)
            ema21 = ema(closes, 21)
            current_rsi = rsi(closes)[-1]

            buy_condition = ema9[-2] < ema21[-2] and ema9[-1] > ema21[-1] and current_rsi > 40
            sell_condition = ema9[-2] > ema21[-2] and ema9[-1] < ema21[-1] and current_rsi < 60

            price = closes[-1]
            target = round(price * 1.03, 2)
            stop = round(price * 0.97, 2)

            if buy_condition:
                send_message(f"🟢 BUY SIGNAL – {symbol}\n💹 Price: {price}\n🎯 Target: {target}\n📉 Stop: {stop}\n⚙️ RSI+EMA crossover detected")
            elif sell_condition:
                send_message(f"🔴 SELL SIGNAL – {symbol}\n💹 Price: {price}\n🎯 Target: {target}\n📉 Stop: {stop}\n⚙️ RSI+EMA crossover detected")

        except Exception as e:
            print(f"Error on {symbol}: {e}")

    time.sleep(60)  # wait 1 minute
