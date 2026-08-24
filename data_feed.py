# =========================================================
# GoldPro+ Data Feed V3
#
# Twelve Data
#
# 15M -> Trend
# 5M  -> Confirmation
# 1M  -> Entry
#
# هدف:
# کاهش شدید مصرف API
# جلوگیری از 429
# استفاده از آخرین دیتای موفق
# فقط CLOSED candles
# =========================================================

import time
import requests
import pandas as pd

from datetime import datetime, timezone, timedelta

from config import TWELVE_DATA_API_KEY


# =========================================================
# TWELVE DATA
# =========================================================

URL = "https://api.twelvedata.com/time_series"


# =========================================================
# DEBUG
# =========================================================

DEBUG = True


# =========================================================
# FETCH INTERVAL
#
# حداقل فاصله بین درخواست‌های واقعی API
#
# 15M -> هر 30 دقیقه
# 5M  -> هر 15 دقیقه
# 1M  -> هر 3 دقیقه
# =========================================================

FETCH_INTERVAL = {

    "15min": 1800,

    "5min": 900,

    "1min": 180,
}


# =========================================================
# CACHE
#
# داده موفق آخر را نگه می‌داریم.
#
# =========================================================

_DATA_CACHE = {}


# =========================================================
# LAST REQUEST
#
# زمان آخرین درخواست واقعی
# =========================================================

_LAST_REQUEST = {}


# =========================================================
# API COOLDOWN
#
# اگر 429 دریافت شود،
# درخواست جدید تا زمان مناسب متوقف می‌شود.
# =========================================================

_API_COOLDOWN_UNTIL = None


# =========================================================
# API STATUS
# =========================================================

_API_BLOCKED = False


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
# UTC NOW
# =========================================================

def _utc_now():

    return datetime.now(
        timezone.utc
    )


# =========================================================
# NEXT UTC RESET
#
# Twelve Data روزانه در UTC ریست می‌شود.
# =========================================================

def _next_utc_reset():

    now = _utc_now()

    tomorrow = (
        now.date()
        + timedelta(days=1)
    )

    return datetime.combine(
        tomorrow,
        datetime.min.time(),
        tzinfo=timezone.utc
    )


# =========================================================
# BLOCK API UNTIL RESET
# =========================================================

def _block_api_until_reset():

    global _API_COOLDOWN_UNTIL
    global _API_BLOCKED

    _API_BLOCKED = True

    _API_COOLDOWN_UNTIL = (
        _next_utc_reset()
    )

    if DEBUG:

        remaining = (
            _API_COOLDOWN_UNTIL
            - _utc_now()
        ).total_seconds()

        minutes = int(
            max(
                remaining,
                0
            ) / 60
        )

        print(
            "🚫 Twelve Data daily limit reached."
        )

        print(
            f"⏳ API requests blocked "
            f"until next UTC reset "
            f"(~{minutes} minutes)"
        )


# =========================================================
# CHECK API BLOCK
# =========================================================

def _is_api_blocked():

    global _API_BLOCKED
    global _API_COOLDOWN_UNTIL

    if not _API_BLOCKED:

        return False

    if (
        _API_COOLDOWN_UNTIL is None
    ):

        return False

    now = _utc_now()

    if now >= _API_COOLDOWN_UNTIL:

        _API_BLOCKED = False

        _API_COOLDOWN_UNTIL = None

        print(
            "🟢 Twelve Data daily limit "
            "window reset."
        )

        return False

    remaining = (
        _API_COOLDOWN_UNTIL
        - now
    ).total_seconds()

    minutes = int(
        max(
            remaining,
            0
        ) / 60
    )

    if DEBUG:

        print(
            f"⏳ Twelve Data blocked "
            f"until UTC reset "
            f"(~{minutes} min remaining)"
        )

    return True


# =========================================================
# GET CACHE
# =========================================================

def _get_cache(
    symbol,
    interval
):

    key = (
        symbol,
        interval
    )

    item = _DATA_CACHE.get(
        key
    )

    if item is None:

        return None

    dataframe = item.get(
        "data"
    )

    saved_at = item.get(
        "saved_at"
    )

    if (
        dataframe is None
        or saved_at is None
    ):

        return None

    return dataframe.copy()


# =========================================================
# CACHE AGE
# =========================================================

def _cache_age(
    symbol,
    interval
):

    key = (
        symbol,
        interval
    )

    item = _DATA_CACHE.get(
        key
    )

    if item is None:

        return None

    saved_at = item.get(
        "saved_at"
    )

    if saved_at is None:

        return None

    return (
        _utc_now()
        - saved_at
    ).total_seconds()


# =========================================================
# SAVE CACHE
# =========================================================

def _save_cache(
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
            _utc_now(),

        "data":
            df.copy()
    }


# =========================================================
# SHOULD REQUEST
# =========================================================

def _should_request(
    symbol,
    interval
):

    key = (
        symbol,
        interval
    )

    now = _utc_now()

    last_request = (
        _LAST_REQUEST.get(
            key
        )
    )

    if last_request is None:

        return True

    elapsed = (
        now - last_request
    ).total_seconds()

    required = FETCH_INTERVAL.get(
        interval,
        300
    )

    if elapsed >= required:

        return True

    remaining = (
        required - elapsed
    )

    if DEBUG:

        print(
            f"[{symbol} {interval}] "
            f"API request skipped. "
            f"Next request in "
            f"{int(remaining)}s"
        )

    return False


# =========================================================
# MARK REQUEST
# =========================================================

def _mark_request(
    symbol,
    interval
):

    key = (
        symbol,
        interval
    )

    _LAST_REQUEST[key] = (
        _utc_now()
    )


# =========================================================
# PREPARE DATAFRAME
# =========================================================

def _prepare_dataframe(
    symbol,
    interval,
    data
):

    if not data:

        print(
            f"[{symbol} {interval}] "
            "Empty API response"
        )

        return None

    if "values" not in data:

        print(
            f"[{symbol} {interval}] "
            "No values returned."
        )

        return None

    df = pd.DataFrame(
        data["values"]
    )

    if df.empty:

        print(
            f"[{symbol} {interval}] "
            "Empty dataframe"
        )

        return None

    # -----------------------------------------------------
    # DATETIME
    # -----------------------------------------------------

    if "datetime" not in df.columns:

        print(
            f"[{symbol} {interval}] "
            "Missing datetime column"
        )

        return None

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce",
        utc=True
    )

    # -----------------------------------------------------
    # OHLC
    # -----------------------------------------------------

    for column in [
        "open",
        "high",
        "low",
        "close"
    ]:

        if column not in df.columns:

            print(
                f"[{symbol} {interval}] "
                f"Missing column: {column}"
            )

            return None

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # -----------------------------------------------------
    # VOLUME
    # -----------------------------------------------------

    if "volume" in df.columns:

        df["volume"] = pd.to_numeric(
            df["volume"],
            errors="coerce"
        )

    # -----------------------------------------------------
    # CLEAN
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # RENAME
    # -----------------------------------------------------

    df.rename(
        columns={
            "datetime": "time"
        },
        inplace=True
    )

    # -----------------------------------------------------
    # REMOVE FORMING CANDLE
    # -----------------------------------------------------

    minutes = _interval_to_minutes(
        interval
    )

    if minutes is not None:

        now = pd.Timestamp(
            _utc_now()
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

    # -----------------------------------------------------
    # EMPTY AFTER CLEAN
    # -----------------------------------------------------

    if df.empty:

        print(
            f"[{symbol} {interval}] "
            "No CLOSED candles available"
        )

        return None

    return df


# =========================================================
# MARKET DATA
# =========================================================

def get_market_data(
    symbol,
    interval,
    outputsize=200
):

    global _API_BLOCKED

    # =====================================================
    # API KEY
    # =====================================================

    if not TWELVE_DATA_API_KEY:

        print(
            "❌ TWELVE_DATA_API_KEY is missing"
        )

        return None

    # =====================================================
    # DAILY API BLOCK
    # =====================================================

    if _is_api_blocked():

        cached = _get_cache(
            symbol,
            interval
        )

        if cached is not None:

            age = _cache_age(
                symbol,
                interval
            )

            print(
                f"[{symbol} {interval}] "
                f"Using last successful cache "
                f"({age:.0f}s old)"
            )

            return cached

        print(
            f"[{symbol} {interval}] "
            "No cache available."
        )

        return None

    # =====================================================
    # CACHE
    #
    # اگر هنوز زمان درخواست نرسیده،
    # از آخرین داده موفق استفاده کن.
    # =====================================================

    if not _should_request(
        symbol,
        interval
    ):

        cached = _get_cache(
            symbol,
            interval
        )

        if cached is not None:

            age = _cache_age(
                symbol,
                interval
            )

            print(
                f"[{symbol} {interval}] "
                f"Using cached data "
                f"({age:.0f}s old)"
            )

            return cached

        # اگر cache نداریم،
        # اجازه می‌دهیم درخواست انجام شود.

    # =====================================================
    # REQUEST
    # =====================================================

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

    # -----------------------------------------------------
    # ثبت زمان درخواست
    # -----------------------------------------------------

    _mark_request(
        symbol,
        interval
    )

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
        # 429
        # =================================================

        if response.status_code == 429:

            print(
                f"[{symbol} {interval}] "
                "HTTP error: 429"
            )

            try:

                data = response.json()

            except Exception:

                data = {
                    "message":
                    response.text
                }

            print(
                f"[{symbol} {interval}] "
                "Twelve Data response:"
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

            # -------------------------------------------------
            # DAILY LIMIT
            # -------------------------------------------------

            daily_limit = (
                "credits for the day"
                in message
                or
                "daily limit"
                in message
                or
                "current limit"
                in message
            )

            if daily_limit:

                print(
                    "🚫 Twelve Data "
                    "daily limit detected."
                )

                _block_api_until_reset()

            else:

                print(
                    "🚫 Twelve Data "
                    "429 detected."
                )

            # -------------------------------------------------
            # USE CACHE
            # -------------------------------------------------

            cached = _get_cache(
                symbol,
                interval
            )

            if cached is not None:

                age = _cache_age(
                    symbol,
                    interval
                )

                print(
                    f"[{symbol} {interval}] "
                    f"Using last successful "
                    f"cache after 429 "
                    f"({age:.0f}s old)"
                )

                return cached

            return None

        # =================================================
        # OTHER HTTP ERROR
        # =================================================

        if response.status_code != 200:

            print(
                f"[{symbol} {interval}] "
                f"HTTP error: "
                f"{response.status_code}"
            )

            cached = _get_cache(
                symbol,
                interval
            )

            if cached is not None:

                return cached

            return None

        # =================================================
        # JSON
        # =================================================

        try:

            data = response.json()

        except Exception as exc:

            print(
                f"[{symbol} {interval}] "
                f"JSON error: {exc}"
            )

            cached = _get_cache(
                symbol,
                interval
            )

            if cached is not None:

                return cached

            return None

        # =================================================
        # TWELVE DATA ERROR
        # =================================================

        if data.get(
            "status"
        ) == "error":

            message = str(
                data.get(
                    "message",
                    ""
                )
            )

            print(
                f"[{symbol} {interval}] "
                f"Twelve Data error: "
                f"{message}"
            )

            # -------------------------------------------------
            # DAILY LIMIT
            # -------------------------------------------------

            message_lower = (
                message.lower()
            )

            if (
                "credits for the day"
                in message_lower
                or
                "daily limit"
                in message_lower
                or
                "current limit"
                in message_lower
            ):

                _block_api_until_reset()

            cached = _get_cache(
                symbol,
                interval
            )

            if cached is not None:

                return cached

            return None

        # =================================================
        # PREPARE
        # =================================================

        df = _prepare_dataframe(
            symbol,
            interval,
            data
        )

        if df is None:

            cached = _get_cache(
                symbol,
                interval
            )

            if cached is not None:

                return cached

            return None

        # =================================================
        # LATEST CLOSED CANDLE
        # =================================================

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

        # =================================================
        # SAVE SUCCESSFUL DATA
        # =================================================

        _save_cache(
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

        cached = _get_cache(
            symbol,
            interval
        )

        if cached is not None:

            print(
                f"[{symbol} {interval}] "
                "Using cached data "
                "after connection error."
            )

            return cached

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

        cached = _get_cache(
            symbol,
            interval
        )

        if cached is not None:

            return cached

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
# GOLD GENERIC
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

    print()
    print(
        "========== GOLDPRO+ DATA CACHE =========="
    )

    if not _DATA_CACHE:

        print(
            "Cache is empty."
        )

        print(
            "=========================================="
        )

        return

    now = _utc_now()

    for key, value in _DATA_CACHE.items():

        symbol, interval = key

        saved_at = value.get(
            "saved_at"
        )

        df = value.get(
            "data"
        )

        if saved_at is None:

            continue

        age = (
            now - saved_at
        ).total_seconds()

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
        "=========================================="
    )


# =========================================================
# API STATUS
# =========================================================

def print_api_status():

    print()
    print(
        "========== TWELVE DATA STATUS =========="
    )

    if _API_BLOCKED:

        print(
            "🚫 API STATUS: BLOCKED"
        )

        if _API_COOLDOWN_UNTIL:

            print(
                "Reset UTC:",
                _API_COOLDOWN_UNTIL
            )

    else:

        print(
            "🟢 API STATUS: AVAILABLE"
        )

    print(
        "========================================"
    )