import pandas as pd

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))

def trend_catcher_signal(df, rsi_buy=50, rsi_sell=50):
    """
    استراتژی روندی با قابلیت تنظیم RSI
    """
    if df is None or len(df) < 60:
        return {
            "signal": "NO SIGNAL",
            "price": None,
            "score": 0,
            "quality": "WEAK",
            "reasons": ["داده کافی نیست"]
        }

    close = df['close']
    ema20 = calculate_ema(close, 20)
    ema50 = calculate_ema(close, 50)
    rsi = calculate_rsi(close, 14)

    last = df.iloc[-1]
    price = float(last['close'])
    prev = df.iloc[-2]

    bullish_trend = price > ema20.iloc[-1] > ema50.iloc[-1]
    bearish_trend = price < ema20.iloc[-1] < ema50.iloc[-1]
    rsi_val = float(rsi.iloc[-1])

    # سیگنال خرید
    if bullish_trend and rsi_val < rsi_buy and last['close'] > last['open']:
        score = 65
        if rsi_val < 40:
            score += 10
        if last['close'] > prev['close'] * 1.001:
            score += 10
        if price > ema20.iloc[-1] * 1.002:
            score += 5
        return {
            "signal": "BUY",
            "price": price,
            "score": min(score, 100),
            "quality": "STRONG" if score >= 80 else "NORMAL",
            "reasons": [
                f"روند صعودی (EMA20>EMA50)",
                f"RSI={rsi_val:.1f} (زیر {rsi_buy})",
                "کندل صعودی"
            ]
        }

    # سیگنال فروش
    if bearish_trend and rsi_val > rsi_sell and last['close'] < last['open']:
        score = 65
        if rsi_val > 60:
            score += 10
        if last['close'] < prev['close'] * 0.999:
            score += 10
        if price < ema20.iloc[-1] * 0.998:
            score += 5
        return {
            "signal": "SELL",
            "price": price,
            "score": min(score, 100),
            "quality": "STRONG" if score >= 80 else "NORMAL",
            "reasons": [
                f"روند نزولی (EMA20<EMA50)",
                f"RSI={rsi_val:.1f} (بالای {rsi_sell})",
                "کندل نزولی"
            ]
        }

    return {
        "signal": "NO SIGNAL",
        "price": price,
        "score": 0,
        "quality": "WEAK",
        "reasons": ["شرایط روند یا RSI برقرار نیست"]
    }