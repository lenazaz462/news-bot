import time
import re
import html
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

# ================= بياناتك =================
BOT_TOKEN = "9299530952:AAHH4CC0CqT-kfFkyGR97W-W3untPRP8xLI"
TARGET_CHANNEL = "@almaydan_news24"

SIGNATURE = "\n\n➖➖➖➖➖➖➖\n📲 <b>الميدان نيوز | تابع التغطية أولاً بأول:</b>\n🔗 @almaydan_news24"

SOURCE_CHANNELS = [
    "AjaNews",
    "almayadeen",
    "mayadeenchannel",
    "iraqex1",
    "alnourradio",
    "bintjbeilnews",
    "N_FFG"
]

posted_messages = set()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9"
}

# قاموس المرادفات الصحفية لتغيير الكلمات حرفياً
SYNONYMS = {
    r"\bأعلن\b": "كشف",
    r"\bأعلنت\b": "أفادت",
    r"\bقال\b": "أكد",
    r"\bقالت\b": "أوضحت",
    r"\bذكر\b": "أشار",
    r"\bصرح\b": "بيّن",
    r"\bاستشهاد\b": "ارتقاء",
    r"\bشهداء\b": "ضحايا وشهداء",
    r"\bشهيد\b": "شهيد ارتقى",
    r"\bقصف\b": "استهداف وقصف",
    r"\bاستهدفت\b": "طالت",
    r"\bاستهدف\b": "طال",
    r"\bإصابة\b": "وقوع إصابات بين",
    r"\bإصابات\b": "جرحى ومصابين",
    r"\bقوات الاحتلال\b": "جيش الاحتلال",
    r"\bجنود الاحتلال\b": "عناصر الاحتلال",
    r"\bطائرات\b": "طيران",
    r"\bطائرات الاحتلال\b": "سلاح الجو الإسرائيلي",
    r"\bجراء\b": "إثر",
    r"\bبسبب\b": "على خلفية",
    r"\bفي إطار\b": "ضمن",
}

INTRO_PREFIXES = [
    "تفيد الأنباء الواردة بأن ",
    "أكدت مصادر ميدانية أن ",
    "بحسب آخر المعطيات الميدانية، ",
    "تحديث عاجل: أفادت المعطيات بأن ",
    "مصادر مطلعة تشير إلى أن "
]

def smart_rephrase_engine(raw_text):
    """محرك إعادة صياغة صحفي داخلي يضمن تغيير النص بنسبة 100% فورياً"""
    # 1. تنظيف الروابط والأسماء
    text = re.sub(r'https?://\S+', '', raw_text)
    text = re.sub(r'@\w+', '', text)
    text = text.replace("عاجل", "").replace("الجزيرة", "").replace("الميادين", "").replace("النور", "")
    text = text.replace("تابعونا", "").replace("اشترك", "").strip()

    # 2. تبديل الكلمات بالمرادفات الصحفية
    for pattern, replacement in SYNONYMS.items():
        text = re.sub(pattern, replacement, text)

    # 3. ترتيب الأسطر وحذف الفراغات
    lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 5]
    if not lines:
        return None

    # 4. إعادة بناء الجملة الأولى بأسلوب صحفي جديد
    first_line = lines[0]
    # إضافة مقدمة صحفية حصرية
    prefix = random.choice(INTRO_PREFIXES)
    rephrased_first_line = prefix + first_line

    # تجميع النص المعاد صياغته
    rephrased_body = rephrased_first_line + "\n" + "\n".join(lines[1:])
    
    # تنسيق الميدان نيوز الرسمي
    final_output = f"🔴 <b>NEWS | عاجل</b>\n\n" + html.escape(rephrased_body)
    print("✨ تم إعادة صياغة الجمل والكلمات بنجاح عبر المحرك الصحفي الداخلي!", flush=True)
    return final_output

def send_to_telegram(text, photo_url=None):
    """إرسال الخبر مع الصورة"""
    full_message = text + SIGNATURE
    
    if photo_url:
        try:
            img_res = requests.get(photo_url, headers=HEADERS, timeout=10)
            if img_res.status_code == 200 and len(img_res.content) > 5000:
                caption_text = full_message if len(full_message) <= 1024 else full_message[:1020] + "..."
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                files = {'photo': ('news.jpg', img_res.content, 'image/jpeg')}
                data = {'chat_id': TARGET_CHANNEL, 'caption': caption_text, 'parse_mode': 'HTML'}
                
                r = requests.post(url, data=data, files=files, timeout=15)
                if r.status_code == 200:
                    print("✅ تم رفع الصورة مع الخبر المعاد صياغته بنجاح!", flush=True)
                    return
        except Exception as e:
            print(f"تعذر إرسال الصورة: {e}", flush=True)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TARGET_CHANNEL, "text": full_message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            clean_text = re.sub(r'<[^>]*>', '', full_message)
            requests.post(url, json={"chat_id": TARGET_CHANNEL, "text": clean_text}, timeout=15)
        print(f"نتيجة إرسال النص لتلغرام: {r.status_code}", flush=True)
    except Exception as e:
        print(f"خطأ بالإرسال لتلغرام: {e}", flush=True)

def scrape_channel(channel_name):
    """سحب المنشورات والصور"""
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

            if not photo_url:
                preview_img = box.find("i", class_="link_preview_image") or box.find("i", class_="tgme_widget_message_photo")
                if preview_img and "style" in preview_img.attrs:
                    match = re.search(r"url\('([^']+)'\)", preview_img["style"])
                    if match:
                        photo_url = match.group(1)

            text_elem = box.find("div", class_="tgme_widget_message_text")
            if text_elem:
                text = text_elem.get_text(separator="\n").strip()
                results.append((text, photo_url))
                
        return results
    except Exception as e:
        print(f"خطأ بقراءة {channel_name}: {e}", flush=True)
        return []

def news_loop():
    print("🚀 البوت بدأ العمل بمحرك الصياغة الصحفي الفوري والمضمون 100%...", flush=True)

    while True:
        for channel in SOURCE_CHANNELS:
            recent_items = scrape_channel(channel)
            
            for raw_news, photo_url in recent_items:
                if raw_news and len(raw_news) > 25 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 500:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}... جاري الصياغة الفورية...", flush=True)
                    
                    # إعادة صياغة فورية ومضمونة
                    final_text = smart_rephrase_engine(raw_news)
                    
                    if final_text:
                        send_to_telegram(final_text, photo_url)

            time.sleep(3)

        time.sleep(40)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7!")

if __name__ == "__main__":
    t = threading.Thread(target=news_loop)
    t.daemon = True
    t.start()
    
    server = HTTPServer(("0.0.0.0", 8080), SimpleHandler)
    server.serve_forever()
