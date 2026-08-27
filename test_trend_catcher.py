import os
from datetime import datetime, timedelta, timezone
from data_feed import get_market_data
from trend_catcher import trend_catcher_signal

def test_trend_catcher(days_back=7, interval="5min"):
    """
    تست استراتژی TrendCatcher روی بازه زمانی مشخص
    - days_back: تعداد روزهای اخیر برای تست
    - interval: تایم‌فریم (1min, 5min, 15min, 30min, 1h)
    """
    print("=" * 60)
    print("🧪 TEST TREND CATCHER STRATEGY")
    print("=" * 60)

    # دریافت داده
    df = get_market_data("XAU/USD", interval, outputsize=1000)
    if df is None or df.empty:
        print("❌ داده دریافت نشد")
        return

    # فیلتر بازه زمانی
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    df = df[df['time'] >= cutoff].reset_index(drop=True)

    if len(df) < 60:
        print(f"⚠️ تعداد کندل‌ها ({len(df)}) کمتر از حد نیاز است")
        return

    print(f"📊 تعداد کندل‌ها: {len(df)} از {df['time'].iloc[0]} تا {df['time'].iloc[-1]}")
    print("-" * 60)

    signals = []
    total_candles = len(df)

    # شبیه‌سازی کندل به کندل
    for i in range(60, total_candles):
        current_df = df.iloc[:i+1]
        result = trend_catcher_signal(current_df)

        if result['signal'] in ('BUY', 'SELL'):
            signals.append(result)
            print(f"🟢 {result['signal']} در {current_df['time'].iloc[-1]}")
            print(f"   قیمت: {result['price']:.2f}")
            print(f"   امتیاز: {result['score']}")
            print(f"   کیفیت: {result['quality']}")
            print(f"   دلایل: {', '.join(result['reasons'])}")
            print("-" * 40)

    # گزارش نهایی
    print("=" * 60)
    print("📊 گزارش نهایی")
    print("=" * 60)
    print(f"تعداد کل سیگنال‌ها: {len(signals)}")

    if signals:
        buy = sum(1 for s in signals if s['signal'] == 'BUY')
        sell = len(signals) - buy
        avg_score = sum(s['score'] for s in signals) / len(signals)
        print(f"   BUY: {buy}")
        print(f"   SELL: {sell}")
        print(f"   میانگین امتیاز: {avg_score:.1f}")
        print(f"   آخرین سیگنال: {signals[-1]['signal']} در {signals[-1]['price']:.2f}")
    else:
        print("   ⚠️ هیچ سیگنالی پیدا نشد.")
        print("   💡 پیشنهادات:")
        print("      - تایم‌فریم را به 1min تغییر دهید (interval='1min')")
        print("      - تعداد روزها را افزایش دهید (days_back=14)")
        print("      - از استراتژی ساده‌تر استفاده کنید (فایل trend_catcher.py را به‌روز کنید)")

    print("=" * 60)

if __name__ == "__main__":
    # تست روی ۷ روز اخیر با تایم‌فریم ۵ دقیقه
    test_trend_catcher(days_back=7, interval="5min")