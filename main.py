# اضافه کردن importها
from risk_manager import RiskManager
from news_filter import NewsFilter

# در ابتدای main:
risk_manager = RiskManager()
news_filter = NewsFilter(api_key=os.getenv("ALPHA_VANTAGE_API_KEY"))

# در حلقه while، قبل از check_market، اگر فیلتر خبری فعال است:
if news_filter.is_blocked(datetime.now(timezone.utc)):
    print("⏳ منتظر پایان اخبار مهم...")
    time.sleep(60)
    continue

# در تابع check_market، بعد از دریافت سیگنال:
if signal in ('BUY', 'SELL'):
    # محاسبه حجم معامله
    atr = result.get('atr')
    if atr is not None:
        sl, tp1, tp2 = risk_manager.set_stop_loss_take_profit(price, atr, signal)
        position_size = risk_manager.calculate_position_size(price, sl)
        if position_size <= 0:
            print("❌ حجم معامله صفر است، ورود انجام نمی‌شود")
            return
        # نمایش اطلاعات مدیریت ریسک
        print(f"📊 حجم معامله: {position_size}")
        print(f"🛑 استاپ لاس: {sl}")
        print(f"🎯 حد سود ۱: {tp1}")
        print(f"🎯 حد سود ۲: {tp2}")
        # به‌روزرسانی موجودی (شبیه‌سازی)
        # در محیط واقعی، اینجا سفارش ارسال می‌شود