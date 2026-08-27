import time
from datetime import datetime, timezone
import os

from config import (
    MARKETS,
    STRATEGY_MODE,
    ENTRY_TIMEFRAME,
    CANDLE_LIMIT_15M,
    CANDLE_LIMIT_5M,
    CANDLE_LIMIT_1M,
    CHECK_DELAY_SECONDS,
    NEWS_FILTER_ENABLED,
)

from data_feed import get_market_data
from telegram_bot import send_goldpro_signal
from risk_manager import RiskManager
from news_filter import NewsFilter

# =========================================================
# STRATEGY SELECTOR
# =========================================================

if STRATEGY_MODE == "SCALPER":
    from scalper_strategy import generate_scalper_signal
    print("🧠 Strategy Loaded: GoldPro+ Scalper V7")
else:
    from goldpro_plus_strategy import generate_goldpro_plus_signal
    print("🧠 Strategy Loaded: GoldPro+ Classic")

# =========================================================
# LAST SENT SIGNAL (برای جلوگیری از تکرار)
# =========================================================

LAST_SENT_SIGNAL = None
LAST_SENT_SIGNAL_TIME = None
SIGNAL_COOLDOWN_SECONDS = 900

# =========================================================
# مدیریت ریسک و فیلتر خبری
# =========================================================

risk_manager = RiskManager()
news_filter = NewsFilter(api_key=os.getenv("ALPHA_VANTAGE_API_KEY"))

# =========================================================
# VALIDATE SCALPER SIGNAL
# =========================================================

def validate_scalper_signal(result):
    signal = result.get("signal", "NO SIGNAL")
    if signal not in ("BUY", "SELL"):
        return False, "Signal is not BUY/SELL"

    reasons = result.get("reasons", [])
    for reason in reasons:
        reason_text = str(reason).upper()
        if "BLOCK:" in reason_text or "FAIL:" in reason_text or "INVALID:" in reason_text:
            return False, f"Blocked condition: {reason}"

    quality = str(result.get("quality", "")).upper()
    if quality == "WEAK":
        return False, "Signal quality is WEAK"

    score = result.get("score", 0)
    try:
        score = float(score)
    except Exception:
        return False, "Invalid score"

    if score < 75:
        return False, f"Score too low: {score}"

    return True, "All conditions confirmed"

# =========================================================
# DUPLICATE PROTECTION
# =========================================================

def is_duplicate_signal(symbol, result):
    global LAST_SENT_SIGNAL, LAST_SENT_SIGNAL_TIME
    signal = result.get("signal", "NO SIGNAL")
    price = result.get("price")
    if signal not in ("BUY", "SELL") or price is None:
        return False
    try:
        price = float(price)
    except Exception:
        return False

    fingerprint = (symbol, signal, round(price, 2))
    if fingerprint == LAST_SENT_SIGNAL:
        return True

    if LAST_SENT_SIGNAL_TIME is not None:
        elapsed = time.time() - LAST_SENT_SIGNAL_TIME
        if elapsed < SIGNAL_COOLDOWN_SECONDS:
            last_dir = LAST_SENT_SIGNAL[1] if LAST_SENT_SIGNAL else None
            if last_dir == signal:
                return True
    return False

def mark_signal_as_sent(symbol, result):
    global LAST_SENT_SIGNAL, LAST_SENT_SIGNAL_TIME
    signal = result.get("signal", "NO SIGNAL")
    price = result.get("price")
    if signal not in ("BUY", "SELL") or price is None:
        return
    try:
        price = float(price)
    except Exception:
        return
    LAST_SENT_SIGNAL = (symbol, signal, round(price, 2))
    LAST_SENT_SIGNAL_TIME = time.time()

# =========================================================
# MARKET CHECK
# =========================================================

def check_market(symbol):
    print()
    print("=" * 60)
    print(f"========== {symbol} ==========")
    print("=" * 60)

    try:
        # دریافت داده‌ها
        df15 = None
        if STRATEGY_MODE == "SCALPER":
            print(f"[{symbol}] Getting 15M trend data...")
            df15 = get_market_data(symbol, "15min", CANDLE_LIMIT_15M)
            if df15 is None or df15.empty:
                print(f"[{symbol}] No 15M data received")
                return

        print(f"[{symbol}] Getting 5M data...")
        df5 = get_market_data(symbol, "5min", CANDLE_LIMIT_5M)
        if df5 is None or df5.empty:
            print(f"[{symbol}] No 5M data received")
            return

        print(f"[{symbol}] Getting 1M data...")
        df1 = get_market_data(symbol, ENTRY_TIMEFRAME, CANDLE_LIMIT_1M)
        if df1 is None or df1.empty:
            print(f"[{symbol}] No 1M data received")
            return

        # تولید سیگنال
        if STRATEGY_MODE == "SCALPER":
            result = generate_scalper_signal(df15, df5, df1)
        else:
            result = generate_goldpro_plus_signal(df5, df1)

        if not isinstance(result, dict):
            print("❌ Strategy returned invalid result.")
            return

        print()
        print(f"[{symbol}] GoldPro+ Signal:")
        print(result)

        signal = result.get("signal", "NO SIGNAL")
        score = result.get("score", 0)
        quality = result.get("quality", "UNKNOWN")
        price = result.get("price")
        trend = result.get("trend", "NONE")

        print()
        print(f"📈 Trend: {trend}")
        print(f"🎯 Signal: {signal}")
        print(f"⭐ Score: {score}/100")
        print(f"🏷️ Quality: {quality}")
        print(f"💰 Price: {price}")

        reasons = result.get("reasons", [])
        for reason in reasons:
            print(" •", reason)

        if signal not in ("BUY", "SELL"):
            print()
            print("⚪ GOLDPRO+ WAITING / NO SIGNAL")
            return

        # اعتبارسنجی سیگنال اسکالپر
        if STRATEGY_MODE == "SCALPER":
            valid, validation_message = validate_scalper_signal(result)
            if not valid:
                print()
                print("🛑 SIGNAL REJECTED")
                print(f"   Reason: {validation_message}")
                print("   Telegram: NOT SENT")
                return

        # بررسی تکراری
        if is_duplicate_signal(symbol, result):
            print()
            print("🔁 DUPLICATE SIGNAL")
            print("   Telegram: NOT SENT")
            return

        # =====================================================
        # مدیریت ریسک
        # =====================================================
        atr = result.get("atr")
        if atr is not None:
            sl, tp1, tp2 = risk_manager.set_stop_loss_take_profit(price, atr, signal)
            position_size = risk_manager.calculate_position_size(price, sl)
            if position_size <= 0:
                print("❌ حجم معامله صفر است، ورود انجام نمی‌شود")
                return
            print(f"📊 حجم معامله: {position_size}")
            print(f"🛑 استاپ لاس: {sl}")
            print(f"🎯 حد سود ۱: {tp1}")
            print(f"🎯 حد سود ۲: {tp2}")
        else:
            print("⚠️ ATR موجود نیست، مدیریت ریسک انجام نشد.")

        # =====================================================
        # ارسال به تلگرام
        # =====================================================
        print()
        print("📱 Sending signal to Telegram...")
        telegram_ok = send_goldpro_signal(symbol, result)
        if telegram_ok:
            mark_signal_as_sent(symbol, result)
            print("✅ Telegram signal sent.")
            print("🔒 Signal marked as sent.")
        else:
            print("❌ Telegram signal was not sent.")

    except Exception as exc:
        print()
        print(f"❌ [{symbol}] Market check error:")
        print(repr(exc))

# =========================================================
# MAIN LOOP
# =========================================================

def main():
    print()
    print("🟡 GoldPro+ Signal Bot Started")
    print(f"📊 Markets: {MARKETS}")
    print(f"⚙️ Mode: {STRATEGY_MODE}")
    if STRATEGY_MODE == "SCALPER":
        print("📈 Strategy: 15M Trend → 5M Structure → 1M Wave Entry")
    else:
        print("📈 Strategy: 5M Trend → 1M Entry")
    print()
    print("⏳ Waiting for market data...")

    while True:
        try:
            # =====================================================
            # فیلتر اخبار (قبل از هر بررسی بازار)
            # =====================================================
            if NEWS_FILTER_ENABLED:
                current_time = datetime.now(timezone.utc)
                if news_filter.is_blocked(current_time):
                    print("⏳ منتظر پایان اخبار مهم...")
                    time.sleep(60)
                    continue   # ← این continue داخل حلقه while است

            for symbol in MARKETS:
                check_market(symbol)

            print()
            print(f"⏳ Next check in {CHECK_DELAY_SECONDS} seconds...")
            time.sleep(CHECK_DELAY_SECONDS)

        except KeyboardInterrupt:
            print()
            print("🛑 GoldPro+ stopped")
            break
        except Exception as exc:
            print()
            print("❌ Main loop error:")
            print(repr(exc))
            time.sleep(5)

# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()