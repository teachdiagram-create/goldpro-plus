# hybrid_strategy.py
# =========================================================
# GoldPro+ Hybrid V2 - بدون وابستگی به ta
# =========================================================

import pandas as pd
import numpy as np
from datetime import datetime

# =========================================================
# SETTINGS
# =========================================================

MIN_SCORE = 70
STRONG_SCORE = 85

EMA_FAST = 9
EMA_SLOW = 20
EMA_TREND = 50

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_NEUTRAL_LOW = 40
RSI_NEUTRAL_HIGH = 60

RISK_PER_TRADE = 1.5
STOP_LOSS_ATR = 1.5
TAKE_PROFIT_ATR = 2.5
MAX_SPREAD = 0.5

MIN_VOLUME_RATIO = 1.2
MAX_ATR_CHANGE = 2.0

PULLBACK_MIN = 0.30
PULLBACK_MAX = 0.70
FIB_LEVELS = [0.382, 0.500, 0.618]

TRAILING_STOP = 0.5


# =========================================================
# INDICATORS (محاسبه دستی)
# =========================================================

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series, period=RSI_PERIOD):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def calculate_atr(df, period=14):
    if df is None or df.empty or len(df) < 2:
        return None
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce")
    previous_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - previous_close).abs()
    tr3 = (low - previous_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None


def safe_float(value, default=None):
    try:
        val = float(value)
        if pd.isna(val):
            return default
        return val
    except (TypeError, ValueError):
        return default


def get_latest(df):
    return df.iloc[-1]


def get_previous(df):
    return df.iloc[-2]


# =========================================================
# DATA PREPARATION (بدون وابستگی به indicators.py)
# =========================================================

def prepare_data(df):
    if df is None or df.empty:
        return None
    df_copy = df.copy()
    # محاسبه اندیکاتورها به صورت دستی
    df_copy["EMA9"] = calculate_ema(df_copy["close"], EMA_FAST)
    df_copy["EMA20"] = calculate_ema(df_copy["close"], EMA_SLOW)
    df_copy["EMA50"] = calculate_ema(df_copy["close"], EMA_TREND)
    df_copy["RSI"] = calculate_rsi(df_copy["close"])
    # ATR به صورت سری محاسبه می‌شود
    atr_values = []
    for i in range(len(df_copy)):
        if i < 14:
            atr_values.append(None)
        else:
            atr_values.append(calculate_atr(df_copy.iloc[:i+1]))
    df_copy["ATR"] = atr_values
    return df_copy


# =========================================================
# TREND ANALYSIS (15M)
# =========================================================

def _bars_since_condition(condition, max_bars=50):
    if condition is None:
        return None
    count = 0
    for i in range(len(condition)-1, -1, -1):
        if condition.iloc[i]:
            count += 1
        else:
            break
        if count >= max_bars:
            break
    return count if count > 0 else None


def analyze_trend_15m(df15):
    result = {
        "trend": "NONE",
        "strength": 0,
        "phase": "UNKNOWN",
        "age": None,
        "reasons": []
    }
    if df15 is None or len(df15) < 30:
        result["reasons"].append("Insufficient 15M data")
        return result
    last = get_latest(df15)
    price = safe_float(last.get("close"))
    ema9 = safe_float(last.get("EMA9"))
    ema20 = safe_float(last.get("EMA20"))
    ema50 = safe_float(last.get("EMA50"))
    rsi = safe_float(last.get("RSI"))
    if None in (price, ema9, ema20, ema50, rsi):
        result["reasons"].append("Missing indicators")
        return result
    score = 0
    if price > ema9 > ema20 > ema50:
        result["trend"] = "BUY"
        score += 30
    elif price < ema9 < ema20 < ema50:
        result["trend"] = "SELL"
        score += 30
    else:
        result["trend"] = "NONE"
        result["reasons"].append("EMAs not aligned")
        return result
    if result["trend"] == "BUY" and rsi > 50:
        score += 20
    elif result["trend"] == "SELL" and rsi < 50:
        score += 20
    else:
        result["reasons"].append("RSI neutral")
    spread = df15["EMA9"] - df15["EMA20"]
    if result["trend"] == "BUY":
        age = _bars_since_condition(spread > 0)
    else:
        age = _bars_since_condition(spread < 0)
    result["age"] = age
    if age is None:
        result["phase"] = "UNKNOWN"
    elif age <= 3:
        result["phase"] = "EARLY"
        score += 15
    elif age <= 8:
        result["phase"] = "DEVELOPING"
        score += 10
    elif age <= 15:
        result["phase"] = "MATURE"
    else:
        result["phase"] = "LATE"
        score -= 10
        result["reasons"].append("Late trend, caution")
    result["strength"] = score
    result["reasons"].append(f"15M Trend: {result['trend']} ({result['phase']})")
    return result


# =========================================================
# MOMENTUM ANALYSIS (5M)
# =========================================================

def analyze_fibonacci(df, trend, lookback=24):
    result = {
        "in_zone": False,
        "ratio": None,
        "level": None,
        "reasons": []
    }
    if df is None or len(df) < lookback:
        return result
    work = df.tail(lookback)
    high = safe_float(work["high"].max())
    low = safe_float(work["low"].min())
    current = safe_float(work["close"].iloc[-1])
    if None in (high, low, current) or high == low:
        return result
    if trend == "BUY":
        ratio = (high - current) / (high - low)
    else:
        ratio = (current - low) / (high - low)
    result["ratio"] = ratio
    for level in FIB_LEVELS:
        if abs(ratio - level) < 0.05:
            result["in_zone"] = True
            result["level"] = level
            result["reasons"].append(f"Fibonacci {level*100:.1f}%")
            break
    return result


def detect_reversal_5m(df5, trend):
    result = {
        "detected": False,
        "type": "NONE",
        "strength": 0,
        "reasons": []
    }
    if df5 is None or len(df5) < 10:
        return result
    last = get_latest(df5)
    prev = get_previous(df5)
    rsi_now = safe_float(last.get("RSI"))
    rsi_prev = safe_float(prev.get("RSI"))
    price_now = safe_float(last.get("close"))
    price_prev = safe_float(prev.get("close"))
    if None not in (rsi_now, rsi_prev, price_now, price_prev):
        if trend == "BUY":
            if price_now > price_prev and rsi_now < rsi_prev:
                result["detected"] = True
                result["type"] = "BEARISH_DIVERGENCE"
                result["strength"] += 2
                result["reasons"].append("Bearish RSI divergence")
        else:
            if price_now < price_prev and rsi_now > rsi_prev:
                result["detected"] = True
                result["type"] = "BULLISH_DIVERGENCE"
                result["strength"] += 2
                result["reasons"].append("Bullish RSI divergence")
    return result


def analyze_momentum_5m(df5, trend):
    result = {
        "ok": False,
        "pullback": False,
        "reclaim": False,
        "fib_zone": False,
        "volume_ok": False,
        "reversal_warning": False,
        "reasons": []
    }
    if df5 is None or len(df5) < 30 or trend not in ("BUY", "SELL"):
        result["reasons"].append("Insufficient 5M data")
        return result
    last = get_latest(df5)
    prev = get_previous(df5)
    price = safe_float(last.get("close"))
    prev_price = safe_float(prev.get("close"))
    ema9 = safe_float(last.get("EMA9"))
    ema20 = safe_float(last.get("EMA20"))
    atr = safe_float(last.get("ATR"))
    if None in (price, prev_price, ema9, ema20, atr):
        result["reasons"].append("Missing 5M indicators")
        return result
    if trend == "BUY":
        aligned = ema9 > ema20
    else:
        aligned = ema9 < ema20
    if not aligned:
        result["reasons"].append("5M EMAs not aligned with trend")
        return result
    result["ok"] = True
    result["reasons"].append("5M EMAs aligned")
    if trend == "BUY":
        is_pullback = price < ema9
        is_reclaim = prev_price < ema9 and price > ema9
    else:
        is_pullback = price > ema9
        is_reclaim = prev_price > ema9 and price < ema9
    result["pullback"] = is_pullback
    result["reclaim"] = is_reclaim
    if is_pullback:
        result["reasons"].append("5M Pullback detected")
    if is_reclaim:
        result["reasons"].append("5M Reclaim detected")
    fib = analyze_fibonacci(df5, trend)
    result["fib_zone"] = fib["in_zone"]
    if fib["in_zone"]:
        result["reasons"].append(f"5M Fibonacci zone ({fib['ratio']*100:.1f}%)")
    reversal = detect_reversal_5m(df5, trend)
    result["reversal_warning"] = reversal["detected"]
    if reversal["detected"]:
        result["reasons"].append(f"5M reversal warning: {reversal['type']}")
    return result


# =========================================================
# ENTRY ANALYSIS (1M)
# =========================================================

def analyze_entry_1m(df1, trend):
    result = {
        "ok": False,
        "rsi_ok": False,
        "candle_ok": False,
        "bb_ok": False,
        "reasons": []
    }
    if df1 is None or len(df1) < 20 or trend not in ("BUY", "SELL"):
        result["reasons"].append("Insufficient 1M data")
        return result
    last = get_latest(df1)
    prev = get_previous(df1)
    rsi = safe_float(last.get("RSI"))
    rsi_prev = safe_float(prev.get("RSI"))
    if None in (rsi, rsi_prev):
        result["reasons"].append("RSI missing")
    else:
        if trend == "BUY":
            if rsi <= RSI_OVERSOLD or (rsi_prev <= RSI_OVERSOLD and rsi > RSI_OVERSOLD):
                result["rsi_ok"] = True
                result["reasons"].append("RSI oversold reversal")
            elif RSI_NEUTRAL_LOW <= rsi <= RSI_NEUTRAL_HIGH:
                result["rsi_ok"] = True
                result["reasons"].append("RSI neutral zone")
        else:
            if rsi >= RSI_OVERBOUGHT or (rsi_prev >= RSI_OVERBOUGHT and rsi < RSI_OVERBOUGHT):
                result["rsi_ok"] = True
                result["reasons"].append("RSI overbought reversal")
            elif RSI_NEUTRAL_LOW <= rsi <= RSI_NEUTRAL_HIGH:
                result["rsi_ok"] = True
                result["reasons"].append("RSI neutral zone")
    close = safe_float(last.get("close"))
    open_price = safe_float(last.get("open"))
    prev_close = safe_float(prev.get("close"))
    if None in (close, open_price, prev_close):
        result["reasons"].append("Candle data missing")
    else:
        if trend == "BUY":
            if close > open_price and close > prev_close:
                result["candle_ok"] = True
                result["reasons"].append("Bullish candle")
        else:
            if close < open_price and close < prev_close:
                result["candle_ok"] = True
                result["reasons"].append("Bearish candle")
    score = sum([result["rsi_ok"], result["candle_ok"], result["bb_ok"]])
    result["ok"] = score >= 1
    if not result["ok"]:
        result["reasons"].append("Entry conditions not met")
    return result


# =========================================================
# RISK MANAGEMENT
# =========================================================

def calculate_risk_management(df1, trend, account_balance=10000):
    result = {
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "position_size": 0,
        "risk_reward": 0,
        "reasons": []
    }
    if df1 is None or df1.empty or trend not in ("BUY", "SELL"):
        result["reasons"].append("No data for risk management")
        return result
    last = get_latest(df1)
    price = safe_float(last.get("close"))
    atr = safe_float(last.get("ATR"))
    if None in (price, atr) or atr <= 0:
        result["reasons"].append("Price or ATR missing")
        return result
    result["entry"] = price
    sl_distance = atr * STOP_LOSS_ATR
    tp_distance = atr * TAKE_PROFIT_ATR
    if trend == "BUY":
        result["stop_loss"] = price - sl_distance
        result["take_profit"] = price + tp_distance
    else:
        result["stop_loss"] = price + sl_distance
        result["take_profit"] = price - tp_distance
    risk_amount = account_balance * (RISK_PER_TRADE / 100)
    risk_per_unit = abs(price - result["stop_loss"])
    if risk_per_unit > 0:
        result["position_size"] = risk_amount / risk_per_unit
    else:
        result["position_size"] = 0
    reward = abs(result["take_profit"] - price)
    risk = abs(result["stop_loss"] - price)
    if risk > 0:
        result["risk_reward"] = reward / risk
    else:
        result["risk_reward"] = 0
    return result


# =========================================================
# MAIN SIGNAL GENERATOR
# =========================================================

def generate_hybrid_signal(df15, df5, df1, account_balance=10000):
    if df15 is None or df5 is None or df1 is None:
        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "score": 0,
            "quality": "WEAK",
            "reasons": ["Missing data"]
        }
    df15 = prepare_data(df15)
    df5 = prepare_data(df5)
    df1 = prepare_data(df1)
    if None in (df15, df5, df1):
        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "score": 0,
            "quality": "WEAK",
            "reasons": ["Failed to prepare data"]
        }
    trend_result = analyze_trend_15m(df15)
    trend = trend_result["trend"]
    if trend == "NONE":
        return {
            "signal": "NO SIGNAL",
            "stage": "15M",
            "score": 0,
            "quality": "WEAK",
            "trend": "NONE",
            "reasons": trend_result["reasons"]
        }
    momentum = analyze_momentum_5m(df5, trend)
    if momentum["reversal_warning"]:
        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "score": 0,
            "quality": "WEAK",
            "trend": trend,
            "reasons": ["5M reversal warning"] + momentum["reasons"]
        }
    entry = analyze_entry_1m(df1, trend)
    score = 0
    reasons = []
    filters = {}
    score += min(trend_result["strength"], 30)
    filters["Trend"] = True
    reasons.append(f"15M trend: {trend} ({trend_result['phase']})")
    momentum_score = 0
    if momentum["ok"]:
        momentum_score += 10
    if momentum["pullback"]:
        momentum_score += 10
    if momentum["reclaim"]:
        momentum_score += 5
    if momentum["fib_zone"]:
        momentum_score += 5
    score += min(momentum_score, 30)
    filters["Momentum"] = momentum["ok"]
    reasons.extend(momentum["reasons"])
    entry_score = 0
    if entry["rsi_ok"]:
        entry_score += 15
    if entry["candle_ok"]:
        entry_score += 15
    score += entry_score
    filters["Entry"] = entry["ok"]
    reasons.extend(entry["reasons"])
    risk = calculate_risk_management(df1, trend, account_balance)
    if risk["risk_reward"] >= 2.0:
        score += 10
        reasons.append(f"Good RR: {risk['risk_reward']:.2f}")
    elif risk["risk_reward"] >= 1.5:
        score += 5
        reasons.append(f"OK RR: {risk['risk_reward']:.2f}")
    else:
        reasons.append(f"Low RR: {risk['risk_reward']:.2f}")
    price = safe_float(get_latest(df1).get("close"))
    rsi = safe_float(get_latest(df1).get("RSI"))
    atr = safe_float(get_latest(df1).get("ATR"))
    hard_block = False
    if trend_result["phase"] == "LATE" and not (momentum["pullback"] and momentum["reclaim"]):
        hard_block = True
        reasons.append("BLOCK: Late trend needs pullback + reclaim")
    if trend_result["phase"] == "MATURE" and not momentum["pullback"]:
        hard_block = True
        reasons.append("BLOCK: Mature trend needs pullback")
    signal = "NO SIGNAL"
    quality = "WEAK"
    if score >= MIN_SCORE and not hard_block:
        signal = trend
        quality = "STRONG" if score >= STRONG_SCORE else "NORMAL"
    elif score >= MIN_SCORE and hard_block:
        reasons.append("WAIT: Structure blocking entry")
    else:
        reasons.append(f"WAIT: Score {score} < {MIN_SCORE}")
    return {
        "signal": signal,
        "stage": "ENTRY" if signal != "NO SIGNAL" else "WAIT",
        "trend": trend,
        "trend_phase": trend_result["phase"],
        "score": score,
        "confidence": score,
        "quality": quality,
        "price": price,
        "rsi": rsi,
        "atr": atr,
        "entry": risk["entry"],
        "stop_loss": risk["stop_loss"],
        "take_profit": risk["take_profit"],
        "position_size": risk["position_size"],
        "risk_reward": risk["risk_reward"],
        "filters": filters,
        "reasons": reasons,
        "time": str(get_latest(df1).get("time"))
    }


# =========================================================
# TELEGRAM FORMATTER
# =========================================================

def format_signal_for_telegram(signal_data):
    if signal_data.get("signal") == "NO SIGNAL":
        return f"""
📊 **GoldPro+ Hybrid V2**
⏰ {signal_data.get('time', 'N/A')}
📈 Trend: {signal_data.get('trend', 'NONE')}
🎯 Signal: NO SIGNAL
⭐ Score: {signal_data.get('score', 0)}/100
📝 {signal_data.get('reasons', [''])[0]}
"""
    emoji = "🟢" if signal_data["signal"] == "BUY" else "🔴"
    reasons_text = "\n".join([f"• {r}" for r in signal_data.get('reasons', [])[:5]])
    return f"""
{emoji} **GoldPro+ Hybrid V2 SIGNAL**
⏰ {signal_data.get('time', 'N/A')}

📈 **Trend**: {signal_data['trend']} ({signal_data.get('trend_phase', 'UNKNOWN')})
🎯 **Signal**: {signal_data['signal']}
⭐ **Score**: {signal_data['score']}/100
💪 **Quality**: {signal_data.get('quality', 'WEAK')}

💰 **Entry**: {signal_data.get('entry', 0):.2f}
🛑 **Stop Loss**: {signal_data.get('stop_loss', 0):.2f}
🎯 **Take Profit**: {signal_data.get('take_profit', 0):.2f}
📊 **RR Ratio**: {signal_data.get('risk_reward', 0):.2f}

📊 **Indicators**:
• RSI: {signal_data.get('rsi', 0):.1f}
• ATR: {signal_data.get('atr', 0):.2f}

📝 **Reasons**:
{reasons_text}

#GoldProPlus #TradingSignal
"""
