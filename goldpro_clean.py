"""
GoldPro+ Clean Version - Early Entry Strategy
Only depends on: pandas, numpy, requests
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time
import json

# =========================================================
# 📌 تنظیمات (اینجا تغییر دهید)
# =========================================================

CONFIG = {
    "API_KEY": os.environ.get('TWELVE_DATA_API_KEY', 'YOUR_API_KEY_HERE'),
    "SYMBOL": "XAU/USD",
    "DAYS_BACK": 3,
    
    # تنظیمات Early Entry
    "EARLY_ENTRY": True,
    "BOS_LOOKBACK": 8,
    "EARLY_SCORE_THRESHOLD": 60,
    "NORMAL_SCORE_THRESHOLD": 70,
    
    # آستانه‌های RSI
    "RSI_OVERSOLD": 30,
    "RSI_OVERBOUGHT": 70,
    
    # فیبوناچی
    "FIB_LOOKBACK": 50,
    "FIB_EARLY_ZONE": 38.2,
    
    # پشتیبانی/مقاومت
    "SR_LOOKBACK": 20,
    "SR_ATR_DISTANCE": 1.0,
}

# =========================================================
# 📥 دریافت داده (با کش و مدیریت خطا)
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
                print(f"⚠️ HTTP 429 (Too Many Requests). Waiting {wait}s...")
                time.sleep(wait)
                continue
                
            if resp.status_code != 200:
                print(f"⚠️ HTTP {resp.status_code} برای {interval}")
                return None
            
            data = resp.json()
            if 'values' not in data or len(data['values']) < 50:
                print(f"⚠️ داده کافی نیست برای {interval}")
                return None
            
            df = pd.DataFrame(data['values'])
            
            # بررسی وجود ستون‌های اصلی
            required_cols = ['datetime', 'open', 'high', 'low', 'close']
            for col in required_cols:
                if col not in df.columns:
                    print(f"⚠️ ستون {col} در پاسخ وجود ندارد")
                    return None
            
            # اگر volume نبود، اضافه کن
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
            print(f"❌ خطا در دریافت {interval}: {e}")
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
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def add_indicators(df):
    """اضافه کردن EMA, RSI, ATR به DataFrame"""
    df = df.copy()
    df['EMA20'] = calculate_ema(df['close'], 20)
    df['EMA50'] = calculate_ema(df['close'], 50)
    df['RSI'] = calculate_rsi(df['close'], 14)
    df['ATR'] = calculate_atr(df, 14)
    return df

# =========================================================
# 🔍 تشخیص شکست ساختار (Break of Structure)
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
# 🧠 استراتژی اصلی
# =========================================================

def analyze_signal(df5, df1):
    """
    تحلیل ترکیبی:
    - df5: تایم‌فریم 5 دقیقه (روند و ساختار)
    - df1: تایم‌فریم 1 دقیقه (ورود)
    """
    
    # آماده‌سازی داده‌ها
    df5 = add_indicators(df5)
    df1 = add_indicators(df1)
    
    if df5 is None or df1 is None or len(df5) < 30 or len(df1) < 30:
        return {
            "signal": "NO SIGNAL",
            "reasons": ["داده کافی نیست"]
        }
    
    # ========== استخراج داده‌های فعلی ==========
    last5 = df5.iloc[-1]
    last1 = df1.iloc[-1]
    
    price = float(last1['close'])
    rsi1 = float(last1['RSI'])
    atr1 = float(last1['ATR'])
    
    ema20_5 = float(last5['EMA20'])
    ema50_5 = float(last5['EMA50'])
    
    # ========== 1. تشخیص روند در 5M ==========
    if ema20_5 > ema50_5:
        trend = "BUY"
    elif ema20_5 < ema50_5:
        trend = "SELL"
    else:
        trend = "NONE"
    
    # ========== 2. شکست ساختار (BOS) ==========
    bos_signal, bos_level = detect_bos(df5)
    
    # ========== 3. واگرایی RSI ==========
    divergence = detect_rsi_divergence(df5)
    
    # ========== 4. فیبوناچی پولبک ==========
    fib_pullback, fib_high, fib_low = calc_fib_pullback(df5)
    
    # ========== 5. شرایط ورود 1M ==========
    # RSI Reversal (خروج از اشباع)
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
    
    # کندل 1M
    candle_bull = last1['close'] > last1['open']
    candle_bear = last1['close'] < last1['open']
    candle_strong = abs(last1['close'] - last1['open']) > atr1 * 0.3
    
    # پشتیبانی/مقاومت
    near_sup, support = near_support(df1)
    near_res, resistance = near_resistance(df1)
    
    # ========== 6. تحلیل خرید ==========
    score_buy = 0
    reasons_buy = []
    
    # روند
    if trend == "BUY":
        score_buy += 30
        reasons_buy.append("OK: 5M uptrend")
    else:
        reasons_buy.append("WAIT: 5M uptrend")
    
    # BOS (اگر Early Entry فعال باشد)
    if CONFIG["EARLY_ENTRY"] and bos_signal == "BUY":
        score_buy += 25
        reasons_buy.append(f"EARLY: BOS BUY at {bos_level:.2f}")
    
    # RSI Reversal
    if rsi_buy_trigger:
        score_buy += 25
        reasons_buy.append("OK: RSI reversal from oversold")
    
    # کندل
    if candle_bull and candle_strong:
        score_buy += 20
        reasons_buy.append("OK: strong bullish candle")
    elif candle_bull:
        score_buy += 10
        reasons_buy.append("OK: bullish candle")
    
    # پشتیبانی
    if near_sup:
        score_buy += 15
        reasons_buy.append(f"OK: near support {support:.2f}")
    
    # واگرایی
    if divergence == "BULLISH":
        score_buy += 15
        reasons_buy.append("OK: RSI bullish divergence")
    
    # فیبوناچی (پولبک زیاد = نزدیک به حمایت)
    if fib_pullback is not None and fib_pullback > (100 - CONFIG["FIB_EARLY_ZONE"]):
        score_buy += 10
        reasons_buy.append(f"OK: Fib pullback {fib_pullback:.1f}%")
    
    # ========== 7. تحلیل فروش ==========
    score_sell = 0
    reasons_sell = []
    
    if trend == "SELL":
        score_sell += 30
        reasons_sell.append("OK: 5M downtrend")
    else:
        reasons_sell.append("WAIT: 5M downtrend")
    
    if CONFIG["EARLY_ENTRY"] and bos_signal == "SELL":
        score_sell += 25
        reasons_sell.append(f"EARLY: BOS SELL at {bos_level:.2f}")
    
    if rsi_sell_trigger:
        score_sell += 25
        reasons_sell.append("OK: RSI reversal from overbought")
    
    if candle_bear and candle_strong:
        score_sell += 20
        reasons_sell.append("OK: strong bearish candle")
    elif candle_bear:
        score_sell += 10
        reasons_sell.append("OK: bearish candle")
    
    if near_res:
        score_sell += 15
        reasons_sell.append(f"OK: near resistance {resistance:.2f}")
    
    if divergence == "BEARISH":
        score_sell += 15
        reasons_sell.append("OK: RSI bearish divergence")
    
    if fib_pullback is not None and fib_pullback < CONFIG["FIB_EARLY_ZONE"]:
        score_sell += 10
        reasons_sell.append(f"OK: Fib pullback {fib_pullback:.1f}%")
    
    # ========== 8. تصمیم‌گیری نهایی ==========
    threshold_early = CONFIG["EARLY_SCORE_THRESHOLD"]
    threshold_normal = CONFIG["NORMAL_SCORE_THRESHOLD"]
    
    # بررسی سیگنال فروش
    if score_sell >= threshold_normal:
        return create_result("SELL", score_sell, reasons_sell, price, rsi1, atr1, trend, "NORMAL")
    
    if CONFIG["EARLY_ENTRY"] and score_sell >= threshold_early and bos_signal == "SELL":
        return create_result("SELL", score_sell, reasons_sell, price, rsi1, atr1, trend, "EARLY")
    
    # بررسی سیگنال خرید
    if score_buy >= threshold_normal:
        return create_result("BUY", score_buy, reasons_buy, price, rsi1, atr1, trend, "NORMAL")
    
    if CONFIG["EARLY_ENTRY"] and score_buy >= threshold_early and bos_signal == "BUY":
        return create_result("BUY", score_buy, reasons_buy, price, rsi1, atr1, trend, "EARLY")
    
    # بدون سیگنال
    return {
        "signal": "NO SIGNAL",
        "score": max(score_buy, score_sell),
        "quality": "WEAK",
        "price": price,
        "trend": trend,
        "rsi": rsi1,
        "fib_pullback": fib_pullback,
        "bos_signal": bos_signal,
        "divergence": divergence,
        "reasons": ["شرایط برقرار نیست"]
    }

def create_result(signal, score, reasons, price, rsi, atr, trend, entry_type):
    quality = "STRONG" if score >= 85 else "NORMAL" if score >= 70 else "WEAK"
    return {
        "signal": signal,
        "score": min(score, 100),
        "quality": quality,
        "price": price,
        "rsi": rsi,
        "atr": atr,
        "trend": trend,
        "entry_type": entry_type,
        "reasons": [f"Score: {score}/100"] + reasons + [f"FINAL {signal} SIGNAL ({entry_type})"]
    }

# =========================================================
# 🚀 اجرای اصلی (برای تست مستقل)
# =========================================================

def main():
    print("=" * 60)
    print("🧪 GOLDPRO+ CLEAN (EARLY ENTRY ENABLED)")
    print("=" * 60)
    
    print("📥 دریافت داده 5M...")
    df5 = fetch_data("5min")
    print("📥 دریافت داده 1M...")
    df1 = fetch_data("1min", days=1)
    
    if df5 is None or df1 is None:
        print("❌ دریافت داده ناموفق")
        return
    
    print(f"📊 5M: {len(df5)} کندل")
    print(f"📊 1M: {len(df1)} کندل")
    
    result = analyze_signal(df5, df1)
    
    print("\n" + "=" * 60)
    print("📊 گزارش نهایی")
    print("=" * 60)
    
    if result['signal'] != "NO SIGNAL":
        emoji = "🔴" if result['signal'] == "SELL" else "🟢"
        print(f"{emoji} {CONFIG['SYMBOL']} {result['signal']} SIGNAL ({result.get('entry_type', 'NORMAL')})")
        print(f"💰 قیمت: {result['price']:.5f}")
        print(f"⭐ امتیاز: {result['score']}/100")
        print(f"🏷️ کیفیت: {result['quality']}")
        print(f"📈 روند 5M: {result.get('trend', 'NONE')}")
        print(f"📊 RSI 1M: {result.get('rsi', 0):.1f}")
        if result.get('fib_pullback'):
            print(f"📐 فیبوناچی پولبک: {result['fib_pullback']:.1f}%")
        print("\n📋 دلایل:")
        for r in result['reasons']:
            print(f"  • {r}")
    else:
        print("⚠️ هیچ سیگنالی یافت نشد.")
        print(f"   روند 5M: {result.get('trend', 'NONE')}")
        if result.get('fib_pullback'):
            print(f"   فیبوناچی پولبک: {result['fib_pullback']:.1f}%")
        if result.get('bos_signal'):
            print(f"   شکست ساختار: {result['bos_signal']}")
        if result.get('divergence'):
            print(f"   واگرایی RSI: {result['divergence']}")
        print("💡 پیشنهاد: EARLY_ENTRY=True (هم‌اکنون فعال است)")
        print(f"   آستانه Early Entry: {CONFIG['EARLY_SCORE_THRESHOLD']}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()