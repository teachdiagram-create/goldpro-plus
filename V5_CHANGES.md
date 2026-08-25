# GoldPro+ Scalper V5

هدف V5 اصلاح مشکل ورود در انتهای موج است.

## تغییرات
- Wave/Impulse analysis روی 1M اضافه شد.
- Wave stage: IMPULSE / CONTINUATION / PULLBACK / RECLAIM / EXTENDED.
- Wave position مشخص می‌کند قیمت چند درصد از موج فعلی را طی کرده است.
- در MATURE و LATE، Pullback ساختاری + Reclaim اجباری است.
- ورود در بخش پایانی موج بدون ساختار جدید Block می‌شود.
- Score دیگر نمی‌تواند Structural Entry Filter را دور بزند.
- 5M trend shift سریع‌تر در خروجی گزارش می‌شود.
- 1M EMA weakening فقط هشدار است و به‌تنهایی باعث رد سیگنال نمی‌شود.
- سیگنال‌های هم‌جهت در یک بازه 15 دقیقه‌ای تکرار نمی‌شوند.
- Telegram شامل Wave Stage، Wave Position و محدوده موج می‌شود.

## منطق اصلی
Trend Strength و Entry Quality از هم جدا شده‌اند.

Score بالا به معنی ورود خوب نیست. ابتدا ساختار موج و محل قیمت داخل موج بررسی می‌شود، سپس Score برای قدرت تأییدها استفاده می‌شود.
