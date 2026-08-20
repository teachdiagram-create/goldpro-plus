import requests
import pandas as pd
from datetime import datetime, timezone

from config import (
    TWELVE_DATA_API_KEY,
    SYMBOL,
    TREND_TIMEFRAME,
    ENTRY_TIMEFRAME,
    CANDLE_LIMIT_5M,
    CANDLE_LIMIT_1M,
)


# =========================================================
# GOLDPRO+ DATA FEED
# =========================================================

URL = "https://api.twelvedata.com/time_series"


# =========================================================
# GET MARKET DATA
# =========================================================

def get_market_data(symbol, interval, outputsize):
    """
    دریافت OHLC از Twelve Data
    فقط کندل‌های بسته‌شده را برمی‌گرداند.
    """

    if not TWELVE_DATA_API_KEY:
        print(
            "[DATA] ERROR: "
            "TWELVE_DATA_API_KEY is missing"
        )
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

        response.raise_for_status()

        data = response.json()

        # -------------------------------------------------
        # API ERROR
        # -------------------------------------------------

        if data.get("status") == "error":

            print(
                f"[DATA] "
                f"{symbol} {interval} API error:",
                data
            )

            return None

        # -------------------------------------------------
        # DATA CHECK
        # -------------------------------------------------

        if "values" not in data:

            print(
                f"[DATA] "
                f"{symbol} {interval} "
                f"missing values:",
                data
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
                f"[DATA] "
                f"{symbol} {interval} "
                f"empty dataframe"
            )

            return None

        # -------------------------------------------------
        # TIME
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
        )

        df = df.reset_index(
            drop=True
        )

        # -------------------------------------------------
        # RENAME TIME
        # -------------------------------------------------

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

        if interval.endswith("min"):

            try:

                minutes = int(
                    interval.replace(
                        "min",
                        ""
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

            except ValueError:

                print(
                    f"[DATA] "
                    f"Invalid interval: "
                    f"{interval}"
                )

        # -------------------------------------------------
        # FINAL CHECK
        # -------------------------------------------------

        if df.empty:

            print(
                f"[DATA] "
                f"{symbol} {interval} "
                f"no CLOSED candles"
            )

            return None

        # -------------------------------------------------
        # LOG
        # -------------------------------------------------

        latest = df.iloc[-1]

        print(
            f"[DATA] "
            f"{symbol} {interval} "
            f"Latest CLOSED: "
            f"{latest['time']}"
        )

        print(
            f"[DATA] "
            f"{symbol} {interval} "
            f"Close: "
            f"{latest['close']}"
        )

        return df

    except requests.RequestException as exc:

        print(
            f"[DATA] "
            f"{symbol} {interval} "
            f"Connection error:",
            exc
        )

        return None

    except Exception as exc:

        print(
            f"[DATA] "
            f"{symbol} {interval} "
            f"Unexpected error:",
            exc
        )

        return None


# =========================================================
# 5 MINUTE TREND DATA
# =========================================================

def get_trend_data():

    return get_market_data(
        SYMBOL,
        TREND_TIMEFRAME,
        CANDLE_LIMIT_5M
    )


# =========================================================
# 1 MINUTE ENTRY DATA
# =========================================================

def get_entry_data():

    return get_market_data(
        SYMBOL,
        ENTRY_TIMEFRAME,
        CANDLE_LIMIT_1M
    )


# =========================================================
# GOLD DATA
# =========================================================

def get_gold_data():

    df5 = get_trend_data()

    df1 = get_entry_data()

    if df5 is None:

        print(
            "[DATA] 5M data unavailable"
        )

    if df1 is None:

        print(
            "[DATA] 1M data unavailable"
        )

    return df5, df1