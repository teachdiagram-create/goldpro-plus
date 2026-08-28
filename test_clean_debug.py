"""
فایل تست مستقل برای دیباگ goldpro_clean
"""

import sys
import os

# اطمینان از اینکه مسیر پروژه در PATH است
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goldpro_clean import fetch_data, analyze_signal, CONFIG
import json

print("=" * 60)
print("🧪 تست مستقل GOLDPRO+ CLEAN با دیباگ")
print("=" * 60)

# دریافت داده
print("📥 دریافت داده 5M...")
df5 = fetch_data("5min")
print("📥 دریافت داده 1M...")
df1 = fetch_data("1min", days=1)

if df5 is None or df1 is None:
    print("❌ دریافت داده ناموفق")
    sys.exit(1)

print(f"📊 5M: {len(df5)} کندل")
print(f"📊 1M: {len(df1)} کندل")

# اجرای تحلیل
print("\n🧠 اجرای تحلیل...")
result = analyze_signal(df5, df1)

# نمایش کامل نتیجه
print("\n" + "=" * 60)
print("📊 نتیجه کامل:")
print(json.dumps(result, indent=2, default=str))
print("=" * 60)