import math
from config import (
    RISK_PER_TRADE,
    ACCOUNT_BALANCE,
    MAX_POSITIONS,
    SL_ATR_MULTIPLIER,
    TP1_ATR_MULTIPLIER,
    TP2_ATR_MULTIPLIER,
    TRAILING_STOP_ACTIVATE,
    TRAILING_STOP_DISTANCE,
)


class RiskManager:
    def __init__(self, balance=ACCOUNT_BALANCE):
        self.balance = balance
        self.positions = []

    def calculate_position_size(self, entry_price, stop_loss_price):
        """محاسبه حجم معامله بر اساس ریسک ثابت"""
        risk_amount = self.balance * RISK_PER_TRADE
        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit <= 0:
            return 0
        size = risk_amount / risk_per_unit
        # محدود کردن به حداکثر پوزیشن‌های همزمان
        if len(self.positions) >= MAX_POSITIONS:
            return 0
        return round(size, 2)

    def set_stop_loss_take_profit(self, entry_price, atr, direction):
        """محاسبه SL و TP بر اساس ATR"""
        sl_distance = atr * SL_ATR_MULTIPLIER
        tp1_distance = atr * TP1_ATR_MULTIPLIER
        tp2_distance = atr * TP2_ATR_MULTIPLIER

        if direction == "BUY":
            stop_loss = entry_price - sl_distance
            take_profit_1 = entry_price + tp1_distance
            take_profit_2 = entry_price + tp2_distance
        else:  # SELL
            stop_loss = entry_price + sl_distance
            take_profit_1 = entry_price - tp1_distance
            take_profit_2 = entry_price - tp2_distance

        return stop_loss, take_profit_1, take_profit_2

    def update_trailing_stop(self, position, current_price):
        """به‌روزرسانی استاپ متحرک"""
        if position['direction'] == "BUY":
            profit = current_price - position['entry']
            if profit >= position['entry'] * TRAILING_STOP_ACTIVATE:
                new_sl = current_price - position['entry'] * TRAILING_STOP_DISTANCE
                if new_sl > position['stop_loss']:
                    position['stop_loss'] = new_sl
                    return True
        else:  # SELL
            profit = position['entry'] - current_price
            if profit >= position['entry'] * TRAILING_STOP_ACTIVATE:
                new_sl = current_price + position['entry'] * TRAILING_STOP_DISTANCE
                if new_sl < position['stop_loss']:
                    position['stop_loss'] = new_sl
                    return True
        return False