import pandas as pd
import ta

from config import (
    EMA_FAST,
    EMA_SLOW,
    RSI_PERIOD,
    ATR_PERIOD,
)


# =========================================================
# GOLDPRO+ INDICATORS
# =========================================================


def add_indicators(df):

    if df is None or df.empty:
        return None


    data = df.copy()


    # -----------------------------------------------------
    # EMA TREND
    # فقط جهت روند
    # -----------------------------------------------------

    data["EMA20"] = (
        ta.trend.EMAIndicator(
            close=data["close"],
            window=EMA_FAST
        )
        .ema_indicator()
    )


    data["EMA50"] = (
        ta.trend.EMAIndicator(
            close=data["close"],
            window=EMA_SLOW
        )
        .ema_indicator()
    )


    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    data["RSI"] = (
        ta.momentum.RSIIndicator(
            close=data["close"],
            window=RSI_PERIOD
        )
        .rsi()
    )


    # -----------------------------------------------------
    # ATR
    # برای SL / TP
    # -----------------------------------------------------

    data["ATR"] = (
        ta.volatility.AverageTrueRange(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            window=ATR_PERIOD
        )
        .average_true_range()
    )


    # -----------------------------------------------------
    # MACD
    # گزارش
    # -----------------------------------------------------

    macd = ta.trend.MACD(
        close=data["close"]
    )

    data["MACD"] = (
        macd.macd()
    )

    data["MACD_SIGNAL"] = (
        macd.macd_signal()
    )


    # -----------------------------------------------------
    # ADX
    # گزارش قدرت روند
    # -----------------------------------------------------

    adx = ta.trend.ADXIndicator(
        high=data["high"],
        low=data["low"],
        close=data["close"]
    )

    data["ADX"] = (
        adx.adx()
    )


    data = data.dropna()

    return data.reset_index(
        drop=True
    )