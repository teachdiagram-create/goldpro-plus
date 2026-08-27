# telegram_bot.py
import os
import logging
import requests

logger = logging.getLogger(__name__)

# توکن و چت آیدی رو از environment variables بگیر
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_message(message):
    """ارسال پیام به تلگرام"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Telegram message sent")
            return True
        else:
            logger.error(f"❌ Telegram error: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Telegram send error: {e}")
        return False