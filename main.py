import time

from config import (
    MARKETS,
    STRATEGY_MODE,
    ENTRY_TIMEFRAME,
    CANDLE_LIMIT_15M,
    CANDLE_LIMIT_5M,
    CANDLE_LIMIT_1M,
    CHECK_DELAY_SECONDS,
)

from data_feed import get_market_data
from telegram_bot import send_goldpro_signal


# =========================================================
# GOLDPRO+ MAIN V3
#
# وظایف:
#
# 1. دریافت 15M / 5M / 1M
# 2. اجرای Scalper Strategy
# 3. ارسال فقط سیگنال معتبر
# 4. جلوگیری از ارسال سیگنال ناقص
# 5. جلوگیری از ارسال تکراری
#
# =========================================================


# =========================================================
# LAST SENT SIGNAL
# =========================================================

# برای جلوگیری از ارسال چندباره یک سیگنال
#
# مثال:
# BUY 4637.88696
#
# فقط یک بار ارسال می‌شود.
#
LAST_SENT_SIGNAL = None
LAST_SENT_SIGNAL_TIME = None
LAST_SENT_SIGNAL_WAVE = None
SIGNAL_COOLDOWN_SECONDS = 900


# =========================================================
# STRATEGY SELECTOR
# =========================================================

if STRATEGY_MODE == "SCALPER":

    from scalper_strategy import (
        generate_scalper_signal
    )

    print(
        "🧠 Strategy Loaded: GoldPro+ Scalper V5"
    )

else:

    from goldpro_plus_strategy import (
        generate_goldpro_plus_signal
    )

    print(
        "🧠 Strategy Loaded: GoldPro+ Classic"
    )


# =========================================================
# VALIDATE SCALPER SIGNAL
# =========================================================

def validate_scalper_signal(result):

    """
    بررسی می‌کند که آیا سیگنال Scalper
    واقعاً تمام شروط لازم را دارد یا خیر.

    برای BUY / SELL باید:

    15M Trend       = OK
    5M EMA9         = OK
    1M RSI          = OK
    1M Candle       = OK
    Candlestick     = OK

    اگر هر کدام WAIT باشد:
        سیگنال ارسال نمی‌شود.
    """

    signal = result.get(
        "signal",
        "NO SIGNAL"
    )

    if signal not in (
        "BUY",
        "SELL"
    ):

        return False, "Signal is not BUY/SELL"


    reasons = result.get(
        "reasons",
        []
    )


    # ---------------------------------------------------------
    # تمام دلایل را بررسی می‌کنیم
    # ---------------------------------------------------------

    for reason in reasons:

        reason_text = str(
            reason
        ).upper()


        # در V4، WAIT می‌تواند فقط وضعیت یک عامل غیرضروری باشد.
        # Strategy فقط وقتی BUY/SELL می‌دهد که timing filter و شرایط سخت ورود تأیید شده باشند.
        # بنابراین فقط BLOCK/FAIL/INVALID باید سیگنال را رد کنند.

        if "BLOCK:" in reason_text:

            return False, (
                f"Blocked condition: {reason}"
            )


        # هر FAIL یعنی setup نامعتبر است
        if "FAIL:" in reason_text:

            return False, (
                f"Failed condition: {reason}"
            )


        # هر INVALID یعنی setup نامعتبر است
        if "INVALID:" in reason_text:

            return False, (
                f"Invalid condition: {reason}"
            )


    # ---------------------------------------------------------
    # بررسی کیفیت
    # ---------------------------------------------------------

    quality = str(
        result.get(
            "quality",
            ""
        )
    ).upper()


    if quality == "WEAK":

        return False, (
            "Signal quality is WEAK"
        )


    # ---------------------------------------------------------
    # بررسی Score
    # ---------------------------------------------------------

    score = result.get(
        "score",
        0
    )


    try:

        score = float(
            score
        )

    except Exception:

        return False, (
            "Invalid score"
        )


    # ---------------------------------------------------------
    # حداقل Score برای ارسال
    # ---------------------------------------------------------

    if score < 75:

        return False, (
            f"Score too low: {score}"
        )


    # ---------------------------------------------------------
    # اگر همه چیز OK بود
    # ---------------------------------------------------------

    return True, (
        "All conditions confirmed"
    )


# =========================================================
# DUPLICATE PROTECTION
# =========================================================

def is_duplicate_signal(
    symbol,
    result
):

    global LAST_SENT_SIGNAL, LAST_SENT_SIGNAL_TIME, LAST_SENT_SIGNAL_WAVE

    signal = result.get("signal", "NO SIGNAL")
    price = result.get("price")

    if signal not in ("BUY", "SELL") or price is None:
        return False

    try:
        price = float(price)
    except Exception:
        return False

    # Exact/near-exact duplicate.
    fingerprint = (symbol, signal, round(price, 2))
    if fingerprint == LAST_SENT_SIGNAL:
        return True

    # Same-direction cooldown: do not fire multiple entries inside one short impulse.
    if LAST_SENT_SIGNAL_TIME is not None:
        elapsed = time.time() - LAST_SENT_SIGNAL_TIME
        if elapsed < SIGNAL_COOLDOWN_SECONDS:
            last_wave = LAST_SENT_SIGNAL_WAVE or {}
            current_wave = {
                "low": result.get("wave_low"),
                "high": result.get("wave_high"),
            }
            last_dir = LAST_SENT_SIGNAL[1] if LAST_SENT_SIGNAL else None
            if last_dir == signal:
                return True

    return False


# =========================================================
# MARK SIGNAL AS SENT
# =========================================================

def mark_signal_as_sent(
    symbol,
    result
):

    global LAST_SENT_SIGNAL, LAST_SENT_SIGNAL_TIME, LAST_SENT_SIGNAL_WAVE

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
    LAST_SENT_SIGNAL_WAVE = {
        "low": result.get("wave_low"),
        "high": result.get("wave_high"),
    }


# =========================================================
# MARKET CHECK
# =========================================================

def check_market(symbol):

    print()

    print(
        "=" * 60
    )

    print(
        f"========== {symbol} =========="
    )

    print(
        "=" * 60
    )


    try:

        # =====================================================
        # 15M DATA
        # =====================================================

        df15 = None


        if STRATEGY_MODE == "SCALPER":

            print(
                f"[{symbol}] Getting 15M trend data..."
            )


            df15 = get_market_data(
                symbol,
                "15min",
                CANDLE_LIMIT_15M
            )


            if (
                df15 is None
                or df15.empty
            ):

                print(
                    f"[{symbol}] No 15M data received"
                )

                return


        # =====================================================
        # 5M DATA
        # =====================================================

        print(
            f"[{symbol}] Getting 5M data..."
        )


        df5 = get_market_data(
            symbol,
            "5min",
            CANDLE_LIMIT_5M
        )


        if (
            df5 is None
            or df5.empty
        ):

            print(
                f"[{symbol}] No 5M data received"
            )

            return


        # =====================================================
        # 1M DATA
        # =====================================================

        print(
            f"[{symbol}] Getting 1M data..."
        )


        df1 = get_market_data(
            symbol,
            ENTRY_TIMEFRAME,
            CANDLE_LIMIT_1M
        )


        if (
            df1 is None
            or df1.empty
        ):

            print(
                f"[{symbol}] No 1M data received"
            )

            return


        # =====================================================
        # GENERATE SIGNAL
        # =====================================================

        if STRATEGY_MODE == "SCALPER":

            result = generate_scalper_signal(
                df15,
                df5,
                df1
            )

        else:

            result = generate_goldpro_plus_signal(
                df5,
                df1
            )


        # =====================================================
        # SAFETY
        # =====================================================

        if not isinstance(
            result,
            dict
        ):

            print(
                "❌ Strategy returned invalid result."
            )

            return


        # =====================================================
        # RESULT
        # =====================================================

        print()

        print(
            f"[{symbol}] GoldPro+ Signal:"
        )

        print(
            result
        )


        # =====================================================
        # READ RESULT
        # =====================================================

        signal = result.get(
            "signal",
            "NO SIGNAL"
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


        price = result.get(
            "price"
        )


        trend = result.get(
            "trend",
            "NONE"
        )


        # =====================================================
        # DISPLAY
        # =====================================================

        print()

        print(
            f"📈 Trend: {trend}"
        )


        print(
            f"🎯 Signal: {signal}"
        )


        print(
            f"⭐ Score: {score}/100"
        )


        print(
            f"💪 Confidence: {confidence}%"
        )


        print(
            f"🏷️ Quality: {quality}"
        )


        trend_phase = result.get("trend_phase", "UNKNOWN")
        wave_stage = result.get("wave_stage", "UNKNOWN")
        wave_position = result.get("wave_position")

        print(
            f"🧭 Trend Phase: {trend_phase}"
        )

        print(
            f"🌊 Wave Stage: {wave_stage}"
        )

        if wave_position is not None:

            print(
                f"📍 Wave Position: {wave_position * 100:.1f}%"
            )


        print(
            f"💰 Price: {price}"
        )


        # =====================================================
        # REASONS
        # =====================================================

        reasons = result.get(
            "reasons",
            []
        )


        for reason in reasons:

            print(
                " •",
                reason
            )


        # =====================================================
        # ONLY BUY / SELL
        # =====================================================

        if signal not in (
            "BUY",
            "SELL"
        ):

            print()

            print(
                "⚪ GOLDPRO+ WAITING / NO SIGNAL"
            )

            return


        # =====================================================
        # SCALPER VALIDATION
        # =====================================================

        if STRATEGY_MODE == "SCALPER":

            valid, validation_message = (
                validate_scalper_signal(
                    result
                )
            )


            if not valid:

                print()

                print(
                    "🛑 SIGNAL REJECTED"
                )


                print(
                    f"   Reason: {validation_message}"
                )


                print(
                    "   Telegram: NOT SENT"
                )


                return


        # =====================================================
        # DUPLICATE CHECK
        # =====================================================

        if is_duplicate_signal(
            symbol,
            result
        ):

            print()

            print(
                "🔁 DUPLICATE SIGNAL"
            )


            print(
                "   Telegram: NOT SENT"
            )


            return


        # =====================================================
        # VALID SIGNAL
        # =====================================================

        print()

        print(
            "🟢 =============================="
        )


        print(
            f"🟢 GOLDPRO+ {signal} SIGNAL"
        )


        print(
            "🟢 =============================="
        )


        print(
            f"Entry: {price}"
        )


        # =====================================================
        # TELEGRAM
        # =====================================================

        print()

        print(
            "📱 Sending signal to Telegram..."
        )


        telegram_ok = send_goldpro_signal(
            symbol,
            result
        )


        if telegram_ok:

            mark_signal_as_sent(
                symbol,
                result
            )


            print(
                "✅ Telegram signal sent."
            )


            print(
                "🔒 Signal marked as sent."
            )


        else:

            print(
                "❌ Telegram signal was not sent."
            )


    # =========================================================
    # MARKET ERROR
    # =========================================================

    except Exception as exc:

        print()

        print(
            f"❌ [{symbol}] Market check error:"
        )


        print(
            repr(exc)
        )


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    print()

    print(
        "🟡 GoldPro+ Signal Bot Started"
    )


    print(
        f"📊 Markets: {MARKETS}"
    )


    print(
        f"⚙️ Mode: {STRATEGY_MODE}"
    )


    if STRATEGY_MODE == "SCALPER":

        print(
            "📈 Strategy: "
            "15M Trend → 5M Structure → 1M Wave Entry"
        )


        print(
            "💡 API optimization:"
        )


        print(
            "   15M → cache/API according to data feed TTL"
        )


        print(
            "   5M  → cache/API according to data feed TTL"
        )


        print(
            "   1M  → cache/API according to data feed TTL"
        )


    else:

        print(
            "📈 Strategy: "
            "5M Trend → 1M Entry"
        )


    print()

    print(
        "⏳ Waiting for market data..."
    )


    # =====================================================
    # MAIN LOOP
    # =====================================================

    while True:

        try:

            for symbol in MARKETS:

                check_market(
                    symbol
                )


            print()

            print(
                f"⏳ Next check in "
                f"{CHECK_DELAY_SECONDS} seconds..."
            )


            time.sleep(
                CHECK_DELAY_SECONDS
            )


        except KeyboardInterrupt:

            print()

            print(
                "🛑 GoldPro+ stopped"
            )

            break


        except Exception as exc:

            print()

            print(
                "❌ Main loop error:"
            )


            print(
                repr(exc)
            )


            time.sleep(
                5
            )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()