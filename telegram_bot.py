import os
import requests


# =========================================================
# TELEGRAM CONFIG
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# =========================================================
# SEND TELEGRAM MESSAGE
# =========================================================

def send_telegram_message(message):

    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN is missing")
        return False

    if not CHAT_ID:
        print("❌ CHAT_ID is missing")
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        if response.status_code == 200:

            print("📱 Telegram message sent successfully")
            return True

        print(
            "❌ Telegram error:",
            response.status_code,
            response.text
        )

        return False

    except requests.RequestException as exc:

        print(
            "❌ Telegram connection error:",
            repr(exc)
        )

        return False


# =========================================================
# FORMAT GOLDPRO+ SIGNAL
# =========================================================

def format_signal_message(symbol, result):

    signal = result.get(
        "signal",
        "NO SIGNAL"
    )

    price = result.get(
        "price"
    )

    score = result.get(
        "score",
        0
    )

    confidence = result.get(
        "confidence",
        0
    )

    quality = result.get(
        "quality",
        "UNKNOWN"
    )

    trend = result.get(
        "trend",
        "NONE"
    )

    trend_phase = result.get(
        "trend_phase",
        "UNKNOWN"
    )

    entry_timing_ok = result.get(
        "entry_timing_ok",
        False
    )

    recent_high = result.get(
        "recent_high"
    )

    recent_low = result.get(
        "recent_low"
    )

    extension_atr = result.get(
        "extension_atr"
    )

    wave_stage = result.get(
        "wave_stage",
        "UNKNOWN"
    )

    wave_position = result.get(
        "wave_position"
    )

    wave_low = result.get(
        "wave_low"
    )

    wave_high = result.get(
        "wave_high"
    )

    reasons = result.get(
        "reasons",
        []
    )

    if signal == "BUY":

        title = "🟢 GOLDPRO+ BUY SIGNAL"

    elif signal == "SELL":

        title = "🔴 GOLDPRO+ SELL SIGNAL"

    else:

        title = "⚪ GOLDPRO+ NO SIGNAL"


    message = (
        f"{title}\n"
        f"\n"
        f"💰 Symbol: {symbol}\n"
        f"💵 Entry: {price}\n"
        f"\n"
        f"📈 Trend: {trend}\n"
        f"🧭 Trend Phase: {trend_phase}\n"
        f"🌊 Wave Stage: {wave_stage}\n"
        f"⏱️ Entry Timing: {'OK' if entry_timing_ok else 'FILTERED'}\n"
        f"⭐ Score: {score}/100\n"
        f"💪 Confidence: {confidence}%\n"
        f"🏷️ Quality: {quality}\n"
        f"\n"
        f"🧠 Strategy:\n"
        f"15M Trend → 5M Confirmation → 1M Entry"
    )


    if wave_position is not None:

        try:
            wave_position_text = f"{float(wave_position) * 100:.1f}%"
        except Exception:
            wave_position_text = str(wave_position)

        message += (
            f"\n📍 Wave Position: {wave_position_text}"
        )

    if wave_low is not None and wave_high is not None:

        message += (
            f"\n🌊 Wave: {wave_low} → {wave_high}"
        )

    if reasons:

        message += "\n\n📋 Conditions:"

        for reason in reasons:

            message += (
                f"\n• {reason}"
            )


    return message


# =========================================================
# SEND GOLDPRO+ SIGNAL
# =========================================================

def send_goldpro_signal(
    symbol,
    result
):

    signal = result.get(
        "signal",
        "NO SIGNAL"
    )

    # فقط BUY و SELL ارسال شوند
    if signal not in (
        "BUY",
        "SELL"
    ):

        return False


    message = format_signal_message(
        symbol,
        result
    )


    return send_telegram_message(
        message
    )