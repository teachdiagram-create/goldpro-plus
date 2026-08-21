import pandas as pd

from indicators import add_indicators


# =========================================================
# GoldPro+ Scalper V1
#
# 15M Trend
# 5M Confirmation
# 1M Entry
# =========================================================


MIN_SCORE = 70


# =========================================================
# HELPERS
# =========================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except:
        return default


def prepare(df):

    if df is None or df.empty:
        return None

    try:
        return add_indicators(df.copy())
    except Exception as e:
        print("Indicator error:", e)
        return None


def last(df):
    return df.iloc[-1]


# =========================================================
# 15M TREND
# =========================================================

def trend_15m(df):

    candle = last(df)

    ema20 = safe_float(
        candle.get("EMA20")
    )

    ema50 = safe_float(
        candle.get("EMA50")
    )

    if ema20 > ema50:
        return "BUY"

    if ema20 < ema50:
        return "SELL"

    return "NONE"


# =========================================================
# 5M EMA9 CONFIRMATION
# =========================================================

def ema9_confirmation(df5, direction):

    candle = last(df5)

    price = safe_float(
        candle.get("close")
    )

    ema9 = safe_float(
        candle.get("EMA9")
    )

    if direction == "BUY":
        return price > ema9

    if direction == "SELL":
        return price < ema9

    return False


# =========================================================
# RSI REVERSAL
# =========================================================

def rsi_entry(df1, direction):

    if len(df1) < 3:
        return False

    rsi_now = safe_float(
        df1.iloc[-1].get("RSI")
    )

    rsi_prev = safe_float(
        df1.iloc[-2].get("RSI")
    )


    if direction == "BUY":

        return (
            rsi_prev < 35
            and rsi_now > rsi_prev
        )


    if direction == "SELL":

        return (
            rsi_prev > 65
            and rsi_now < rsi_prev
        )


    return False


# =========================================================
# STRONG CANDLE
# =========================================================

def strong_candle(df1, direction):

    candle = last(df1)

    open_price = safe_float(
        candle.get("open")
    )

    close = safe_float(
        candle.get("close")
    )

    high = safe_float(
        candle.get("high")
    )

    low = safe_float(
        candle.get("low")
    )


    total = high - low

    if total <= 0:
        return False


    body = abs(
        close - open_price
    )

    ratio = body / total


    if ratio < 0.55:
        return False


    if direction == "BUY":
        return close > open_price


    if direction == "SELL":
        return close < open_price


    return False


# =========================================================
# MAIN SIGNAL
# =========================================================

def generate_scalper_signal(
    df15,
    df5,
    df1
):

    df15 = prepare(df15)
    df5 = prepare(df5)
    df1 = prepare(df1)


    if (
        df15 is None
        or df5 is None
        or df1 is None
    ):

        return {
            "signal": "NO SIGNAL",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "No data"
            ]
        }


    direction = trend_15m(df15)

    candle = last(df1)

    price = safe_float(
        candle.get("close")
    )


    score = 0

    reasons = []


    # Trend 15M
    if direction != "NONE":

        score += 35

        reasons.append(
            "OK: 15M trend"
        )

    else:

        reasons.append(
            "WAIT: 15M trend"
        )


    # 5M EMA9

    if ema9_confirmation(
        df5,
        direction
    ):

        score += 25

        reasons.append(
            "OK: 5M EMA9"
        )

    else:

        reasons.append(
            "WAIT: 5M EMA9"
        )


    # RSI

    if rsi_entry(
        df1,
        direction
    ):

        score += 25

        reasons.append(
            "OK: 1M RSI reversal"
        )

    else:

        reasons.append(
            "WAIT: 1M RSI"
        )


    # Candle

    if strong_candle(
        df1,
        direction
    ):

        score += 15

        reasons.append(
            "OK: strong 1M candle"
        )

    else:

        reasons.append(
            "WAIT: candle"
        )


    signal = "NO SIGNAL"


    if (
        score >= MIN_SCORE
        and direction in [
            "BUY",
            "SELL"
        ]
    ):

        signal = direction


    return {

        "signal": signal,

        "price": price,

        "score": score,

        "confidence": score,

        "quality":
            "STRONG"
            if score >= 85
            else "NORMAL"
            if score >= 70
            else "WEAK",

        "trend": direction,

        "rsi": safe_float(
            candle.get("RSI")
        ),

        "atr": safe_float(
            candle.get("ATR")
        ),

        "reasons": reasons,

        "time": str(
            candle.get("time")
        )
    }
