import time
from datetime import datetime, timedelta
from data_feed import get_market_data
from scalper_strategy import generate_scalper_signal

def quick_test(days_back=3):
    """تست سریع روی چند روز گذشته"""
    print("=" * 60)
    print("🚀 QUICK TEST - GoldPro+ Scalper V7")
    print("=" * 60)
    
    # دریافت داده‌های بیشتر (۳ روز = ۴۳۲۰ کندل ۱ دقیقه‌ای)
    print("📥 Downloading data...")
    df1 = get_market_data("XAU/USD", "1min", outputsize=5000)
    df5 = get_market_data("XAU/USD", "5min", outputsize=2000)
    df15 = get_market_data("XAU/USD", "15min", outputsize=500)
    
    if df1 is None or df5 is None or df15 is None:
        print("❌ Failed to get data")
        return
    
    print(f"✅ Data loaded: {len(df1)} candles (1M)")
    
    # محدود کردن به چند روز اخیر
    cutoff = datetime.now() - timedelta(days=days_back)
    df1 = df1[df1['time'] >= cutoff].reset_index(drop=True)
    
    if len(df1) < 50:
        print(f"⚠️ Only {len(df1)} candles in the last {days_back} days. Try increasing days_back.")
        return
    
    print(f"📊 Testing on {len(df1)} candles from {df1['time'].iloc[0]} to {df1['time'].iloc[-1]}")
    print("=" * 60)
    
    signals = []
    total_candles = len(df1)
    
    # شبیه‌سازی کندل به کندل
    for i in range(50, total_candles):
        current_df1 = df1.iloc[:i+1].copy()
        current_time = current_df1['time'].iloc[-1]
        
        # یافتن داده‌های ۵ و ۱۵ دقیقه‌ای متناظر
        current_df5 = df5[df5['time'] <= current_time].tail(50)
        current_df15 = df15[df15['time'] <= current_time].tail(30)
        
        if len(current_df5) < 20 or len(current_df15) < 15:
            continue
        
        result = generate_scalper_signal(current_df15, current_df5, current_df1)
        signal = result.get("signal", "NO SIGNAL")
        score = result.get("score", 0)
        
        if signal in ("BUY", "SELL"):
            signals.append({
                'time': current_time,
                'signal': signal,
                'price': result.get('price'),
                'score': score,
                'quality': result.get('quality'),
                'reasons': result.get('reasons', [])[:3],  # فقط ۳ دلیل اول
            })
            
            # چاپ سیگنال به‌محض پیدا شدن
            print(f"🟢 {signal} at {current_time}")
            print(f"   Price: {result.get('price')}")
            print(f"   Score: {score}/100")
            print(f"   Quality: {result.get('quality')}")
            print(f"   Reasons: {result.get('reasons', [])[:3]}")
            print("-" * 40)
    
    # گزارش نهایی
    print("=" * 60)
    print(f"📊 TEST COMPLETE")
    print(f"   Total signals found: {len(signals)}")
    
    if signals:
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']
        print(f"   BUY: {len(buy_signals)}")
        print(f"   SELL: {len(sell_signals)}")
        print(f"   Avg Score: {sum(s['score'] for s in signals) / len(signals):.1f}")
        print(f"   Last signal: {signals[-1]['time']} - {signals[-1]['signal']} @ {signals[-1]['price']}")
    else:
        print("   ⚠️ No signals found in the tested period.")
        print("   💡 Try increasing days_back or check market conditions.")
    
    print("=" * 60)

if __name__ == "__main__":
    # تست روی ۵ روز اخیر (می‌توانید عدد را تغییر دهید)
    quick_test(days_back=5)

