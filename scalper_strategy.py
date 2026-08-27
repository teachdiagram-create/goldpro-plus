# =========================================================
# قسمت اول: اصلاح safe_float
# =========================================================

def safe_float(value):
    """Convert to float, return None if invalid or NaN."""
    try:
        val = float(value)
        if pd.isna(val):
            return None
        return val
    except Exception:
        return None


# =========================================================
# اصلاح get_trend_state
# =========================================================

def get_trend_state(df15):
    if df15 is None or df15.empty or len(df15) < 25:
        return {
            "trend": "NONE",
            "age_bars": None,
            "phase": "UNKNOWN",
            "ema9": None,
            "ema20": None,
            "price": None,
            "fresh": False
        }

    df = _ema_state(df15, EMA_TREND_FAST, EMA_TREND_SLOW)
    
    # بررسی وجود ستون‌ها
    if "ema_fast" not in df.columns or "ema_slow" not in df.columns:
        return {
            "trend": "NONE",
            "age_bars": None,
            "phase": "UNKNOWN",
            "ema9": None,
            "ema20": None,
            "price": None,
            "fresh": False
        }

    last = df.iloc[-1]
    price = safe_float(last.get("close"))
    ema9 = safe_float(last.get("ema_fast"))
    ema20 = safe_float(last.get("ema_slow"))

    if None in (price, ema9, ema20):
        return {
            "trend": "NONE",
            "age_bars": None,
            "phase": "UNKNOWN",
            "ema9": ema9,
            "ema20": ema20,
            "price": price,
            "fresh": False
        }

    spread = df["ema_fast"] - df["ema_slow"]
    if spread.empty or pd.isna(spread.iloc[-1]):
        return {
            "trend": "NONE",
            "age_bars": None,
            "phase": "UNKNOWN",
            "ema9": ema9,
            "ema20": ema20,
            "price": price,
            "fresh": False
        }

    # تعیین ترند
    if price > ema9 and spread.iloc[-1] > 0:
        trend = "BUY"
    elif price < ema9 and spread.iloc[-1] < 0:
        trend = "SELL"
    else:
        trend = "NONE"

    # محاسبه age
    if trend != "NONE":
        wanted = 1 if trend == "BUY" else -1
        age = _bars_since_sign_change(spread, wanted)
    else:
        age = None

    # تعیین phase
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
# اصلاح get_5m_momentum_state
# =========================================================

def get_5m_momentum_state(df5, trend):
    if df5 is None or df5.empty or len(df5) < 25 or trend not in ("BUY", "SELL"):
        return {
            "ok": False,
            "shift": False,
            "slope_ok": False,
            "ema9": None,
            "ema20": None,
            "age_bars": None,
            "spread": None
        }

    df = _ema_state(df5, 9, 20)
    
    if "ema_fast" not in df.columns or "ema_slow" not in df.columns:
        return {
            "ok": False,
            "shift": False,
            "slope_ok": False,
            "ema9": None,
            "ema20": None,
            "age_bars": None,
            "spread": None
        }

    spread = df["ema_fast"] - df["ema_slow"]
    wanted = 1 if trend == "BUY" else -1
    age = _bars_since_sign_change(spread, wanted)

    last = df.iloc[-1]
    prev = df.iloc[-2]
    ema9 = safe_float(last.get("ema_fast"))
    ema20 = safe_float(last.get("ema_slow"))
    prev_ema9 = safe_float(prev.get("ema_fast"))

    if None in (ema9, prev_ema9, ema20):
        return {
            "ok": False,
            "shift": False,
            "slope_ok": False,
            "ema9": ema9,
            "ema20": ema20,
            "age_bars": age,
            "spread": safe_float(spread.iloc[-1])
        }

    slope_ok = ema9 > prev_ema9 if trend == "BUY" else ema9 < prev_ema9
    alignment = ema9 > ema20 if trend == "BUY" else ema9 < ema20
    shift = age is not None and age <= FAST_CROSS_LOOKBACK_5M

    return {
        "ok": alignment,
        "shift": shift,
        "slope_ok": slope_ok,
        "ema9": ema9,
        "ema20": ema20,
        "age_bars": age,
        "spread": safe_float(spread.iloc[-1])
    }


# =========================================================
# اصلاح check_rsi
# =========================================================

def check_rsi(df1, trend):
    if df1 is None or df1.empty or len(df1) < RSI_PERIOD + 2 or trend not in ("BUY", "SELL"):
        return False, None

    df = df1.copy()
    df["rsi"] = calculate_rsi(df["close"], RSI_PERIOD)
    
    current = safe_float(df.iloc[-1].get("rsi"))
    previous = safe_float(df.iloc[-2].get("rsi"))
    
    if None in (current, previous):
        return False, current

    if trend == "BUY":
        return ((50 <= current <= 68) or (previous <= 50 and current > previous)), current
    return ((32 <= current <= 50) or (previous >= 50 and current < previous)), current