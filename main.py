import time
from datetime import datetime

from config import (
    MARKETS,
    TREND_TIMEFRAME,
    ENTRY_TIMEFRAME,
    CANDLE_LIMIT_5M,
    CANDLE_LIMIT_1M,
    CHECK_DELAY_SECONDS,
)

from data_feed import get_market_data

from goldpro_plus_strategy import (
    generate_goldpro_plus_signal
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
        # 5M DATA
        # =================================================

        print(
            f"[{symbol}] Getting "
            f"{TREND_TIMEFRAME} trend data..."
        )

        df5 = get_market_data(
            symbol,
            TREND_TIMEFRAME,
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
            f"[{symbol}] Getting "
            f"{ENTRY_TIMEFRAME} entry data..."
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
        # GOLDPRO+
        #
        # 5M = TREND
        # 1M = ENTRY
        # =================================================

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

        # =================================================
        # BASIC INFORMATION
        # =================================================

        signal = result.get(
            "signal",
            "NO SIGNAL"
        )

        score = result.get(
            "score",
            0
        )

        trend = result.get(
            "trend",
            "NONE"
        )

        price = result.get(
            "price"
        )

        rsi = result.get(
            "rsi"
        )

        atr = result.get(
            "atr"
        )

        print()
        print(
            f"📈 5M Trend: {trend}"
        )

        print(
            f"🎯 1M Signal: {signal}"
        )

        print(
            f"⭐ Score: {score}/100"
        )

        print(
            f"💰 Price: {price}"
        )

        print(
            f"RSI: {rsi}"
        )

        print(
            f"ATR: {atr}"
        )

        # =================================================
        # BUY
        # =================================================

        if signal == "BUY":

            print()
            print(
                "🟢 =============================="
            )

            print(
                "🟢 GOLDPRO+ BUY SIGNAL"
            )

            print(
                "🟢 =============================="
            )

            print(
                f"Entry: {price}"
            )

            print(
                f"Score: {score}/100"
            )

            print(
                "Note: TP/SL will be added "
                "in the next strategy version."
            )

        # =================================================
        # SELL
        # =================================================

        elif signal == "SELL":

            print()
            print(
                "🔴 =============================="
            )

            print(
                "🔴 GOLDPRO+ SELL SIGNAL"
            )

            print(
                "🔴 =============================="
            )

            print(
                f"Entry: {price}"
            )

            print(
                f"Score: {score}/100"
            )

            print(
                "Note: TP/SL will be added "
                "in the next strategy version."
            )

        # =================================================
        # NO SIGNAL
        # =================================================

        else:

            print()
            print(
                "⚪ GOLDPRO+ WAITING / NO SIGNAL"
            )

            print(
                f"Reason:"
            )

            for reason in result.get(
                "reasons",
                []
            ):

                print(
                    f"  • {reason}"
                )

    except Exception as exc:

        print()
        print(
            f"❌ [{symbol}] "
            f"Market check error:"
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
        "🟡 GoldPro+ 1M Signal Bot Started"
    )

    print(
        "📊 Markets: XAU/USD"
    )

    print(
        "📈 Trend timeframe: 5M"
    )

    print(
        "🎯 Entry timeframe: 1M"
    )

    print(
        "🧠 Strategy: 5M Trend → 1M Entry"
    )

    print()
    print(
        "⏳ Waiting for market data..."
    )

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

            time.sleep(5)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
