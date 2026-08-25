# =========================================================
# GoldPro+ Scalper V4
#
# 15M Trend -> 5M Momentum -> 1M Pullback/Entry
#
# V4 هدف:
# - تشخیص سریع تغییر روند
# - جلوگیری از ورود در انتهای حرکت
# - جلوگیری از تعقیب قیمت نزدیک سقف/کف
# - ترجیح Pullback + Continuation
# - حتی Score=100 بدون Entry-Quality اجازه ورود ندارد
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

# V4 trend / timing filters
RECENT_LOOKBACK_1M = 30
RECENT_LOOKBACK_5M = 12
TREND_CROSS_LOOKBACK_15M = 8
TREND_CROSS_LOOKBACK_5M = 4

# چند ATR از کف/سقف اخیر که بعد از آن ورود تعقیبی ممنوع است
MAX_EXTENSION_ATR = 2.20
NEAR_EXTREME_ATR = 0.65

# حداقل امتیاز مرحله ورود
ENTRY_QUALITY_MIN = 75


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
# ATR HELPER
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
        return {
            "trend": "NONE", "age_bars": None, "phase": "UNKNOWN",
            "ema9": None, "ema20": None, "price": None,
            "fresh": False,
        }

    df = _ema_state(df15, EMA_TREND_FAST, EMA_TREND_SLOW)
    last = df.iloc[-1]
    price = safe_float(last["close"])
    ema9 = safe_float(last["ema_fast"])
    ema20 = safe_float(last["ema_slow"])

    if None in (price, ema9, ema20):
        return {"trend": "NONE", "age_bars": None, "phase": "UNKNOWN", "ema9": ema9, "ema20": ema20, "price": price, "fresh": False}

    spread = ema9 - ema20
    if price > ema9 and spread > 0:
        trend = "BUY"
        age = _bars_since_sign_change(df["ema_fast"] - df["ema_slow"], 1)
    elif price < ema9 and spread < 0:
        trend = "SELL"
        age = _bars_since_sign_change(df["ema_fast"] - df["ema_slow"], -1)
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


def get_5m_momentum_state(df5, trend):
    if df5 is None or df5.empty or len(df5) < 25 or trend not in ("BUY", "SELL"):
        return {"ok": False, "shift": False, "slope_ok": False, "ema9": None, "ema20": None, "age_bars": None}

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
    shift = age is not None and age <= TREND_CROSS_LOOKBACK_5M

    return {"ok": alignment, "shift": shift, "slope_ok": slope_ok, "ema9": ema9, "ema20": ema20, "age_bars": age}


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
# ENTRY TIMING / LATE MOVE FILTER
# =========================================================

def analyze_entry_timing(df1, df5, trend):
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

    lookback = work.iloc[-RECENT_LOOKBACK_1M:]
    current = safe_float(work.iloc[-1]["close"])
    previous = safe_float(work.iloc[-2]["close"])
    if current is None or previous is None:
        result["reasons"].append("WAIT: entry price")
        return result

    recent_high = safe_float(lookback["high"].max())
    recent_low = safe_float(lookback["low"].min())
    result["recent_high"] = recent_high
    result["recent_low"] = recent_low

    # 1M EMA9
    work["ema9"] = calculate_ema(work["close"], 9)
    ema9 = safe_float(work.iloc[-1]["ema9"])
    prev_ema9 = safe_float(work.iloc[-2]["ema9"])

    if atr is None or atr <= 0 or ema9 is None:
        result["reasons"].append("WAIT: entry volatility")
        return result

    if trend == "BUY":
        extension = current - ema9
        distance_extreme = recent_high - current
        move_from_opposite = current - recent_low
        result["extension_atr"] = extension / atr
        result["extended"] = extension > MAX_EXTENSION_ATR * atr
        result["near_extreme"] = distance_extreme <= NEAR_EXTREME_ATR * atr

        # Pullback + reclaim: previous close at/below EMA9, current back above it.
        result["pullback"] = previous <= safe_float(work.iloc[-2]["ema9"]) and current >= ema9
        result["momentum_weak"] = (
            prev_ema9 is not None
            and ema9 < prev_ema9
        )

        if result["near_extreme"]:
            result["reasons"].append("BLOCK: near recent HIGH")
        elif result["extended"]:
            result["reasons"].append("BLOCK: price extended from 1M EMA9")
        elif result["pullback"]:
            result["reasons"].append("OK: 1M pullback/reclaim")
        else:
            result["reasons"].append("OK: entry not near extreme")

        if result["momentum_weak"]:
            result["reasons"].append("WARN: 1M EMA9 momentum weakening")

        # Strong move without pullback is allowed only if it is not extended.
        result["timing_ok"] = not result["near_extreme"] and not result["extended"] and not result["momentum_weak"]

    else:
        extension = ema9 - current
        distance_extreme = current - recent_low
        move_from_opposite = recent_high - current
        result["extension_atr"] = extension / atr
        result["extended"] = extension > MAX_EXTENSION_ATR * atr
        result["near_extreme"] = distance_extreme <= NEAR_EXTREME_ATR * atr
        result["pullback"] = previous >= safe_float(work.iloc[-2]["ema9"]) and current <= ema9
        result["momentum_weak"] = prev_ema9 is not None and ema9 > prev_ema9

        if result["near_extreme"]:
            result["reasons"].append("BLOCK: near recent LOW")
        elif result["extended"]:
            result["reasons"].append("BLOCK: price extended from 1M EMA9")
        elif result["pullback"]:
            result["reasons"].append("OK: 1M pullback/reclaim")
        else:
            result["reasons"].append("OK: entry not near extreme")

        if result["momentum_weak"]:
            result["reasons"].append("WARN: 1M EMA9 momentum weakening")

        result["timing_ok"] = not result["near_extreme"] and not result["extended"] and not result["momentum_weak"]

    return result


# =========================================================
# RAPID REVERSAL / TREND WEAKENING
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
            if prev_ema9 is not None and ema9 is not None and ema9 < prev_ema9:
                warnings.append("5M EMA9 slope DOWN")
        else:
            if ema9 is not None and ema20 is not None and ema9 > ema20:
                warnings.append("5M EMA9 crossed above EMA20")
            if prev_ema9 is not None and ema9 is not None and ema9 > prev_ema9:
                warnings.append("5M EMA9 slope UP")

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
# MAIN SIGNAL V4
# =========================================================

def generate_scalper_signal(df15, df5, df1):
    reasons = []

    if df15 is None or df5 is None or df1 is None or df15.empty or df5.empty or df1.empty:
        return {
            "signal": "NO SIGNAL", "price": None, "score": 0,
            "confidence": 0, "quality": "WEAK", "trend": "NONE",
            "rsi": None, "atr": None, "pattern": "NONE",
            "stage": "DATA", "trend_phase": "UNKNOWN",
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
            "stage": "WAIT", "trend_phase": phase,
            "trend_age_bars": trend_state["age_bars"],
            "reasons": ["WAIT: 15M trend"],
        }

    reasons.append(f"OK: 15M trend ({trend})")
    reasons.append(f"INFO: 15M trend phase ({phase})")

    # Rapid reversal block before scoring.
    reversal, reversal_warnings = detect_reversal_warning(df5, df1, trend)
    if reversal:
        reasons.extend(f"BLOCK: {w}" for w in reversal_warnings)
        return {
            "signal": "NO SIGNAL", "price": price, "score": 0,
            "confidence": 0, "quality": "WEAK", "trend": trend,
            "rsi": None, "atr": calculate_atr(df1), "pattern": "NONE",
            "stage": "REVERSAL_WARNING", "trend_phase": phase,
            "trend_age_bars": trend_state["age_bars"],
            "reasons": reasons,
        }

    # Score: base trend 25 + 5M EMA 20 + 5M momentum 15 + RSI 15 + candle 10 + pattern 15 = 100
    score = 25

    ema_ok = check_5m_ema(df5, trend)
    if ema_ok:
        score += 20
        reasons.append("OK: 5M EMA9")
    else:
        reasons.append("WAIT: 5M EMA9")

    momentum = get_5m_momentum_state(df5, trend)
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

    # Timing filter is NOT just a score item; it is a hard gate.
    timing = analyze_entry_timing(df1, df5, trend)
    reasons.extend(timing["reasons"])

    # Mature/Late trend requires a pullback. Early/Developing may enter continuation.
    late_phase = phase in ("MATURE", "LATE")
    if late_phase and not timing["pullback"]:
        reasons.append("BLOCK: late trend without pullback")
        timing["timing_ok"] = False

    # If trend is very old and price is extended, hard block.
    if phase == "LATE" and timing["extended"]:
        reasons.append("BLOCK: late + extended move")
        timing["timing_ok"] = False

    # Near recent extreme is always a hard block for fresh entries.
    if timing["near_extreme"]:
        reasons.append("BLOCK: entry too close to recent extreme")
        timing["timing_ok"] = False

    confidence = min(int(score), 100)
    signal = "NO SIGNAL"

    if score >= SIGNAL_SCORE and timing["timing_ok"]:
        signal = trend
    elif score >= SIGNAL_SCORE:
        reasons.append("BLOCK: timing filter")

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
        "entry_timing_ok": timing["timing_ok"],
        "pullback": timing["pullback"],
        "near_extreme": timing["near_extreme"],
        "extended": timing["extended"],
        "extension_atr": timing["extension_atr"],
        "recent_high": timing["recent_high"],
        "recent_low": timing["recent_low"],
        "stage": stage,
        "reasons": reasons,
        "time": str(last1.get("time", "")),
    }
