# =========================================================
# GoldPro+ Scalper V3
#
# 15M Trend
# 5M EMA9 + EMA20 Confirmation
# 1M RSI + Candle Trigger
#
# هدف:
# کاهش سیگنال‌های ضعیف
# جلوگیری از ورود خلاف تأیید 5M
# جلوگیری از ورود دیرهنگام
# =========================================================

import pandas as pd


# =========================================================
# SETTINGS
# =========================================================

EMA_FAST = 9
EMA_SLOW = 20

RSI_PERIOD = 14

SIGNAL_SCORE = 80
WATCH_SCORE = 65

RSI_BUY_MIN = 52
RSI_BUY_MAX = 68

RSI_SELL_MIN = 32
RSI_SELL_MAX = 48

CANDLE_BODY_MIN = 0.55

# حداکثر فاصله مجاز قیمت از EMA9
# برای جلوگیری از ورود بعد از حرکت شدید
MAX_EMA_DISTANCE = 0.35


# =========================================================
# EMA
# =========================================================

def calculate_ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# RSI
# =========================================================

def calculate_rsi(
    series,
    period=RSI_PERIOD
):

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        pd.NA
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


# =========================================================
# SAFE FLOAT
# =========================================================

def safe_float(value):

    try:

        if pd.isna(value):
            return None

        return float(value)

    except Exception:

        return None


# =========================================================
# CANDLE STRENGTH
# =========================================================

def candle_strength(candle):

    open_price = safe_float(
        candle.get("open")
    )

    high = safe_float(
        candle.get("high")
    )

    low = safe_float(
        candle.get("low")
    )

    close = safe_float(
        candle.get("close")
    )

    if None in (
        open_price,
        high,
        low,
        close
    ):

        return {
            "bullish": False,
            "bearish": False,
            "strong": False,
            "body_ratio": 0,
            "range": 0
        }

    candle_range = high - low

    if candle_range <= 0:

        return {
            "bullish": False,
            "bearish": False,
            "strong": False,
            "body_ratio": 0,
            "range": 0
        }

    body = abs(
        close - open_price
    )

    body_ratio = (
        body / candle_range
    )

    bullish = (
        close > open_price
    )

    bearish = (
        close < open_price
    )

    strong = (
        body_ratio >= CANDLE_BODY_MIN
    )

    return {

        "bullish":
            bullish,

        "bearish":
            bearish,

        "strong":
            strong,

        "body_ratio":
            body_ratio,

        "range":
            candle_range
    }


# =========================================================
# 15M TREND
# =========================================================

def get_trend(df15):

    if df15 is None:
        return "NONE"

    if df15.empty:
        return "NONE"

    if len(df15) < 30:
        return "NONE"

    df = df15.copy()

    df["ema9"] = calculate_ema(
        df["close"],
        EMA_FAST
    )

    df["ema20"] = calculate_ema(
        df["close"],
        EMA_SLOW
    )

    last = df.iloc[-1]

    price = safe_float(
        last["close"]
    )

    ema9 = safe_float(
        last["ema9"]
    )

    ema20 = safe_float(
        last["ema20"]
    )

    if None in (
        price,
        ema9,
        ema20
    ):

        return "NONE"

    # =====================================================
    # BUY
    # =====================================================

    if (
        price > ema9
        and ema9 > ema20
    ):

        return "BUY"

    # =====================================================
    # SELL
    # =====================================================

    if (
        price < ema9
        and ema9 < ema20
    ):

        return "SELL"

    return "NONE"


# =========================================================
# 5M CONFIRMATION
# =========================================================

def check_5m_confirmation(
    df5,
    trend
):

    result = {

        "ok":
            False,

        "ema9":
            None,

        "ema20":
            None,

        "price":
            None,

        "distance":
            None,

        "reason":
            "WAIT: 5M confirmation"
    }

    if df5 is None:
        return result

    if df5.empty:
        return result

    if len(df5) < 30:
        return result

    df = df5.copy()

    df["ema9"] = calculate_ema(
        df["close"],
        EMA_FAST
    )

    df["ema20"] = calculate_ema(
        df["close"],
        EMA_SLOW
    )

    last = df.iloc[-1]

    price = safe_float(
        last["close"]
    )

    ema9 = safe_float(
        last["ema9"]
    )

    ema20 = safe_float(
        last["ema20"]
    )

    if None in (
        price,
        ema9,
        ema20
    ):

        return result

    result["price"] = price
    result["ema9"] = ema9
    result["ema20"] = ema20

    distance = abs(
        price - ema9
    )

    result["distance"] = distance

    # =====================================================
    # BUY
    # =====================================================

    if trend == "BUY":

        if price <= ema9:

            result["reason"] = (
                "WAIT: 5M price below EMA9"
            )

            return result

        if ema9 <= ema20:

            result["reason"] = (
                "WAIT: 5M EMA9 below EMA20"
            )

            return result

        result["ok"] = True

        result["reason"] = (
            "OK: 5M bullish confirmation"
        )

        return result

    # =====================================================
    # SELL
    # =====================================================

    if trend == "SELL":

        if price >= ema9:

            result["reason"] = (
                "WAIT: 5M price above EMA9"
            )

            return result

        if ema9 >= ema20:

            result["reason"] = (
                "WAIT: 5M EMA9 above EMA20"
            )

            return result

        result["ok"] = True

        result["reason"] = (
            "OK: 5M bearish confirmation"
        )

        return result

    return result


# =========================================================
# 1M RSI
# =========================================================

def check_rsi(
    df1,
    trend
):

    if df1 is None:
        return False, None, "WAIT: 1M RSI"

    if df1.empty:
        return False, None, "WAIT: 1M RSI"

    if len(df1) < RSI_PERIOD + 5:

        return (
            False,
            None,
            "WAIT: insufficient RSI data"
        )

    df = df1.copy()

    df["rsi"] = calculate_rsi(
        df["close"],
        RSI_PERIOD
    )

    current = safe_float(
        df.iloc[-1]["rsi"]
    )

    previous = safe_float(
        df.iloc[-2]["rsi"]
    )

    if (
        current is None
        or previous is None
    ):

        return (
            False,
            current,
            "WAIT: invalid RSI"
        )

    # =====================================================
    # BUY
    # =====================================================

    if trend == "BUY":

        bullish_zone = (
            RSI_BUY_MIN
            <= current
            <= RSI_BUY_MAX
        )

        bullish_recovery = (
            previous < RSI_BUY_MIN
            and current >= RSI_BUY_MIN
        )

        if (
            bullish_zone
            or bullish_recovery
        ):

            return (
                True,
                current,
                "OK: 1M RSI"
            )

        return (
            False,
            current,
            "WAIT: 1M RSI"
        )

    # =====================================================
    # SELL
    # =====================================================

    if trend == "SELL":

        bearish_zone = (
            RSI_SELL_MIN
            <= current
            <= RSI_SELL_MAX
        )

        bearish_recovery = (
            previous > RSI_SELL_MAX
            and current <= RSI_SELL_MAX
        )

        if (
            bearish_zone
            or bearish_recovery
        ):

            return (
                True,
                current,
                "OK: 1M RSI"
            )

        return (
            False,
            current,
            "WAIT: 1M RSI"
        )

    return (
        False,
        current,
        "WAIT: 1M RSI"
    )


# =========================================================
# EMA DISTANCE FILTER
# =========================================================

def check_ema_distance(
    df5,
    price
):

    if df5 is None:
        return False

    if df5.empty:
        return False

    if len(df5) < EMA_FAST:
        return False

    df = df5.copy()

    df["ema9"] = calculate_ema(
        df["close"],
        EMA_FAST
    )

    ema9 = safe_float(
        df.iloc[-1]["ema9"]
    )

    if ema9 is None:
        return False

    distance = abs(
        price - ema9
    )

    # بدون ATR از درصد قیمت استفاده می‌کنیم
    max_distance = (
        price * 0.0015
    )

    return (
        distance <= max_distance
    )


# =========================================================
# MAIN SIGNAL
# =========================================================

def generate_scalper_signal(
    df15,
    df5,
    df1
):

    reasons = []

    # =====================================================
    # BASIC CHECK
    # =====================================================

    if (
        df15 is None
        or df5 is None
        or df1 is None
    ):

        return {

            "signal":
                "NO SIGNAL",

            "price":
                None,

            "score":
                0,

            "confidence":
                0,

            "quality":
                "WEAK",

            "trend":
                "NONE",

            "rsi":
                None,

            "atr":
                None,

            "reasons":
                ["Insufficient market data"]
        }

    if (
        df15.empty
        or df5.empty
        or df1.empty
    ):

        return {

            "signal":
                "NO SIGNAL",

            "price":
                None,

            "score":
                0,

            "confidence":
                0,

            "quality":
                "WEAK",

            "trend":
                "NONE",

            "rsi":
                None,

            "atr":
                None,

            "reasons":
                ["Empty market data"]
        }

    # =====================================================
    # PRICE
    # =====================================================

    last1 = df1.iloc[-1]

    price = safe_float(
        last1["close"]
    )

    if price is None:

        return {

            "signal":
                "NO SIGNAL",

            "price":
                None,

            "score":
                0,

            "confidence":
                0,

            "quality":
                "WEAK",

            "trend":
                "NONE",

            "rsi":
                None,

            "atr":
                None,

            "reasons":
                ["Invalid price"]
        }

    # =====================================================
    # 15M TREND
    # =====================================================

    trend = get_trend(
        df15
    )

    if trend == "NONE":

        reasons.append(
            "WAIT: 15M trend"
        )

        return {

            "signal":
                "NO SIGNAL",

            "price":
                price,

            "score":
                0,

            "confidence":
                0,

            "quality":
                "WEAK",

            "trend":
                "NONE",

            "rsi":
                None,

            "atr":
                None,

            "reasons":
                reasons
        }

    reasons.append(
        f"OK: 15M trend ({trend})"
    )

    # =====================================================
    # SCORE
    # =====================================================

    score = 30

    # =====================================================
    # 5M CONFIRMATION
    # =====================================================

    confirmation = check_5m_confirmation(
        df5,
        trend
    )

    if confirmation["ok"]:

        score += 25

        reasons.append(
            confirmation["reason"]
        )

    else:

        reasons.append(
            confirmation["reason"]
        )

    # =====================================================
    # 1M RSI
    # =====================================================

    rsi_ok, rsi, rsi_reason = check_rsi(
        df1,
        trend
    )

    if rsi_ok:

        score += 20

    reasons.append(
        rsi_reason
    )

    # =====================================================
    # 1M CANDLE
    # =====================================================

    candle = candle_strength(
        last1
    )

    candle_ok = False

    if trend == "BUY":

        candle_ok = (
            candle["bullish"]
            and candle["strong"]
        )

    elif trend == "SELL":

        candle_ok = (
            candle["bearish"]
            and candle["strong"]
        )

    if candle_ok:

        score += 15

        reasons.append(
            "OK: strong 1M candle"
        )

    else:

        reasons.append(
            "WAIT: candle"
        )

    # =====================================================
    # ATR
    # =====================================================

    atr = None

    if "atr" in df1.columns:

        atr = safe_float(
            last1["atr"]
        )

    # =====================================================
    # QUALITY
    # =====================================================

    if score >= 90:

        quality = "VERY STRONG"

    elif score >= 80:

        quality = "STRONG"

    elif score >= 65:

        quality = "NORMAL"

    else:

        quality = "WEAK"

    # =====================================================
    # SIGNAL
    #
    # مهم:
    # امتیاز به تنهایی کافی نیست.
    # 5M confirmation اجباری است.
    # =====================================================

    signal = "NO SIGNAL"

    if (
        trend == "BUY"
        and confirmation["ok"]
        and rsi_ok
        and candle_ok
        and score >= SIGNAL_SCORE
    ):

        signal = "BUY"

    elif (
        trend == "SELL"
        and confirmation["ok"]
        and rsi_ok
        and candle_ok
        and score >= SIGNAL_SCORE
    ):

        signal = "SELL"

    # =====================================================
    # EXTRA SAFETY
    #
    # جلوگیری از ورود وقتی قیمت خیلی از EMA9 فاصله دارد
    # =====================================================

    if signal in (
        "BUY",
        "SELL"
    ):

        distance_ok = check_ema_distance(
            df5,
            price
        )

        if not distance_ok:

            signal = "NO SIGNAL"

            reasons.append(
                "BLOCK: price too far from 5M EMA9"
            )

        else:

            reasons.append(
                "OK: EMA9 entry distance"
            )

    # =====================================================
    # WATCH
    # =====================================================

    if (
        signal == "NO SIGNAL"
        and score >= WATCH_SCORE
    ):

        reasons.append(
            "WATCH: setup developing"
        )

    # =====================================================
    # CONFIDENCE
    # =====================================================

    confidence = score

    # =====================================================
    # RESULT
    # =====================================================

    return {

        "signal":
            signal,

        "price":
            price,

        "score":
            score,

        "confidence":
            confidence,

        "quality":
            quality,

        "trend":
            trend,

        "rsi":
            rsi,

        "atr":
            atr,

        "reasons":
            reasons,

        "time":
            str(
                last1.get(
                    "time",
                    ""
                )
            )
    }