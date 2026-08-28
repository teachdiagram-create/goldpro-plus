import requests
import os

# =========================================================
# تنظیمات تلگرام (از متغیرهای محیطی یا مستقیم)
# =========================================================

TELEGRAM_TOKEN = os.environ.get('8976953594:AAEY4NAFO1I2ps8KkLPDft2PCl0B2xoZ5qU', 'YOUR_BOT_TOKEN_HERE')
TELEGRAM_CHAT_ID = os.environ.get('100881313', 'YOUR_CHAT_ID_HERE')

# =========================================================
# ارسال پیام به تلگرام
# =========================================================

def send_signal(signal_data, strategy_name="GOLDPRO+"):
    """
    ارسال سیگنال به تلگرام با نام استراتژی
    """
    if signal_data is None:
        return
    
    if signal_data.get('signal') == "NO SIGNAL":
        print(f"⏳ {strategy_name}: No signal to send")
        return
    
    # ایموجی based on signal type
    if signal_data['signal'] == "SELL":
        emoji = "🔴"
    elif signal_data['signal'] == "BUY":
        emoji = "🟢"
    else:
        emoji = "⚪"
    
    # ساخت پیام
    message = f"""{emoji} <b>{strategy_name}</b> {signal_data['signal']} SIGNAL

💰 Symbol: XAU/USD
💵 Entry: {signal_data.get('price', 0):.5f}

⭐ Score: {signal_data.get('score', 0)}/100
🏷️ Quality: {signal_data.get('quality', 'WEAK')}

📈 Trend: {signal_data.get('trend', 'NONE')}
🧭 Phase: {signal_data.get('trend_phase', signal_data.get('phase', 'UNKNOWN'))}
🔄 Reversal: {signal_data.get('reversal_state', signal_data.get('stage', 'NONE'))}

📋 Details:
"""
    # اضافه کردن دلایل (حداکثر ۵ مورد)
    reasons = signal_data.get('reasons', [])
    if isinstance(reasons, list):
        for r in reasons[:5]:
            message += f"  • {r}\n"
    else:
        message += f"  • {reasons}\n"
    
    # اضافه کردن زمان
    if signal_data.get('time'):
        message += f"\n⏰ {signal_data.get('time')}"
    
    # ارسال به تلگرام
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ پیام {strategy_name} ارسال شد")
        else:
            print(f"❌ خطا در ارسال {strategy_name}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ خطا در ارسال {strategy_name}: {e}")

# =========================================================
# تابع تست (برای بررسی سریع)
# =========================================================

if __name__ == "__main__":
    # تست ارسال پیام
    test_signal = {
        "signal": "BUY",
        "price": 4600.00,
        "score": 80,
        "quality": "STRONG",
        "trend": "BUY",
        "trend_phase": "MATURE",
        "reversal_state": "CONFIRMED",
        "reasons": ["Test reason 1", "Test reason 2"],
        "time": "2026-08-28 16:30:00"
    }
    send_signal(test_signal, strategy_name="TEST")