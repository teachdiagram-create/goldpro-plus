from telegram_bot import send_signal

test_signal = {
    "signal": "BUY",
    "price": 4600.00,
    "score": 80,
    "quality": "STRONG",
    "trend": "BUY",
    "trend_phase": "MATURE",
    "reversal_state": "CONFIRMED",
    "reasons": ["Test reason 1", "Test reason 2"],
    "time": "2026-08-28 16:30:00"
}

send_signal(test_signal, strategy_name="TEST")