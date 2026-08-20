import requests
import pandas as pd
from datetime import datetime, timezone

from config import TWELVE_DATA_API_KEY


URL = "https://api.twelvedata.com/time_series"


def get_market_data(symbol, interval, outputsize=200):
    """
    دریافت کندل‌های بازار از Twelve Data
    فقط کندل‌های بسته‌شده برگردانده می‌شوند.
    """

    if not TWELVE_DATA_API_KEY:
        print("❌ TWELVE_DATA_API_KEY is missing")
        return None

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "timezone": "UTC",
        "apikey": TWELVE_DATA_API_KEY,
    }

    try:
        response = requests.get(
            URL,
            params=params,
            timeout=30
        )

        data = response.json()

        if data.get("status") == "error":
            print(
                f"[{symbol} {interval}] "
                f"Twelve Data error: {data}"
            )
            return None

        if "values" not in data:
            print(
                f"[{symbol} {interval}] "
                f"No values returned: {data}"
            )
            return None

        df = pd.DataFrame(data["values"])

        if df.empty:
            print(
                f"[{symbol} {interval}] "
                "Empty dataframe"
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
        # REMOVE CURRENT / FORMING CANDLE
        # -------------------------------------------------

        now = pd.Timestamp(
            datetime.now(timezone.utc)
        )

        minutes = _interval_to_minutes(
            interval
        )

        if minutes is not None:

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

        if df.empty:
            print(
                f"[{symbol} {interval}] "
                "No CLOSED candles available"
            )
            return None

        # -------------------------------------------------
        # LOG
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

        return df

    except requests.RequestException as exc:

        print(
            f"[{symbol} {interval}] "
            f"Connection error: {exc}"
        )

        return None

    except Exception as exc:

        print(
            f"[{symbol} {interval}] "
            f"Data processing error: {exc}"
        )

        return None


def _interval_to_minutes(interval):
    """
    تبدیل interval های Twelve Data
    مثل 1min / 5min / 15min به دقیقه.
    """

    if not interval:
        return None

    interval = str(interval).lower().strip()

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
# GOLD DATA
# =========================================================

def get_gold_1m(
    outputsize=200
):
    """
    داده 1 دقیقه‌ای طلا
    برای پیدا کردن Entry
    """

    return get_market_data(
        "XAU/USD",
        "1min",
        outputsize
    )


def get_gold_5m(
    outputsize=200
):
    """
    داده 5 دقیقه‌ای طلا
    برای تعیین Trend
    """

    return get_market_data(
        "XAU/USD",
        "5min",
        outputsize
    )


# =========================================================
# GENERIC GOLD
# =========================================================

def get_gold_data(
    interval="1min",
    outputsize=200
):
    """
    دریافت داده طلا با تایم‌فریم دلخواه.
    """

    return get_market_data(
        "XAU/USD",
        interval,
        outputsize
    )