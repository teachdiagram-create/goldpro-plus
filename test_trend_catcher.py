import os
from datetime import datetime, timedelta, timezone
from data_feed import get_market_data
from trend_catcher import trend_catcher_signal

def test_trend_catcher(days_back=5, interval="15min"):
    print("=" * 60)
    print("🧪 TEST TREND CATCHER STRATEGY")
    print("=" * 60)

    df = get_market_data("XAU/USD", interval, outputsize=1000)
    if df is None or df.empty:
        print("❌ داده دریافت نشد")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    df = df[df['time'] >= cutoff].reset_index(drop=True)
    print(f"📊 تعداد کندل‌ها: {len(df)} از {df['time'].iloc[0]} تا {df['time'].iloc[-1]}")

    signals = []
    for i in range(60, len(df)):
        current_df = df.iloc[:i+1]
        result = trend_catcher_signal(current_df)
        if result['signal'] in ('BUY', 'SELL'):
            signals.append(result)
            print(f"🟢 {result['signal']} در {current_df['time'].iloc[-1]} | قیمت: {result['price']:.2f} | امتیاز: {result['score']} | {result['quality']}")
            print(f"   دلایل: {', '.join(result['reasons'])}")
            print("-" * 40)

    print("=" * 60)
    print(f"📊 تعداد کل سیگنال‌ها: {len(signals)}")
    if signals:
        buy = sum(1 for s in signals if s['signal'] == 'BUY')
        sell = len(signals) - buy
        avg_score = sum(s['score'] for s in signals) / len(signals)
        print(f"   BUY: {buy}")
        print(f"   SELL: {sell}")
        print(f"   میانگین امتیاز: {avg_score:.1f}")
    else:
        print("   ⚠️ هیچ سیگنالی پیدا نشد.")
    print("=" * 60)

if __name__ == "__main__":
    test_trend_catcher(days_back=7, interval="15min")