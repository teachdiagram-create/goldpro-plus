import time
from datetime import datetime, timezone

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
# MEMORY CACHE
#
# این Cache برای جلوگیری از درخواست‌های تکراری
# در main.py است.
#
# data_feed.py نیز Cache خودش را دارد.
# =========================================================

_MARKET_DATA = {}


# =========================================================
# LAST REQUEST TIME
# =========================================================

_LAST_REQUEST = {
    "15min": {},
    "5min": {},
    "1min": {},
}


# =========================================================
# REQUEST INTERVAL
#
# 15M -> فقط یک بار در 15 دقیقه
# 5M  -> فقط یک بار در 5 دقیقه
# 1M  -> هر 3 دقیقه
# =========================================================

REQUEST_INTERVAL = {
    "15min": 900,
    "5min": 300,
    "1min": 180,
}


# =========================================================
# CURRENT UTC
# =========================================================

def _utc_now():

    return datetime.now(
        timezone.utc
    )


# =========================================================
# SHOULD REQUEST?
# =========================================================

def _should_request(
    symbol,
    interval
):

    now = time.time()

    last_request = (
        _LAST_REQUEST
        .get(interval, {})
        .get(symbol)
    )

    if last_request is None:

        return True

    wait_time = REQUEST_INTERVAL.get(
        interval,
        180
    )

    elapsed = (
        now - last_request
    )

    if elapsed >= wait_time:

        return True

    return False


# =========================================================
# GET DATA
#
# این تابع تصمیم می‌گیرد:
#
# آیا باید Twelve Data صدا زده شود؟
# یا داده قبلی استفاده شود؟
# =========================================================

def _get_data(
    symbol,
    interval,
    outputsize
):

    # -----------------------------------------------------
    # EXISTING DATA
    # -----------------------------------------------------

    existing = (
        _MARKET_DATA
        .get(symbol, {})
        .get(interval)
    )


    # -----------------------------------------------------
    # NO NEED TO REQUEST
    # -----------------------------------------------------

    if not _should_request(
        symbol,
        interval
    ):

        if existing is not None:

            print(
                f"[{symbol} {interval}] "
                "Using main memory cache."
            )

            return existing

        # اگر داده نداریم، اجازه درخواست بده
        # حتی اگر تایمر قبلی وجود داشته باشد.
        return get_market_data(
            symbol,
            interval,
            outputsize
        )


    # -----------------------------------------------------
    # REQUEST
    # -----------------------------------------------------

    print(
        f"[{symbol} {interval}] "
        "Refreshing market data..."
    )


    _LAST_REQUEST.setdefault(
        interval,
        {}
    )[symbol] = time.time()


    dataframe = get_market_data(
        symbol,
        interval,
        outputsize
    )


    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    if dataframe is not None and not dataframe.empty:

        _MARKET_DATA.setdefault(
            symbol,
            {}
        )[interval] = dataframe

        return dataframe


    # -----------------------------------------------------
    # FAILED REQUEST
    #
    # اگر قبلاً داده معتبر داریم،
    # همان را نگه می‌داریم.
    # -----------------------------------------------------

    if existing is not None:

        print(
            f"[{symbol} {interval}] "
            "Request failed; "
            "using previous data."
        )

        return existing


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
        df5 = None
        df1 = None


        # =================================================
        # SCALPER
        # =================================================

        if STRATEGY_MODE == "SCALPER":

            # ---------------------------------------------
            # 15M TREND
            # ---------------------------------------------

            print(
                f"[{symbol}] "
                "Getting 15M trend data..."
            )


            df15 = _get_data(
                symbol,
                "15min",
                CANDLE_LIMIT_15M
            )


            if df15 is None or df15.empty:

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


        df5 = _get_data(
            symbol,
            "5min",
            CANDLE_LIMIT_5M
        )


        if df5 is None or df5.empty:

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


        df1 = _get_data(
            symbol,
            ENTRY_TIMEFRAME,
            CANDLE_LIMIT_1M
        )


        if df1 is None or df1.empty:

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
        # BASIC VALUES
        # =================================================

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

        confidence = result.get(
            "confidence",
            score
        )

        quality = result.get(
            "quality",
            "UNKNOWN"
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
        # SIGNAL DISPLAY
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
# CACHE STATUS
# =========================================================

def print_main_cache_status():

    print()
    print(
        "========== MAIN CACHE =========="
    )


    if not _MARKET_DATA:

        print(
            "Main cache is empty."
        )

        print(
            "================================"
        )

        return


    for symbol, intervals in _MARKET_DATA.items():

        for interval, dataframe in intervals.items():

            rows = (
                len(dataframe)
                if dataframe is not None
                else 0
            )

            print(
                f"{symbol} {interval} "
                f"| Rows: {rows}"
            )


    print(
        "================================"
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
        "   15M → every 15 minutes"
    )

    print(
        "   5M  → every 5 minutes"
    )

    print(
        "   1M  → every 3 minutes"
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