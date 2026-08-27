# telegram_bot.py
import os
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ TELEGRAM_TOKEN or CHAT_ID missing")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            print("📱 Telegram message sent successfully")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram connection error: {repr(e)}")
        return False


def format_signal_message(symbol, result):
    signal = result.get("signal", "NO SIGNAL")
    price = result.get("price")
    score = result.get("score", 0)
    quality = result.get("quality", "UNKNOWN")
    trend = result.get("trend", "NONE")
    trend_phase = result.get("trend_phase", "UNKNOWN")
    entry = result.get("entry")
    stop_loss = result.get("stop_loss")
    take_profit = result.get("take_profit")
    risk_reward = result.get("risk_reward", 0)
    rsi = result.get("rsi")
    atr = result.get("atr")
    reasons = result.get("reasons", [])
    
    if signal == "BUY":
        title = "🟢 GOLDPRO+ BUY SIGNAL"
    elif signal == "SELL":
        title = "🔴 GOLDPRO+ SELL SIGNAL"
    else:
        title = "⚪ GOLDPRO+ NO SIGNAL"
    
    message = f"""{title}
💰 Symbol: {symbol}
💵 Entry: {price}

📈 Trend: {trend} ({trend_phase})
⭐ Score: {score}/100
🏷️ Quality: {quality}
"""
    
    if entry and stop_loss and take_profit:
        message += f"""
🛑 Stop Loss: {stop_loss:.2f}
🎯 Take Profit: {take_profit:.2f}
📊 RR Ratio: {risk_reward:.2f}
"""
    
    if rsi is not None:
        message += f"📊 RSI: {rsi:.1f}\n"
    if atr is not None:
        message += f"📊 ATR: {atr:.2f}\n"
    
    if reasons:
        message += "\n📋 Conditions:\n"
        for r in reasons[:5]:
            message += f"• {r}\n"
    
    message += "\n#GoldProPlus #TradingSignal"
    return message


def send_goldpro_signal(symbol, result):
    signal = result.get("signal", "NO SIGNAL")
    if signal not in ("BUY", "SELL"):
        return False
    
    message = format_signal_message(symbol, result)
    return send_telegram_message(message)