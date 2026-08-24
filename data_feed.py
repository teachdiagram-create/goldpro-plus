# =========================================================
# GoldPro+ Data Feed - Optimized V3
#
# XAU/USD
#
# 15M -> Trend
# 5M  -> Confirmation
# 1M  -> Entry
#
# هدف:
# - کاهش شدید مصرف Twelve Data
# - استفاده از Cache
# - فقط CLOSED candles
# - جلوگیری از درخواست‌های تکراری
# - مدیریت هوشمند HTTP 429
# - توقف درخواست‌ها تا ریست روزانه UTC
# =========================================================

import os
import time
import requests
import pandas as pd

from datetime import datetime, timezone, timedelta

from config import TWELVE_DATA_API_KEY


# =========================================================
# SETTINGS
# =========================================================

URL = "https://api.twelvedata.com/time_series"

DEBUG = True


# =========================================================
# CACHE TTL
#
# هر چند ثانیه یک بار اجازه درخواست جدید داریم
#
# 1M  = هر 3 دقیقه
# 5M  = هر 5 دقیقه
# 15M = هر 15 دقیقه
#
# با چک شدن Main هر 60 ثانیه،
# API فقط طبق این زمان‌ها درخواست می‌شود.
# =========================================================

CACHE_TTL = {
    "1min": 180,
    "5min": 300,
    "15min": 900,
    "30min": 1800,
}


# =========================================================
# GLOBAL CACHE
# =========================================================

_DATA_CACHE = {}


# =========================================================
# API BLOCK STATE
# =========================================================

_API_BLOCKED_UNTIL = None


# =========================================================
# SESSION
#
# استفاده از Session باعث می‌شود ارتباط HTTP بهینه‌تر شود.
# =========================================================

_SESSION = requests.Session()


# =========================================================
# INTERVAL -> MINUTES
# =========================================================

def _interval_to_minutes(interval):

    if not interval:
        return None

    value = str(interval).lower().strip()

    if value.endswith("min"):

        try:
            return int(
                value.replace("min", "")
            )

        except ValueError:
            return None

    return None


# =========================================================
# CURRENT UTC
# =========================================================

def _utc_now():

    return datetime.now(
        timezone.utc
    )


# =========================================================
# NEXT UTC RESET
#
# Twelve Data daily limit is treated as UTC based.
# =========================================================

def _next_utc_reset():

    now = _utc_now()

    tomorrow = (
        now + timedelta(days=1)
    ).date()

    return datetime.combine(
        tomorrow,
        datetime.min.time(),
        tzinfo=timezone.utc
    )


# =========================================================
# BLOCK API
# =========================================================

def _block_api_until_reset():

    global _API_BLOCKED_UNTIL

    _API_BLOCKED_UNTIL = (
        _next_utc_reset()
    )

    remaining = (
        _API_BLOCKED_UNTIL - _utc_now()
    ).total_seconds()

    minutes = max(
        0,
        int(remaining / 60)
    )

    print(
        "🚫 Twelve Data daily limit detected."
    )

    print(
        "🚫 Twelve Data requests are blocked "
        "until UTC reset."
    )

    print(
        f"⏳ Approx. {minutes} minutes remaining."
    )


# =========================================================
# CHECK API BLOCK
# =========================================================

def _api_is_blocked():

    global _API_BLOCKED_UNTIL

    if _API_BLOCKED_UNTIL is None:
        return False

    now = _utc_now()

    if now >= _API_BLOCKED_UNTIL:

        print(
            "✅ Twelve Data UTC reset reached."
        )

        print(
            "🔓 API requests enabled again."
        )

        _API_BLOCKED_UNTIL = None

        return False

    remaining = (
        _API_BLOCKED_UNTIL - now
    ).total_seconds()

    minutes = max(
        0,
        int(remaining / 60)
    )

    print(
        f"⏳ Twelve Data blocked until "
        f"UTC reset (~{minutes} min remaining)"
    )

    return True


# =========================================================
# CACHE GET
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
        or dataframe.empty
    ):
        return None

    ttl = CACHE_TTL.get(
        interval,
        180
    )

    age = (
        _utc_now() - saved_at
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
# CACHE GET - EVEN IF EXPIRED
#
# در صورت 429، آخرین داده موفق را برمی‌گرداند.
# =========================================================

def _get_last_cached_data(
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

    dataframe = cached.get(
        "data"
    )

    if (
        dataframe is None
        or dataframe.empty
    ):
        return None

    saved_at = cached.get(
        "saved_at"
    )

    if saved_at is not None:

        age = (
            _utc_now() - saved_at
        ).total_seconds()

        print(
            f"[{symbol} {interval}] "
            f"Using last cached data "
            f"({age:.0f}s old)"
        )

    return dataframe.copy()


# =========================================================
# CACHE SAVE
# =========================================================

def _save_cached_data(
    symbol,
    interval,
    dataframe
):

    key = (
        symbol,
        interval
    )

    _DATA_CACHE[key] = {

        "saved_at":
            _utc_now(),

        "data":
            dataframe.copy()
    }


# =========================================================
# CLEAN CLOSED CANDLES
# =========================================================

def _remove_forming_candle(
    dataframe,
    interval
):

    minutes = _interval_to_minutes(
        interval
    )

    if minutes is None:
        return dataframe

    if dataframe.empty:
        return dataframe

    now = pd.Timestamp(
        _utc_now()
    )

    cutoff = (
        now
        - pd.Timedelta(
            minutes=minutes
        )
    )

    dataframe = dataframe[
        dataframe["time"] <= cutoff
    ]

    return dataframe.reset_index(
        drop=True
    )


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

    - Cache
    - فقط CLOSED candles
    - مدیریت 429
    - استفاده از آخرین Cache در صورت خطا
    - کاهش مصرف API
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
    # NORMALIZE
    # -----------------------------------------------------

    symbol = str(
        symbol
    ).strip()

    interval = str(
        interval
    ).lower().strip()


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
    # DAILY API BLOCK
    # -----------------------------------------------------

    if _api_is_blocked():

        last_cached = _get_last_cached_data(
            symbol,
            interval
        )

        if last_cached is not None:

            return last_cached

        print(
            f"[{symbol} {interval}] "
            "No cache available."
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

        response = _SESSION.get(
            URL,
            params=params,
            timeout=30
        )


        # -------------------------------------------------
        # HTTP STATUS
        # -------------------------------------------------

        if DEBUG:

            print(
                f"[{symbol} {interval}] "
                f"HTTP status: "
                f"{response.status_code}"
            )


        # -------------------------------------------------
        # 429
        # -------------------------------------------------

        if response.status_code == 429:

            try:
                error_data = response.json()
            except Exception:
                error_data = {
                    "message":
                    response.text
                }


            print(
                f"[{symbol} {interval}] "
                "HTTP error: 429"
            )

            print(
                f"[{symbol} {interval}] "
                "Twelve Data response:"
            )

            print(
                error_data
            )


            message = str(
                error_data.get(
                    "message",
                    ""
                )
            ).lower()


            # ---------------------------------------------
            # DAILY LIMIT
            # ---------------------------------------------

            daily_limit = (
                "day" in message
                or "daily" in message
                or "credits" in message
                or "limit" in message
            )


            if daily_limit:

                _block_api_until_reset()

            else:

                print(
                    "⚠️ Twelve Data 429 detected."
                )

                print(
                    "⏳ Temporary rate limit."
                )


            # ---------------------------------------------
            # USE CACHE
            # ---------------------------------------------

            last_cached = _get_last_cached_data(
                symbol,
                interval
            )

            if last_cached is not None:

                print(
                    f"[{symbol} {interval}] "
                    "Returning cached data "
                    "after 429."
                )

                return last_cached


            return None


        # -------------------------------------------------
        # OTHER HTTP ERROR
        # -------------------------------------------------

        if response.status_code != 200:

            print(
                f"[{symbol} {interval}] "
                f"HTTP error: "
                f"{response.status_code}"
            )

            # آخرین Cache
            last_cached = _get_last_cached_data(
                symbol,
                interval
            )

            if last_cached is not None:

                return last_cached

            return None


        # -------------------------------------------------
        # JSON
        # -------------------------------------------------

        try:

            data = response.json()

        except Exception as exc:

            print(
                f"[{symbol} {interval}] "
                "JSON parsing error:",
                exc
            )

            return None


        # -------------------------------------------------
        # TWELVE DATA ERROR
        # -------------------------------------------------

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


            message = str(
                data.get(
                    "message",
                    ""
                )
            ).lower()


            if (
                "day" in message
                or "daily" in message
                or "credits" in message
                or "limit" in message
            ):

                _block_api_until_reset()


            last_cached = _get_last_cached_data(
                symbol,
                interval
            )

            if last_cached is not None:

                return last_cached

            return None


        # -------------------------------------------------
        # VALUES
        # -------------------------------------------------

        if "values" not in data:

            print(
                f"[{symbol} {interval}] "
                "No values returned."
            )

            if DEBUG:

                print(data)

            return None


        # -------------------------------------------------
        # DATAFRAME
        # -------------------------------------------------

        dataframe = pd.DataFrame(
            data["values"]
        )


        if dataframe.empty:

            print(
                f"[{symbol} {interval}] "
                "Empty dataframe."
            )

            return None


        # -------------------------------------------------
        # DATETIME
        # -------------------------------------------------

        if "datetime" not in dataframe.columns:

            print(
                f"[{symbol} {interval}] "
                "Missing datetime column."
            )

            return None


        dataframe["datetime"] = pd.to_datetime(
            dataframe["datetime"],
            errors="coerce",
            utc=True
        )


        # -------------------------------------------------
        # OHLC
        # -------------------------------------------------

        required_columns = [
            "open",
            "high",
            "low",
            "close"
        ]


        for column in required_columns:

            if column not in dataframe.columns:

                print(
                    f"[{symbol} {interval}] "
                    f"Missing column: {column}"
                )

                return None


            dataframe[column] = pd.to_numeric(
                dataframe[column],
                errors="coerce"
            )


        # -------------------------------------------------
        # VOLUME
        # -------------------------------------------------

        if "volume" in dataframe.columns:

            dataframe["volume"] = pd.to_numeric(
                dataframe["volume"],
                errors="coerce"
            )


        # -------------------------------------------------
        # CLEAN
        # -----------------------------------------------------

        dataframe = dataframe.dropna(
            subset=[
                "datetime",
                "open",
                "high",
                "low",
                "close"
            ]
        )


        # -------------------------------------------------
        # SORT
        # -------------------------------------------------

        dataframe = dataframe.sort_values(
            "datetime"
        ).reset_index(
            drop=True
        )


        # -------------------------------------------------
        # RENAME
        # -------------------------------------------------

        dataframe.rename(
            columns={
                "datetime": "time"
            },
            inplace=True
        )


        # -------------------------------------------------
        # ONLY CLOSED CANDLES
        # -------------------------------------------------

        dataframe = _remove_forming_candle(
            dataframe,
            interval
        )


        if dataframe.empty:

            print(
                f"[{symbol} {interval}] "
                "No CLOSED candles available."
            )

            return None


        # -------------------------------------------------
        # LATEST CLOSED CANDLE
        # -------------------------------------------------

        latest = dataframe.iloc[-1]


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
        # -----------------------------------------------------

        _save_cached_data(
            symbol,
            interval,
            dataframe
        )


        return dataframe.copy()


    # =====================================================
    # CONNECTION ERROR
    # =====================================================

    except requests.RequestException as exc:

        print(
            f"[{symbol} {interval}] "
            "Connection error:"
        )

        print(
            repr(exc)
        )


        last_cached = _get_last_cached_data(
            symbol,
            interval
        )

        if last_cached is not None:

            print(
                f"[{symbol} {interval}] "
                "Using cached data after "
                "connection error."
            )

            return last_cached


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
# GENERIC GOLD DATA
# =========================================================


def get_gold_data(
    interval="1min",
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
        "========== GOLDPRO+ DATA CACHE =========="
    )


    if not _DATA_CACHE:

        print(
            "Cache is empty."
        )

        print(
            "========================================="
        )

        return


    now = _utc_now()


    for key, value in _DATA_CACHE.items():

        symbol, interval = key

        dataframe = value.get(
            "data"
        )

        saved_at = value.get(
            "saved_at"
        )


        if saved_at is None:
            continue


        age = (
            now - saved_at
        ).total_seconds()


        rows = (
            len(dataframe)
            if dataframe is not None
            else 0
        )


        ttl = CACHE_TTL.get(
            interval,
            180
        )


        print(
            f"{symbol} {interval} | "
            f"Age: {age:.0f}s | "
            f"TTL: {ttl}s | "
            f"Rows: {rows}"
        )


    print(
        "========================================="
    )