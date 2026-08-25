# =========================================================
# GoldPro+ Scalper V3
#
# 15M Trend
# 5M EMA9 Confirmation
# 1M RSI
# 1M Candle Strength
# 1M Candlestick Pattern
#
# هدف:
# افزایش کیفیت سیگنال‌ها
# کاهش ورودهای ضعیف
# تأیید چندمرحله‌ای قبل از BUY / SELL
# =========================================================

import pandas as pd


# =========================================================
# SETTINGS
# =========================================================

EMA_FAST = 9
EMA_TREND_FAST = 9
EMA_TREND_SLOW = 20

RSI_PERIOD = 14

SIGNAL_SCORE = 75
WATCH_SCORE = 60

CANDLE_BODY_MIN = 0.45


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

        value = float(value)

        if pd.isna(value):
            return None

        return value

    except Exception:

        return None


# =========================================================
# CANDLE INFORMATION
# =========================================================

def candle_info(candle):

    open_price = safe_float(
        candle["open"]
    )

    high = safe_float(
        candle["high"]
    )

    low = safe_float(
        candle["low"]
    )

    close = safe_float(
        candle["close"]
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
            "body_ratio": 0.0,
            "upper_wick_ratio": 0.0,
            "lower_wick_ratio": 0.0,
            "range": 0.0,
        }


    candle_range = high - low

    if candle_range <= 0:

        return {
            "bullish": False,
            "bearish": False,
            "strong": False,
            "body_ratio": 0.0,
            "upper_wick_ratio": 0.0,
            "lower_wick_ratio": 0.0,
            "range": 0.0,
        }


    body = abs(
        close - open_price
    )

    upper_wick = (
        high
        - max(open_price, close)
    )

    lower_wick = (
        min(open_price, close)
        - low
    )


    body_ratio = (
        body / candle_range
    )

    upper_wick_ratio = (
        upper_wick / candle_range
    )

    lower_wick_ratio = (
        lower_wick / candle_range
    )


    return {

        "bullish":
            close > open_price,

        "bearish":
            close < open_price,

        "strong":
            body_ratio >= CANDLE_BODY_MIN,

        "body_ratio":
            body_ratio,

        "upper_wick_ratio":
            upper_wick_ratio,

        "lower_wick_ratio":
            lower_wick_ratio,

        "range":
            candle_range,
    }


# =========================================================
# BULLISH ENGULFING
# =========================================================

def bullish_engulfing(
    previous,
    current
):

    prev = candle_info(
        previous
    )

    curr = candle_info(
        current
    )


    prev_open = safe_float(
        previous["open"]
    )

    prev_close = safe_float(
        previous["close"]
    )

    curr_open = safe_float(
        current["open"]
    )

    curr_close = safe_float(
        current["close"]
    )


    if None in (
        prev_open,
        prev_close,
        curr_open,
        curr_close
    ):

        return False


    return (

        prev["bearish"]

        and curr["bullish"]

        and curr_open <= prev_close

        and curr_close >= prev_open

        and curr["body_ratio"] >= 0.50
    )


# =========================================================
# BEARISH ENGULFING
# =========================================================

def bearish_engulfing(
    previous,
    current
):

    prev = candle_info(
        previous
    )

    curr = candle_info(
        current
    )


    prev_open = safe_float(
        previous["open"]
    )

    prev_close = safe_float(
        previous["close"]
    )

    curr_open = safe_float(
        current["open"]
    )

    curr_close = safe_float(
        current["close"]
    )


    if None in (
        prev_open,
        prev_close,
        curr_open,
        curr_close
    ):

        return False


    return (

        prev["bullish"]

        and curr["bearish"]

        and curr_open >= prev_close

        and curr_close <= prev_open

        and curr["body_ratio"] >= 0.50
    )


# =========================================================
# HAMMER
# =========================================================

def hammer(candle):

    info = candle_info(
        candle
    )


    return (

        info["bullish"]

        and info["lower_wick_ratio"] >= 0.45

        and info["upper_wick_ratio"] <= 0.20

        and info["body_ratio"] >= 0.15
    )


# =========================================================
# SHOOTING STAR
# =========================================================

def shooting_star(candle):

    info = candle_info(
        candle
    )


    return (

        info["bearish"]

        and info["upper_wick_ratio"] >= 0.45

        and info["lower_wick_ratio"] <= 0.20

        and info["body_ratio"] >= 0.15
    )


# =========================================================
# BULLISH MARUBOZU
# =========================================================

def bullish_marubozu(candle):

    info = candle_info(
        candle
    )


    return (

        info["bullish"]

        and info["body_ratio"] >= 0.75

        and info["upper_wick_ratio"] <= 0.10

        and info["lower_wick_ratio"] <= 0.10
    )


# =========================================================
# BEARISH MARUBOZU
# =========================================================

def bearish_marubozu(candle):

    info = candle_info(
        candle
    )


    return (

        info["bearish"]

        and info["body_ratio"] >= 0.75

        and info["upper_wick_ratio"] <= 0.10

        and info["lower_wick_ratio"] <= 0.10
    )


# =========================================================
# CANDLE PATTERN DETECTOR
# =========================================================

def detect_candlestick_pattern(df):

    if df is None:
        return "NONE"


    if len(df) < 3:
        return "NONE"


    previous = df.iloc[-2]

    current = df.iloc[-1]


    # -----------------------------------------------------
    # ENGULFING
    # -----------------------------------------------------

    if bullish_engulfing(
        previous,
        current
    ):

        return "BULLISH_ENGULFING"


    if bearish_engulfing(
        previous,
        current
    ):

        return "BEARISH_ENGULFING"


    # -----------------------------------------------------
    # HAMMER
    # -----------------------------------------------------

    if hammer(
        current
    ):

        return "HAMMER"


    # -----------------------------------------------------
    # SHOOTING STAR
    # -----------------------------------------------------

    if shooting_star(
        current
    ):

        return "SHOOTING_STAR"


    # -----------------------------------------------------
    # MARUBOZU
    # -----------------------------------------------------

    if bullish_marubozu(
        current
    ):

        return "BULLISH_MARUBOZU"


    if bearish_marubozu(
        current
    ):

        return "BEARISH_MARUBOZU"


    return "NONE"


# =========================================================
# PATTERN DIRECTION
# =========================================================

def pattern_direction(pattern):

    bullish_patterns = {

        "BULLISH_ENGULFING",

        "HAMMER",

        "BULLISH_MARUBOZU",
    }


    bearish_patterns = {

        "BEARISH_ENGULFING",

        "SHOOTING_STAR",

        "BEARISH_MARUBOZU",
    }


    if pattern in bullish_patterns:

        return "BUY"


    if pattern in bearish_patterns:

        return "SELL"


    return "NONE"


# =========================================================
# 15M TREND
# =========================================================

def get_trend(df15):

    if df15 is None:

        return "NONE"


    if df15.empty:

        return "NONE"


    if len(df15) < 20:

        return "NONE"


    df = df15.copy()


    df["ema9"] = calculate_ema(
        df["close"],
        EMA_TREND_FAST
    )


    df["ema20"] = calculate_ema(
        df["close"],
        EMA_TREND_SLOW
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
    # BUY TREND
    # =====================================================

    if (

        price > ema9

        and ema9 > ema20
    ):

        return "BUY"


    # =====================================================
    # SELL TREND
    # =====================================================

    if (

        price < ema9

        and ema9 < ema20
    ):

        return "SELL"


    return "NONE"


# =========================================================
# 5M EMA CONFIRMATION
# =========================================================

def check_5m_ema(
    df5,
    trend
):

    if df5 is None:

        return False


    if df5.empty:

        return False


    if len(df5) < EMA_FAST:

        return False


    if trend not in (
        "BUY",
        "SELL"
    ):

        return False


    df = df5.copy()


    df["ema9"] = calculate_ema(
        df["close"],
        EMA_FAST
    )


    last = df.iloc[-1]


    price = safe_float(
        last["close"]
    )

    ema9 = safe_float(
        last["ema9"]
    )


    if None in (
        price,
        ema9
    ):

        return False


    if trend == "BUY":

        return price >= ema9


    if trend == "SELL":

        return price <= ema9


    return False


# =========================================================
# 1M RSI
# =========================================================

def check_rsi(
    df1,
    trend
):

    if df1 is None:

        return False, None


    if df1.empty:

        return False, None


    if len(df1) < RSI_PERIOD + 2:

        return False, None


    if trend not in (
        "BUY",
        "SELL"
    ):

        return False, None


    df = df1.copy()


    df["rsi"] = calculate_rsi(
        df["close"],
        RSI_PERIOD
    )


    current = df.iloc[-1]

    previous = df.iloc[-2]


    rsi = safe_float(
        current["rsi"]
    )

    previous_rsi = safe_float(
        previous["rsi"]
    )


    if None in (
        rsi,
        previous_rsi
    ):

        return False, rsi


    # =====================================================
    # BUY RSI
    # =====================================================

    if trend == "BUY":

        bullish_zone = (

            50 <= rsi <= 68
        )


        bullish_reversal = (

            previous_rsi <= 50

            and rsi > previous_rsi
        )


        return (

            bullish_zone

            or bullish_reversal,

            rsi
        )


    # =====================================================
    # SELL RSI
    # =====================================================

    if trend == "SELL":

        bearish_zone = (

            32 <= rsi <= 50
        )


        bearish_reversal = (

            previous_rsi >= 50

            and rsi < previous_rsi
        )


        return (

            bearish_zone

            or bearish_reversal,

            rsi
        )


    return False, rsi


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
    # DATA CHECK
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

            "pattern":
                "NONE",

            "reasons":
                [
                    "Insufficient market data"
                ],
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

            "pattern":
                "NONE",

            "reasons":
                [
                    "Empty market data"
                ],
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


    else:

        reasons.append(
            f"OK: 15M trend ({trend})"
        )


    # =====================================================
    # PRICE
    # =====================================================

    last1 = df1.iloc[-1]


    price = safe_float(
        last1["close"]
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
    # TREND NONE
    # =====================================================

    if trend == "NONE":

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
                atr,

            "pattern":
                "NONE",

            "reasons":
                reasons,
        }


    # =====================================================
    # SCORE
    #
    # Maximum = 100
    #
    # 15M trend       = 30
    # 5M EMA          = 20
    # 1M RSI          = 20
    # Candle strength = 10
    # Pattern         = 20
    # =====================================================

    score = 30


    # =====================================================
    # 5M EMA
    # =====================================================

    ema_ok = check_5m_ema(
        df5,
        trend
    )


    if ema_ok:

        score += 20

        reasons.append(
            "OK: 5M EMA9"
        )

    else:

        reasons.append(
            "WAIT: 5M EMA9"
        )


    # =====================================================
    # 1M RSI
    # =====================================================

    rsi_ok, rsi = check_rsi(
        df1,
        trend
    )


    if rsi_ok:

        score += 20

        reasons.append(
            "OK: 1M RSI"
        )

    else:

        reasons.append(
            "WAIT: 1M RSI"
        )


    # =====================================================
    # 1M CANDLE STRENGTH
    # =====================================================

    candle = candle_info(
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

        score += 10

        reasons.append(
            "OK: strong 1M candle"
        )

    else:

        reasons.append(
            "WAIT: candle"
        )


    # =====================================================
    # CANDLE PATTERN
    # =====================================================

    pattern = detect_candlestick_pattern(
        df1
    )


    pattern_side = pattern_direction(
        pattern
    )


    # -----------------------------------------------------
    # Pattern matches trend
    # -----------------------------------------------------

    if (

        pattern != "NONE"

        and pattern_side == trend
    ):

        score += 20

        reasons.append(
            f"OK: {pattern}"
        )


    # -----------------------------------------------------
    # Pattern opposite trend
    # -----------------------------------------------------

    elif (

        pattern != "NONE"

        and pattern_side != trend
    ):

        reasons.append(
            f"WAIT: opposite pattern ({pattern})"
        )


    else:

        reasons.append(
            "WAIT: candlestick pattern"
        )


    # =====================================================
    # CONFIDENCE
    # =====================================================

    confidence = min(
        score,
        100
    )


    # =====================================================
    # SIGNAL
    # =====================================================

    signal = "NO SIGNAL"


    if (

        trend == "BUY"

        and score >= SIGNAL_SCORE
    ):

        signal = "BUY"


    elif (

        trend == "SELL"

        and score >= SIGNAL_SCORE
    ):

        signal = "SELL"


    # =====================================================
    # QUALITY
    # =====================================================

    if score >= 90:

        quality = "VERY STRONG"

    elif score >= 75:

        quality = "STRONG"

    elif score >= 60:

        quality = "NORMAL"

    else:

        quality = "WEAK"


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

        "pattern":
            pattern,

        