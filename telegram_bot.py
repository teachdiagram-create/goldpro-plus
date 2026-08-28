import requests
import os

# =========================================================
# تنظیمات تلگرام
# =========================================================

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8976953594:AAEY4NAFO1I2ps8KkLPDft2PCl0B2xoZ5qU')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '100881313')

# =========================================================
# ارسال پیام به تلگرام
# =========================================================

def send_signal(signal_data, strategy_name="GOLDPRO+"):
    if signal_data is None:
        return

    if signal_data.get('signal') == "NO SIGNAL":
        print(f"⏳ {strategy_name}: No signal to send")
        return

    emoji = "🔴" if signal_data['signal'] == "SELL" else "🟢"

    message = f"""{emoji} <b>{strategy_name}</b> {signal_data['signal']} SIGNAL

💰 Symbol: XAU/USD
💵 Entry: {signal_data.get('price', 0):.5f}"""

    if signal_data.get('sl') is not None:
        message += f"""
🛑 Stop Loss: {signal_data['sl']:.2f}
🎯 TP1: {signal_data['tp1']:.2f}
🎯 TP2: {signal_data['tp2']:.2f}
📊 Risk/Reward: ~1:2"""

    message += f"""

⭐ Score: {signal_data.get('score', 0)}/100
🏷️ Quality: {signal_data.get('quality', 'WEAK')}

📈 Trend: {signal_data.get('trend', 'NONE')}
🧭 Phase: {signal_data.get('trend_phase', signal_data.get('phase', 'UNKNOWN'))}
🔄 Reversal: {signal_data.get('reversal_state', signal_data.get('stage', 'NONE'))}

📋 Details:
"""
    reasons = signal_data.get('reasons', [])
    if isinstance(reasons, list):
        for r in reasons[:5]:
            message += f"  • {r}\n"
    else:
        message += f"  • {reasons}\n"

    if signal_data.get('time'):
        message += f"\n⏰ {signal_data.get('time')}"

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
# تست سریع
# =========================================================

if __name__ == "__main__":
    test_signal = {
        "signal": "SELL",
        "price": 4620.50,
        "sl": 4632.00,
        "tp1": 4608.00,
        "tp2": 4596.00,
        "score": 65,
        "quality": "NORMAL",
        "trend": "SELL",
        "trend_phase": "EARLY",
        "reversal_state": "CONFIRMED",
        "reasons": ["OK: 5M downtrend (+30)", "OK: strong bearish candle (+20)", "OK: ADX 32.4 (+10)"],
        "time": "2026-08-28 16:30:00"
    }
    send_signal(test_signal, strategy_name="GOLDPRO+ (CLEAN)")