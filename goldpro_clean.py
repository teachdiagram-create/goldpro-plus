"""
GoldPro+ Clean Version - Early Entry Strategy با SL/TP و جلوگیری از تکرار
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time

# =========================================================
# 📌 تنظیمات
# =========================================================

CONFIG = {
    "API_KEY": os.environ.get('TWELVE_DATA_API_KEY', 'YOUR_API_KEY_HERE'),
    "SYMBOL": "XAU/USD",
    "DAYS_BACK": 3,
    
    "EARLY_ENTRY": True,
    "BOS_LOOKBACK": 5,
    "EARLY_SCORE_THRESHOLD": 50,
    "NORMAL_SCORE_THRESHOLD": 70,
    
    "RSI_OVERSOLD": 45,
    "RSI_OVERBOUGHT": 55,
    
    "ADX_THRESHOLD": 20,
    "ADX_STRONG_THRESHOLD": 35,
    
    "FIB_LOOKBACK": 50,
    "FIB_EARLY_ZONE": 30,
    
    "SR_LOOKBACK": 20,
    "SR_ATR_DISTANCE": 1.0,
    
    "MIN_PRICE_CHANGE_ATR": 0.8,
    "COOLDOWN_MINUTES": 5,
    
    "DEFAULT_RR_RATIO": 2.0,
    "SL_ATR_MULTIPLIER": 1.5,
    "TP1_ATR_MULTIPLIER": 1.0,
    "TP2_ATR_MULTIPLIER": 2.0,
}

# =========================================================
# 📌 وضعیت آخرین سیگنال
# =========================================================

_last_signal_state = {
    "direction": None,
    "price": 0.0,
    "time": None,
    "score": 0
}

# =========================================================
# 📥 دریافت داده
# =========================================================

_cache = {}

def fetch_data(interval, days=None):
    if days is None:
        days = CONFIG["DAYS_BACK"]
    
    cache_key = f"{CONFIG['SYMBOL']}_{interval}_{days}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": CONFIG["SYMBOL"],
        "interval": interval,
        "outputsize": 500,
        "apikey": CONFIG["API_KEY"],
        "start_date": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.status_code == 429:
                wait = (attempt + 1) * 10
                print(f"⚠️ HTTP 429. Waiting {wait}s...")
                time.sleep(wait)
                continue
                
            if resp.status_code != 200:
                print(f"⚠️ HTTP {resp.status_code}")
                return None
            
            data = resp.json()
            if 'values' not in data or len(data['values']) < 50:
                print(f"⚠️ داده کافی نیست")
                return None
            
            df = pd.DataFrame(data['values'])
            
            required_cols = ['datetime', 'open', 'high', 'low', 'close']
            for col in required_cols:
                if col not in df.columns:
                    print(f"⚠️ ستون {col} وجود ندارد")
                    return None
            
            if 'volume' not in df.columns:
                df['volume'] = 0
                
            df = df.rename(columns={
                'datetime': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').set_index('timestamp')
            df = df.astype(float)
            
            _cache[cache_key] = df
            return df
            
        except Exception as e:
            print(f"❌ خطا: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None
    return None

# =========================================================
# 📊 محاسبه اندیکاتورها
# =========================================================

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_adx(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).rolling(period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()
    return adx

def add_indicators(df):
    df = df.copy()
    df['EMA20'] = calculate_ema(df['close'], 20)
    df['EMA50'] = calculate_ema(df['close'], 50)
    df['RSI'] = calculate_rsi(df['close'], 14)
    df['ATR'] = calculate_atr(df, 14)
    df['ADX'] = calculate_adx(df, 14)
    return df

# =========================================================
# 🔍 تشخیص شکست ساختار (BOS)
# =========================================================

def detect_bos(df, lookback=None):
    if lookback is None:
        lookback = CONFIG["BOS_LOOKBACK"]
    
    if len(df) < lookback + 2:
        return None, None
    
    recent_lows = df['low'].iloc[-lookback:-1].min()
    recent_highs = df['high'].iloc[-lookback:-1].max()
    current_close = df['close'].iloc[-1]
    
    if current_close < recent_lows:
        return "SELL", float(recent_lows)
    elif current_close > recent_highs:
        return "BUY", float(recent_highs)
    return None, None

# =========================================================
# 🔍 تشخیص واگرایی RSI
# =========================================================

def detect_rsi_divergence(df, lookback=30):
    if len(df) < lookback + 5:
        return None
    
    rsi = calculate_rsi(df['close'], 14)
    price = df['close']
    
    last_peak_idx = price.iloc[-lookback:].idxmax()
    prev_peak_idx = price.iloc[-lookback*2:-lookback].idxmax() if len(df) > lookback*2 else None
    
    if prev_peak_idx is None:
        return None
    
    if price.loc[last_peak_idx] > price.loc[prev_peak_idx]:
        if rsi.loc[last_peak_idx] < rsi.loc[prev_peak_idx]:
            return "BEARISH"
    elif price.loc[last_peak_idx] < price.loc[prev_peak_idx]:
        if rsi.loc[last_peak_idx] > rsi.loc[prev_peak_idx]:
            return "BULLISH"
    
    return None

# =========================================================
# 📐 فیبوناچی پولبک
# =========================================================

def calc_fib_pullback(df):
    lookback = CONFIG["FIB_LOOKBACK"]
    if len(df) < lookback:
        return None, None, None
    
    high = df['high'].iloc[-lookback:].max()
    low = df['low'].iloc[-lookback:].min()
    if high == low:
        return None, None, None
    
    current = df['close'].iloc[-1]
    pullback = ((high - current) / (high - low)) * 100
    return pullback, high, low

# =========================================================
# 📐 پشتیبانی/مقاومت
# =========================================================

def find_support_resistance(df):
    lookback = CONFIG["SR_LOOKBACK"]
    if len(df) < lookback:
        return None, None
    
    support = df['low'].iloc[-lookback:].min()
    resistance = df['high'].iloc[-lookback:].max()
    return support, resistance

def near_support(df):
    last = df.iloc[-1]
    price = float(last['close'])
    atr = float(last['ATR'])
    support, _ = find_support_resistance(df)
    
    if support is None:
        return False, None
    
    max_dist = max(atr * CONFIG["SR_ATR_DISTANCE"], 0.5)
    distance = abs(price - support)
    return (distance <= max_dist, support)

def near_resistance(df):
    last = df.iloc[-1]
    price = float(last['close'])
    atr = float(last['ATR'])
    _, resistance = find_support_resistance(df)
    
    if resistance is None:
        return False, None
    
    max_dist = max(atr * CONFIG["SR_ATR_DISTANCE"], 0.5)
    distance = abs(price - resistance)
    return (distance <= max_dist, resistance)

# =========================================================
# 🔄 محاسبه SL/TP
# =========================================================

def calculate_sl_tp(signal, price, atr, support=None, resistance=None):
    sl_mult = CONFIG["SL_ATR_MULTIPLIER"]
    tp1_mult = CONFIG["TP1_ATR_MULTIPLIER"]
    tp2_mult = CONFIG["TP2_ATR_MULTIPLIER"]
    
    if signal == "SELL":
        if resistance is not None:
            sl = resistance + atr * 0.3
        else:
            sl = price + atr * sl_mult
        
        tp1 = price - atr * tp1_mult
        tp2 = price - atr * tp2_mult
        
        if tp2 > tp1:
            tp2 = tp1 - atr * 0.5
            
    elif signal == "BUY":
        if support is not None:
            sl = support - atr * 0.3
        else:
            sl = price - atr * sl_mult
        
        tp1 = price + atr * tp1_mult
        tp2 = price + atr * tp2_mult
        
        if tp2 < tp1:
            tp2 = tp1 + atr * 0.5
    else:
        return None, None, None
    
    return round(sl, 2), round(tp1, 2), round(tp2, 2)

# =========================================================
# 🔄 جلوگیری از سیگنال تکراری
# =========================================================

def is_duplicate_signal(signal_direction, price, atr):
    global _last_signal_state
    
    if _last_signal_state["direction"] == signal_direction:
        min_move = CONFIG["MIN_PRICE_CHANGE_ATR"] * atr
        price_diff = abs(price - _last_signal_state["price"])
        
        if price_diff < min_move:
            return True, f"Price moved only {price_diff:.2f} < {min_move:.2f}"
        
        if _last_signal_state["time"] is not None:
            time_diff = (datetime.now() - _last_signal_state["time"]).total_seconds() / 60
            if time_diff < CONFIG["COOLDOWN_MINUTES"]:
                return True, f"Cooldown active ({time_diff:.1f}/{CONFIG['COOLDOWN_MINUTES']} min)"
    
    return False, None

def update_last_signal(direction, price, score):
    global _last_signal_state
    _last_signal_state["direction"] = direction
    _last_signal_state["price"] = price
    _last_signal_state["time"] = datetime.now()
    _last_signal_state["score"] = score

# =========================================================
# 🧠 استراتژی اصلی
# =========================================================

def analyze_signal(df5, df1):
    df5 = add_indicators(df5)
    df1 = add_indicators(df1)
    
    if df5 is None or df1 is None or len(df5) < 30 or len(df1) < 30:
        return {"signal": "NO SIGNAL", "reasons": ["داده کافی نیست"]}
    
    last5 = df5.iloc[-1]
    last1 = df1.iloc[-1]
    
    price = float(last1['close'])
    rsi1 = float(last1['RSI'])
    atr1 = float(last1['ATR'])
    adx = float(last5['ADX'])
    
    ema20_5 = float(last5['EMA20'])
    ema50_5 = float(last5['EMA50'])
    
    if ema20_5 > ema50_5:
        trend = "BUY"
    elif ema20_5 < ema50_5:
        trend = "SELL"
    else:
        trend = "NONE"
    
    bos_signal, bos_level = detect_bos(df5)
    divergence = detect_rsi_divergence(df5)
    fib_pullback, _, _ = calc_fib_pullback(df5)
    
    if len(df1) >= 3:
        rsi_prev = float(df1.iloc[-2]['RSI'])
        rsi_before = float(df1.iloc[-3]['RSI'])
        
        rsi_buy_trigger = (
            (rsi_before < CONFIG["RSI_OVERSOLD"] or rsi_prev < CONFIG["RSI_OVERSOLD"]) and
            rsi_prev <= CONFIG["RSI_OVERSOLD"] and
            rsi1 > CONFIG["RSI_OVERSOLD"]
        )
        
        rsi_sell_trigger = (
            (rsi_before > CONFIG["RSI_OVERBOUGHT"] or rsi_prev > CONFIG["RSI_OVERBOUGHT"]) and
            rsi_prev >= CONFIG["RSI_OVERBOUGHT"] and
            rsi1 < CONFIG["RSI_OVERBOUGHT"]
        )
    else:
        rsi_buy_trigger = False
        rsi_sell_trigger = False
    
    candle_bull = last1['close'] > last1['open']
    candle_bear = last1['close'] < last1['open']
    candle_strong = abs(last1['close'] - last1['open']) > atr1 * 0.3
    
    near_sup, support = near_support(df1)
    near_res, resistance = near_resistance(df1)
    
    # ========== تحلیل خرید ==========
    score_buy = 0
    reasons_buy = []
    
    if trend == "BUY":
        score_buy += 30
        reasons_buy.append("OK: 5M uptrend (+30)")
    else:
        reasons_buy.append("WAIT: 5M uptrend (+0)")
    
    if CONFIG["EARLY_ENTRY"] and bos_signal == "BUY":
        score_buy += 25
        reasons_buy.append(f"EARLY: BOS BUY (+25)")
    
    if rsi_buy_trigger:
        score_buy += 20
        reasons_buy.append("OK: RSI reversal (+20)")
    
    if candle_bull and candle_strong:
        score_buy += 20
        reasons_buy.append("OK: strong bullish candle (+20)")
    elif candle_bull:
        score_buy += 10
        reasons_buy.append("OK: bullish candle (+10)")
    
    if near_sup:
        score_buy += 15
        reasons_buy.append(f"OK: near support (+15)")
    
    if divergence == "BULLISH":
        score_buy += 15
        reasons_buy.append("OK: RSI bullish divergence (+15)")
    
    if fib_pullback is not None and fib_pullback > (100 - CONFIG["FIB_EARLY_ZONE"]):
        score_buy += 10
        reasons_buy.append(f"OK: Fib pullback {fib_pullback:.1f}% (+10)")
    
    if adx > CONFIG["ADX_THRESHOLD"]:
        score_buy += 10
        reasons_buy.append(f"OK: ADX {adx:.1f} (+10)")
        if adx > CONFIG["ADX_STRONG_THRESHOLD"]:
            score_buy += 5
            reasons_buy.append(f"🔥 ADX strong (+5)")
    
    # ========== تحلیل فروش ==========
    score_sell = 0
    reasons_sell = []
    
    if trend == "SELL":
        score_sell += 30
        reasons_sell.append("OK: 5M downtrend (+30)")
    else:
        reasons_sell.append("WAIT: 5M downtrend (+0)")
    
    if CONFIG["EARLY_ENTRY"] and bos_signal == "SELL":
        score_sell += 25
        reasons_sell.append(f"EARLY: BOS SELL (+25)")
    
    if rsi_sell_trigger:
        score_sell += 20
        reasons_sell.append("OK: RSI reversal (+20)")
    
    if candle_bear and candle_strong:
        score_sell += 20
        reasons_sell.append("OK: strong bearish candle (+20)")
    elif candle_bear:
        score_sell += 10
        reasons_sell.append("OK: bearish candle (+10)")
    
    if near_res:
        score_sell += 15
        reasons_sell.append(f"OK: near resistance (+15)")
    
    if divergence == "BEARISH":
        score_sell += 15
        reasons_sell.append("OK: RSI bearish divergence (+15)")
    
    if fib_pullback is not None and fib_pullback < CONFIG["FIB_EARLY_ZONE"]:
        score_sell += 10
        reasons_sell.append(f"OK: Fib pullback {fib_pullback:.1f}% (+10)")
    
    if adx > CONFIG["ADX_THRESHOLD"]:
        score_sell += 10
        reasons_sell.append(f"OK: ADX {adx:.1f} (+10)")
        if adx > CONFIG["ADX_STRONG_THRESHOLD"]:
            score_sell += 5
            reasons_sell.append(f"🔥 ADX strong (+5)")
    
    # ========== تصمیم‌گیری نهایی ==========
    threshold_early = CONFIG["EARLY_SCORE_THRESHOLD"]
    threshold_normal = CONFIG["NORMAL_SCORE_THRESHOLD"]
    
    # فروش Early
    if CONFIG["EARLY_ENTRY"] and score_sell >= threshold_early:
        is_dup, reason = is_duplicate_signal("SELL", price, atr1)
        if is_dup:
            return {"signal": "NO SIGNAL", "score": score_sell, "quality": "WEAK", "price": price, "trend": trend, "reasons": [f"⚠️ DUPLICATE: {reason}"]}
        update_last_signal("SELL", price, score_sell)
        sl, tp1, tp2 = calculate_sl_tp("SELL", price, atr1, resistance=resistance if near_res else None)
        return create_result("SELL", score_sell, reasons_sell, price, rsi1, adx, trend, "EARLY", sl, tp1, tp2)
    
    # فروش Normal
    if score_sell >= threshold_normal:
        is_dup, reason = is_duplicate_signal("SELL", price, atr1)
        if is_dup:
            return {"signal": "NO SIGNAL", "score": score_sell, "quality": "WEAK", "price": price, "trend": trend, "reasons": [f"⚠️ DUPLICATE: {reason}"]}
        update_last_signal("SELL", price, score_sell)
        sl, tp1, tp2 = calculate_sl_tp("SELL", price, atr1, resistance=resistance if near_res else None)
        return create_result("SELL", score_sell, reasons_sell, price, rsi1, adx, trend, "NORMAL", sl, tp1, tp2)
    
    # خرید Early
    if CONFIG["EARLY_ENTRY"] and score_buy >= threshold_early:
        is_dup, reason = is_duplicate_signal("BUY", price, atr1)
        if is_dup:
            return {"signal": "NO SIGNAL", "score": score_buy, "quality": "WEAK", "price": price, "trend": trend, "reasons": [f"⚠️ DUPLICATE: {reason}"]}
        update_last_signal("BUY", price, score_buy)
        sl, tp1, tp2 = calculate_sl_tp("BUY", price, atr1, support=support if near_sup else None)
        return create_result("BUY", score_buy, reasons_buy, price, rsi1, adx, trend, "EARLY", sl, tp1, tp2)
    
    # خرید Normal
    if score_buy >= threshold_normal:
        is_dup, reason = is_duplicate_signal("BUY", price, atr1)
        if is_dup:
            return {"signal": "NO SIGNAL", "score": score_buy, "quality": "WEAK", "price": price, "trend": trend, "reasons": [f"⚠️ DUPLICATE: {reason}"]}
        update_last_signal("BUY", price, score_buy)
        sl, tp1, tp2 = calculate_sl_tp("BUY", price, atr1, support=support if near_sup else None)
        return create_result("BUY", score_buy, reasons_buy, price, rsi1, adx, trend, "NORMAL", sl, tp1, tp2)
    
    # بدون سیگنال
    return {
        "signal": "NO SIGNAL",
        "score": max(score_buy, score_sell),
        "quality": "WEAK",
        "price": price,
        "trend": trend,
        "rsi": rsi1,
        "adx": adx,
        "fib_pullback": fib_pullback,
        "bos_signal": bos_signal,
        "divergence": divergence,
        "reasons": ["شرایط برقرار نیست"]
    }

def create_result(signal, score, reasons, price, rsi, adx, trend, entry_type, sl=None, tp1=None, tp2=None):
    quality = "STRONG" if score >= 85 else "NORMAL" if score >= 70 else "WEAK"
    result = {
        "signal": signal,
        "score": min(score, 100),
        "quality": quality,
        "price": price,
        "rsi": rsi,
        "adx": adx,
        "trend": trend,
        "entry_type": entry_type,
        "reasons": [f"Score: {score}/100"] + reasons + [f"FINAL {signal} SIGNAL ({entry_type})"]
    }
    if sl is not None:
        result["sl"] = sl
        result["tp1"] = tp1
        result["tp2"] = tp2
    return result

# =========================================================
# 🚀 اجرای مستقل (برای تست)
# =========================================================

def main():
    print("=" * 60)
    print("🧪 GOLDPRO+ CLEAN (نسخه نهایی با SL/TP)")
    print("=" * 60)
    
    df5 = fetch_data("5min")
    df1 = fetch_data("1min", days=1)
    
    if df5 is None or df1 is None:
        print("❌ دریافت داده ناموفق")
        return
    
    result = analyze_signal(df5, df1)
    
    print("\n" + "=" * 60)
    print("📊 گزارش نهایی")
    print("=" * 60)
    
    if result['signal'] != "NO SIGNAL":
        emoji = "🔴" if result['signal'] == "SELL" else "🟢"
        print(f"{emoji} {CONFIG['SYMBOL']} {result['signal']} ({result.get('entry_type', 'NORMAL')})")
        print(f"💰 قیمت: {result['price']:.5f}")
        if result.get('sl') is not None:
            print(f"🛑 SL: {result['sl']:.2f}")
            print(f"🎯 TP1: {result['tp1']:.2f}")
            print(f"🎯 TP2: {result['tp2']:.2f}")
        print(f"⭐ امتیاز: {result['score']}/100")
        print(f"🏷️ کیفیت: {result['quality']}")
        print(f"📈 روند: {result.get('trend', 'NONE')}")
        print(f"📊 RSI: {result.get('rsi', 0):.1f}")
        print(f"📊 ADX: {result.get('adx', 0):.1f}")
        if result.get('fib_pullback'):
            print(f"📐 فیبوناچی: {result['fib_pullback']:.1f}%")
        print("\n📋 دلایل:")
        for r in result['reasons']:
            print(f"  • {r}")
    else:
        print("⚠️ هیچ سیگنالی یافت نشد.")
        if result.get('reasons'):
            print(f"   دلیل: {result['reasons']}")
        print(f"   امتیاز: {result.get('score', 0)}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
