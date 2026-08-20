# =========================================================
# GoldPro+ Data Feed V2
#
# Twelve Data
#
# 30M Trend  <- built from 15M
# 15M        <- confirmation
# 5M         <- entry
#
# فقط CLOSED candles
# دارای CACHE برای کاهش مصرف API
# =========================================================

import requests
import pandas as pd

from datetime import datetime, timezone


from config import TWELVE_DATA_API_KEY


# =========================================================
# TWELVE DATA
# =========================================================

URL = "https://api.twelvedata.com/time_series"


# =========================================================
# CACHE
# =========================================================

# ساختار:
#
# {
#     ("XAU/USD", "5min"): {
#         "data": dataframe,
#         "time": timestamp
#     }
# }
#
# هدف:
# جلوگیری از درخواست‌های تکراری Twelve Data
# =========================================================

_DATA_CACHE = {}


# =========================================================
# CACHE TTL
# =========================================================

CACHE_TTL = {
    "1min": 50,
    "5min": 240,
    "15min": 840,
    "30min": 1680,
}


# =========================================================
# DEBUG
# =========================================================

DEBUG = True


# =========================================================
# INTERVAL TO MINUTES
# =========================================================

def _interval_to_minutes(interval):

    if not interval:
        return None

    interval = str(
        interval
    ).lower().strip()

    if interval.endswith("min"):

        try:

            return int(
                interval.replace(
                    "min",
                    ""
                )
            )

        except ValueError:

            return None

    return None


# =========================================================
# CACHE CHECK
# =========================================================

def _get_cached_data(
    symbol,
    interval
):

    key = (
        symbol,
        interval
    )

    cached = _DATA_CACHE.get(
        key
    )

    if cached is None:
        return None

    saved_at = cached.get(
        "saved_at"
    )

    dataframe = cached.get(
        "data"
    )

    if (
        saved_at is None
        or dataframe is None
    ):
        return None

    ttl = CACHE_TTL.get(
        interval,
        60
    )

    now = datetime.now(
        timezone.utc
    )

    age = (
        now - saved_at
    ).total_seconds()

    if age < ttl:

        if DEBUG:

            print(
                f"[{symbol} {interval}] "
                f"Using cached data "
                f"({age:.0f}s old)"
            )

        return dataframe.copy()

    return None


# =========================================================
# CACHE SAVE
# =========================================================

def _save_cached_data(
    symbol,
    interval,
    df
):

    key = (
        symbol,
        interval
    )

    _DATA_CACHE[key] = {

        "saved_at":
            datetime.now(
                timezone.utc
            ),

        "data":
            df.copy()
    }


# =========================================================
# FETCH MARKET DATA
# =========================================================

def get_market_data(
    symbol,
    interval,
    outputsize=200
):
    """
    دریافت داده بازار از Twelve Data.

    ویژگی‌ها:

    - فقط CLOSED candles
    - Cache
    - تبدیل OHLC به عدد
    - مرتب‌سازی زمانی
    - مدیریت خطای API
    """

    # -----------------------------------------------------
    # API KEY
    # -----------------------------------------------------

    if not TWELVE_DATA_API_KEY:

        print(
            "❌ TWELVE_DATA_API_KEY is missing"
        )

        return None


    # -----------------------------------------------------
    # CACHE
    # -----------------------------------------------------

    cached = _get_cached_data(
        symbol,
        interval
    )

    if cached is not None:

        return cached


    # -----------------------------------------------------
    # REQUEST
    # -----------------------------------------------------

    print(
        f"[{symbol} {interval}] "
        f"Requesting Twelve Data..."
    )


    params = {

        "symbol":
            symbol,

        "interval":
            interval,

        "outputsize":
            outputsize,

        "timezone":
            "UTC",

        "apikey":
            TWELVE_DATA_API_KEY,
    }


    try:

        response = requests.get(
            URL,
            params=params,
            timeout=30
        )


        # -------------------------------------------------
        # HTTP CHECK
        # -------------------------------------------------

        if response.status_code != 200:

            print(
                f"[{symbol} {interval}] "
                f"HTTP error: "
                f"{response.status_code}"
            )

            return None


        data = response.json()


        # -------------------------------------------------
        # TWELVE DATA ERROR
        # -------------------------------------------------

        if data.get(
            "status"
        ) == "error":

            print(
                f"[{symbol} {interval}] "
                f"Twelve Data error: "
                f"{data}"
            )

            return None


        # -------------------------------------------------
        # VALUES CHECK
        # -------------------------------------------------

        if "values" not in data:

            print(
                f"[{symbol} {interval}] "
                f"No values returned: "
                f"{data}"
            )

            return None


        # -------------------------------------------------
        # DATAFRAME
        # -------------------------------------------------

        df = pd.DataFrame(
            data["values"]
        )


        if df.empty:

            print(
                f"[{symbol} {interval}] "
                f"Empty dataframe"
            )

            return None


        # -------------------------------------------------
        # DATETIME
        # -------------------------------------------------

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            errors="coerce",
            utc=True
        )


        # -------------------------------------------------
        # OHLC
        # -------------------------------------------------

        for column in [
            "open",
            "high",
            "low",
            "close"
        ]:

            if column not in df.columns:

                print(
                    f"[{symbol} {interval}] "
                    f"Missing column: "
                    f"{column}"
                )

                return None


            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )


        # -------------------------------------------------
        # VOLUME
        # -------------------------------------------------

        if "volume" in df.columns:

            df["volume"] = pd.to_numeric(
                df["volume"],
                errors="coerce"
            )


        # -------------------------------------------------
        # CLEAN
        # -------------------------------------------------

        df = df.dropna(
            subset=[
                "datetime",
                "open",
                "high",
                "low",
                "close"
            ]
        )


        df = df.sort_values(
            "datetime"
        ).reset_index(
            drop=True
        )


        df.rename(
            columns={
                "datetime": "time"
            },
            inplace=True
        )


        # -------------------------------------------------
        # REMOVE FORMING CANDLE
        # -------------------------------------------------

        minutes = _interval_to_minutes(
            interval
        )


        if minutes is not None:

            now = pd.Timestamp(
                datetime.now(
                    timezone.utc
                )
            )


            cutoff = (
                now
                - pd.Timedelta(
                    minutes=minutes
                )
            )


            df = df[
                df["time"] <= cutoff
            ].reset_index(
                drop=True
            )


        # -------------------------------------------------
        # EMPTY CHECK
        # -------------------------------------------------

        if df.empty:

            print(
                f"[{symbol} {interval}] "
                f"No CLOSED candles available"
            )

            return None


        # -------------------------------------------------
        # LATEST CANDLE
        # -------------------------------------------------

        latest = df.iloc[-1]


        print(
            f"[{symbol} {interval}] "
            f"Latest CLOSED candle: "
            f"{latest['time']}"
        )


        print(
            f"[{symbol} {interval}] "
            f"Latest CLOSED close: "
            f"{latest['close']}"
        )


        # -------------------------------------------------
        # SAVE CACHE
        # -------------------------------------------------

        _save_cached_data(
            symbol,
            interval,
            df
        )


        return df.copy()


    # =====================================================
    # REQUEST ERROR
    # =====================================================

    except requests.RequestException as exc:

        print(
            f"[{symbol} {interval}] "
            f"Connection error: "
            f"{exc}"
        )

        return None


    # =====================================================
    # GENERAL ERROR
    # =====================================================

    except Exception as exc:

        print(
            f"[{symbol} {interval}] "
            f"Data processing error: "
            f"{exc}"
        )

        return None


# =========================================================
# GOLD 5M
# =========================================================

def get_gold_5m(
    outputsize=200
):

    return get_market_data(
        "XAU/USD",
        "5min",
        outputsize
    )


# =========================================================
# GOLD 15M
# =========================================================

def get_gold_15m(
    outputsize=200
):

    return get_market_data(
        "XAU/USD",
        "15min",
        outputsize
    )


# =========================================================
# GOLD GENERIC
# =========================================================

def get_gold_data(
    interval="5min",
    outputsize=200
):

    return get_market_data(
        "XAU/USD",
        interval,
        outputsize
    )


# =========================================================
# CACHE STATUS
# =========================================================

def print_cache_status():

    print(
        "========== DATA CACHE =========="
    )


    if not _DATA_CACHE:

        print(
            "Cache is empty."
        )

        return


    now = datetime.now(
        timezone.utc
    )


    for key, value in _DATA_CACHE.items():

        symbol, interval = key

        saved_at = value.get(
            "saved_at"
        )

        if saved_at is None:
            continue


        age = (
            now - saved_at
        ).total_seconds()


        df = value.get(
            "data"
        )


        rows = (
            len(df)
            if df is not None
            else 0
        )


        print(
            f"{symbol} {interval} | "
            f"Age: {age:.0f}s | "
            f"Rows: {rows}"
        )


    print(
        "================================"
    )