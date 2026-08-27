# main.py
import time
import logging
from datetime import datetime
from data_feed import get_market_data
from hybrid_strategy import generate_hybrid_signal, format_signal_for_telegram
from telegram_bot import send_telegram_message
from last_check import save_last_check, get_last_signal

# تنظیمات
SYMBOL = "XAU/USD"
CHECK_INTERVAL = 60  # ثانیه
ACCOUNT_BALANCE = 10000  # دلار

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🚀 GoldPro+ Hybrid V2 Started")
    logger.info(f"📊 Symbol: {SYMBOL}")
    logger.info(f"⏱️ Check interval: {CHECK_INTERVAL}s")
    
    last_signal = None
    
    while True:
        try:
            # دریافت داده‌ها
            logger.info(f"[{SYMBOL}] Getting market data...")
            
            df15 = get_market_data(SYMBOL, "15min", limit=50)
            df5 = get_market_data(SYMBOL, "5min", limit=50)
            df1 = get_market_data(SYMBOL, "1min", limit=30)
            
            if df15 is None or df5 is None or df1 is None:
                logger.warning("Failed to get market data, retrying...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # تولید سیگنال
            signal = generate_hybrid_signal(df15, df5, df1, ACCOUNT_BALANCE)
            
            # نمایش در کنسول
            logger.info(f"[{SYMBOL}] Signal: {signal['signal']} | Score: {signal['score']}/100")
            logger.info(f"Reasons: {signal['reasons'][:3]}")
            
            # ارسال به تلگرام
            if signal["signal"] != "NO SIGNAL":
                # بررسی سیگنال تکراری نباشد
                prev_signal = get_last_signal(SYMBOL)
                if prev_signal is None or prev_signal.get("signal") != signal["signal"]:
                    # سیگنال جدید
                    message = format_signal_for_telegram(signal)
                    send_telegram_message(message)
                    last_signal = signal["signal"]
                    logger.info(f"✅ Signal sent to Telegram: {signal['signal']}")
                else:
                    logger.info("Same signal, not sending duplicate")
            
            # ذخیره آخرین بررسی
            save_last_check(SYMBOL, signal)
            
            # انتظار
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("👋 Stopped by user")
            break
            
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()