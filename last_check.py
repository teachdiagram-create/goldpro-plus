# last_check.py
# =========================================================
# مدیریت آخرین بررسی و سیگنال‌ها (ذخیره در حافظه)
# =========================================================

import json
import os
from datetime import datetime

DATA_FILE = "last_check_data.json"
_last_signals = {}


def save_last_check(symbol, signal_data):
    """ذخیره آخرین سیگنال برای یک نماد"""
    global _last_signals
    _last_signals[symbol] = {
        "signal": signal_data.get("signal"),
        "timestamp": datetime.now().isoformat(),
        "data": signal_data
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(_last_signals, f)
    except Exception:
        pass


def get_last_check_time(symbol):
    """دریافت زمان آخرین بررسی برای یک نماد"""
    global _last_signals
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                _last_signals.update(data)
    except Exception:
        pass
    if symbol in _last_signals:
        return _last_signals[symbol].get("timestamp")
    return None


def get_last_signal(symbol):
    """دریافت آخرین سیگنال ذخیره‌شده برای یک نماد"""
    global _last_signals
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                _last_signals.update(data)
    except Exception:
        pass
    if symbol in _last_signals:
        return _last_signals[symbol].get("data")
    return None


def clear_last_check(symbol=None):
    """پاک کردن داده‌های ذخیره‌شده"""
    global _last_signals
    if symbol:
        _last_signals.pop(symbol, None)
    else:
        _last_signals.clear()
    try:
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
    except Exception:
        pass