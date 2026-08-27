import requests
from datetime import datetime, timedelta
from config import (
    NEWS_FILTER_ENABLED,
    NEWS_BLOCK_MINUTES_BEFORE,
    NEWS_BLOCK_MINUTES_AFTER,
)

# برای استفاده از API تقویم اقتصادی (مثلاً ForexFactory یا Alpha Vantage)
# در اینجا یک نمونه ساده با استفاده از API رایگان (مثلاً https://www.alphavantage.co/query?function=ECONOMIC_CALENDAR)
# پیاده‌سازی می‌کنیم، اما نیاز به کلید API دارد.


class NewsFilter:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.high_impact_events = []  # لیست رویدادهای با اهمیت بالا

    def fetch_events(self, date_from, date_to):
        """دریافت رویدادهای اقتصادی از یک API"""
        if not self.api_key:
            print("⚠️ کلید API برای اخبار تنظیم نشده است")
            return

        url = f"https://www.alphavantage.co/query?function=ECONOMIC_CALENDAR&from={date_from}&to={date_to}&apikey={self.api_key}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            # پردازش داده‌ها و استخراج رویدادهای با اهمیت بالا
            for event in data.get('data', []):
                if event.get('impact') in ['High', 'Medium']:
                    self.high_impact_events.append({
                        'time': datetime.fromisoformat(event['time']),
                        'event': event['event'],
                        'impact': event['impact'],
                    })
        except Exception as e:
            print(f"❌ خطا در دریافت اخبار: {e}")

    def is_blocked(self, current_time, buffer_before=NEWS_BLOCK_MINUTES_BEFORE, buffer_after=NEWS_BLOCK_MINUTES_AFTER):
        """بررسی اینکه آیا زمان فعلی در محدوده ممنوعه است"""
        if not NEWS_FILTER_ENABLED:
            return False

        for event in self.high_impact_events:
            event_time = event['time']
            if (event_time - timedelta(minutes=buffer_before) <= current_time <=
                event_time + timedelta(minutes=buffer_after)):
                print(f"⛔ معامله ممنوع: رویداد {event['event']} در {event_time}")
                return True
        return False

# استفاده در main.py قبل از تولید سیگنال