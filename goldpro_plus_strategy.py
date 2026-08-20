# =========================================================
# GoldPro+ Strategy V1
#
# 5M = TREND
# 1M = ENTRY
#
# EMA20 / EMA50:
# ONLY define trend direction.
#
# BUY:
#   1) 5M EMA20 > EMA50
#   2) 1M RSI was below 30 and crossed back above 30
#   3) Last 1M candle is bullish
#   4) Price is near 1M OR 5M support
#   5) Bullish RSI divergence = +10 bonus
#
# SELL:
#   1) 5M EMA20 < EMA50
#   2) 1M RSI was above 70 and crossed back below 70
#   3) Last 1M candle is bearish
#   4) Price is near 1M OR 5M resistance
#   5) Bearish RSI divergence = +10 bonus
#
# Minimum score = 70
# =========================================================

from indicators import add_indicators


# =========================================================
# SETTINGS
# =========================================================

MIN_SCORE = 70

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

SR_LOOKBACK_1M = 20
SR_LOOKBACK_5M = 20

SR_ATR_DISTANCE = 1.0

SL_ATR_MULTIPLIER = 1.5
TP1_ATR_MULTIPLIER = 2.0
TP2_ATR_MULTIPLIER = 3.0


# =========================================================
# BASIC HELPERS
# =========================================================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _latest(df):
    return df.iloc[-1]


def _previous(df):
    return df.iloc[-2]


def _prepare(df):
    if df is None or df.empty:
        return None

    try:
        result = add_indicators(df.copy())

        if result is None or result.empty:
            return None

        return result

    except Exception as exc:
        print("[GoldPro+] Indicator error:", exc)
        return None


# =========================================================
# 5M TREND
#
# EMA20 / EMA50 ONLY DEFINE TREND
# =========================================================

def _get_trend_5m(df5):

    if df5 is None or len(df5) < 2:
        return "NONE"

    last = _latest(df5)

    ema20 = _safe_float(last.get("EMA20"))
    ema50 = _safe_float(last.get("EMA50"))

    if ema20 > ema50:
        return "BUY"

    if ema20 < ema50:
        return "SELL"

    return "NONE"


# =========================================================
# RSI BUY REVERSAL
# =========================================================

def _rsi_buy_trigger(df1):

    if df1 is None or len(df1) < 3:
        return False

    current = _safe_float(
        df1.iloc[-1].get("RSI")
    )

    previous = _safe_float(
        df1.iloc[-2].get("RSI")
    )

    before = _safe_float(
        df1.iloc[-3].get("RSI")
    )

    went_oversold = (
        before < RSI_OVERSOLD
        or previous < RSI_OVERSOLD
    )

    crossed_back = (
        previous <= RSI_OVERSOLD
        and current > RSI_OVERSOLD
    )

    return (
        went_oversold
        and crossed_back
    )


# =========================================================
# RSI SELL REVERSAL
# =========================================================

def _rsi_sell_trigger(df1):

    if df1 is None or len(df1) < 3:
        return False

    current = _safe_float(
        df1.iloc[-1].get("RSI")
    )

    previous = _safe_float(
        df1.iloc[-2].get("RSI")
    )

    before = _safe_float(
        df1.iloc[-3].get("RSI")
    )

    went_overbought = (
        before > RSI_OVERBOUGHT
        or previous > RSI_OVERBOUGHT
    )

    crossed_back = (
        previous >= RSI_OVERBOUGHT
        and current < RSI_OVERBOUGHT
    )

    return (
        went_overbought
        and crossed_back
    )


# =========================================================
# 1M BULLISH CANDLE
# =========================================================

def _bullish_candle(df1):

    if df1 is None or len(df1) < 2:
        return False

    last = _latest(df1)
    previous = _previous(df1)

    close = _safe_float(last.get("close"))
    open_price = _safe_float(last.get("open"))
    previous_close = _safe_float(
        previous.get("close")
    )

    return (
        close > open_price
        and close > previous_close
    )


# =========================================================
# 1M BEARISH CANDLE
# =========================================================

def _bearish_candle(df1):

    if df1 is None or len(df1) < 2:
        return False

    last = _latest(df1)
    previous = _previous(df1)

    close = _safe_float(last.get("close"))
    open_price = _safe_float(last.get("open"))
    previous_close = _safe_float(
        previous.get("close")
    )

    return (
        close < open_price
        and close < previous_close
    )


# =========================================================
# SUPPORT
# =========================================================

def _find_support(df, lookback):

    if df is None or df.empty:
        return None

    count = min(
        int(lookback),
        len(df)
    )

    if count <= 0:
        return None

    try:
        value = df.iloc[-count:]["low"].min()
        return _safe_float(value, None)

    except Exception:
        return None


# =========================================================
# RESISTANCE
# =========================================================

def _find_resistance(df, lookback):

    if df is None or df.empty:
        return None

    count = min(
        int(lookback),
        len(df)
    )

    if count <= 0:
        return None

    try:
        value = df.iloc[-count:]["high"].max()
        return _safe_float(value, None)

    except Exception:
        return None


# =========================================================
# SUPPORT CONTEXT
# =========================================================

def _support_context(df1, df5):

    price = _safe_float(
        _latest(df1).get("close")
    )

    atr = _safe_float(
        _latest(df1).get("ATR")
    )

    support1 = _find_support(
        df1,
        SR_LOOKBACK_1M
    )

    support5 = _find_support(
        df5,
        SR_LOOKBACK_5M
    )

    max_distance = max(
        atr * SR_ATR_DISTANCE,
        0.5
    )

    if support1 is not None:
        distance1 = abs(
            price - support1
        )
    else:
        distance1 = float("inf")

    if support5 is not None:
        distance5 = abs(
            price - support5
        )
    else:
        distance5 = float("inf")

    near1 = (
        distance1 <= max_distance
    )

    near5 = (
        distance5 <= max_distance
    )

    confirmed = (
        near1 or near5
    )

    return confirmed, {
        "support_1m": support1,
        "support_5m": support5,
        "distance_to_support_1m": distance1,
        "distance_to_support_5m": distance5,
        "near_support_1m": near1,
        "near_support_5m": near5,
    }


# =========================================================
# RESISTANCE CONTEXT
# =========================================================

def _resistance_context(df1, df5):

    price = _safe_float(
        _latest(df1).get("close")
    )

    atr = _safe_float(
        _latest(df1).get("ATR")
    )

    resistance1 = _find_resistance(
        df1,
        SR_LOOKBACK_1M
    )

    resistance5 = _find_resistance(
        df5,
        SR_LOOKBACK_5M
    )

    max_distance = max(
        atr * SR_ATR_DISTANCE,
        0.5
    )

    if resistance1 is not None:
        distance1 = abs(
            price - resistance1
        )
    else:
        distance1 = float("inf")

    if resistance5 is not None:
        distance5 = abs(
            price - resistance5
        )
    else:
        distance5 = float("inf")

    near1 = (
        distance1 <= max_distance
    )

    near5 = (
        distance5 <= max_distance
    )

    confirmed = (
        near1 or near5
    )

    return confirmed, {
        "resistance_1m": resistance1,
        "resistance_5m": resistance5,
        "distance_to_resistance_1m": distance1,
        "distance_to_resistance_5m": distance5,
        "near_resistance_1m": near1,
        "near_resistance_5m": near5,
    }


# =========================================================
# BULLISH RSI DIVERGENCE
# =========================================================

def _bullish_divergence(df1):

    if df1 is None or len(df1) < 10:
        return False

    recent = df1.iloc[-10:]

    first = recent.iloc[:5]
    second = recent.iloc[5:]

    try:
        idx1 = first["low"].idxmin()
        idx2 = second["low"].idxmin()

        price_low_1 = _safe_float(
            first.loc[idx1, "low"]
        )

        price_low_2 = _safe_float(
            second.loc[idx2, "low"]
        )

        rsi_low_1 = _safe_float(
            first.loc[idx1, "RSI"]
        )

        rsi_low_2 = _safe_float(
            second.loc[idx2, "RSI"]
        )

        return (
            price_low_2 < price_low_1
            and rsi_low_2 > rsi_low_1
        )

    except Exception:
        return False


# =========================================================
# BEARISH RSI DIVERGENCE
# =========================================================

def _bearish_divergence(df1):

    if df1 is None or len(df1) < 10:
        return False

    recent = df1.iloc[-10:]

    first = recent.iloc[:5]
    second = recent.iloc[5:]

    try:
        idx1 = first["high"].idxmax()
        idx2 = second["high"].idxmax()

        price_high_1 = _safe_float(
            first.loc[idx1, "high"]
        )

        price_high_2 = _safe_float(
            second.loc[idx2, "high"]
        )

        rsi_high_1 = _safe_float(
            first.loc[idx1, "RSI"]
        )

        rsi_high_2 = _safe_float(
            second.loc[idx2, "RSI"]
        )

        return (
            price_high_2 > price_high_1
            and rsi_high_2 < rsi_high_1
        )

    except Exception:
        return False


# =========================================================
# BUY ANALYSIS
# =========================================================

def _analyze_buy(df5, df1):

    trend_ok = (
        _get_trend_5m(df5)
        == "BUY"
    )

    rsi_ok = _rsi_buy_trigger(
        df1
    )

    candle_ok = _bullish_candle(
        df1
    )

    support_ok, sr = _support_context(
        df1,
        df5
    )

    divergence = _bullish_divergence(
        df1
    )

    score = 0

    reasons = []

    filters = {}

    # Trend = 20
    filters["Trend"] = trend_ok

    if trend_ok:
        score += 20
        reasons.append(
            "OK: 5M EMA20 > EMA50 trend"
        )
    else:
        reasons.append(
            "WAIT: 5M EMA trend"
        )

    # RSI = 35
    filters["RSI Reversal"] = rsi_ok

    if rsi_ok:
        score += 35
        reasons.append(
            "OK: 1M RSI below 30 -> back above 30"
        )
    else:
        reasons.append(
            "WAIT: 1M RSI reversal"
        )

    # Candle = 20
    filters["1M Candle"] = candle_ok

    if candle_ok:
        score += 20
        reasons.append(
            "OK: bullish 1M candle"
        )
    else:
        reasons.append(
            "WAIT: bullish 1M candle"
        )

    # Support = 15
    filters["Support"] = support_ok

    if support_ok:
        score += 15
        reasons.append(
            "OK: 1M/5M support"
        )
    else:
        reasons.append(
            "WAIT: 1M/5M support"
        )

    # Divergence = 10 bonus
    filters["RSI Divergence"] = divergence

    if divergence:
        score += 10
        reasons.append(
            "BONUS: bullish RSI divergence"
        )
    else:
        reasons.append(
            "No bullish RSI divergence"
        )

    return (
        score,
        filters,
        reasons,
        sr,
        divergence
    )


# =========================================================
# SELL ANALYSIS
# =========================================================

def _analyze_sell(df5, df1):

    trend_ok = (
        _get_trend_5m(df5)
        == "SELL"
    )

    rsi_ok = _rsi_sell_trigger(
        df1
    )

    candle_ok = _bearish_candle(
        df1
    )

    resistance_ok, sr = _resistance_context(
        df1,
        df5
    )

    divergence = _bearish_divergence(
        df1
    )

    score = 0

    reasons = []

    filters = {}

    # Trend = 20
    filters["Trend"] = trend_ok

    if trend_ok:
        score += 20
        reasons.append(
            "OK: 5M EMA20 < EMA50 trend"
        )
    else:
        reasons.append(
            "WAIT: 5M EMA trend"
        )

    # RSI = 35
    filters["RSI Reversal"] = rsi_ok

    if rsi_ok:
        score += 35
        reasons.append(
            "OK: 1M RSI above 70 -> back below 70"
        )
    else:
        reasons.append(
            "WAIT: 1M RSI reversal"
        )

    # Candle = 20
    filters["1M Candle"] = candle_ok

    if candle_ok:
        score += 20
        reasons.append(
            "OK: bearish 1M candle"
        )
    else:
        reasons.append(
            "WAIT: bearish 1M candle"
        )

    # Resistance = 15
    filters["Resistance"] = resistance_ok

    if resistance_ok:
        score += 15
        reasons.append(
            "OK: 1M/5M resistance"
        )
    else:
        reasons.append(
            "WAIT: 1M/5M resistance"
        )

    # Divergence = 10 bonus
    filters["RSI Divergence"] = divergence

    if divergence:
        score += 10
        reasons.append(
            "BONUS: bearish RSI divergence"
        )
    else:
        reasons.append(
            "No bearish RSI divergence"
        )

    return (
        score,
        filters,
        reasons,
        sr,
        divergence
    )


# =========================================================
# QUALITY
# =========================================================

def _quality(score):

    if score >= 85:
        return "STRONG"

    if score >= MIN_SCORE:
        return "NORMAL"

    return "WEAK"


# =========================================================
# COMMON DATA
# =========================================================

def _common_data(df1):

    last = _latest(df1)

    return {
        "price": _safe_float(
            last.get("close")
        ),

        "rsi": _safe_float(
            last.get("RSI")
        ),

        "adx": _safe_float(
            last.get("ADX")
        ),

        "atr": _safe_float(
            last.get("ATR")
        ),

        "ema20": _safe_float(
            last.get("EMA20")
        ),

        "ema50": _safe_float(
            last.get("EMA50")
        ),

        "macd": _safe_float(
            last.get("MACD")
        ),

        "macd_signal": _safe_float(
            last.get("MACD_SIGNAL")
        ),

        "time": str(
            last.get("time")
        )
    }


# =========================================================
# NO SIGNAL
# =========================================================

def _build_no_signal(
    trend,
    score,
    reasons,
    filters,
    data,
    sr,
    divergence
):

    result = {
        "signal": "NO SIGNAL",
        "stage": "1M",
        "trend": trend,

        "score": score,
        "confidence": score,

        "quality": _quality(
            score
        ),

        "reasons": [
            f"Score: {score}/100"
        ] + reasons,

        "filters": filters,

        "divergence": divergence
    }

    result.update(data)

    if trend == "BUY":

        result["support"] = sr.get(
            "support_1m"
        )

        result["support_5m"] = sr.get(
            "support_5m"
        )

    elif trend == "SELL":

        result["resistance"] = sr.get(
            "resistance_1m"
        )

        result["resistance_5m"] = sr.get(
            "resistance_5m"
        )

    return result


# =========================================================
# BUILD SIGNAL
# =========================================================

def _build_signal(
    signal,
    trend,
    score,
    reasons,
    filters,
    data,
    sr,
    divergence
):

    price = data["price"]
    atr = data["atr"]

    if atr <= 0:

        return _build_no_signal(
            trend,
            score,
            reasons + [
                "WAIT: ATR unavailable"
            ],
            filters,
            data,
            sr,
            divergence
        )

    if signal == "BUY":

        sl = (
            price
            - atr * SL_ATR_MULTIPLIER
        )

        tp1 = (
            price
            + atr * TP1_ATR_MULTIPLIER
        )

        tp2 = (
            price
            + atr * TP2_ATR_MULTIPLIER
        )

    else:

        sl = (
            price
            + atr * SL_ATR_MULTIPLIER
        )

        tp1 = (
            price
            - atr * TP1_ATR_MULTIPLIER
        )

        tp2 = (
            price
            - atr * TP2_ATR_MULTIPLIER
        )

    result = {
        "signal": signal,

        "stage": "1M",

        "trend": trend,

        "score": score,

        "confidence": score,

        "quality": _quality(
            score
        ),

        "price": price,

        "sl": sl,

        "tp1": tp1,

        "tp2": tp2,

        "rsi": data["rsi"],

        "adx": data["adx"],

        "atr": atr,

        "ema20": data["ema20"],

        "ema50": data["ema50"],

        "macd": data["macd"],

        "macd_signal": data["macd_signal"],

        "divergence": divergence,

        "filters": filters,

        "time": data["time"],

        "reasons": [
            f"Score: {score}/100"
        ] + reasons + [
            f"FINAL {signal} SIGNAL"
        ]
    }

    if signal == "BUY":

        result["support"] = sr.get(
            "support_1m"
        )

        result["support_5m"] = sr.get(
            "support_5m"
        )

    else:

        result["resistance"] = sr.get(
            "resistance_1m"
        )

        result["resistance_5m"] = sr.get(
            "resistance_5m"
        )

    return result


# =========================================================
# MAIN
# =========================================================

def generate_goldpro_plus_signal(
    df5,
    df1
):

    # -----------------------------------------------------
    # DATA CHECK
    # -----------------------------------------------------

    if (
        df5 is None
        or df1 is None
        or df5.empty
        or df1.empty
    ):

        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "trend": "NONE",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "Insufficient market data"
            ]
        }

    # -----------------------------------------------------
    # PREPARE INDICATORS
    # -----------------------------------------------------

    prepared5 = _prepare(
        df5
    )

    prepared1 = _prepare(
        df1
    )

    if (
        prepared5 is None
        or prepared1 is None
        or prepared5.empty
        or prepared1.empty
    ):

        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "trend": "NONE",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "Indicator calculation failed"
            ]
        }

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    trend = _get_trend_5m(
        prepared5
    )

    data = _common_data(
        prepared1
    )

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if trend == "BUY":

        (
            score,
            filters,
            reasons,
            sr,
            divergence
        ) = _analyze_buy(
            prepared5,
            prepared1
        )

        if score >= MIN_SCORE:

            return _build_signal(
                "BUY",
                trend,
                score,
                reasons,
                filters,
                data,
                sr,
         