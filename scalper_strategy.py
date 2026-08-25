# =========================================================
# GoldPro+ Scalper V5
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
# SETTINGS
# =========================================================

EMA_FAST = 9
EMA_TREND_FAST = 9
EMA_TREND_SLOW = 20
RSI_PERIOD = 14

SIGNAL_SCORE = 75
WATCH_SCORE = 60
CANDLE_BODY_MIN = 0.45

# 1M wave/structure settings
WAVE_LOOKBACK_1M = 60
PULLBACK_LOOKBACK_1M = 15
MIN_PULLBACK_RATIO = 0.30
MAX_ENTRY_POSITION = 0.68
HARD_MAX_ENTRY_POSITION = 0.78
MIN_PULLBACK_ATR = 1.20

# Extension / extreme filters
MAX_EXTENSION_ATR = 2.00
NEAR_EXTREME_ATR = 0.65

# Fast 5M trend-change detection
FAST_CROSS_LOOKBACK_5M = 3


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
        return ((50 <= current <= 68) or (previous <= 50 and current > previous)), current
    return ((32 <= current <= 50) or (previous >= 50 and current < previous)), current


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

        # Lowest point before the impulse high.
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

        # Pullback must be recent. A pullback from an old high is not a fresh entry.
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

        # If price has already travelled deep into the impulse, a small 1M bounce is chasing.
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

    # Do not hard-block solely on one weakening EMA tick; wave structure decides.
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
# MAIN SIGNAL V5
# =========================================================

def generate_scalper_signal(df15, df5, df1):
    reasons = []

    if df15 is None or df5 is None or df1 is None or df15.empty or df5.empty or df1.empty:
        return {
            "signal": "NO SIGNAL", "price": None, "score": 0,
            "confidence": 0, "quality": "WEAK", "trend": "NONE",
            "rsi": None, "atr": None, "pattern": "NONE",
            "stage": "DATA", "trend_phase": "UNKNOWN", "wave_stage": "UNKNOWN",
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
            "reasons": ["WAIT: 15M trend"],
        }

    reasons.append(f"OK: 15M trend ({trend})")
    reasons.append(f"INFO: 15M trend phase ({phase})")

    momentum = get_5m_momentum_state(df5, trend)
    if momentum["shift"]:
        reasons.append("⚡ INFO: rapid 5M trend shift detected")

    reversal, reversal_warnings = detect_reversal_warning(df5, df1, trend)
    if reversal:
        reasons.extend(f"BLOCK: {w}" for w in reversal_warnings)
        return {
            "signal": "NO SIGNAL", "price": price, "score": 0,
            "confidence": 0, "quality": "WEAK", "trend": trend,
            "rsi": None, "atr": calculate_atr(df1), "pattern": "NONE",
            "stage": "REVERSAL_WARNING", "trend_phase": phase,
            "trend_age_bars": trend_state["age_bars"], "wave_stage": "REVERSAL_RISK",
            "reasons": reasons,
        }

    # Score measures confirmation strength only. It can NEVER override structure/timing.
    score = 25

    ema_ok = check_5m_ema(df5, trend)
    if ema_ok:
        score += 20
        reasons.append("OK: 5M EMA9")
    else:
        reasons.append("WAIT: 5M EMA9")

    if momentum["ok"] and momentum["slope_ok"]:
        score += 15
        reasons.append("OK: 5M momentum")
    elif momentum["ok"]:
        score += 8
        reasons.append("WATCH: 5M momentum flat")
    else:
        reasons.append("WAIT: 5M momentum")

    rsi_ok, rsi = check_rsi(df1, trend)
    if rsi_ok:
        score += 15
        reasons.append("OK: 1M RSI")
    else:
        reasons.append("WAIT: 1M RSI")

    candle = candle_info(last1)
    candle_ok = (candle["bullish"] and candle["strong"]) if trend == "BUY" else (candle["bearish"] and candle["strong"])
    if candle_ok:
        score += 10
        reasons.append("OK: strong 1M candle")
    else:
        reasons.append("WAIT: candle")

    pattern = detect_candlestick_pattern(df1)
    pattern_side = pattern_direction(pattern)
    if pattern != "NONE" and pattern_side == trend:
        score += 15
        reasons.append(f"OK: {pattern}")
    elif pattern != "NONE":
        reasons.append(f"WAIT: opposite pattern ({pattern})")
    else:
        reasons.append("WAIT: candlestick pattern")

    timing = analyze_entry_timing(df1, trend)
    reasons.extend(timing["reasons"])

    wave = analyze_impulse_wave(df1, trend)
    reasons.extend(wave["reasons"])

    # =====================================================
    # HARD STRUCTURAL ENTRY RULES
    # =====================================================

    hard_block = False

    # Late trend: no chasing. A late move is allowed only after a fresh structural pullback + reclaim,
    # and even then the price must not be too deep in the original impulse.
    if phase == "LATE":
        if not (wave["fresh_pullback"] and wave["reclaim"] and wave["wave_position"] is not None and wave["wave_position"] < 0.70):
            reasons.append("BLOCK: LATE trend requires fresh structural pullback + reclaim")
            hard_block = True

    # Mature trend: pullback/reclaim required. No continuation chase.
    if phase == "MATURE":
        if not (wave["fresh_pullback"] and wave["reclaim"]):
            reasons.append("BLOCK: MATURE trend requires fresh structural pullback + reclaim")
            hard_block = True

    # Deep impulse: score does not matter.
    if wave["chasing"]:
        reasons.append("BLOCK: entry is chasing the current impulse")
        hard_block = True

    # If position is beyond 78% of the identified impulse, only a new structural cycle may reset entry.
    if wave["wave_position"] is not None and wave["wave_position"] >= HARD_MAX_ENTRY_POSITION:
        reasons.append("BLOCK: price is in the final part of the impulse")
        hard_block = True

    if timing["near_extreme"]:
        reasons.append("BLOCK: entry too close to recent extreme")
        hard_block = True

    if timing["extended"]:
        reasons.append("BLOCK: price extended from 1M EMA9")
        hard_block = True

    # A pullback/reclaim is only considered a valid new entry when it is structural, not a 1-candle dip.
    if phase in ("MATURE", "LATE") and wave["fresh_pullback"] and not wave["reclaim"]:
        reasons.append("BLOCK: pullback exists but reclaim is not confirmed")
        hard_block = True

    confidence = min(int(score), 100)
    signal = "NO SIGNAL"

    if score >= SIGNAL_SCORE and not hard_block and timing["timing_ok"] and wave["structure_ok"]:
        signal = trend
    elif score >= SIGNAL_SCORE:
        reasons.append("BLOCK: structural entry filter")

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
        "pullback": bool(wave["fresh_pullback"] and wave["reclaim"]),
        "near_extreme": timing["near_extreme"],
        "extended": timing["extended"],
        "extension_atr": timing["extension_atr"],
        "recent_high": timing["recent_high"],
        "recent_low": timing["recent_low"],
        "wave_stage": wave["wave_stage"],
        "wave_low": wave["wave_low"],
        "wave_high": wave["wave_high"],
        "wave_range": wave["wave_range"],
        "wave_position": wave["wave_position"],
        "pullback_ratio": wave["pullback_ratio"],
        "pullback_atr": wave["pullback_atr"],
        "fresh_pullback": wave["fresh_pullback"],
        "reclaim": wave["reclaim"],
        "chasing": wave["chasing"],
        "structure_ok": wave["structure_ok"],
        "stage": stage,
        "reasons": reasons,
        "time": str(last1.get("time", "")),
    }
