# main.py
import time
import logging
from datetime import datetime

from config import (
    MARKETS,
    STRATEGY_MODE,
    ENTRY_TIMEFRAME,
    CANDLE_LIMIT_15M,
    CANDLE_LIMIT_5M,
    CANDLE_LIMIT_1M,
    CHECK_DELAY_SECONDS,
    SYMBOL
)

from data_feed import get_market_data
from telegram_bot import send_goldpro_signal
from last_check import save_last_check, get_last_signal

# انتخاب استراتژی
if STRATEGY_MODE == "HYBRID":
    from hybrid_strategy import generate_hybrid_signal as generate_signal
    print("🧠 Strategy Loaded: GoldPro+ Hybrid V2")
elif STRATEGY_MODE == "SCALPER":
    from scalper_strategy import generate_scalper_signal as generate_signal
    print("🧠 Strategy Loaded: GoldPro+ Scalper V7")
else:
    from goldpro_plus_strategy import generate_goldpro_plus_signal as generate_signal
    print("🧠 Strategy Loaded: GoldPro+ Classic")

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_signal(result):
    """بررسی اعتبار سیگنال"""
    signal = result.get("signal", "NO SIGNAL")
    if signal not in ("BUY", "SELL"):
        return False, "Not a BUY/SELL signal"
    
    reasons = result.get("reasons", [])
    for reason in reasons:
        if "BLOCK:" in reason or "FAIL:" in reason or "INVALID:" in reason:
            return False, reason
    
    quality = result.get("quality", "").upper()
    if quality == "WEAK":
        return False, "Quality is WEAK"
    
    score = result.get("score", 0)
    if score < 75:
        return False, f"Score too low: {score}"
    
    return True, "Valid"


def check_market(symbol):
    logger.info(f"========== {symbol} ==========")
    
    try:
        # دریافت داده‌ها
        if STRATEGY_MODE == "HYBRID" or STRATEGY_MODE == "SCALPER":
            logger.info(f"[{symbol}] Getting 15M trend data...")
            df15 = get_market_data(symbol, "15min", CANDLE_LIMIT_15M)
            if df15 is None or df15.empty:
                logger.warning(f"[{symbol}] No 15M data")
                return
        else:
            df15 = None
        
        logger.info(f"[{symbol}] Getting 5M data...")
        df5 = get_market_data(symbol, "5min", CANDLE_LIMIT_5M)
        if df5 is None or df5.empty:
            logger.warning(f"[{symbol}] No 5M data")
            return
        
        logger.info(f"[{symbol}] Getting 1M data...")
        df1 = get_market_data(symbol, ENTRY_TIMEFRAME, CANDLE_LIMIT_1M)
        if df1 is None or df1.empty:
            logger.warning(f"[{symbol}] No 1M data")
            return
        
        # تولید سیگنال
        if STRATEGY_MODE == "HYBRID":
            result = generate_signal(df15, df5, df1, account_balance=10000)
        elif STRATEGY_MODE == "SCALPER":
            result = generate_signal(df15, df5, df1)
        else:
            result = generate_signal(df5, df1)
        
        if not isinstance(result, dict):
            logger.error("Invalid result from strategy")
            return
        
        # نمایش نتایج
        signal = result.get("signal", "NO SIGNAL")
        score = result.get("score", 0)
        quality = result.get("quality", "UNKNOWN")
        price = result.get("price")
        trend = result.get("trend", "NONE")
        
        logger.info(f"📈 Trend: {trend}")
        logger.info(f"🎯 Signal: {signal}")
        logger.info(f"⭐ Score: {score}/100")
        logger.info(f"🏷️ Quality: {quality}")
        logger.info(f"💰 Price: {price}")
        
        # نمایش دلایل
        for reason in result.get("reasons", [])[:5]:
            logger.info(f" • {reason}")
        
        # فقط سیگنال‌های BUY/SELL را پردازش کن
        if signal not in ("BUY", "SELL"):
            logger.info("⚪ GOLDPRO+ WAITING / NO SIGNAL")
            return
        
        # اعتبارسنجی
        valid, msg = validate_signal(result)
        if not valid:
            logger.info(f"🛑 SIGNAL REJECTED: {msg}")
            return
        
        # جلوگیری از ارسال تکراری
        prev_signal = get_last_signal(symbol)
        if prev_signal and prev_signal.get("signal") == signal:
            logger.info("🔁 DUPLICATE SIGNAL - Not sending")
            return
        
        # ارسال به تلگرام
        logger.info("📱 Sending signal to Telegram...")
        telegram_ok = send_goldpro_signal(symbol, result)
        if telegram_ok:
            save_last_check(symbol, result)
            logger.info("✅ Signal sent and marked as sent")
        else:
            logger.error("❌ Failed to send Telegram message")
            
    except Exception as e:
        logger.error(f"❌ Market check error: {repr(e)}")


def main():
    logger.info("🟡 GoldPro+ Signal Bot Started")
    logger.info(f"📊 Markets: {MARKETS}")
    logger.info(f"⚙️ Mode: {STRATEGY_MODE}")
    logger.info(f"⏳ Check interval: {CHECK_DELAY_SECONDS}s")
    
    while True:
        try:
            for symbol in MARKETS:
                check_market(symbol)
            
            logger.info(f"⏳ Next check in {CHECK_DELAY_SECONDS} seconds...")
            time.sleep(CHECK_DELAY_SECONDS)
            
        except KeyboardInterrupt:
            logger.info("🛑 GoldPro+ stopped")
            break
        except Exception as e:
            logger.error(f"❌ Main loop error: {repr(e)}")
            time.sleep(5)


if __name__ == "__main__":
    main()