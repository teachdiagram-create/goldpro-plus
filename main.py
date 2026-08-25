import time
from telegram_bot import send_goldpro_signal

from config import (
    MARKETS,
    STRATEGY_MODE,
    ENTRY_TIMEFRAME,
    CANDLE_LIMIT_15M,
    CANDLE_LIMIT_5M,
    CANDLE_LIMIT_1M,
    CHECK_DELAY_SECONDS,

    TREND_REFRESH_SECONDS,
    CONFIRMATION_REFRESH_SECONDS,
    ENTRY_REFRESH_SECONDS,
)

from data_feed import get_market_data


# =========================================================
# STRATEGY SELECTOR
# =========================================================

if STRATEGY_MODE == "SCALPER":

    from scalper_strategy import generate_scalper_signal

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
# MEMORY CACHE
# =========================================================

_MARKET_DATA = {}


# =========================================================
# LAST SUCCESSFUL REQUEST
# =========================================================

_LAST_REQUEST = {}


# =========================================================
# REFRESH INTERVALS
# =========================================================

REFRESH_INTERVALS = {

    "15min":
        TREND_REFRESH_SECONDS,

    "5min":
        CONFIRMATION_REFRESH_SECONDS,

    "1min":
        ENTRY_REFRESH_SECONDS,
}


# =========================================================
# GET CACHED DATA
# =========================================================

def _get_memory_data(
    symbol,
    interval
):

    return (
        _MARKET_DATA
        .get(symbol, {})
        .get(interval)
    )


# =========================================================
# SHOULD REFRESH
# =========================================================

def _should_refresh(
    symbol,
    interval
):

    now = time.time()

    last = (
        _LAST_REQUEST
        .get(symbol, {})
        .get(interval)
    )

    # اولین درخواست
    if last is None:
        return True

    refresh_time = REFRESH_INTERVALS.get(
        interval,
        300
    )

    return (
        now - last
    ) >= refresh_time


# =========================================================
# GET MARKET DATA SMART
# =========================================================

def _get_smart_market_data(
    symbol,
    interval,
    outputsize
):

    cached = _get_memory_data(
        symbol,
        interval
    )


    # -----------------------------------------------------
    # USE CACHE
    # -----------------------------------------------------

    if not _should_refresh(
        symbol,
        interval
    ):

        if cached is not None:

            print(
                f"[{symbol} {interval}] "
                "Using main memory cache."
            )

            return cached

        # اگر cache نداریم،
        # درخواست اجباری است.
        print(
            f"[{symbol} {interval}] "
            "No memory cache available."
        )


    # -----------------------------------------------------
    # REQUEST
    # -----------------------------------------------------

    print(
        f"[{symbol} {interval}] "
        "Refreshing market data..."
    )


    dataframe = get_market_data(
        symbol,
        interval,
        outputsize
    )


    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    if (
        dataframe is not None
        and not dataframe.empty
    ):

        _MARKET_DATA.setdefault(
            symbol,
            {}
        )[interval] = dataframe

        _LAST_REQUEST.setdefault(
            symbol,
            {}
        )[interval] = time.time()

        print(
            f"[{symbol} {interval}] "
            "Market data updated successfully."
        )

        return dataframe


    # -----------------------------------------------------
    # FAILED REQUEST
    #
    # اگر داده قبلی داریم، همان را استفاده می‌کنیم.
    # -----------------------------------------------------

    if cached is not None:

        print(
            f"[{symbol} {interval}] "
            "Request failed; using cached data."
        )

        return cached


    return None


# =========================================================
# MARKET CHECK
# =========================================================

def check_market(symbol):

    print()
    print("=" * 60)

    print(
        f"========== {symbol} =========="
    )

    print("=" * 60)


    try:

        df15 = None


        # =================================================
        # 15M TREND
        # =================================================

        if STRATEGY_MODE == "SCALPER":

            print(
                f"[{symbol}] "
                "Getting 15M trend data..."
            )


            df15 = _get_smart_market_data(
                symbol,
                "15min",
                CANDLE_LIMIT_15M
            )


            if (
                df15 is None
                or df15.empty
            ):

                print(
                    f"[{symbol}] "
                    "No 15M data received"
                )

                return


        # =================================================
        # 5M CONFIRMATION
        # =================================================

        print(
            f"[{symbol}] "
            "Getting 5M data..."
        )


        df5 = _get_smart_market_data(
            symbol,
            "5min",
            CANDLE_LIMIT_5M
        )


        if (
            df5 is None
            or df5.empty
        ):

            print(
                f"[{symbol}] "
                "No 5M data received"
            )

            return


        # =================================================
        # 1M ENTRY
        # =================================================

        print(
            f"[{symbol}] "
            "Getting 1M data..."
        )


        df1 = _get_smart_market_data(
            symbol,
            ENTRY_TIMEFRAME,
            CANDLE_LIMIT_1M
        )


        if (
            df1 is None
            or df1.empty
        ):

            print(
                f"[{symbol}] "
                "No 1M data received"
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
# TELEGRAM AUTO SIGNAL
# =================================================

if result.get("signal") in ("BUY", "SELL"):

    send_goldpro_signal(
        symbol,
        result
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
            score
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

        print()

        for reason in result.get(
            "reasons",
            []
        ):

            print(
                " •",
                reason
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


        # =================================================
        # NO SIGNAL
        # =================================================

        else:

            print()

            print(
                "⚪ GOLDPRO+ WAITING / NO SIGNAL"
            )


    except Exception as exc:

        print()

        print(
            f"❌ [{symbol}] "
            "Market check error:"
        )

        print(
            repr(exc)
        )


# =========================================================
# MAIN
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

    else:

        print(
            "📈 Strategy: "
            "5M Trend → 1M Entry"
        )


    print()

    print(
        "💡 API optimization:"
    )

    print(
        f"   15M → every "
        f"{TREND_REFRESH_SECONDS // 60} minutes"
    )

    print(
        f"   5M  → every "
        f"{CONFIRMATION_REFRESH_SECONDS // 60} minutes"
    )

    print(
        f"   1M  → every "
        f"{ENTRY_REFRESH_SECONDS // 60} minutes"
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