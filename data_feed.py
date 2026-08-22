# =========================================================
# GoldPro+ Data Feed V3
#
# Twelve Data
#
# 15M -> Trend
# 5M  -> Confirmation
# 1M  -> Entry
#
# Features:
# - CLOSED candles only
# - Cache
# - 429 detection
# - Full API error response
# - Automatic cooldown after 429
# =========================================================

import requests
import pandas as pd

from datetime import datetime, timezone, timedelta

from config import TWELVE_DATA_API_KEY


# =========================================================
# TWELVE DATA
# =========================================================

URL = "https://api.twelvedata.com/time_series"


# =========================================================
# CACHE
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
# 429 COOLDOWN
# =========================================================
#
# اگر Twelve Data خطای 429 بدهد،
# تا پایان این مدت درخواست جدید نمی‌فرستیم.
#
# =========================================================

RATE_LIMIT_COOLDOWN_SECONDS = 120

_RATE_LIMIT_UNTIL = None


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
# RATE LIMIT CHECK
# =========================================================

def _rate_limit_active():

    global _RATE_LIMIT_UNTIL

    if _RATE_LIMIT_UNTIL is None:
        return False

    now = datetime.now(
        timezone.utc
    )

    if now >= _RATE_LIMIT_UNTIL:

        _RATE_LIMIT_UNTIL = None

        return False

    remaining = (
        _RATE_LIMIT_UNTIL - now
    ).total_seconds()

    print(
        "⏳ Twelve Data cooldown active: "
        f"{remaining:.0f}s remaining"
    )

    return True


# =========================================================
# START RATE LIMIT COOLDOWN
# =========================================================

def _start_rate_limit_cooldown():

    global _RATE_LIMIT_UNTIL

    _RATE_LIMIT_UNTIL = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            seconds=RATE_LIMIT_COOLDOWN_SECONDS
        )
    )

    print(
        "🚫 Twelve Data 429 detected."
    )

    print(
        "⏳ New API requests paused for "
        f"{RATE_LIMIT_COOLDOWN_SECONDS} seconds."
    )


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
    # RATE LIMIT
    # -----------------------------------------------------

    if _rate_limit_active():

        print(
            f"[{symbol} {interval}] "
            "Skipping Twelve Data request."
        )

        return None


    # -----------------------------------------------------
    # REQUEST
    # -----------------------------------------------------

    print(
        f"[{symbol} {interval}] "
        "Requesting Twelve Data..."
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


        # =================================================
        # HTTP STATUS
        # =================================================

        print(
            f"[{symbol} {interval}] "
            f"HTTP status: "
            f"{response.status_code}"
        )


        # =================================================
        # HTTP 429
        # =================================================

        if response.status_code == 429:

            print(
                f"[{symbol} {interval}] "
                "HTTP error: 429"
            )

            print(
                f"[{symbol} {interval}] "
                "Twelve Data full response:"
            )

            print(
                response.text
            )

            _start_rate_limit_cooldown()

            return None


        # =================================================
        # OTHER HTTP ERRORS
        # =================================================

        if response.status_code != 200:

            print(
                f"[{symbol} {interval}] "
                f"HTTP error: "
                f"{response.status_code}"
            )

            print(
                f"[{symbol} {interval}] "
                "Twelve Data response:"
            )

            print(
                response.text
            )

            return None


        # =================================================
        # JSON
        # =================================================

        try:

            data = response.json()

        except ValueError:

            print(
                f"[{symbol} {interval}] "
                "Invalid JSON response:"
            )

            print(
                response.text
            )

            return None


        # =================================================
        # TWELVE DATA ERROR
        # =================================================

        if data.get(
            "status"
        ) == "error":

            print(
                f"[{symbol} {interval}] "
                "Twelve Data error:"
            )

            print(
                data
            )

            return None


        # =================================================
        # VALUES CHECK
        # =================================================

        if "values" not in data:

            print(
                f"[{symbol} {interval}] "
                "No values returned:"
            )

            print(
                data
            )

            return None


        # =================================================
        # DATAFRAME
        # =================================================

        df = pd.DataFrame(
            data["values"]
        )


        if df.empty:

            print(
                f"[{symbol} {interval}] "
                "Empty dataframe"
            )

            return None


        # =================================================
        # DATETIME
        # =================================================

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            errors="coerce",
            utc=True
        )


        # =================================================
        # OHLC
        # =================================================

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


        # =================================================
        # VOLUME
        # =================================================

        if "volume" in df.columns:

            df["volume"] = pd.to_numeric(
                df["volume"],
                errors="coerce"
            )


        # =================================================
        # CLEAN
        # =================================================

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


        # =================================================
        # REMOVE FORMING CANDLE
        # =================================================

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


        # =================================================
        # EMPTY CHECK
        # =================================================

        if df.empty:

            print(
                f"[{symbol} {interval}] "
                "No CLOSED candles available"
            )

            return None


        # =================================================
        # LATEST CANDLE
        # =================================================

        latest = df.iloc[-1]


        print(
            f"[{symbol} {interval}] "
            "Latest CLOSED candle: "
            f"{latest['time']}"
        )


        print(
            f"[{symbol} {interval}] "
            "Latest CLOSED close: "
            f"{latest['close']}"
        )


        # =================================================
        # SAVE CACHE
        # =================================================

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
            "Connection error:"
        )

        print(
            repr(exc)
        )

        return None


    # =====================================================
    # GENERAL ERROR
    # =====================================================

    except Exception as exc:

        print(
            f"[{symbol} {interval}] "
            "Data processing error:"
        )

        print(
            repr(exc)
        )

        return None


# =========================================================
# GOLD 1M
# =========================================================

def get_gold_1m(
    outputsize=200
):

    return get_market_data(
        "XAU/USD",
        "1min",
        outputsize
    )


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
# GOLD 30M
# =========================================================

def get_gold_30m(
    outputsize=200
):

    return get_market_data(
        "XAU/USD",
        "30min",
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
            f"{symbol} {interval