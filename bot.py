import time
import requests
import os
import numpy as np

# === CONFIG ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # your Telegram numeric ID

# === TELEGRAM MESSAGE ===
def send_message(text: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=payload)
        print("Sent message:", r.text)
    except Exception as e:
        print("Error sending message:", e)

# === MARKET DATA (CoinGecko) ===
def fetch_candles(coin_id, vs="usd", days=2):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs, "days": days, "interval": "hourly"}
    r = requests.get(url, params=params)
    data = r.json().get("prices", [])
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
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    rs = up/down if down != 0 else 0
    rsi_arr = np.zeros_like(values)
    rsi_arr[:period] = 100. - 100./(1.+rs)
    for i in range(period, len(values)):
        delta = deltas[i-1]
        upval = delta if delta > 0 else 0.
        downval = -delta if delta < 0 else 0.
        up = (up*(period-1)+upval)/period
        down = (down*(period-1)+downval)/period
        rs = up/down if down != 0 else 0
        rsi_arr[i] = 100. - 100./(1.+rs)
    return rsi_arr

# === NEWS SENTIMENT (FinancialModelingPrep) ===
FMP_NEWS_URL = "https://financialmodelingprep.com/api/v4/crypto_news"
POSITIVE = ["surge", "partnership", "record", "adoption", "upgrade", "bullish"]
NEGATIVE = ["hack", "ban", "lawsuit", "scam", "bearish", "down"]

def fetch_news_sentiment():
    try:
        r = requests.get(FMP_NEWS_URL)
        headlines = [item.get("title", "").lower() for item in r.json()[:20]]
        score = 0
        for h in headlines:
            if any(p in h for p in POSITIVE):
                score += 1
            if any(n in h for n in NEGATIVE):
                score -= 1
        return score
    except Exception as e:
        print("News error:", e)
        return 0

# === COINS ===
COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "fetch-ai": "FET"
}

# === MAIN LOOP ===
send_message("✅ Bot started with RSI+EMA & News Sentiment. Scanning every 2 hours...")

while True:
    sentiment_score = fetch_news_sentiment()
    for cg_id, symbol in COINS.items():
        try:
            closes = fetch_candles(cg_id)
            if len(closes) < 22:
                continue

            # RSI + EMA crossover
            ema9 = ema(closes, 9)
            ema21 = ema(closes, 21)
            current_rsi = rsi(closes)[-1]

            price = closes[-1]
            target = round(price * 1.03, 2)
            stop = round(price * 0.97, 2)

            buy_condition = ema9[-2] < ema21[-2] and ema9[-1] > ema21[-1] and current_rsi > 40
            sell_condition = ema9[-2] > ema21[-2] and ema9[-1] < ema21[-1] and current_rsi < 60

            if buy_condition:
                send_message(f"🟢 BUY SIGNAL – {symbol}\n⚙️ RSI+EMA crossover\n💹 Price: {price}\n🎯 Target: {target}\n📉 Stop: {stop}")
            if sell_condition:
                send_message(f"🔴 SELL SIGNAL – {symbol}\n⚙️ RSI+EMA crossover\n💹 Price: {price}\n🎯 Target: {target}\n📉 Stop: {stop}")

            # News Sentiment strategy
            if sentiment_score >= 3 and price > closes[-4] * 1.02:
                send_message(f"🟢 BUY SIGNAL – {symbol} (NEWS)\n📰 Positive sentiment\nScore: {sentiment_score}\n💹 Price: {price}\n🎯 Target: {target}")
            if sentiment_score <= -3 and price < closes[-4] * 0.97:
                send_message(f"🔴 SELL SIGNAL – {symbol} (NEWS)\n📰 Negative sentiment\nScore: {sentiment_score}\n💹 Price: {price}")

        except Exception as e:
            print(f"Error on {symbol}: {e}")

    time.sleep(2 * 60 * 60)  # wait 2 hours between scans