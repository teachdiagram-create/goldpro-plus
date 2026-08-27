import pandas as pd
from datetime import datetime
from config import BACKTEST_START, BACKTEST_END
from data_feed import get_market_data
from scalper_strategy import generate_scalper_signal
from risk_manager import RiskManager


class Backtester:
    def __init__(self, symbol="XAU/USD"):
        self.symbol = symbol
        self.results = []
        self.risk = RiskManager()

    def run(self):
        # دریافت داده‌های تاریخی (مثلاً 1M, 5M, 15M)
        # اینجا باید داده‌ها را بر اساس بازه تاریخی دریافت کنیم
        # برای سادگی، از تابع موجود استفاده می‌کنیم و محدوده زمانی را اعمال می‌کنیم
        df1 = get_market_data(self.symbol, "1min", outputsize=5000)
        df5 = get_market_data(self.symbol, "5min", outputsize=5000)
        df15 = get_market_data(self.symbol, "15min", outputsize=5000)

        if df1 is None or df5 is None or df15 is None:
            print("❌ داده کافی برای بک‌تست وجود ندارد")
            return

        # فیلتر بر اساس تاریخ
        df1 = df1[(df1['time'] >= BACKTEST_START) & (df1['time'] <= BACKTEST_END)]
        df5 = df5[(df5['time'] >= BACKTEST_START) & (df5['time'] <= BACKTEST_END)]
        df15 = df15[(df15['time'] >= BACKTEST_START) & (df15['time'] <= BACKTEST_END)]

        # شبیه‌سازی کندل به کندل
        # برای هر کندل ۱ دقیقه، سیگنال تولید و اگر سیگنال داشت، معامله شبیه‌سازی می‌شود
        # این یک بک‌تست ساده است؛ برای دقت بیشتر باید از داده‌های تیک یا دقیقه‌ای استفاده کرد

        for i in range(len(df1)):
            # داده‌های جاری (تا کندل i)
            current_df1 = df1.iloc[:i+1]
            # داده‌های ۵ دقیقه‌ای تا زمان حال (با توجه به تایم‌فریم)
            current_df5 = df5[df5['time'] <= current_df1.iloc[-1]['time']]
            current_df15 = df15[df15['time'] <= current_df1.iloc[-1]['time']]

            if len(current_df5) < 20 or len(current_df15) < 20:
                continue

            signal = generate_scalper_signal(current_df15, current_df5, current_df1)
            if signal['signal'] in ('BUY', 'SELL'):
                entry_price = signal['price']
                atr = signal.get('atr')
                if atr is None:
                    continue

                direction = signal['signal']
                sl, tp1, tp2 = self.risk.set_stop_loss_take_profit(entry_price, atr, direction)

                # ثبت معامله
                self.results.append({
                    'time': current_df1.iloc[-1]['time'],
                    'direction': direction,
                    'entry': entry_price,
                    'stop_loss': sl,
                    'take_profit_1': tp1,
                    'take_profit_2': tp2,
                    'score': signal['score'],
                })

        self.analyze()

    def analyze(self):
        """تحلیل نتایج"""
        if not self.results:
            print("هیچ معامله‌ای انجام نشد.")
            return

        df = pd.DataFrame(self.results)
        print(f"تعداد کل معاملات: {len(df)}")
        print(f"میانگین امتیاز: {df['score'].mean():.2f}")
        print(f"بازه زمانی: {df['time'].min()} تا {df['time'].max()}")
        # می‌توان ضرایب برد/باخت و ... را بر اساس قیمت‌های بعدی محاسبه کرد
        # اینجا به دلیل نبود داده‌های آتی، فقط آمار اولیه ارائه می‌شود


if __name__ == "__main__":
    bt = Backtester()
    bt.run()