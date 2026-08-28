import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time

# ==========================================
# 📌 تنظیمات اولیه
# ==========================================
API_KEY = os.environ.get('TWELVE_DATA_API_KEY', 'YOUR_API_KEY_HERE')
SYMBOL = "XAU/USD"
INTERVAL = "5min"          # تایم‌فریم اصلی (می‌توان 1min, 5min, 15min)
DAYS_BACK = 3              # تعداد روزهای برگشتی برای دریافت داده
EARLY_ENTRY = True         # True = تشخیص زودهنگام تغییر روند
RSI_BUY = 45               # آستانه RSI برای خرید (کمتر = oversold)
RSI_SELL = 55              # آستانه RSI برای فروش (بیشتر = overbought)

# ==========================================
# 📥 دریافت داده از Twelve Data
# ==========================================
def fetch_twelve_data(symbol=SYMBOL, interval=INTERVAL, days=DAYS_BACK):
    """دریافت داده از Twelve Data و تبدیل به DataFrame"""
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 500,
        "apikey": API_KEY,
        "start_date": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"⚠️ HTTP {resp.status_code}")
            return None
        data = resp.json()
        if 'values' not in data or len(data['values']) < 50:
            print("⚠️ داده کافی نیست")
            return None
        
        df = pd.DataFrame(data['values'])
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
        return df
    except Exception as e:
        print(f"❌ خطا: {e}")
        return None

# ==========================================
# 📊 محاسبه اندیکاتورها
# ==========================================
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

def calculate_fib_levels(df, lookback=50):
    """محاسبه سطوح فیبوناچی بر اساس آخرین موج"""
    if len(df) < lookback:
        return None, None, None, None
    high = df['high'].iloc[-lookback:].max()
    low = df['low'].iloc[-lookback:].min()
    if high == low:
        return None, None, None, None
    diff = high - low
    levels = {
        '0.0': high,
        '0.236': high - diff * 0.236,
        '0.382': high - diff * 0.382,
        '0.5': high - diff * 0.5,
        '0.618': high - diff * 0.618,
        '1.0': low
    }
    current_price = df['close'].iloc[-1]
    pullback_pct = ((high - current_price) / diff) * 100 if diff != 0 else 0
    return levels, pullback_pct, high, low

# ==========================================
# 🧠 تشخیص شکست ساختار (Break of Structure)
# ==========================================
def detect_break_of_structure(df, lookback=10):
    """تشخیص شکست کف/سقف اخیر برای ورود زودهنگام"""
    if len(df) < lookback + 2:
        return None, None
    recent_lows = df['low'].iloc[-lookback:-1]
    recent_highs = df['high'].iloc[-lookback:-1]
    current_close = df['close'].iloc[-1]
    
    if current_close < recent_lows.min():
        return "SELL", recent_lows.min()   # شکست کف => سیگنال فروش
    elif current_close > recent_highs.max():
        return "BUY", recent_highs.max()   # شکست سقف => سیگنال خرید
    return None, None

# ==========================================
# 🔍 تشخیص واگرایی RSI
# ==========================================
def detect_rsi_divergence(df, period=14, lookback=30):
    """تشخیص واگرایی منفی/مثبت بین قیمت و RSI"""
    if len(df) < lookback + 5:
        return None
    rsi = calculate_rsi(df['close'], period)
    price = df['close']
    
    # پیدا کردن قله‌های اخیر قیمت
    last_peak_idx = price.iloc[-lookback:].idxmax()
    prev_peak_idx = price.iloc[-lookback*2:-lookback].idxmax() if len(df) > lookback*2 else None
    if prev_peak_idx is None:
        return None
    
    # واگرایی منفی (قیمت بالا رفته ولی RSI پایین آمده)
    if price.loc[last_peak_idx] > price.loc[prev_peak_idx]:
        if rsi.loc[last_peak_idx] < rsi.loc[prev_peak_idx]:
            return "BEARISH"
    # واگرایی مثبت (قیمت پایین رفته ولی RSI بالا آمده)
    elif price.loc[last_peak_idx] < price.loc[prev_peak_idx]:
        if rsi.loc[last_peak_idx] > rsi.loc[prev_peak_idx]:
            return "BULLISH"
    return None

# ==========================================
# 🧠 استراتژی اصلی (ترکیبی)
# ==========================================
def trend_catcher_signal(df, rsi_buy=RSI_BUY, rsi_sell=RSI_SELL, early_entry=EARLY_ENTRY):
    """تشخیص سیگنال بر اساس روند، شکست ساختار، واگرایی و فیبوناچی"""
    if df is None or len(df) < 60:
        return {
            "signal": "NO SIGNAL",
            "price": None,
            "score": 0,
            "quality": "WEAK",
            "reasons": ["داده کافی نیست"]
        }

    close = df['close']
    ema20 = calculate_ema(close, 20)
    ema50 = calculate_ema(close, 50)
    rsi = calculate_rsi(close, 14)
    
    last = df.iloc[-1]
    price = float(last['close'])
    prev = df.iloc[-2]
    
    rsi_val = float(rsi.iloc[-1])
    bullish_trend = price > ema20.iloc[-1] > ema50.iloc[-1]
    bearish_trend = price < ema20.iloc[-1] < ema50.iloc[-1]
    
    # تشخیص شکست ساختار و واگرایی
    bos_signal, bos_level = detect_break_of_structure(df, lookback=10)
    divergence = detect_rsi_divergence(df)
    
    # محاسبه فیبوناچی
    fib_levels, pullback_pct, high, low = calculate_fib_levels(df)
    
    reasons = []
    score = 0

    # ========== سیگنال فروش (SELL) ==========
    if bearish_trend or (early_entry and bos_signal == "SELL"):
        if rsi_val > rsi_sell and last['close'] < last['open']:
            score += 30
            reasons.append(f"روند نزولی (EMA20<EMA50)")
            if rsi_val > 60:
                score += 15
                reasons.append(f"RSI={rsi_val:.1f} (بالای 60)")
            else:
                score += 10
                reasons.append(f"RSI={rsi_val:.1f} (بالای {rsi_sell})")
            
            if last['close'] < prev['close'] * 0.999:
                score += 10
                reasons.append("کندل نزولی قوی")
            
            # امتیازات اضافی برای ورود زودهنگام
            if bos_signal == "SELL":
                score += 20
                reasons.append(f"شکست کف اخیر ({bos_level:.2f})")
            if divergence == "BEARISH":
                score += 15
                reasons.append("واگرایی منفی RSI")
            if early_entry and not bearish_trend:
                score += 10
                reasons.append("ورود زودهنگام (Early Entry)")
            if pullback_pct is not None and pullback_pct < 38.2:
                score += 10
                reasons.append(f"فیبوناچی پولبک {pullback_pct:.1f}% (منطقه اولیه)")
            
            quality = "STRONG" if score >= 80 else "NORMAL"
            return {
                "signal": "SELL",
                "price": price,
                "score": min(score, 100),
                "quality": quality,
                "reasons": reasons,
                "fib_pullback": pullback_pct,
                "bos_level": bos_level,
                "divergence": divergence
            }

    # ========== سیگنال خرید (BUY) ==========
    if bullish_trend or (early_entry and bos_signal == "BUY"):
        if rsi_val < rsi_buy and last['close'] > last['open']:
            score += 30
            reasons.append(f"روند صعودی (EMA20>EMA50)")
            if rsi_val < 40:
                score += 15
                reasons.append(f"RSI={rsi_val:.1f} (زیر 40)")
            else:
                score += 10
                reasons.append(f"RSI={rsi_val:.1f} (زیر {rsi_buy})")
            
            if last['close'] > prev['close'] * 1.001:
                score += 10
                reasons.append("کندل صعودی قوی")
            
            if bos_signal == "BUY":
                score += 20
                reasons.append(f"شکست سقف اخیر ({bos_level:.2f})")
            if divergence == "BULLISH":
                score += 15
                reasons.append("واگرایی مثبت RSI")
            if early_entry and not bullish_trend:
                score += 10
                reasons.append("ورود زودهنگام (Early Entry)")
            if pullback_pct is not None and pullback_pct > 61.8:
                score += 10
                reasons.append(f"فیبوناچی پولبک {pullback_pct:.1f}% (منطقه حمایت)")
            
            quality = "STRONG" if score >= 80 else "NORMAL"
            return {
                "signal": "BUY",
                "price": price,
                "score": min(score, 100),
                "quality": quality,
                "reasons": reasons,
                "fib_pullback": pullback_pct,
                "bos_level": bos_level,
                "divergence": divergence
            }

    # ========== بدون سیگنال ==========
    return {
        "signal": "NO SIGNAL",
        "price": price,
        "score": 0,
        "quality": "WEAK",
        "reasons": ["شرایط روند یا RSI برقرار نیست"],
        "fib_pullback": pullback_pct,
        "bos_level": bos_level,
        "divergence": divergence
    }

# ==========================================
# 🚀 اجرای اصلی
# ==========================================
def main():
    print("=" * 60)
    print("🧪 GOLDPRO+ TREND CATCHER (EARLY ENTRY ENABLED)")
    print("=" * 60)
    
    df = fetch_twelve_data()
    if df is None:
        print("❌ دریافت داده ناموفق")
        return
    
    print(f"📊 تعداد کندل‌ها: {len(df)} از {df.index[0]} تا {df.index[-1]}")
    
    result = trend_catcher_signal(df)
    
    print("\n" + "=" * 60)
    print("📊 گزارش نهایی")
    print("=" * 60)
    
    if result['signal'] != "NO SIGNAL":
        emoji = "🔴" if result['signal'] == "SELL" else "🟢"
        print(f"{emoji} {SYMBOL} {result['signal']} SIGNAL")
        print(f"💰 قیمت ورود: {result['price']:.5f}")
        print(f"⭐ امتیاز: {result['score']}/100")
        print(f"🏷️ کیفیت: {result['quality']}")
        if result.get('fib_pullback') is not None:
            print(f"📐 فیبوناچی پولبک: {result['fib_pullback']:.1f}%")
        if result.get('bos_level'):
            print(f"📍 شکست ساختار در سطح: {result['bos_level']:.5f}")
        if result.get('divergence'):
            print(f"🔍 واگرایی RSI: {result['divergence']}")
        print("\n📋 دلایل:")
        for r in result['reasons']:
            print(f"  • {r}")
    else:
        print("⚠️ هیچ سیگنالی یافت نشد.")
        if result.get('fib_pullback') is not None:
            print(f"   فیبوناچی پولبک: {result['fib_pullback']:.1f}%")
        print("💡 پیشنهاد: EARLY_ENTRY را True کنید یا RSI_BUY/RSI_SELL را تنظیم نمایید.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()