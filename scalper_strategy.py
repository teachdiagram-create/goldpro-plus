# =========================================================
# GoldPro+ Scalper V2
#
# 15M Trend
# 5M EMA9 Confirmation
# 1M RSI + Candle Entry
#
# هدف:
# افزایش تعداد فرصت‌های اسکالپینگ
# بدون حذف فیلتر روند
# =========================================================

import pandas as pd


# =========================================================
# SETTINGS
# =========================================================

EMA_PERIOD = 9
RSI_PERIOD = 14

SIGNAL_SCORE = 70
WATCH_SCORE = 60

RSI_BUY_ZONE = 50
RSI_SELL_ZONE = 50

CANDLE_BODY_MIN = 0.45


# =========================================================
# EMA
# =========================================================

def calculate_ema(series, period=EMA_PERIOD):

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
# CANDLE STRENGTH
# =========================================================

def candle_strength(candle):

    open_price = float(
        candle["open"]
    )

    high = float(
        candle["high"]
    )

    low = float(
        candle["low"]
    )

    close = float(
        candle["close"]
    )

    candle_range = high - low

    if candle_range <= 0:

        return {
            "bullish": False,
            "bearish": False,
            "strong": False,
            "body_ratio": 0,
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
    }


# =========================================================
# TREND DETECTION
# =========================================================

def get_trend(df15):

    if df15 is None:
        return "NONE"

    if len(df15) < 20:
        return "NONE"


    df = df15.copy()


    df["ema9"] = calculate_ema(
        df["close"],
        9
    )


    df["ema20"] = calculate_ema(
        df["close"],
        20
    )


    last = df.iloc[-1]


    price = float(
        last["close"]
    )

    ema9 = float(
        last["ema9"]
    )

    ema20 = float(
        last["ema20"]
    )


    # -----------------------------------------------------
    # BULLISH
    # -----------------------------------------------------

    if (
        price > ema9
        and ema9 > ema20
    ):

        return "BUY"


    # -----------------------------------------------------
    # BEARISH
    # -----------------------------------------------------

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

    if len(df5) < EMA_PERIOD:
        return False


    df = df5.copy()


    df["ema9"] = calculate_ema(
        df["close"],
        EMA_PERIOD
    )


    last = df.iloc[-1]

    price = float(
        last["close"]
    )

    ema9 = float(
        last["ema9"]
    )


    # =====================================================
    # BUY
    # =====================================================

    if trend == "BUY":

        # قیمت بالای EMA9
        if price >= ema9:
            return True

        # یا فاصله بسیار کم باشد
        distance = abs(
            price - ema9
        )

        atr = 0

        if "atr" in df.columns:

            try:
                atr = float(
                    last["atr"]
                )
            except:
                atr = 0

        if atr > 0:

            return (
                distance <= atr * 0.20
            )

        return False


    # =====================================================
    # SELL
    # =====================================================

    if trend == "SELL":

        if price <= ema9:
            return True

        distance = abs(
            price - ema9
        )

        atr = 0

        if "atr" in df.columns:

            try:
                atr = float(
                    last["atr"]
                )
            except:
                atr = 0

        if atr > 0:

            return (
                distance <= atr * 0.20
            )

        return False


    return False


# =========================================================
# RSI CHECK
# =========================================================

def check_rsi(
    df1,
    trend
):

    if df1 is None:
        return False, None


    if len(df1) < RSI_PERIOD + 2:
        return False, None


    df = df1.copy()


    df["rsi"] = calculate_rsi(
        df["close"],
        RSI_PERIOD
    )


    current = df.iloc[-1]

    previous = df.iloc[-2]


    rsi = float(
        current["rsi"]
    )

    previous_rsi = float(
        previous["rsi"]
    )


    # =====================================================
    # BUY
    # =====================================================

    if trend == "BUY":

        # RSI برگشت صعودی
        reversal = (
            previous_rsi <= 50
            and rsi > previous_rsi
        )

        # RSI در محدوده bullish
        bullish_zone = (
            50 <= rsi <= 68
        )

        return (
            reversal or bullish_zone,
            rsi
        )


    # =====================================================
    # SELL
    # =====================================================

    if trend == "SELL":

        reversal = (
            previous_rsi >= 50
            and rsi < previous_rsi
        )

        bearish_zone = (
            32 <= rsi <= 50
        )

        return (
            reversal or bearish_zone,
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

            "score":
                0,

            "confidence":
                0,

            "quality":
                "WEAK",

            "trend":
                "NONE",

            "price":
                None,

            "rsi":
                None,

            "atr":
                None,

            "reasons":
                ["Insufficient market data"],
        }


    if (
        df15.empty
        or df5.empty
        or df1.empty
    ):

        return {

            "signal":
                "NO SIGNAL",

            "score":
                0,

            "confidence":
                0,

            "quality":
                "WEAK",

            "trend":
                "NONE",

            "price":
                None,

            "rsi":
                None,

            "atr":
                None,

            "reasons":
                ["Empty market data"],
        }


    # =====================================================
    # TREND
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


    price = float(
        last1["close"]
    )


    # =====================================================
    # ATR
    # =====================================================

    atr = None

    if "atr" in df1.columns:

        try:

            atr = float(
                last1["atr"]
            )

        except:

            atr = None


    # =====================================================
    # SCORE
    # =====================================================

    score = 0


    # =====================================================
    # 15M TREND
    # =====================================================

    if trend in [
        "BUY",
        "SELL"
    ]:

        score += 30


    # =====================================================
    # 5M EMA9
    # =====================================================

    ema_ok = check_5m_ema(
        df5,
        trend
    )


    if ema_ok:

        score += 25

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

        score += 25

        reasons.append(
            "OK: 1M RSI"
        )

    else:

        reasons.append(
            "WAIT: 1M RSI"
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

        score += 20

        reasons.append(
            "OK: strong 1M candle"
        )

    else:

        reasons.append(
            "WAIT: candle"
        )


    # =====================================================
    # CONFIDENCE
    # =====================================================

    confidence = score


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

    if score >= 85:

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

        "reasons":
            reasons,

        "time":
            str(
                last1.get(
                    "time",
                    ""
                )
            ),
    }