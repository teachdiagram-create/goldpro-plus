"""
GoldPro+ Parallel Strategy Runner
اجرای همزمان استراتژی‌های PLUS و CLEAN
هر استراتژی داده‌های خود را جداگانه دریافت می‌کند
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =========================================================
# ایمپورت استراتژی‌ها
# =========================================================

try:
    from goldpro_plus_strategy import generate_goldpro_plus_signal
    print("✅ GOLDPRO+ (PLUS) loaded")
except ImportError as e:
    print(f"❌ GOLDPRO+ (PLUS) import error: {e}")
    generate_goldpro_plus_signal = None

try:
    from goldpro_clean import analyze_signal, fetch_data
    print("✅ GOLDPRO+ (CLEAN) loaded")
except ImportError as e:
    print(f"❌ GOLDPRO+ (CLEAN) import error: {e}")
    analyze_signal = None
    fetch_data = None

from telegram_bot import send_signal

# =========================================================
# تنظیمات
# =========================================================

CHECK_INTERVAL = 60  # ثانیه بین هر بررسی

# =========================================================
# حلقه اصلی
# =========================================================

def main_loop():
    print("=" * 60)
    print("🚀 GoldPro+ Parallel Strategy Runner")
    print(f"📊 استراتژی‌ها: PLUS={generate_goldpro_plus_signal is not None}, CLEAN={analyze_signal is not None}")
    print(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
    print("=" * 60)
    
    if generate_goldpro_plus_signal is None and analyze_signal is None:
        print("❌ هیچ استراتژی در دسترس نیست. برنامه متوقف شد.")
        return
    
    while True:
        try:
            print("\n" + "-" * 40)
            print(f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # ===== استراتژی PLUS =====
            if generate_goldpro_plus_signal is not None:
                try:
                    print("\n🧠 [PLUS] Getting data...")
                    df5_plus = fetch_data("5min")
                    df1_plus = fetch_data("1min", days=1)
                    
                    if df5_plus is not None and df1_plus is not None:
                        print("🧠 [PLUS] Analyzing...")
                        signal_plus = generate_goldpro_plus_signal(df5_plus, df1_plus)
                        if signal_plus and signal_plus.get('signal') != "NO SIGNAL":
                            print(f"✅ [PLUS] Signal: {signal_plus['signal']} at {signal_plus.get('price', 0):.2f}")
                            send_signal(signal_plus, strategy_name="GOLDPRO+ (PLUS)")
                        else:
                            score = signal_plus.get('score', 0) if signal_plus else 0
                            print(f"⏳ [PLUS] No signal (Score: {score})")
                    else:
                        print("⚠️ [PLUS] No data available")
                except Exception as e:
                    print(f"❌ [PLUS] Error: {e}")
            
            # ===== استراتژی CLEAN =====
            if analyze_signal is not None:
                try:
                    print("\n🧠 [CLEAN] Getting data...")
                    df5_clean = fetch_data("5min")
                    df1_clean = fetch_data("1min", days=1)
                    
                    if df5_clean is not None and df1_clean is not None:
                        print("🧠 [CLEAN] Analyzing...")
                        signal_clean = analyze_signal(df5_clean, df1_clean)
                        if signal_clean and signal_clean.get('signal') != "NO SIGNAL":
                            print(f"✅ [CLEAN] Signal: {signal_clean['signal']} at {signal_clean.get('price', 0):.2f}")
                            send_signal(signal_clean, strategy_name="GOLDPRO+ (CLEAN)")
                        else:
                            score = signal_clean.get('score', 0) if signal_clean else 0
                            print(f"⏳ [CLEAN] No signal (Score: {score})")
                    else:
                        print("⚠️ [CLEAN] No data available")
                except Exception as e:
                    print(f"❌ [CLEAN] Error: {e}")
            
            print(f"\n⏳ Next check in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n🛑 برنامه متوقف شد (Ctrl+C)")
            break
        except Exception as e:
            print(f"❌ خطای غیرمنتظره: {e}")
            print("⏳ تلاش مجدد در ۱۰ ثانیه...")
            time.sleep(10)

# =========================================================
# اجرا
# =========================================================

if __name__ == "__main__":
    main_loop()