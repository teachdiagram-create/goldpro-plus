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


# =========================================================
# STRATEGY SELECTOR
# =========================================================

if STRATEGY_MODE == "SCALPER":

    from scalper_strategy import (
        generate_scalper_signal
    )

    print(
        "🧠 Strategy Loaded: GoldPro+ Scalper V1"
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

        df15 = None


        # =================================================
        # SCALPER DATA
        # =================================================

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
        # STRATEGY
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


        price = result.get(
            "price"
        )


        trend = result.get(
            "trend",
            "NONE"
        )


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
            f"💰 Price: {price}"
        )


        print()


        for reason in result.get(
            "reasons",
            []
        ):

            print(
                " •",
                reason
            )



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
            "📈 Strategy: 15M Trend → 5M Confirmation → 1M Entry"
        )

    else:

        print(
            "📈 Strategy: 5M Trend → 1M Entry"
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


            print(
                "🛑 Bot stopped"
            )

            break



        except Exception as exc:


            print(
                "❌ Main loop error:",
                repr(exc)
            )


            time.sleep(5)



# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()