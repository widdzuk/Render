import requests
import time
import numpy as np

COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "fetch-ai": "FET"
}

def fetch_candles(coin_id, vs="usd", days=2):
    # CoinGecko market_chart: last 2 days in 2h candles
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs, "days": days, "interval": "hourly"}
    r = requests.get(url, params=params)
    data = r.json()["prices"]
    # last 48 hours hourly, group every 2 hours
    closes = [p[1] for p in data]
    # simple downsample to 2h by taking every 2nd
    closes = closes[::2]
    return closes[-50:]  # limit to last ~100h (50 points)

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
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
        up = (up*(period-1)+upval)/period
        down = (down*(period-1)+downval)/period
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1.+rs)
    return rsi

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

            # Conditions
            buy_condition = ema9[-2] < ema21[-2] and ema9[-1] > ema21[-1] and current_rsi > 40
            sell_condition = ema9[-2] > ema21[-2] and ema9[-1] < ema21[-1] and current_rsi < 60

            price = closes[-1]
            target = round(price * 1.03, 2)  # example +3%
            stop = round(price * 0.97, 2)    # example -3%

            if buy_condition:
                send_message(f"🟢 BUY SIGNAL – {symbol}\n💹 Price: {price}\n🎯 Target: {target}\n📉 Stop: {stop}\n⚙️ RSI+EMA crossover detected")
            elif sell_condition:
                send_message(f"🔴 SELL SIGNAL – {symbol}\n💹 Price: {price}\n🎯 Target: {target}\n📉 Stop: {stop}\n⚙️ RSI+EMA crossover detected")

        except Exception as e:
            print(f"Error on {symbol}: {e}")

    time.sleep(2 * 60 * 60)  # wait 2 hours
