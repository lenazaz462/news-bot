import time
import re
import html
import random
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import tweepy

# ================= بيانات تلغرام =================
NEWS_BOT_TOKEN = "9299530952:AAHH4CC0CqT-kfFkyGR97W-W3untPRP8xLI"
NEWS_TARGET_CHANNEL = "@almaydan_news24"
SIGNATURE = "\n\n➖➖➖➖➖➖➖\n📲 <b>الميدان نيوز | تابع التغطية أولاً بأول:</b>\n🔗 @almaydan_news24"

SOURCE_CHANNELS = [
    "AjaNews", "almayadeen", "mayadeenchannel",
    "iraqex1", "alnourradio", "bintjbeilnews", "N_FFG"
]

# ================= بيانات تويتر (X) =================
TWITTER_API_KEY = "ifOECbkOlqZrzvKZqUioWpEou"
TWITTER_API_SECRET = "lwPoGZyNNqiq4nzEgd4K5LdEeGfCG3TjPIjQwRhNoDWLKHhjAn"
TWITTER_ACCESS_TOKEN = "2117392638458384384-mNaXBDphr8UmEr0ru9og09Lo8SGJTU"
TWITTER_ACCESS_TOKEN_SECRET = "2mq4F3AIApmtAsIJf3GsN4oNqLTBVF1veJWBuKZi7Dq5T"

# ================= بيانات موقع الربح =================
SHORTENER_API = "6741aa28a3eabcc90c89f1ab9f55a5ffa832408b"

# ================= قوالب تغريدات شاملة للأقسام الأربعة =================
TWEETS_POOL = [
    # --- 1. قسم الرياضة والمباريات ---
    {
        "category": "رياضة",
        "text": "⚽️ بث مباشر لمباريات اليوم بدون تقطيع وبأعلى جودة مناسبة لجميع الأجهزة!\n\n👇 سيرفر المشاهدة السريع هنا:\n{link}\n\n#مباراة_اليوم #الهلال #النصر #الاتحاد #دوري_ابطال_اوروبا #ريال_مدريد #برشلونة #كورة_لايف"
    },
    {
        "category": "رياضة",
        "text": "🔥 ملخص وأهداف مباريات اليوم كاملة بجودة عالية Full HD وتغطية حصرية فورية!\n\n👇 شاهد فيديو الأهداف واللقطات الآن:\n{link}\n\n#الدوري_الانجليزي #الدوري_السعودي #ليفربول #مانشستر_سيتي #كورة"
    },

    # --- 2. قسم المسلسلات والأفلام ---
    {
        "category": "مسلسلات",
        "text": "🎬 فيلم السهرة الحصري والأكثر طلباً اليوم متوفر الآن للمشاهدة والتحميل بأعلى جودة مترجم!\n\n👇 رابط المشاهدة المباشر:\n{link}\n\n#سينما #افلام #مسلسلات #نتفلكس #ايجي_بست #سهرة_الخميس #سهرة_الليلة"
    },
    {
        "category": "مسلسلات",
        "text": "🍿 الحلقات الجديدة من أقوى المسلسلات العربية والتركية متوفرة الآن بدون إعلانات مزعجة!\n\n👇 شاهد الحلقة كاملة الآن:\n{link}\n\n#مسلسلات_تركية #مسلسلات_عربية #شاهد #دراما #اكسبلور #ترند"
    },

    # --- 3. قسم الأخبار العاجلة والتريند ---
    {
        "category": "أخبار",
        "text": "🔴 عاجل | تطورات ميدانية متسارعة وأنباء هامة نضعكم في تفاصيلها أولاً بأول!\n\n👇 شاهد التفاصيل الكاملة والفيديو الحصري:\n{link}\n\n#عاجل #أخبار #السعودية #الخليج #الميدان #ترند_اليوم #خبر_عاجل"
    },
    {
        "category": "أخبار",
        "text": "🚨 فيديو متداول ومثير للجدل يتصدر منصات التواصل الآن.. شاهد ما حدث بالكامل!\n\n👇 رابط مشاهدة الفيديو المباشر:\n{link}\n\n#فيديو_متداول #ترند #اكسبلور_فولو #أخبار_اليوم #حدث_الان"
    },

    # --- 4. قسم العملات الرقمية والإيردروبات ---
    {
        "category": "عملات رقمية",
        "text": "💎 إيردروب حصري وتوزيع مجاني لعملات رقمية موثوقة وسحب مباشر لمحفظتك الإلكترونية بدون إيداع!\n\n👇 رابط التسجيل السريع:\n{link}\n\n#كريبتو #بيتكوين #الربح_من_الانترنت #Crypto #Airdrop #Bitcoin #Binance #عملات_رقمية"
    },
    {
        "category": "عملات رقمية",
        "text": "🚀 بوت تلغرام جديد لتعدين وربح العملات الرقمية مجاناً وسحب فوري لمحفظتك.. فرصة لا تفوتها!\n\n👇 ابدأ الجمع والسحب الآن:\n{link}\n\n#تعدين #تداول #عملات #استثمار #TON #USDT #BTC #ربح_مجاني"
    }
]

DESTINATIONS = [
    "https://google.com",
    "https://t.me/almaydan_news24"
]

posted_messages = set()
tweet_counter = 0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# --- اتصال تويتر الرسمي ---
try:
    twitter_client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    print("✅ تم الاتصال بحساب تويتر بنجاح!", flush=True)
except Exception as e:
    print(f"❌ خطأ بالاتصال بتويتر: {e}", flush=True)

def shorten_url(url):
    api_url = f"https://exe.io/api?api={SHORTENER_API}&url={url}"
    try:
        res = requests.get(api_url, timeout=10).json()
        if res.get("status") == "success":
            return res.get("shortenedUrl")
    except Exception:
        pass
    return url

# --- حلقة التغريد الآمنة (كل 30 دقيقة تختار قسماً مختلفاً) ---
def twitter_loop():
    global tweet_counter
    print("🚀 بدء تشغيل بوت التغريدات (رياضة + مسلسلات + أخبار + كريبتو)...", flush=True)
    time.sleep(15)
    
    while True:
        try:
            chosen = random.choice(TWEETS_POOL)
            dest = random.choice(DESTINATIONS)
            short_link = shorten_url(dest)
            
            tweet_text = chosen["text"].replace("{link}", short_link)
            
            response = twitter_client.create_tweet(text=tweet_text)
            tweet_counter += 1
            print(f"🐦 [تغريدة {chosen['category']} رقم {tweet_counter}]: تم النشر بنجاح! ID: {response.data['id']}", flush=True)
        except Exception as e:
            print(f"⚠️ خطأ أثناء التغريد: {e}", flush=True)
            
        print("⏳ سيعاود التغريد بمحتوى جديد بعد 30 دقيقة...\n", flush=True)
        time.sleep(1800)

# --- حلقة بوت الأخبار على تلغرام ---
def send_news_telegram(text, photo_url=None):
    full_message = text + SIGNATURE
    if photo_url:
        try:
            img_res = requests.get(photo_url, headers=HEADERS, timeout=10)
            if img_res.status_code == 200 and len(img_res.content) > 5000:
                caption_text = full_message if len(full_message) <= 1024 else full_message[:1020] + "..."
                url = f"https://api.telegram.org/bot{NEWS_BOT_TOKEN}/sendPhoto"
                files = {'photo': ('news.jpg', img_res.content, 'image/jpeg')}
                data = {'chat_id': NEWS_TARGET_CHANNEL, 'caption': caption_text, 'parse_mode': 'HTML'}
                r = requests.post(url, data=data, files=files, timeout=15)
                if r.status_code == 200:
                    return
        except Exception:
            pass

    url = f"https://api.telegram.org/bot{NEWS_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": NEWS_TARGET_CHANNEL, "text": full_message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception:
        pass

def free_ai_rephrase(raw_text):
    clean_input = re.sub(r'https?://\S+', '', raw_text)
    clean_input = re.sub(r'@\w+', '', clean_input).replace("تابعونا", "").replace("اشترك", "").strip()
    prompt = f"أعد صياغة هذا الخبر بأسلوب صحفي جديد كلياً وبدون إعلانات، وابدأ بـ 🔴 <b>NEWS | عاجل</b>:\n\n{clean_input}"
    try:
        url = "https://text.pollinations.ai/"
        payload = {"messages": [{"role": "user", "content": prompt}], "model": "mistral"}
        res = requests.post(url, json=payload, timeout=25)
        if res.status_code == 200 and len(res.text) > 30:
            return res.text.strip()
    except Exception:
        pass
    lines = [html.escape(line.strip()) for line in clean_input.split("\n") if line.strip()]
    return "🔴 <b>NEWS | عاجل</b>\n\n" + "\n\n".join(lines)

def scrape_channel(channel_name):
    url = f"https://t.me/s/{channel_name}"
    results = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        message_boxes = soup.find_all("div", class_="tgme_widget_message")
        for box in message_boxes[-3:]:
            if box.find("video"):
                continue
            photo_url = None
            photo_wrap = box.find("a", class_="tgme_widget_message_photo_wrap")
            if photo_wrap and "style" in photo_wrap.attrs:
                match = re.search(r"url\('([^']+)'\)", photo_wrap["style"])
                if match:
                    photo_url = match.group(1)
            text_elem = box.find("div", class_="tgme_widget_message_text")
            if text_elem:
                text = text_elem.get_text(separator="\n").strip()
                results.append((text, photo_url))
        return results
    except Exception:
        return []

def news_loop():
    print("🚀 بوت تلغرام للأخبار يعمل الآن...", flush=True)
    while True:
        for channel in SOURCE_CHANNELS:
            recent_items = scrape_channel(channel)
            for raw_news, photo_url in recent_items:
                if raw_news and len(raw_news) > 25 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    if len(posted_messages) > 500:
                        posted_messages.clear()
                    final_text = free_ai_rephrase(raw_news)
                    send_news_telegram(final_text, photo_url)
            time.sleep(3)
        time.sleep(40)

# --- خادم الويب لإبقاء Render شغال 24/7 ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"Bots Running 24/7! Total Tweets Sent: {tweet_counter}".encode())

if __name__ == "__main__":
    t1 = threading.Thread(target=news_loop)
    t1.daemon = True
    t1.start()

    t2 = threading.Thread(target=twitter_loop)
    t2.daemon = True
    t2.start()

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()
