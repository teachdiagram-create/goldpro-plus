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
# STRATEGY SELECTOR
# =========================================================

if STRATEGY_MODE == "SCALPER":

    from scalper_strategy import (
        generate_scalper_signal
    )

    print(
        "🧠 Strategy Loaded: GoldPro+ Scalper V2"
    )

else:

    from goldpro_plus_strategy import (
        generate_goldpro_plus_signal
    )

    print(
        "🧠 Strategy Loaded: GoldPro+ Classic"
    )


# =========================================================
# MARKET CHECK
# =========================================================

def check_market(symbol):

    print()
    print("=" * 60)
    print(f"========== {symbol} ==========")
    print("=" * 60)

    try:

        # =================================================
        # 15M DATA
        # =================================================

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

            if df15 is None or df15.empty:

                print(
                    f"[{symbol}] No 15M data received"
                )

                return

        # =================================================
        # 5M DATA
        # =================================================

        print(
            f"[{symbol}] Getting 5M data..."
        )

        df5 = get_market_data(
            symbol,
            "5min",
            CANDLE_LIMIT_5M
        )

        if df5 is None or df5.empty:

            print(
                f"[{symbol}] No 5M data received"
            )

            return

        # =================================================
        # 1M DATA
        # =================================================

        print(
            f"[{symbol}] Getting 1M data..."
        )

        df1 = get_market_data(
            symbol,
            ENTRY_TIMEFRAME,
            CANDLE_LIMIT_1M
        )

        if df1 is None or df1.empty:

            print(
                f"[{symbol}] No 1M data received"
            )

            return

        # =================================================
        # GENERATE SIGNAL
        # =================================================

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

        # =================================================
        # RESULT
        # =================================================

        print()

        print(
            f"[{symbol}] GoldPro+ Signal:"
        )

        print(
            result
        )

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

        # =================================================
        # DISPLAY
        # =================================================

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

        print(
            f"💰 Price: {price}"
        )

        # =================================================
        # REASONS
        # =================================================

        for reason in result.get(
            "reasons",
            []
        ):

            print(
                " •",
                reason
            )

        # =================================================
        # TELEGRAM
        #
        # فقط BUY و SELL
        # NO SIGNAL ارسال نمی‌شود
        # =================================================

        if signal in (
            "BUY",
            "SELL"
        ):

            print()

            print(
                "📱 Sending signal to Telegram..."
            )

            telegram_ok = send_goldpro_signal(
                symbol,
                result
            )

            if telegram_ok:

                print(
                    "✅ Telegram signal sent."
                )

            else:

                print(
                    "❌ Telegram signal was not sent."
                )

        else:

            print()

            print(
                "⚪ GOLDPRO+ WAITING / NO SIGNAL"
            )

    # =====================================================
    # MARKET ERROR
    # =====================================================

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
            "15M Trend → 5M Confirmation → 1M Entry"
        )

        print(
            "💡 API optimization:"
        )

        print(
            "   15M → every 30 minutes"
        )

        print(
            "   5M  → every 10 minutes"
        )

        print(
            "   1M  → every 3 minutes"
        )

    else:

        print(
            "📈 Strategy: 5M Trend → 1M Entry"
        )

    print()

    print(
        "⏳ Waiting for market data..."
    )

    # =====================================================
    # LOOP
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