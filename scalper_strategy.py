# =========================================================
# GoldPro+ Scalper V7
#
# 15M Trend -> 5M Momentum/Structure -> 1M Entry
#
# V5 focus:
# - detect trend changes faster through 5M structure
# - distinguish TREND STRENGTH from ENTRY QUALITY
# - detect the current impulse wave
# - block chasing an already extended move
# - require a REAL pullback/reclaim for mature/late moves
# - score never overrides structural entry blocks
# =========================================================

import pandas as pd


# =========================================================
# EASY MODE (برای تست سریع - فقط برای آزمایش!)
# =========================================================
# اگر True باشد، تمام محدودیت‌های سخت‌گیرانه کاهش می‌یابند
# تا تعداد سیگنال‌ها افزایش یابد.
# ⚠️ این حالت فقط برای تست است و برای معاملات واقعی مناسب نیست.
# =========================================================

EASY_MODE = True   # آن را به True یا False تغییر دهید


# =========================================================
# SETTINGS (با پشتیبانی از EASY_MODE)
# =========================================================

if EASY_MODE:
    # ---------- حالت آسان (تست سریع) ----------
    EMA_FAST = 9
    EMA_TREND_FAST = 9
    EMA_TREND_SLOW = 20
    RSI_PERIOD = 14

    SIGNAL_SCORE = 55
    WATCH_SCORE = 45
    CANDLE_BODY_MIN = 0.30

    WAVE_LOOKBACK_1M = 60
    PULLBACK_LOOKBACK_1M = 15
    MIN_PULLBACK_RATIO = 0.08
    MAX_ENTRY_POSITION = 0.75
    HARD_MAX_ENTRY_POSITION = 0.85
    MIN_PULLBACK_ATR = 0.80

    MAX_EXTENSION_ATR = 2.50
    NEAR_EXTREME_ATR = 0.20

    FAST_CROSS_LOOKBACK_5M = 3

    SWING_LOOKBACK_5M = 24
    DIVERGENCE_LOOKBACK_5M = 18
    REVERSAL_CONFIRMATIONS = 2
    REVERSAL_WARNING_SCORE = 1
    PIVOT_LEFT_RIGHT = 1
    DIVERGENCE_MIN_RSI_GAP = 2.5
    REVERSAL_SR_ATR = 0.80
    PULLBACK_MIN_RATIO_5M = 0.08   # برای 5M pullback
    PULLBACK_MAX_RATIO_5M = 0.80
    FIB_ZONE_LOW = 0.382
    FIB_ZONE_HIGH = 0.618
    SR_ATR_DISTANCE = 0.75
    STRUCTURE_BREAK_LOOKBACK = 6

    RSI_OVERSOLD = 25
    RSI_OVERBOUGHT = 75
    RSI_BUY_LEVEL = 40
    RSI_SELL_LEVEL = 60

else:
    # ---------- حالت عادی (سخت‌گیرانه) ----------
    EMA_FAST = 9
    EMA_TREND_FAST = 9
    EMA_TREND_SLOW = 20
    RSI_PERIOD = 14

    SIGNAL_SCORE = 75
    WATCH_SCORE = 60
    CANDLE_BODY_MIN = 0.45

    WAVE_LOOKBACK_1M = 60
    PULLBACK_LOOKBACK_1M = 15
    MIN_PULLBACK_RATIO = 0.30
    MAX_ENTRY_POSITION = 0.68
    HARD_MAX_ENTRY_POSITION = 0.78
    MIN_PULLBACK_ATR = 1.20

    MAX_EXTENSION_ATR = 2.00
    NEAR_EXTREME_ATR = 0.65

    FAST_CROSS_LOOKBACK_5M = 3

    SWING_LOOKBACK_5M = 24
    DIVERGENCE_LOOKBACK_5M = 18
    REVERSAL_CONFIRMATIONS = 4
    REVERSAL_WARNING_SCORE = 2
    PIVOT_LEFT_RIGHT = 1
    DIVERGENCE_MIN_RSI_GAP = 2.5
    REVERSAL_SR_ATR = 0.80
    PULLBACK_MIN_RATIO_5M = 0.20
    PULLBACK_MAX_RATIO_5M = 0.72
    FIB_ZONE_LOW = 0.382
    FIB_ZONE_HIGH = 0.618
    SR_ATR_DISTANCE = 0.75
    STRUCTURE_BREAK_LOOKBACK = 6

    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_BUY_LEVEL = 35
    RSI_SELL_LEVEL = 65


# =========================================================
# EMA / RSI / SAFE FLOAT
# =========================================================

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series, period=RSI_PERIOD):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def safe_float(value):
    try:
        value = float(value)
        if pd.isna(value):
            return None
        return value
    except Exception:
        return None


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=14):
    if df is None or df.empty or len(df) < 2:
        return None

    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce")
    previous_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    return safe_float(atr.iloc[-1])


# =========================================================
# CANDLE INFORMATION
# =========================================================

def candle_info(candle):
    open_price = safe_float(candle.get("open"))
    high = safe_float(candle.get("high"))
    low = safe_float(candle.get("low"))
    close = safe_float(candle.get("close"))

    if None in (open_price, high, low, close):
        return {
            "bullish": False, "bearish": False, "strong": False,
            "body_ratio": 0.0, "upper_wick_ratio": 0.0,
            "lower_wick_ratio": 0.0, "range": 0.0,
        }

    candle_range = high - low
    if candle_range <= 0:
        return {
            "bullish": False, "bearish": False, "strong": False,
            "body_ratio": 0.0, "upper_wick_ratio": 0.0,
            "lower_wick_ratio": 0.0, "range": 0.0,
        }

    body = abs(close - open_price)
    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low

    return {
        "bullish": close > open_price,
        "bearish": close < open_price,
        "strong": (body / candle_range) >= CANDLE_BODY_MIN,
        "body_ratio": body / candle_range,
        "upper_wick_ratio": upper_wick / candle_range,
        "lower_wick_ratio": lower_wick / candle_range,
        "range": candle_range,
    }


# =========================================================
# CANDLE PATTERNS
# =========================================================

def bullish_engulfing(previous, current):
    prev = candle_info(previous)
    curr = candle_info(current)
    po, pc = safe_float(previous.get("open")), safe_float(previous.get("close"))
    co, cc = safe_float(current.get("open")), safe_float(current.get("close"))
    if None in (po, pc, co, cc):
        return False
    return prev["bearish"] and curr["bullish"] and co <= pc and cc >= po and curr["body_ratio"] >= 0.50


def bearish_engulfing(previous, current):
    prev = candle_info(previous)
    curr = candle_info(current)
    po, pc = safe_float(previous.get("open")), safe_float(previous.get("close"))
    co, cc = safe_float(current.get("open")), safe_float(current.get("close"))
    if None in (po, pc, co, cc):
        return False
    return prev["bullish"] and curr["bearish"] and co >= pc and cc <= po and curr["body_ratio"] >= 0.50


def hammer(candle):
    info = candle_info(candle)
    return info["bullish"] and info["lower_wick_ratio"] >= 0.45 and info["upper_wick_ratio"] <= 0.20 and info["body_ratio"] >= 0.15


def shooting_star(candle):
    info = candle_info(candle)
    return info["bearish"] and info["upper_wick_ratio"] >= 0.45 and info["lower_wick_ratio"] <= 0.20 and info["body_ratio"] >= 0.15


def bullish_marubozu(candle):
    info = candle_info(candle)
    return info["bullish"] and info["body_ratio"] >= 0.75 and info["upper_wick_ratio"] <= 0.10 and info["lower_wick_ratio"] <= 0.10


def bearish_marubozu(candle):
    info = candle_info(candle)
    return info["bearish"] and info["body_ratio"] >= 0.75 and info["upper_wick_ratio"] <= 0.10 and info["lower_wick_ratio"] <= 0.10


def detect_candlestick_pattern(df):
    if df is None or len(df) < 3:
        return "NONE"
    previous = df.iloc[-2]
    current = df.iloc[-1]
    if bullish_engulfing(previous, current):
        return "BULLISH_ENGULFING"
    if bearish_engulfing(previous, current):
        return "BEARISH_ENGULFING"
    if hammer(current):
        return "HAMMER"
    if shooting_star(current):
        return "SHOOTING_STAR"
    if bullish_marubozu(current):
        return "BULLISH_MARUBOZU"
    if bearish_marubozu(current):
        return "BEARISH_MARUBOZU"
    return "NONE"


def pattern_direction(pattern):
    if pattern in {"BULLISH_ENGULFING", "HAMMER", "BULLISH_MARUBOZU"}:
        return "BUY"
    if pattern in {"BEARISH_ENGULFING", "SHOOTING_STAR", "BEARISH_MARUBOZU"}:
        return "SELL"
    return "NONE"


# =========================================================
# TREND STATE
# =========================================================

def _ema_state(df, fast=9, slow=20):
    data = df.copy()
    data["ema_fast"] = calculate_ema(data["close"], fast)
    data["ema_slow"] = calculate_ema(data["close"], slow)
    return data


def _bars_since_sign_change(series, wanted_sign, max_bars=50):
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    age = 0
    for value in reversed(values.tail(max_bars).tolist()):
        sign_ok = value > 0 if wanted_sign > 0 else value < 0
        if not sign_ok:
            break
        age += 1
    return age


def get_trend_state(df15):
    if df15 is None or df15.empty or len(df15) < 25:
        return {"trend": "NONE", "age_bars": None, "phase": "UNKNOWN", "ema9": None, "ema20": None, "price": None, "fresh": False}

    df = _ema_state(df15, EMA_TREND_FAST, EMA_TREND_SLOW)
    last = df.iloc[-1]
    price = safe_float(last["close"])
    ema9 = safe_float(last["ema_fast"])
    ema20 = safe_float(last["ema_slow"])

    if None in (price, ema9, ema20):
        return {"trend": "NONE", "age_bars": None, "phase": "UNKNOWN", "ema9": ema9, "ema20": ema20, "price": price, "fresh": False}

    spread = df["ema_fast"] - df["ema_slow"]
    if price > ema9 and spread.iloc[-1] > 0:
        trend = "BUY"
        age = _bars_since_sign_change(spread, 1)
    elif price < ema9 and spread.iloc[-1] < 0:
        trend = "SELL"
        age = _bars_since_sign_change(spread, -1)
    else:
        trend = "NONE"
        age = None

    if age is None:
        phase = "UNKNOWN"
    elif age <= 3:
        phase = "EARLY"
    elif age <= 8:
        phase = "DEVELOPING"
    elif age <= 15:
        phase = "MATURE"
    else:
        phase = "LATE"

    return {
        "trend": trend,
        "age_bars": age,
        "phase": phase,
        "ema9": ema9,
        "ema20": ema20,
        "price": price,
        "fresh": age is not None and age <= 8,
    }


# =========================================================
# FAST 5M TREND SHIFT
# =========================================================

def get_5m_momentum_state(df5, trend):
    if df5 is None or df5.empty or len(df5) < 25 or trend not in ("BUY", "SELL"):
        return {"ok": False, "shift": False, "slope_ok": False, "ema9": None, "ema20": None, "age_bars": None, "spread": None}

    df = _ema_state(df5, 9, 20)
    spread = df["ema_fast"] - df["ema_slow"]
    wanted = 1 if trend == "BUY" else -1
    age = _bars_since_sign_change(spread, wanted)

    last = df.iloc[-1]
    prev = df.iloc[-2]
    ema9 = safe_float(last["ema_fast"])
    ema20 = safe_float(last["ema_slow"])
    prev_ema9 = safe_float(prev["ema_fast"])

    slope_ok = False
    if None not in (ema9, prev_ema9):
        slope_ok = ema9 > prev_ema9 if trend == "BUY" else ema9 < prev_ema9

    alignment = ema9 is not None and ema20 is not None and (ema9 > ema20 if trend == "BUY" else ema9 < ema20)
    shift = age is not None and age <= FAST_CROSS_LOOKBACK_5M

    return {
        "ok": alignment,
        "shift": shift,
        "slope_ok": slope_ok,
        "ema9": ema9,
        "ema20": ema20,
        "age_bars": age,
        "spread": safe_float(spread.iloc[-1]),
    }


# =========================================================
# 5M EMA CONFIRMATION
# =========================================================

def check_5m_ema(df5, trend):
    if df5 is None or df5.empty or len(df5) < EMA_FAST or trend not in ("BUY", "SELL"):
        return False
    df = df5.copy()
    df["ema9"] = calculate_ema(df["close"], EMA_FAST)
    last = df.iloc[-1]
    price = safe_float(last["close"])
    ema9 = safe_float(last["ema9"])
    if None in (price, ema9):
        return False
    return price >= ema9 if trend == "BUY" else price <= ema9


# =========================================================
# 1M RSI
# =========================================================

def check_rsi(df1, trend):
    if df1 is None or df1.empty or len(df1) < RSI_PERIOD + 2 or trend not in ("BUY", "SELL"):
        return False, None
    df = df1.copy()
    df["rsi"] = calculate_rsi(df["close"], RSI_PERIOD)
    current = safe_float(df.iloc[-1]["rsi"])
    previous = safe_float(df.iloc[-2]["rsi"])
    if None in (current, previous):
        return False, current
    if trend == "BUY":
        return ((RSI_BUY_LEVEL <= current <= 68) or (previous <= RSI_BUY_LEVEL and current > previous)), current
    return ((32 <= current <= RSI_SELL_LEVEL) or (previous >= RSI_SELL_LEVEL and current < previous)), current



# =========================================================
# IMPULSE / WAVE ANALYSIS
# =========================================================

def analyze_impulse_wave(df1, trend):
    """Find the current impulse and determine whether price is chasing it."""
    result = {
        "wave_stage": "UNKNOWN",
        "wave_low": None,
        "wave_high": None,
        "wave_range": None,
        "wave_position": None,
        "pullback_low": None,
        "pullback_high": None,
        "pullback_ratio": 0.0,
        "pullback_atr": 0.0,
        "fresh_pullback": False,
        "reclaim": False,
        "chasing": False,
        "structure_ok": False,
        "reasons": [],
    }

    if df1 is None or df1.empty or len(df1) < 20 or trend not in ("BUY", "SELL"):
        result["reasons"].append("BLOCK: insufficient wave structure")
        return result

    work = df1.copy().tail(WAVE_LOOKBACK_1M).reset_index(drop=True)
    atr = calculate_atr(work)
    closes = pd.to_numeric(work["close"], errors="coerce")
    highs = pd.to_numeric(work["high"], errors="coerce")
    lows = pd.to_numeric(work["low"], errors="coerce")

    if closes.isna().all() or highs.isna().all() or lows.isna().all():
        result["reasons"].append("BLOCK: invalid wave data")
        return result

    current = safe_float(closes.iloc[-1])
    if current is None:
        result["reasons"].append("BLOCK: invalid current price")
        return result

    if trend == "BUY":
        high_idx = int(highs.idxmax())
        if high_idx <= 0:
            result["reasons"].append("BLOCK: no bullish impulse found")
            return result

        low_slice = lows.iloc[:high_idx + 1]
        low_idx = int(low_slice.idxmin())
        wave_low = safe_float(lows.iloc[low_idx])
        wave_high = safe_float(highs.iloc[high_idx])

        if wave_low is None or wave_high is None or wave_high <= wave_low:
            result["reasons"].append("BLOCK: invalid bullish impulse")
            return result

        wave_range = wave_high - wave_low
        position = (current - wave_low) / wave_range

        after_high = lows.iloc[high_idx + 1:]
        pullback_low = safe_float(after_high.min()) if not after_high.empty else None
        pullback_ratio = 0.0
        pullback_atr = 0.0
        pullback_idx = None

        if pullback_low is not None:
            pullback_ratio = max(0.0, (wave_high - pullback_low) / wave_range)
            if not after_high.empty:
                pullback_idx = int(after_high.idxmin())
            if atr and atr > 0:
                pullback_atr = (wave_high - pullback_low) / atr

        recent_pullback = pullback_idx is not None and pullback_idx >= max(0, len(work) - PULLBACK_LOOKBACK_1M)

        ema = calculate_ema(work["close"], 9)
        previous = safe_float(closes.iloc[-2])
        current_ema = safe_float(ema.iloc[-1])
        previous_ema = safe_float(ema.iloc[-2])
        reclaim = (
            previous is not None and current_ema is not None and previous_ema is not None
            and previous <= previous_ema and current >= current_ema
        )

        fresh_pullback = (
            recent_pullback
            and pullback_ratio >= MIN_PULLBACK_RATIO
            and pullback_atr >= MIN_PULLBACK_ATR
        )

        chasing = (
            position >= HARD_MAX_ENTRY_POSITION
            or (position >= MAX_ENTRY_POSITION and not fresh_pullback)
        )

        result.update({
            "wave_low": wave_low,
            "wave_high": wave_high,
            "wave_range": wave_range,
            "wave_position": position,
            "pullback_low": pullback_low,
            "pullback_ratio": pullback_ratio,
            "pullback_atr": pullback_atr,
            "fresh_pullback": fresh_pullback,
            "reclaim": reclaim,
            "chasing": chasing,
        })

        if high_idx >= len(work) - 4:
            wave_stage = "IMPULSE"
        elif fresh_pullback and reclaim:
            wave_stage = "RECLAIM"
        elif fresh_pullback:
            wave_stage = "PULLBACK"
        elif position >= MAX_ENTRY_POSITION:
            wave_stage = "EXTENDED"
        else:
            wave_stage = "CONTINUATION"

        result["wave_stage"] = wave_stage

        if chasing:
            result["reasons"].append("BLOCK: chasing extended bullish impulse")
        elif wave_stage == "EXTENDED":
            result["reasons"].append("BLOCK: price too deep inside bullish impulse")
        elif fresh_pullback and reclaim:
            result["reasons"].append("OK: fresh pullback + reclaim")
        elif fresh_pullback:
            result["reasons"].append("WAIT: pullback formed, waiting reclaim")
        else:
            result["reasons"].append("INFO: bullish continuation")

        result["structure_ok"] = (
            not chasing
            and position < HARD_MAX_ENTRY_POSITION
            and (
                position < MAX_ENTRY_POSITION
                or (fresh_pullback and reclaim and position < 0.75)
            )
        )

    else:
        low_idx = int(lows.idxmin())
        if low_idx <= 0:
            result["reasons"].append("BLOCK: no bearish impulse found")
            return result

        high_slice = highs.iloc[:low_idx + 1]
        high_idx = int(high_slice.idxmax())
        wave_high = safe_float(highs.iloc[high_idx])
        wave_low = safe_float(lows.iloc[low_idx])

        if wave_low is None or wave_high is None or wave_high <= wave_low:
            result["reasons"].append("BLOCK: invalid bearish impulse")
            return result

        wave_range = wave_high - wave_low
        position = (wave_high - current) / wave_range

        after_low = highs.iloc[low_idx + 1:]
        pullback_high = safe_float(after_low.max()) if not after_low.empty else None
        pullback_ratio = 0.0
        pullback_atr = 0.0
        pullback_idx = None

        if pullback_high is not None:
            pullback_ratio = max(0.0, (pullback_high - wave_low) / wave_range)
            if not after_low.empty:
                pullback_idx = int(after_low.idxmax())
            if atr and atr > 0:
                pullback_atr = (pullback_high - wave_low) / atr

        recent_pullback = pullback_idx is not None and pullback_idx >= max(0, len(work) - PULLBACK_LOOKBACK_1M)

        ema = calculate_ema(work["close"], 9)
        previous = safe_float(closes.iloc[-2])
        current_ema = safe_float(ema.iloc[-1])
        previous_ema = safe_float(ema.iloc[-2])
        reclaim = (
            previous is not None and current_ema is not None and previous_ema is not None
            and previous >= previous_ema and current <= current_ema
        )

        fresh_pullback = (
            recent_pullback
            and pullback_ratio >= MIN_PULLBACK_RATIO
            and pullback_atr >= MIN_PULLBACK_ATR
        )

        chasing = (
            position >= HARD_MAX_ENTRY_POSITION
            or (position >= MAX_ENTRY_POSITION and not fresh_pullback)
        )

        result.update({
            "wave_low": wave_low,
            "wave_high": wave_high,
            "wave_range": wave_range,
            "wave_position": position,
            "pullback_high": pullback_high,
            "pullback_ratio": pullback_ratio,
            "pullback_atr": pullback_atr,
            "fresh_pullback": fresh_pullback,
            "reclaim": reclaim,
            "chasing": chasing,
        })

        if low_idx >= len(work) - 4:
            wave_stage = "IMPULSE"
        elif fresh_pullback and reclaim:
            wave_stage = "RECLAIM"
        elif fresh_pullback:
            wave_stage = "PULLBACK"
        elif position >= MAX_ENTRY_POSITION:
            wave_stage = "EXTENDED"
        else:
            wave_stage = "CONTINUATION"

        result["wave_stage"] = wave_stage

        if chasing:
            result["reasons"].append("BLOCK: chasing extended bearish impulse")
        elif wave_stage == "EXTENDED":
            result["reasons"].append("BLOCK: price too deep inside bearish impulse")
        elif fresh_pullback and reclaim:
            result["reasons"].append("OK: fresh pullback + reclaim")
        elif fresh_pullback:
            result["reasons"].append("WAIT: pullback formed, waiting reclaim")
        else:
            result["reasons"].append("INFO: bearish continuation")

        result["structure_ok"] = (
            not chasing
            and position < HARD_MAX_ENTRY_POSITION
            and (
                position < MAX_ENTRY_POSITION
                or (fresh_pullback and reclaim and position < 0.75)
            )
        )

    return result

# =========================================================
# ENTRY TIMING / EXTENSION FILTER
# =========================================================

def analyze_entry_timing(df1, trend):
    result = {
        "timing_ok": False,
        "pullback": False,
        "near_extreme": False,
        "extended": False,
        "momentum_weak": False,
        "recent_high": None,
        "recent_low": None,
        "atr": None,
        "extension_atr": None,
        "reasons": [],
    }

    if df1 is None or df1.empty or trend not in ("BUY", "SELL"):
        result["reasons"].append("WAIT: entry timing")
        return result

    work = df1.copy()
    if len(work) < 12:
        result["reasons"].append("WAIT: entry history")
        return result

    atr = calculate_atr(work, RSI_PERIOD)
    result["atr"] = atr
    lookback = work.iloc[-30:]
    current = safe_float(work.iloc[-1]["close"])
    previous = safe_float(work.iloc[-2]["close"])
    if current is None or previous is None or atr is None or atr <= 0:
        result["reasons"].append("WAIT: entry volatility")
        return result

    recent_high = safe_float(lookback["high"].max())
    recent_low = safe_float(lookback["low"].min())
    result["recent_high"] = recent_high
    result["recent_low"] = recent_low

    work["ema9"] = calculate_ema(work["close"], 9)
    ema9 = safe_float(work.iloc[-1]["ema9"])
    prev_ema9 = safe_float(work.iloc[-2]["ema9"])
    if ema9 is None or prev_ema9 is None:
        result["reasons"].append("WAIT: entry EMA")
        return result

    if trend == "BUY":
        extension = current - ema9
        distance_extreme = recent_high - current
        result["extension_atr"] = extension / atr
        result["extended"] = extension > MAX_EXTENSION_ATR * atr
        result["near_extreme"] = distance_extreme <= NEAR_EXTREME_ATR * atr
        result["pullback"] = previous <= safe_float(work.iloc[-2]["ema9"]) and current >= ema9
        result["momentum_weak"] = ema9 < prev_ema9
        if result["near_extreme"]:
            result["reasons"].append("BLOCK: near recent HIGH")
        elif result["extended"]:
            result["reasons"].append("BLOCK: price extended from 1M EMA9")
        elif result["pullback"]:
            result["reasons"].append("OK: 1M EMA9 reclaim")
        else:
            result["reasons"].append("INFO: entry not near extreme")
    else:
        extension = ema9 - current
        distance_extreme = current - recent_low
        result["extension_atr"] = extension / atr
        result["extended"] = extension > MAX_EXTENSION_ATR * atr
        result["near_extreme"] = distance_extreme <= NEAR_EXTREME_ATR * atr
        result["pullback"] = previous >= safe_float(work.iloc[-2]["ema9"]) and current <= ema9
        result["momentum_weak"] = ema9 > prev_ema9
        if result["near_extreme"]:
            result["reasons"].append("BLOCK: near recent LOW")
        elif result["extended"]:
            result["reasons"].append("BLOCK: price extended from 1M EMA9")
        elif result["pullback"]:
            result["reasons"].append("OK: 1M EMA9 reclaim")
        else:
            result["reasons"].append("INFO: entry not near extreme")

    if result["momentum_weak"]:
        result["reasons"].append("WATCH: 1M EMA9 momentum weakening")

    result["timing_ok"] = not result["near_extreme"] and not result["extended"]
    return result


# =========================================================
# RAPID REVERSAL WARNING
# =========================================================

def detect_reversal_warning(df5, df1, trend):
    if trend not in ("BUY", "SELL") or df5 is None or df1 is None:
        return False, []

    warnings = []

    if len(df5) >= 4:
        f = _ema_state(df5, 9, 20)
        last = f.iloc[-1]
        prev = f.iloc[-2]
        ema9 = safe_float(last["ema_fast"])
        ema20 = safe_float(last["ema_slow"])
        prev_ema9 = safe_float(prev["ema_fast"])
        prev_ema20 = safe_float(prev["ema_slow"])
        if trend == "BUY":
            if ema9 is not None and ema20 is not None and ema9 < ema20:
                warnings.append("5M EMA9 crossed below EMA20")
            if prev_ema9 is not None and ema9 is not None and ema9 < prev_ema9 and prev_ema20 is not None and ema20 < prev_ema20:
                warnings.append("5M trend momentum DOWN")
        else:
            if ema9 is not None and ema20 is not None and ema9 > ema20:
                warnings.append("5M EMA9 crossed above EMA20")
            if prev_ema9 is not None and ema9 is not None and ema9 > prev_ema9 and prev_ema20 is not None and ema20 > prev_ema20:
                warnings.append("5M trend momentum UP")

    if len(df1) >= 4:
        f1 = df1.copy()
        f1["ema9"] = calculate_ema(f1["close"], 9)
        last = f1.iloc[-1]
        prev = f1.iloc[-2]
        price = safe_float(last["close"])
        ema9 = safe_float(last["ema9"])
        prev_price = safe_float(prev["close"])
        prev_ema9 = safe_float(prev["ema9"])
        if None not in (price, ema9, prev_price, prev_ema9):
            if trend == "BUY" and price < ema9 and prev_price < prev_ema9:
                warnings.append("1M price below EMA9")
            if trend == "SELL" and price > ema9 and prev_price > prev_ema9:
                warnings.append("1M price above EMA9")

    return len(warnings) >= 2, warnings


# =========================================================
# V6: 5M REVERSAL / DIVERGENCE / SUPPORT-RESISTANCE / FIBONACCI
# =========================================================

def _recent_swing_levels(df, lookback=SWING_LOOKBACK_5M):
    if df is None or df.empty:
        return None, None
    work = df.tail(lookback).copy()
    highs = pd.to_numeric(work["high"], errors="coerce").dropna()
    lows = pd.to_numeric(work["low"], errors="coerce").dropna()
    if highs.empty or lows.empty:
        return None, None
    return safe_float(highs.max()), safe_float(lows.min())


def _rsi_series(df, period=RSI_PERIOD):
    if df is None or df.empty:
        return pd.Series(dtype=float)
    return calculate_rsi(pd.to_numeric(df["close"], errors="coerce"), period)


def _pivot_points(df, left=PIVOT_LEFT_RIGHT, right=PIVOT_LEFT_RIGHT):
    if df is None or df.empty or len(df) < left + right + 3:
        return [], []
    highs = pd.to_numeric(df["high"], errors="coerce").reset_index(drop=True)
    lows = pd.to_numeric(df["low"], errors="coerce").reset_index(drop=True)
    swing_highs, swing_lows = [], []
    last = len(df) - right - 1
    for i in range(left, last + 1):
        h = safe_float(highs.iloc[i])
        lo = safe_float(lows.iloc[i])
        if h is None or lo is None:
            continue
        if h >= max(highs.iloc[i-left:i].tolist() + highs.iloc[i+1:i+right+1].tolist()):
            swing_highs.append((i, h))
        if lo <= min(lows.iloc[i-left:i].tolist() + lows.iloc[i+1:i+right+1].tolist()):
            swing_lows.append((i, lo))
    return swing_highs, swing_lows


def detect_5m_divergence(df5, trend):
    result = {"detected": False, "type": "NONE", "strength": 0, "reasons": []}
    if df5 is None or df5.empty or len(df5) < DIVERGENCE_LOOKBACK_5M or trend not in ("BUY", "SELL"):
        return result
    work = df5.tail(DIVERGENCE_LOOKBACK_5M).copy().reset_index(drop=True)
    rsi = _rsi_series(work)
    swing_highs, swing_lows = _pivot_points(work)
    if trend == "BUY" and len(swing_highs) >= 2:
        (i1, p1), (i2, p2) = swing_highs[-2], swing_highs[-1]
        r1, r2 = safe_float(rsi.iloc[i1]), safe_float(rsi.iloc[i2])
        if None not in (r1, r2) and p2 > p1 and r2 < r1 - DIVERGENCE_MIN_RSI_GAP:
            result.update({"detected": True, "type": "BEARISH_RSI_DIVERGENCE", "strength": 2})
            result["reasons"].append("5M bearish RSI divergence (HH + lower RSI high)")
    elif trend == "SELL" and len(swing_lows) >= 2:
        (i1, p1), (i2, p2) = swing_lows[-2], swing_lows[-1]
        r1, r2 = safe_float(rsi.iloc[i1]), safe_float(rsi.iloc[i2])
        if None not in (r1, r2) and p2 < p1 and r2 > r1 + DIVERGENCE_MIN_RSI_GAP:
            result.update({"detected": True, "type": "BULLISH_RSI_DIVERGENCE", "strength": 2})
            result["reasons"].append("5M bullish RSI divergence (LL + higher RSI low)")
    return result


def detect_5m_reversal_pattern(df5, trend):
    result = {"detected": False, "pattern": "NONE", "strength": 0, "reasons": []}
    if df5 is None or len(df5) < 3 or trend not in ("BUY", "SELL"):
        return result
    previous, current = df5.iloc[-2], df5.iloc[-1]
    if trend == "BUY":
        if bearish_engulfing(previous, current):
            pattern = "BEARISH_ENGULFING"
        elif shooting_star(current):
            pattern = "SHOOTING_STAR"
        elif bearish_marubozu(current):
            pattern = "BEARISH_MARUBOZU"
        else:
            pattern = "NONE"
    else:
        if bullish_engulfing(previous, current):
            pattern = "BULLISH_ENGULFING"
        elif hammer(current):
            pattern = "HAMMER"
        elif bullish_marubozu(current):
            pattern = "BULLISH_MARUBOZU"
        else:
            pattern = "NONE"
    if pattern != "NONE":
        result.update({"detected": True, "pattern": pattern, "strength": 1})
        result["reasons"].append(f"5M reversal candle: {pattern}")
    return result


def detect_5m_structure_shift(df5, trend):
    result = {
        "shift": False, "break_level": None, "reclaim": False,
        "ema_cross": False, "momentum": False, "choch": False,
        "bos": False, "higher_low": False, "lower_high": False,
        "reversal_direction": "NONE", "strength": 0, "reasons": [],
    }
    if df5 is None or df5.empty or len(df5) < 25 or trend not in ("BUY", "SELL"):
        return result

    work = _ema_state(df5.copy(), 9, 20).reset_index(drop=True)
    close = pd.to_numeric(work["close"], errors="coerce")
    ema9 = pd.to_numeric(work["ema_fast"], errors="coerce")
    ema20 = pd.to_numeric(work["ema_slow"], errors="coerce")
    swing_highs, swing_lows = _pivot_points(work.tail(SWING_LOOKBACK_5M).reset_index(drop=True))
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return result

    last = safe_float(close.iloc[-1])
    prev = safe_float(close.iloc[-2])
    last_ema9, prev_ema9 = safe_float(ema9.iloc[-1]), safe_float(ema9.iloc[-2])
    last_ema20, prev_ema20 = safe_float(ema20.iloc[-1]), safe_float(ema20.iloc[-2])
    if None in (last, prev, last_ema9, prev_ema9, last_ema20, prev_ema20):
        return result

    sh1, sh2 = swing_highs[-2][1], swing_highs[-1][1]
    sl1, sl2 = swing_lows[-2][1], swing_lows[-1][1]

    if trend == "BUY":
        if sl2 > sl1:
            result["higher_low"] = True
        if last < sl2:
            result.update({"shift": True, "choch": True, "break_level": sl2,
                           "reversal_direction": "SELL", "strength": 3})
            result["reasons"].append(f"5M CHoCH: close broke last higher-low ({sl2:.2f})")
        elif last > sh2:
            result["bos"] = True
            result["reasons"].append(f"OK: 5M bullish BOS ({sh2:.2f})")
        if prev_ema9 >= prev_ema20 and last_ema9 < last_ema20:
            result["ema_cross"] = True
            result["reasons"].append("5M EMA9/20 bearish cross")
        if last_ema9 < prev_ema9 and last_ema20 < prev_ema20:
            result["momentum"] = True
            result["reasons"].append("5M downside momentum")
    else:
        if sh2 < sh1:
            result["lower_high"] = True
        if last > sh2:
            result.update({"shift": True, "choch": True, "break_level": sh2,
                           "reversal_direction": "BUY", "strength": 3})
            result["reasons"].append(f"5M CHoCH: close broke last lower-high ({sh2:.2f})")
        elif last < sl2:
            result["bos"] = True
            result["reasons"].append(f"OK: 5M bearish BOS ({sl2:.2f})")
        if prev_ema9 <= prev_ema20 and last_ema9 > last_ema20:
            result["ema_cross"] = True
            result["reasons"].append("5M EMA9/20 bullish cross")
        if last_ema9 > prev_ema9 and last_ema20 > prev_ema20:
            result["momentum"] = True
            result["reasons"].append("5M upside momentum")
    return result


def analyze_v7_reversal(df5, trend):
    divergence = detect_5m_divergence(df5, trend)
    pattern = detect_5m_reversal_pattern(df5, trend)
    structure = detect_5m_structure_shift(df5, trend)
    sr = analyze_support_resistance(df5, trend)

    score = 0.0
    categories = 0
    evidence = []
    if structure["choch"]:
        score += 3.0; categories += 1; evidence.append("CHoCH")
    if structure["ema_cross"]:
        score += 2.0; categories += 1; evidence.append("EMA CROSS")
    if structure["momentum"]:
        score += 1.0; categories += 1; evidence.append("MOMENTUM FLIP")
    if divergence["detected"]:
        score += 2.0; categories += 1; evidence.append("DIVERGENCE")
    if pattern["detected"]:
        score += 1.5; categories += 1; evidence.append(pattern["pattern"])
    if sr["near_level"]:
        score += 1.0; categories += 1; evidence.append(sr["level_type"])

    confirmed = (structure["choch"] and categories >= 2 and score >= REVERSAL_CONFIRMATIONS) or score >= REVERSAL_CONFIRMATIONS + 1
    warning = score >= REVERSAL_WARNING_SCORE

    if confirmed:
        state = "CONFIRMED"
    elif warning:
        state = "WARNING"
    else:
        state = "NORMAL"

    reasons = []
    reasons.extend(divergence["reasons"])
    reasons.extend(pattern["reasons"])
    reasons.extend(structure["reasons"])
    if sr["near_level"]:
        reasons.append(f"5M price near {sr['level_type'].lower()} ({sr['level']:.2f})")
    if state == "CONFIRMED":
        reasons.append(f"BLOCK: 5M REVERSAL CONFIRMED ({score:.1f} points / {categories} categories)")
    elif state == "WARNING":
        reasons.append(f"WATCH: 5M REVERSAL WARNING ({score:.1f} points / {categories} categories)")
    else:
        reasons.append("OK: 5M reversal engine normal")

    return {
        "state": state,
        "score": score,
        "categories": categories,
        "reversal": confirmed,
        "confirmations": categories,
        "reversal_direction": structure.get("reversal_direction", "NONE"),
        "reversal_type": divergence["type"] if divergence["detected"] else (pattern["pattern"] if pattern["detected"] else ("CHoCH" if structure["choch"] else "NONE")),
        "divergence": divergence,
        "pattern": pattern,
        "structure": structure,
        "sr": sr,
        "reasons": reasons,
        "evidence": evidence,
    }


def analyze_fibonacci_zone(df5, trend):
    result = {
        "valid": False,
        "in_zone": False,
        "ratio": None,
        "swing_high": None,
        "swing_low": None,
        "reasons": [],
    }
    if df5 is None or df5.empty or len(df5) < 12 or trend not in ("BUY", "SELL"):
        return result

    work = df5.tail(SWING_LOOKBACK_5M).copy().reset_index(drop=True)
    highs = pd.to_numeric(work["high"], errors="coerce")
    lows = pd.to_numeric(work["low"], errors="coerce")
    current = safe_float(work.iloc[-1]["close"])
    if current is None or highs.isna().all() or lows.isna().all():
        return result

    high_idx = int(highs.idxmax())
    low_idx = int(lows.idxmin())
    swing_high = safe_float(highs.max())
    swing_low = safe_float(lows.min())
    if None in (swing_high, swing_low) or swing_high <= swing_low:
        return result

    rng = swing_high - swing_low
    if trend == "BUY":
        ratio = (swing_high - current) / rng
    else:
        ratio = (current - swing_low) / rng

    result.update({
        "valid": True,
        "ratio": ratio,
        "swing_high": swing_high,
        "swing_low": swing_low,
        "in_zone": FIB_ZONE_LOW <= ratio <= FIB_ZONE_HIGH,
    })
    if result["in_zone"]:
        result["reasons"].append(f"OK: 5M Fibonacci pullback zone ({ratio*100:.1f}%)")
    elif ratio < FIB_ZONE_LOW:
        result["reasons"].append(f"INFO: shallow Fibonacci pullback ({ratio*100:.1f}%)")
    else:
        result["reasons"].append(f"WATCH: deep Fibonacci pullback ({ratio*100:.1f}%)")
    return result


def analyze_support_resistance(df5, trend):
    result = {
        "near_level": False,
        "level_type": "NONE",
        "level": None,
        "distance_atr": None,
        "reasons": [],
    }
    if df5 is None or df5.empty or len(df5) < 20 or trend not in ("BUY", "SELL"):
        return result

    atr = calculate_atr(df5)
    recent_high, recent_low = _recent_swing_levels(df5)
    current = safe_float(df5.iloc[-1]["close"])
    if None in (atr, current, recent_high, recent_low) or atr <= 0:
        return result

    if trend == "BUY":
        distance = abs(current - recent_low) / atr
        result.update({"distance_atr": distance, "level": recent_low, "level_type": "SUPPORT"})
        if distance <= SR_ATR_DISTANCE:
            result["near_level"] = True
            result["reasons"].append(f"OK: near 5M support ({recent_low:.2f})")
        else:
            result["reasons"].append("INFO: not near 5M support")
    else:
        distance = abs(recent_high - current) / atr
        result.update({"distance_atr": distance, "level": recent_high, "level_type": "RESISTANCE"})
        if distance <= SR_ATR_DISTANCE:
            result["near_level"] = True
            result["reasons"].append(f"OK: near 5M resistance ({recent_high:.2f})")
        else:
            result["reasons"].append("INFO: not near 5M resistance")
    return result


def analyze_5m_pullback(df5, trend):
    result = {
        "valid": False,
        "reclaim": False,
        "ratio": None,
        "reasons": [],
    }
    if df5 is None or df5.empty or len(df5) < 25 or trend not in ("BUY", "SELL"):
        return result

    work = _ema_state(df5.copy(), 9, 20).reset_index(drop=True)
    close = pd.to_numeric(work["close"], errors="coerce")
    ema9 = pd.to_numeric(work["ema_fast"], errors="coerce")
    ema20 = pd.to_numeric(work["ema_slow"], errors="coerce")
    current = safe_float(close.iloc[-1])
    previous = safe_float(close.iloc[-2])
    e9 = safe_float(ema9.iloc[-1])
    pe9 = safe_float(ema9.iloc[-2])
    e20 = safe_float(ema20.iloc[-1])
    if None in (current, previous, e9, pe9, e20):
        return result

    fib = analyze_fibonacci_zone(df5, trend)
    ratio = fib["ratio"]
    result["ratio"] = ratio

    if trend == "BUY":
        reclaim = previous <= pe9 and current >= e9
        aligned = e9 > e20
    else:
        reclaim = previous >= pe9 and current <= e9
        aligned = e9 < e20

    result["reclaim"] = reclaim
    result["valid"] = bool(aligned and ratio is not None and PULLBACK_MIN_RATIO_5M <= ratio <= PULLBACK_MAX_RATIO_5M)
    if result["valid"]:
        result["reasons"].append("OK: 5M structural pullback")
    else:
        result["reasons"].append("WAIT: 5M structural pullback")
    if reclaim:
        result["reasons"].append("OK: 5M EMA9 reclaim")
    else:
        result["reasons"].append("WAIT: 5M EMA9 reclaim")
    return result

# =========================================================
# MAIN SIGNAL (با پشتیبانی از EASY_MODE)
# =========================================================

def generate_scalper_signal(df15, df5, df1):
    reasons = []

    if df15 is None or df5 is None or df1 is None or df15.empty or df5.empty or df1.empty:
        return {
            "signal": "NO SIGNAL", "price": None, "score": 0,
            "confidence": 0, "quality": "WEAK", "trend": "NONE",
            "rsi": None, "atr": None, "pattern": "NONE",
            "stage": "DATA", "trend_phase": "UNKNOWN", "wave_stage": "UNKNOWN",
            "reversal_confirmations": 0,
            "reasons": ["Insufficient market data"],
        }

    last1 = df1.iloc[-1]
    price = safe_float(last1.get("close"))
    trend_state = get_trend_state(df15)
    trend = trend_state["trend"]
    phase = trend_state["phase"]

    if trend == "NONE":
        return {
            "signal": "NO SIGNAL", "price": price, "score": 0,
            "confidence": 0, "quality": "WEAK", "trend": "NONE",
            "rsi": None, "atr": calculate_atr(df1), "pattern": "NONE",
            "stage": "WAIT", "trend_phase": phase, "wave_stage": "UNKNOWN",
            "trend_age_bars": trend_state["age_bars"],
            "reversal_confirmations": 0,
            "reasons": ["WAIT: 15M trend"],
        }

    reasons.append(f"OK: 15M trend ({trend})")
    reasons.append(f"INFO: 15M trend phase ({phase})")

    # =====================================================
    # 5M reversal engine
    # =====================================================
    reversal = analyze_v7_reversal(df5, trend)
    reasons.extend(reversal["reasons"])

    if reversal["reversal"]:
        return {
            "signal": "NO SIGNAL", "price": price, "score": 0,
            "confidence": 0, "quality": "WEAK", "trend": trend,
            "trend_phase": phase, "trend_age_bars": trend_state["age_bars"],
            "rsi": None, "atr": calculate_atr(df1), "pattern": "NONE",
            "pattern_direction": "NONE", "stage": "REVERSAL_WARNING",
            "wave_stage": "REVERSAL_5M", "reversal_confirmations": reversal["confirmations"],
            "reversal_score": reversal["score"],
            "reversal_state": reversal["state"],
            "reversal_direction": reversal["reversal_direction"],
            "reversal_type": reversal["reversal_type"],
            "reasons": reasons,
        }

    # =====================================================
    # 5M pullback / Fibonacci / S&R
    # =====================================================
    pullback5 = analyze_5m_pullback(df5, trend)
    fib = analyze_fibonacci_zone(df5, trend)
    sr = analyze_support_resistance(df5, trend)
    reasons.extend(pullback5["reasons"])
    reasons.extend(fib["reasons"])
    reasons.extend(sr["reasons"])

    # =====================================================
    # V7: early 5M reversal protection
    # =====================================================
    early_reversal_block = False
    if not EASY_MODE:
        if reversal["state"] == "WARNING" and phase in ("MATURE", "LATE"):
            reasons.append("BLOCK: MATURE/LATE trend has 5M reversal WARNING")
            early_reversal_block = True

    # =====================================================
    # 1M entry confirmation
    # =====================================================
    score = 20  # 15M trend

    if pullback5["valid"]:
        score += 20
    if pullback5["reclaim"]:
        score += 10
    if fib["in_zone"]:
        score += 10
    if sr["near_level"]:
        score += 10

    # 1M RSI
    rsi_ok, rsi = check_rsi(df1, trend)
    if rsi_ok:
        score += 10
        reasons.append("OK: 1M RSI")
    else:
        reasons.append("WAIT: 1M RSI")

    # 1M candle strength
    candle = candle_info(last1)
    candle_ok = (candle["bullish"] and candle["strong"]) if trend == "BUY" else (candle["bearish"] and candle["strong"])
    if candle_ok:
        score += 10
        reasons.append("OK: strong 1M candle")
    else:
        reasons.append("WAIT: candle")

    # 1M pattern
    pattern = detect_candlestick_pattern(df1)
    pattern_side = pattern_direction(pattern)
    if pattern != "NONE" and pattern_side == trend:
        score += 10
        reasons.append(f"OK: {pattern}")
    elif pattern != "NONE":
        reasons.append(f"WAIT: opposite 1M pattern ({pattern})")
    else:
        reasons.append("INFO: no 1M candlestick pattern")

    timing = analyze_entry_timing(df1, trend)
    reasons.extend(timing["reasons"])

    # =====================================================
    # ENTRY RULES (با در نظر گرفتن EASY_MODE)
    # =====================================================
    hard_block = early_reversal_block

    if not EASY_MODE:
        if phase == "LATE":
            if not (pullback5["valid"] and pullback5["reclaim"] and fib["in_zone"]):
                reasons.append("BLOCK: LATE trend requires fresh 5M pullback + reclaim + Fibonacci zone")
                hard_block = True

        if phase == "MATURE":
            if not (pullback5["valid"] and pullback5["reclaim"]):
                reasons.append("BLOCK: MATURE trend requires fresh 5M pullback + reclaim")
                hard_block = True
    else:
        # در حالت EASY، فقط یک هشدار می‌دهیم، نه بلاک
        if phase in ("MATURE", "LATE"):
            if not (pullback5["valid"] and pullback5["reclaim"]):
                reasons.append("WATCH: MATURE/LATE trend could use pullback+reclaim")

    if timing["near_extreme"]:
        reasons.append("BLOCK: entry too close to recent 1M extreme")
        hard_block = True

    if timing["extended"]:
        reasons.append("BLOCK: price extended from 1M EMA9")
        hard_block = True

    if not EASY_MODE:
        if reversal["confirmations"] == 1 and phase in ("MATURE", "LATE"):
            reasons.append("BLOCK: mature/late trend has early 5M reversal evidence")
            hard_block = True

    confidence = min(int(score), 100)
    signal = "NO SIGNAL"

    if score >= SIGNAL_SCORE and not hard_block and timing["timing_ok"]:
        signal = trend
    elif score >= SIGNAL_SCORE:
        reasons.append("BLOCK: structural/timing filter")

    if score >= 90:
        quality = "VERY STRONG"
    elif score >= 75:
        quality = "STRONG"
    elif score >= 60:
        quality = "NORMAL"
    else:
        quality = "WEAK"

    if signal == "NO SIGNAL" and score >= WATCH_SCORE:
        reasons.append("WATCH: setup developing")

    stage = "ENTRY" if signal in ("BUY", "SELL") else ("WATCH" if score >= WATCH_SCORE else "WAIT")

    # Wave analysis (برای سازگاری با خروجی)
    wave = analyze_impulse_wave(df1, trend)

    return {
        "signal": signal,
        "price": price,
        "score": score,
        "confidence": confidence,
        "quality": quality,
        "trend": trend,
        "trend_phase": phase,
        "trend_age_bars": trend_state["age_bars"],
        "rsi": rsi,
        "atr": timing["atr"],
        "pattern": pattern,
        "pattern_direction": pattern_side,
        "entry_timing_ok": bool(timing["timing_ok"] and not hard_block),
        "pullback": bool(pullback5["valid"] and pullback5["reclaim"]),
        "near_extreme": timing["near_extreme"],
        "extended": timing["extended"],
        "extension_atr": timing["extension_atr"],
        "recent_high": timing["recent_high"],
        "recent_low": timing["recent_low"],
        "wave_stage": "PULLBACK" if pullback5["valid"] else wave["wave_stage"],
        "wave_low": wave["wave_low"],
        "wave_high": wave["wave_high"],
        "wave_range": wave["wave_range"],
        "wave_position": wave["wave_position"],
        "pullback_ratio": fib["ratio"],
        "pullback_atr": wave["pullback_atr"],
        "fresh_pullback": pullback5["valid"],
        "reclaim": pullback5["reclaim"],
        "chasing": bool(timing["near_extreme"] or timing["extended"]),
        "structure_ok": bool(pullback5["valid"] and not hard_block),
        "reversal_confirmations": reversal["confirmations"],
        "reversal_score": reversal["score"],
        "reversal_state": reversal["state"],
        "reversal_direction": reversal["reversal_direction"],
        "reversal_type": reversal["reversal_type"],
        "fib_in_zone": fib["in_zone"],
        "fib_ratio": fib["ratio"],
        "fib_swing_high": fib["swing_high"],
        "fib_swing_low": fib["swing_low"],
        "near_support_resistance": sr["near_level"],
        "sr_level_type": sr["level_type"],
        "sr_level": sr["level"],
        "stage": stage,
        "reversal_evidence": reversal["evidence"],
        "reasons": reasons,
        "time": str(last1.get("time", "")),
    }

