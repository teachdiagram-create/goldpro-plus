import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time

# ==================================================
# 📌 تنظیمات اولیه (قابل تغییر توسط کاربر)
# ==================================================
API_KEY = os.environ.get('TWELVE_DATA_API_KEY', 'YOUR_API_KEY_HERE')
SYMBOL = "XAU/USD"
DAYS_BACK = 3                # تعداد روز برای دریافت داده

# ========== تنظیمات استراتژی ==========
EARLY_ENTRY = True           # True = ورود در شکست ساختار یا پولبک‌های اولیه
REVERSAL_THRESHOLD = 2.0     # آستانه‌ی امتیاز برگشت (پیش‌فرض 3.0، کاهش به 2.0 برای ورود زودتر)
RSI_BUY = 45                 # آستانه RSI خرید
RSI_SELL = 55                # آستانه RSI فروش
FIB_EARLY_THRESHOLD = 38.2   # حداکثر پولبک فیبوناچی برای ورود زودهنگام (٪)
BOS_LOOKBACK = 10            # تعداد کندل برای تشخیص شکست ساختار

# ==================================================
# 📥 دریافت داده از Twelve Data (با کش ساده)
# ==================================================
_cache = {}

def fetch_data(interval, days=DAYS_BACK):
    """دریافت داده از Twelve Data با کش کردن برای جلوگیری از درخواست‌های تکراری"""
    cache_key = f"{SYMBOL}_{interval}_{days}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": interval,
        "outputsize": 500,
        "apikey": API_KEY,
        "start_date": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"⚠️ HTTP {resp.status_code} برای {interval}")
            return None
        data = resp.json()
        if 'values' not in data or len(data['values']) < 50:
            print(f"⚠️ داده کافی نیست برای {interval}")
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
        _cache[cache_key] = df
        return df
    except Exception as e:
        print(f"❌ خطا در دریافت {interval}: {e}")
        return None

# ==================================================
# 📊 محاسبه اندیکاتورها (EMA, RSI)
# ==================================================
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

# ==================================================
# 📐 تشخیص شکست ساختار (Break of Structure)
# ==================================================
def detect_bos(df, lookback=BOS_LOOKBACK):
    """تشخیص شکست کف/سقف در یک تایم‌فریم"""
    if len(df) < lookback + 2:
        return None, None
    recent_lows = df['low'].iloc[-lookback:-1].min()
    recent_highs = df['high'].iloc[-lookback:-1].max()
    current_close = df['close'].iloc[-1]
    if current_close < recent_lows:
        return "SELL", recent_lows
    elif current_close > recent_highs:
        return "BUY", recent_highs
    return None, None

# ==================================================
# 📐 واگرایی RSI
# ==================================================
def detect_rsi_divergence(df, period=14, lookback=30):
    if len(df) < lookback + 5:
        return None
    rsi = calculate_rsi(df['close'], period)
    price = df['close']
    last_peak_idx = price.iloc[-lookback:].idxmax()
    prev_peak_idx = price.iloc[-lookback*2:-lookback].idxmax() if len(df) > lookback*2 else None
    if prev_peak_idx is None:
        return None
    if price.loc[last_peak_idx] > price.loc[prev_peak_idx] and rsi.loc[last_peak_idx] < rsi.loc[prev_peak_idx]:
        return "BEARISH"
    elif price.loc[last_peak_idx] < price.loc[prev_peak_idx] and rsi.loc[last_peak_idx] > rsi.loc[prev_peak_idx]:
        return "BULLISH"
    return None

# ==================================================
# 📐 فیبوناچی پولبک
# ==================================================
def calc_fib_pullback(df, lookback=50):
    if len(df) < lookback:
        return None, None, None, None
    high = df['high'].iloc[-lookback:].max()
    low = df['low'].iloc[-lookback:].min()
    if high == low:
        return None, None, None, None
    current = df['close'].iloc[-1]
    pullback = ((high - current) / (high - low)) * 100
    return pullback, high, low

# ==================================================
# 🧠 استراتژی اصلی (چندتایم‌فریمی)
# ==================================================
def goldpro_signal(df_15m, df_5m, df_1m):
    """
    تحلیل ترکیبی ۱۵ دقیقه (روند) + ۵ دقیقه (ساختار) + ۱ دقیقه (ورود)
    خروجی مشابه لاگ GOLDPRO+
    """
    if df_15m is None or df_5m is None or df_1m is None:
        return {"signal": "NO SIGNAL", "score": 0, "quality": "WEAK", "reasons": ["داده缺失"]}

    # ---------- ۱. روند در ۱۵ دقیقه ----------
    ema20_15 = calculate_ema(df_15m['close'], 20)
    ema50_15 = calculate_ema(df_15m['close'], 50)
    last_15 = df_15m.iloc[-1]
    price_15 = last_15['close']
    bullish = price_15 > ema20_15.iloc[-1] > ema50_15.iloc[-1]
    bearish = price_15 < ema20_15.iloc[-1] < ema50_15.iloc[-1]
    trend = "BUY" if bullish else "SELL" if bearish else "NEUTRAL"

    # سن روند (تعداد کندل‌های پشت سر هم)
    trend_age = 0
    if bullish or bearish:
        for i in range(1, min(30, len(df_15m))):
            if (bullish and df_15m['close'].iloc[-i] > ema20_15.iloc[-i] > ema50_15.iloc[-i]) or \
               (bearish and df_15m['close'].iloc[-i] < ema20_15.iloc[-i] < ema50_15.iloc[-i]):
                trend_age += 1
            else:
                break
    phase = "DEVELOPING" if trend_age < 10 else "MATURE"

    # ---------- ۲. ساختار در ۵ دقیقه ----------
    ema9_5 = calculate_ema(df_5m['close'], 9)
    ema20_5 = calculate_ema(df_5m['close'], 20)
    last_5 = df_5m.iloc[-1]
    price_5 = last_5['close']

    # تقاطع EMA
    ema_cross = "BULLISH" if ema9_5.iloc[-1] > ema20_5.iloc[-1] else "BEARISH" if ema9_5.iloc[-1] < ema20_5.iloc[-1] else "NEUTRAL"

    # مومنتوم
    momentum = "UP" if price_5 > df_5m['close'].iloc[-2] else "DOWN"

    # تشخیص برگشت (Reversal)
    # ساده‌سازی: بررسی تغییر جهت کندل‌ها و RSI
    rsi_5 = calculate_rsi(df_5m['close'], 14).iloc[-1]
    reversal_score = 0
    reversal_categories = []
    if last_5['close'] < last_5['open']:
        reversal_score += 1.5
        reversal_categories.append("bearish candle")
    if ema_cross == "BEARISH":
        reversal_score += 1.0
        reversal_categories.append("EMA cross")
    if momentum == "DOWN":
        reversal_score += 0.5
        reversal_categories.append("down momentum")
    if rsi_5 > 60:
        reversal_score += 0.5
        reversal_categories.append("overbought")
    reversal_state = "CONFIRMED" if reversal_score >= REVERSAL_THRESHOLD else "WARNING"

    # ---------- ۳. فیبوناچی ۵ دقیقه ----------
    fib_pullback, high_5, low_5 = calc_fib_pullback(df_5m, lookback=30)

    # ---------- ۴. شکست ساختار در ۱۵ و ۵ ----------
    bos_15, bos_level_15 = detect_bos(df_15m, lookback=10)
    bos_5, bos_level_5 = detect_bos(df_5m, lookback=8)

    # ---------- ۵. واگرایی RSI در ۱۵ دقیقه ----------
    divergence = detect_rsi_divergence(df_15m)

    # ---------- ۶. ورود در ۱ دقیقه ----------
    last_1 = df_1m.iloc[-1]
    price_1 = last_1['close']
    candle_bull = last_1['close'] > last_1['open']
    candle_bear = last_1['close'] < last_1['open']
    rsi_1 = calculate_rsi(df_1m['close'], 14).iloc[-1]

    # ---------- ۷. امتیازدهی و تصمیم‌گیری ----------
    reasons = []
    score = 0

    # --- سیگنال فروش (SELL) ---
    if (trend == "SELL" or (EARLY_ENTRY and bos_5 == "SELL")) and (candle_bear and rsi_1 > RSI_SELL):
        # امتیاز پایه
        score += 30
        reasons.append(f"OK: 15m trend ({trend})")
        reasons.append(f"INFO: 15m trend phase ({phase})")

        # برگشت ۵ دقیقه
        if reversal_state == "CONFIRMED":
            score += 20
            reasons.append(f"BLOCK: 5M REVERSAL CONFIRMED ({reversal_score:.1f} points / {len(reversal_categories)} categories)")
        else:
            score += 10
            reasons.append(f"5M reversal WARNING ({reversal_score:.1f} points)")

        # EMA تقاطع
        if ema_cross == "BEARISH":
            score += 10
            reasons.append("5M EMA9/20 bearish cross")

        # مومنتوم
        if momentum == "DOWN":
            score += 5
            reasons.append("5M downside momentum")

        # شکست ساختار (امتیاز بالا برای ورود زودهنگام)
        if bos_5 == "SELL":
            score += 20
            reasons.append(f"5M BOS SELL at {bos_level_5:.2f}")
        if bos_15 == "SELL":
            score += 15
            reasons.append(f"15M BOS SELL at {bos_level_15:.2f}")

        # واگرایی
        if divergence == "BEARISH":
            score += 15
            reasons.append("15M RSI divergence (bearish)")

        # فیبوناچی اولیه (کمتر از ۳۸.۲٪ برای ورود زودهنگام)
        if fib_pullback is not None and fib_pullback < FIB_EARLY_THRESHOLD:
            score += 10
            reasons.append(f"Fib pullback {fib_pullback:.1f}% (early zone)")

        # کندل ۱ دقیقه
        if candle_bear and rsi_1 > 60:
            score += 10
            reasons.append("1M bearish candle + overbought RSI")

        # اگر EARLY_ENTRY فعال و روند هنوز شکل نگرفته، امتیاز اضافی
        if EARLY_ENTRY and trend != "SELL" and bos_5 == "SELL":
            score += 10
            reasons.append("EARLY ENTRY (BOS detected before trend)")

        quality = "STRONG" if score >= 80 else "NORMAL"
        return {
            "signal": "SELL",
            "price": price_1,
            "score": min(score, 100),
            "quality": quality,
            "trend": trend,
            "trend_phase": phase,
            "trend_age_bars": trend_age,
            "rsi": rsi_1,
            "reversal_score": reversal_score,
            "reversal_state": reversal_state,
            "reversal_categories": len(reversal_categories),
            "fib_pullback": fib_pullback,
            "bos_level": bos_level_5,
            "divergence": divergence,
            "reasons": reasons
        }

    # --- سیگنال خرید (BUY) مشابه فروش با شرایط معکوس ---
    if (trend == "BUY" or (EARLY_ENTRY and bos_5 == "BUY")) and (candle_bull and rsi_1 < RSI_BUY):
        score += 30
        reasons.append(f"OK: 15m trend ({trend})")
        reasons.append(f"INFO: 15m trend phase ({phase})")

        if reversal_state == "CONFIRMED":
            score += 20
            reasons.append(f"BLOCK: 5M REVERSAL CONFIRMED ({reversal_score:.1f} points)")
        else:
            score += 10
            reasons.append(f"5M reversal WARNING")

        if ema_cross == "BULLISH":
            score += 10
            reasons.append("5M EMA9/20 bullish cross")
        if momentum == "UP":
            score += 5
            reasons.append("5M upside momentum")

        if bos_5 == "BUY":
            score += 20
            reasons.append(f"5M BOS BUY at {bos_level_5:.2f}")
        if bos_15 == "BUY":
            score += 15
            reasons.append(f"15M BOS BUY at {bos_level_15:.2f}")
        if divergence == "BULLISH":
            score += 15
            reasons.append("15M RSI divergence (bullish)")

        if fib_pullback is not None and fib_pullback > (100 - FIB_EARLY_THRESHOLD):
            score += 10
            reasons.append(f"Fib pullback {fib_pullback:.1f}% (support zone)")

        if candle_bull and rsi_1 < 40:
            score += 10
            reasons.append("1M bullish candle + oversold RSI")

        if EARLY_ENTRY and trend != "BUY" and bos_5 == "BUY":
            score += 10
            reasons.append("EARLY ENTRY (BOS detected before trend)")

        quality = "STRONG" if score >= 80 else "NORMAL"
        return {
            "signal": "BUY",
            "price": price_1,
            "score": min(score, 100),
            "quality": quality,
            "trend": trend,
            "trend_phase": phase,
            "trend_age_bars": trend_age,
            "rsi": rsi_1,
            "reversal_score": reversal_score,
            "reversal_state": reversal_state,
            "reversal_categories": len(reversal_categories),
            "fib_pullback": fib_pullback,
            "bos_level": bos_level_5,
            "divergence": divergence,
            "reasons": reasons
        }

    # --- بدون سیگنال ---
    return {
        "signal": "NO SIGNAL",
        "price": price_1,
        "score": 0,
        "quality": "WEAK",
        "trend": trend,
        "trend_phase": phase,
        "trend_age_bars": trend_age,
        "rsi": rsi_1 if 'rsi_1' in locals() else None,
        "reversal_score": reversal_score if 'reversal_score' in locals() else 0,
        "reversal_state": reversal_state if 'reversal_state' in locals() else "NONE",
        "reversal_categories": len(reversal_categories) if 'reversal_categories' in locals() else 0,
        "fib_pullback": fib_pullback,
        "bos_level": bos_level_5,
        "divergence": divergence,
        "reasons": ["شرایط برقرار نیست"]
    }

# ==================================================
# 🚀 اجرای اصلی
# ==================================================
def main():
    print("=" * 60)
    print("🧪 GOLDPRO+ TREND CATCHER (EARLY ENTRY ENABLED)")
    print("=" * 60)

    # دریافت داده‌های سه تایم‌فریم
    print("📥 دریافت داده 15M...")
    df_15m = fetch_data("15min", days=DAYS_BACK)
    print("📥 دریافت داده 5M...")
    df_5m = fetch_data("5min", days=DAYS_BACK)
    print("📥 دریافت داده 1M...")
    df_1m = fetch_data("1min", days=1)

    if df_15m is None or df_5m is None or df_1m is None:
        print("❌ دریافت داده ناموفق")
        return

    print(f"📊 15M: {len(df_15m)} کندل از {df_15m.index[0]} تا {df_15m.index[-1]}")
    print(f"📊 5M:  {len(df_5m)} کندل از {df_5m.index[0]} تا {df_5m.index[-1]}")
    print(f"📊 1M:  {len(df_1m)} کندل از {df_1m.index[0]} تا {df_1m.index[-1]}")

    # تحلیل
    result = goldpro_signal(df_15m, df_5m, df_1m)

    # نمایش خروجی
    print("\n" + "=" * 60)
    print("📊 گزارش نهایی")
    print("=" * 60)

    if result['signal'] != "NO SIGNAL":
        emoji = "🔴" if result['signal'] == "SELL" else "🟢"
        print(f"{emoji} {SYMBOL} {result['signal']} SIGNAL")
        print(f"💰 قیمت ورود: {result['price']:.5f}")
        print(f"⭐ امتیاز: {result['score']}/100")
        print(f"🏷️ کیفیت: {result['quality']}")
        print(f"📈 Trend: {result['trend']}")
        print(f"🧭 Trend Phase: {result['trend_phase']}")
        print(f"⏳ Trend Age: {result['trend_age_bars']} bars")
        if result.get('fib_pullback') is not None:
            print(f"📐 Fib Pullback: {result['fib_pullback']:.1f}%")
        if result.get('bos_level'):
            print(f"📍 5M BOS Level: {result['bos_level']:.5f}")
        if result.get('divergence'):
            print(f"🔍 Divergence: {result['divergence']}")
        if result.get('reversal_score') is not None:
            print(f"🔄 Reversal Score: {result['reversal_score']:.1f} ({result['reversal_state']})")
        print("\n📋 دلایل:")
        for r in result['reasons']:
            print(f"  • {r}")
    else:
        print("⚠️ هیچ سیگنالی یافت نشد.")
        if result.get('trend'):
            print(f"   روند 15M: {result['trend']}")
        if result.get('fib_pullback') is not None:
            print(f"   فیبوناچی پولبک: {result['fib_pullback']:.1f}%")
        print("💡 پیشنهادات:")
        print("   - EARLY_ENTRY را True کنید (هم‌اکنون فعال است)")
        print("   - REVERSAL_THRESHOLD را به 2.0 کاهش دهید (هم‌اکنون 2.0)")
        print("   - FIB_EARLY_THRESHOLD را به 50 افزایش دهید (برای ورود در پولبک‌های بیشتر)")

    print("=" * 60)

if __name__ == "__main__":
    main()