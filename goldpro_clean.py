# ========== 10. تصمیم‌گیری نهایی (بدون نیاز به BOS) ==========
threshold_early = CONFIG["EARLY_SCORE_THRESHOLD"]   # 55
threshold_normal = CONFIG["NORMAL_SCORE_THRESHOLD"] # 70

# 🔥 فروش - اولویت با Early (بدون نیاز به BOS)
if CONFIG["EARLY_ENTRY"] and score_sell >= threshold_early:
    return create_result("SELL", score_sell, reasons_sell, price, rsi1, adx, trend, "EARLY")

if score_sell >= threshold_normal:
    return create_result("SELL", score_sell, reasons_sell, price, rsi1, adx, trend, "NORMAL")

# 🔥 خرید - اولویت با Early
if CONFIG["EARLY_ENTRY"] and score_buy >= threshold_early:
    return create_result("BUY", score_buy, reasons_buy, price, rsi1, adx, trend, "EARLY")

if score_buy >= threshold_normal:
    return create_result("BUY", score_buy, reasons_buy, price, rsi1, adx, trend, "NORMAL")

# بدون سیگنال
return {
    "signal": "NO SIGNAL",
    "score": max(score_buy, score_sell),
    "quality": "WEAK",
    "price": price,
    "trend": trend,
    "rsi": rsi1,
    "adx": adx,
    "fib_pullback": fib_pullback,
    "bos_signal": bos_signal,
    "divergence": divergence,
    "reasons": ["شرایط برقرار نیست"]
}