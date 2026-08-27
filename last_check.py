last_candle = None


def is_new_candle(candle_time):

    global last_candle

    if candle_time == last_candle:
        return False

    last_candle = candle_time
    return True