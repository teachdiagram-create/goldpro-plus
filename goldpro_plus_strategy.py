# =========================================================
# GoldPro+ Strategy V1
#
# 5M  -> TREND ONLY
# 1M  -> ENTRY
#
# EMA20 / EMA50 فقط جهت روند را مشخص می‌کنند.
# =========================================================

from indicators import add_indicators


# =========================================================
# SETTINGS
# =========================================================

MIN_SCORE = 70

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

SR_LOOKBACK = 20
SR_ATR_DISTANCE = 1.0


# =========================================================
# HELPERS
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
        return add_indicators(
            df.copy()
        )
    except Exception as exc:
        print(
            "[GoldPro+] Indicator error:",
            exc
        )
        return None


# =========================================================
# 5M TREND
#
# EMA20 / EMA50 ONLY
# =========================================================

def get_trend(df5):

    if df5 is None or len(df5) < 2:
        return "NONE"

    last = _latest(df5)

    ema20 = _safe_float(
        last.get("EMA20")
    )

    ema50 = _safe_float(
        last.get("EMA50")
    )

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
    prev = _previous(df1)

    close = _safe_float(
        last.get("close")
    )

    open_price = _safe_float(
        last.get("open")
    )

    previous_close = _safe_float(
        prev.get("close")
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
    prev = _previous(df1)

    close = _safe_float(
        last.get("close")
    )

    open_price = _safe_float(
        last.get("open")
    )

    previous_close = _safe_float(
        prev.get("close")
    )

    return (
        close < open_price
        and close < previous_close
    )


# =========================================================
# SUPPORT
# =========================================================

def _find_support(df):

    if df is None or df.empty:
        return None

    count = min(
        SR_LOOKBACK,
        len(df)
    )

    if count <= 0:
        return None

    try:
        return float(
            df.iloc[-count:]["low"].min()
        )
    except Exception:
        return None


# =========================================================
# RESISTANCE
# =========================================================

def _find_resistance(df):

    if df is None or df.empty:
        return None

    count = min(
        SR_LOOKBACK,
        len(df)
    )

    if count <= 0:
        return None

    try:
        return float(
            df.iloc[-count:]["high"].max()
        )
    except Exception:
        return None


# =========================================================
# SUPPORT CHECK
# =========================================================

def _near_support(df1):

    last = _latest(df1)

    price = _safe_float(
        last.get("close")
    )

    atr = _safe_float(
        last.get("ATR")
    )

    support = _find_support(
        df1
    )

    if support is None:
        return False, None

    distance = abs(
        price - support
    )

    max_distance = max(
        atr * SR_ATR_DISTANCE,
        0.5
    )

    return (
        distance <= max_distance,
        support
    )


# =========================================================
# RESISTANCE CHECK
# =========================================================

def _near_resistance(df1):

    last = _latest(df1)

    price = _safe_float(
        last.get("close")
    )

    atr = _safe_float(
        last.get("ATR")
    )

    resistance = _find_resistance(
        df1
    )

    if resistance is None:
        return False, None

    distance = abs(
        price - resistance
    )

    max_distance = max(
        atr * SR_ATR_DISTANCE,
        0.5
    )

    return (
        distance <= max_distance,
        resistance
    )


# =========================================================
# BUY ANALYSIS
# =========================================================

def _analyze_buy(df5, df1):

    trend_ok = (
        get_trend(df5) == "BUY"
    )

    rsi_ok = _rsi_buy_trigger(
        df1
    )

    candle_ok = _bullish_candle(
        df1
    )

    support_ok, support = (
        _near_support(df1)
    )

    score = 0

    reasons = []

    filters = {}

    # Trend
    filters["Trend 5M"] = trend_ok

    if trend_ok:
        score += 30
        reasons.append(
            "OK: 5M EMA20 > EMA50"
        )
    else:
        reasons.append(
            "WAIT: 5M bullish trend"
        )

    # RSI
    filters["RSI Reversal 1M"] = rsi_ok

    if rsi_ok:
        score += 30
        reasons.append(
            "OK: 1M RSI below 30 -> above 30"
        )
    else:
        reasons.append(
            "WAIT: 1M RSI reversal"
        )

    # Candle
    filters["Candle 1M"] = candle_ok

    if candle_ok:
        score += 20
        reasons.append(
            "OK: bullish 1M candle"
        )
    else:
        reasons.append(
            "WAIT: bullish 1M candle"
        )

    # Support
    filters["Support 1M"] = support_ok

    if support_ok:
        score += 20
        reasons.append(
            "OK: price near 1M support"
        )
    else:
        reasons.append(
            "WAIT: 1M support"
        )

    return (
        score,
        filters,
        reasons,
        support
    )


# =========================================================
# SELL ANALYSIS
# =========================================================

def _analyze_sell(df5, df1):

    trend_ok = (
        get_trend(df5) == "SELL"
    )

    rsi_ok = _rsi_sell_trigger(
        df1
    )

    candle_ok = _bearish_candle(
        df1
    )

    resistance_ok, resistance = (
        _near_resistance(df1)
    )

    score = 0

    reasons = []

    filters = {}

    # Trend
    filters["Trend 5M"] = trend_ok

    if trend_ok:
        score += 30
        reasons.append(
            "OK: 5M EMA20 < EMA50"
        )
    else:
        reasons.append(
            "WAIT: 5M bearish trend"
        )

    # RSI
    filters["RSI Reversal 1M"] = rsi_ok

    if rsi_ok:
        score += 30
        reasons.append(
            "OK: 1M RSI above 70 -> below 70"
        )
    else:
        reasons.append(
            "WAIT: 1M RSI reversal"
        )

    # Candle
    filters["Candle 1M"] = candle_ok

    if candle_ok:
        score += 20
        reasons.append(
            "OK: bearish 1M candle"
        )
    else:
        reasons.append(
            "WAIT: bearish 1M candle"
        )

    # Resistance
    filters["Resistance 1M"] = resistance_ok

    if resistance_ok:
        score += 20
        reasons.append(
            "OK: price near 1M resistance"
        )
    else:
        reasons.append(
            "WAIT: 1M resistance"
        )

    return (
        score,
        filters,
        reasons,
        resistance
    )


# =========================================================
# MAIN GOLDPRO+ SIGNAL
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

    df5 = _prepare(df5)
    df1 = _prepare(df1)

    if (
        df5 is None
        or df1 is None
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

    trend = get_trend(
        df5
    )

    last = _latest(df1)

    price = _safe_float(
        last.get("close")
    )

    rsi = _safe_float(
        last.get("RSI")
    )

    atr = _safe_float(
        last.get("ATR")
    )

    ema20_5m = _safe_float(
        df5.iloc[-1].get("EMA20")
    )

    ema50_5m = _safe_float(
        df5.iloc[-1].get("EMA50")
    )

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if trend == "BUY":

        (
            score,
            filters,
            reasons,
            support
        ) = _analyze_buy(
            df5,
            df1
        )

        if score >= MIN_SCORE:

            return {
                "signal": "BUY",
                "stage": "1M",
                "trend": trend,
                "score": score,
                "confidence": score,
                "quality": (
                    "STRONG"
                    if score >= 85
                    else "NORMAL"
                ),

                "price": price,
                "rsi": rsi,
                "atr": atr,

                "ema20_5m": ema20_5m,
                "ema50_5m": ema50_5m,

                "support": support,

                "filters": filters,

                "reasons": (
                    [f"Score: {score}/100"]
                    + reasons
                    + ["FINAL BUY SIGNAL"]
                ),

                "time": str(
                    last.get("time")
                )
            }

        return {
            "signal": "NO SIGNAL",
            "stage": "1M",
            "trend": trend,
            "score": score,
            "confidence": score,
            "quality": (
                "STRONG"
                if score >= 85
                else "NORMAL"
                if score >= MIN_SCORE
                else "WEAK"
            ),
            "price": price,
            "rsi": rsi,
            "atr": atr,
            "ema20_5m": ema20_5m,
            "ema50_5m": ema50_5m,
            "support": support,
            "filters": filters,
            "reasons": (
                [f"Score: {score}/100"]
                + reasons
            ),
            "time": str(
                last.get("time")
            )
        }

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    if trend == "SELL":

        (
            score,
            filters,
            reasons,
            resistance
        ) = _analyze_sell(
            df5,
            df1
        )

        if score >= MIN_SCORE:

            return {
                "signal": "SELL",
                "stage": "1M",
                "trend": trend,
                "score": score,
                "confidence": score,
                "quality": (
                    "STRONG"
                    if score >= 85
                    else "NORMAL"
                ),

                "price": price,
                "rsi": rsi,
                "atr": atr,

                "ema20_5m": ema20_5m,
                "ema50_5m": ema50_5m,

                "resistance": resistance,

                "filters": filters,

                "reasons": (
                    [f"Score: {score}/100"]
                    + reasons
                    + ["FINAL SELL SIGNAL"]
                ),

                "time": str(
                    last.get("time")
                )
            }

        return {
            "signal": "NO SIGNAL",
            "stage": "1M",
            "trend": trend,
            "score": score,
            "confidence": score,
            "quality": (
                "STRONG"
                if score >= 85
                else "NORMAL"
                if score >= MIN_SCORE
                else "WEAK"
            ),
            "price": price,
            "rsi": rsi,
            "atr": atr,
            "ema20_5m": ema20_5m,
            "ema50_5m": ema50_5m,
            "resistance": resistance,
            "filters": filters,
            "reasons": (
                [f"Score: {score}/100"]
                + reasons
            ),
            "time": str(
                last.get("time")
            )
        }

    # -----------------------------------------------------
    # NO CLEAR TREND
    # -----------------------------------------------------

    return {
        "signal": "NO SIGNAL",
        "stage": "5M",
        "trend": "NONE",
        "score": 0,
        "confidence": 0,
        "quality": "WEAK",
        "price": price,
        "rsi": rsi,
        "atr": atr,
        "ema20_5m": ema20_5m,
        "ema50_5m": ema50_5m,
        "filters": {},
        "reasons": [
            "WAIT: 5M EMA20 / EMA50 have no clear trend"
        ],
        "time": str(
            last.get("time")
        )
    }