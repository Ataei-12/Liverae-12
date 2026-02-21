import os
import requests
import json
import time
import datetime
import pytz
import jdatetime
import threading
from bs4 import BeautifulSoup
from flask import Flask
import telebot
from dotenv import load_dotenv

# بارگذاری تنظیمات
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = os.getenv("CHANNEL_USERNAME")

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
bot.send_message(CHANNEL, "✅ تست ارسال مستقیم موفق بود")
STATE_FILE = "state.json"

AF_MONTHS = [
    "حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله",
    "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت"
]

# نقشه نمادها به نام فارسی
CURRENCY_MAP = {
    "USD": "دالر امریکا",
    "EUR": "یورو",
    "GBP": "پوند انگلیس",
    "AED": "درهم امارات",
    "SAR": "ریال سعودی",
    "IRR": "ریال ایران",
    "PKR": "کلدار پاکستان",
    "INR": "روپیه هند",
    "CNY": "یوآن چین",
    "TRY": "لیره ترکیه",
    "AFN": "افغانی",
    "CAD": "دالر کانادا",
    "AUD": "دالر آسترالیا",
    "CHF": "فرانک سویس",
    "SEK": "کرون سویدن",
    "JPY": "ین جاپان",
    "RUB": "روبل روسیه",
    "DKK": "کرون دنمارک",
    "NOK": "کرون ناروی",
    "KWD": "دینار کویت",
    "BHD": "دینار بحرین",
    "QAR": "ریال قطر",
}

def translate_currency(name):
    if "US Dollar" in name: return "USD"
    elif "Euro" in name: return "EUR"
    elif "British Pound" in name: return "GBP"
    elif "UAE Dirham" in name: return "AED"
    elif "Saudi Riyal" in name: return "SAR"
    elif "Iranian Rial" in name: return "IRR"
    elif "Pakistani Rupee" in name: return "PKR"
    elif "Indian Rupee" in name: return "INR"
    elif "Chinese Yuan" in name: return "CNY"
    elif "Turkish Lira" in name: return "TRY"
    elif "Afghani" in name: return "AFN"
    elif "Canadian Dollar" in name: return "CAD"
    elif "Australian Dollar" in name: return "AUD"
    elif "Swiss Franc" in name: return "CHF"
    elif "Swedish Krona" in name: return "SEK"
    elif "Japanese Yen" in name: return "JPY"
    elif "Russian Ruble" in name: return "RUB"
    elif "Danish Krone" in name: return "DKK"
    elif "Norwegian Krone" in name: return "NOK"
    elif "Kuwaiti Dinar" in name: return "KWD"
    elif "Bahraini Dinar" in name: return "BHD"
    elif "Qatari Riyal" in name: return "QAR"
    else: return None

def get_rates():
    try:
        url = "https://sarafi.af/en/exchange-rates/sarai-shahzada"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if not table:
            print("❌ جدول پیدا نشد.")
            return None
        rates = {}
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 3:
                raw_name = cols[0].text.strip()
                symbol = translate_currency(raw_name)
                if not symbol: continue
                buy = cols[1].text.strip()
                sell = cols[2].text.strip()
                rates[symbol] = {"buy": buy, "sell": sell}
        return rates
    except Exception as e:
        print("❌ خطا در گرفتن نرخ:", e)
        return None

def load_previous_rates():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_current_rates(rates):
    with open(STATE_FILE, "w") as f:
        json.dump(rates, f, indent=2)

def compare_rates(old, new):
    changed = {}
    for k in new:
        if k not in old or new[k] != old[k]:
            changed[k] = new[k]
    return changed

def get_af_date():
    today = jdatetime.date.today()
    return f"{convert_to_farsi(today.day)} {AF_MONTHS[today.month - 1]} {convert_to_farsi(today.year)}"

def beautify_number(n):
    try:
        return convert_to_farsi(f"{float(n):,.2f}")
    except:
        return n

def convert_to_farsi(text):
    fa_digits = {
        "0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴",
        "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹",
        ",": "٬", ".": "٫"
    }
    return "".join(fa_digits.get(ch, ch) for ch in str(text))

def format_message(rates, title="📈 تغییر نرخ"):
    now = datetime.datetime.now(pytz.timezone("Asia/Kabul"))
    today = get_af_date()
    hour_str = convert_to_farsi(now.strftime("%H:%M"))

    msg = f"{title}\n"
    msg += f"📅 تاریخ: {today} | 🕘 ساعت: {hour_str}\n\n"
    msg += f"<pre>{'نماد':<6}{'نام ارز':<22}{'خرید':>10}{'فروش':>10}\n"
    msg += f"{'-'*48}\n"
    for symbol, val in sorted(rates.items()):
        name = CURRENCY_MAP.get(symbol, "نامشخص")
        buy = beautify_number(val['buy'])
        sell = beautify_number(val['sell'])
        msg += f"{symbol:<6}{name:<22}{buy:>10}{sell:>10}\n"
    msg += "</pre>\n\n📲 برای دریافت لحظه‌ای نرخ ارز:\n@kabulafg2025"
    return msg.strip()

def send_message_to_channel(message):
    try:
        bot.send_message(CHANNEL, message)
        print("✅ پیام ارسال شد.")
    except Exception as e:
        print("❌ خطا در ارسال پیام:", e)

def run_bot():
    last_open_sent = False
    last_close_sent = False
    last_hour_report = -1

    while True:
        now = datetime.datetime.now(pytz.timezone("Asia/Kabul"))
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute

        if weekday == 4:  # جمعه
            time.sleep(60)
            continue

        current_rates = get_rates()
        if not current_rates:
            time.sleep(60)
            continue

        previous_rates = load_previous_rates()
        changed = compare_rates(previous_rates, current_rates)

        if hour == 9 and not last_open_sent:
            msg = format_message(current_rates, "🟢 بازار باز شد")
            send_message_to_channel(msg)
            save_current_rates(current_rates)
            last_open_sent = True
            last_close_sent = False
            last_hour_report = -1

        elif hour == 17 and not last_close_sent:
            msg = format_message(current_rates, "🔴 بازار بسته شد")
            send_message_to_channel(msg)
            save_current_rates(current_rates)
            last_close_sent = True
            last_open_sent = False

        elif 9 <= hour < 17 and changed:
            msg = format_message(changed, "📈 تغییر نرخ")
            send_message_to_channel(msg)
            save_current_rates(current_rates)

        elif 9 <= hour < 16 and minute == 30 and hour != last_hour_report:
            msg = format_message(current_rates, "📊 نرخ کامل ساعتی")
            send_message_to_channel(msg)
            save_current_rates(current_rates)
            last_hour_report = hour

        time.sleep(60)

@app.route('/')
def index():
    return "✅ ربات زنده است."

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=port)
