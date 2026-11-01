import time
import re
import html
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

# ================= بياناتك =================
BOT_TOKEN = "9299530952:AAHH4CC0CqT-kfFkyGR97W-W3untPRP8xLI"
GEMINI_API_KEY = "AIzaSyBUHdNuRzGOcBIZTKapO2bSPxnC1NBJWhU"
TARGET_CHANNEL = "@almaydan_news24"

# التوقيع التلقائي
SIGNATURE = "\n\n➖➖➖➖➖➖➖\n📲 <b>الميدان نيوز | تابع التغطية أولاً بأول:</b>\n🔗 @almaydan_news24"

# القنوات المصدرية
SOURCE_CHANNELS = [
    "AjaNews",
    "almayadeen",
    "mayadeenchannel",
    "iraqex1",
    "alnourradio",
    "bintjbeilnews",
    "N_FFG"
]

# برومبت يحافظ على كامل التفاصيل بدون اختصار
PROMPT = """
أنت محرر صحفي محترف لوكالة أنباء عاجلة.
مهمتك:
1. اقرأ الخبر التالي، وتأكد أنه خبر سياسي أو ميداني يخص: (سوريا، فلسطين وغزة، لبنان، العراق، إيران، أو الشرق الأوسط).
2. قم بإعادة صياغة الخبر بالكامل بأسلوب صحفي رصين وقوي، مع **الحفاظ على جميع التفاصيل والمعلومات والأرقام والأسماء بدقة وبدون أي حذف أو اختصار**.
3. احذف تماماً: الإعلانات، الروابط، وأسماء القنوات (مثل الجزيرة، الميادين..)، والتوجيهات مثل 'تابعونا'.
4. إذا كان الخبر إعلاناً، أو غير مهم، رد بكلمة: IGNORE
5. التنسيق الإجباري:
🔴 <b>NEWS | عاجل | [الدولة أو المنطقة]</b>

[النص بعد إعادة صياغته كاملاً بجميع تفاصيله]

الخبر الأصلي:
"""

posted_messages = set()

def send_to_telegram(text, photo_url=None):
    """إرسال الخبر مع الصورة (إن وجدت) وبدون مشاكل في الرموز"""
    full_message = text + SIGNATURE
    
    # إذا في صورة، ننشر الصورة مع النص (Caption)
    if photo_url:
        # حد التلغرام للشرح مع الصورة هو 1024 حرف
        caption_text = full_message if len(full_message) <= 1024 else full_message[:1020] + "..."
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TARGET_CHANNEL,
            "photo": photo_url,
            "caption": caption_text,
            "parse_mode": "HTML"
        }
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                print("✅ تم نشر الخبر مع الصورة بنجاح!", flush=True)
                return
            else:
                # إذا فشل إرسال الصورة بنرسل كنص عادي كاحتياط
                print(f"⚠️ فشل إرسال الصورة ({r.status_code})، جاري النشر كنص...", flush=True)
        except Exception as e:
            print(f"خطأ بإرسال الصورة: {e}", flush=True)

    # نشر الخبر كنص في حال عدم وجود صورة أو كان فيديو
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TARGET_CHANNEL,
        "text": full_message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            clean_plain_text = re.sub(r'<[^>]*>', '', full_message)
            r = requests.post(url, json={"chat_id": TARGET_CHANNEL, "text": clean_plain_text}, timeout=15)
        print(f"نتيجة إرسال النص لتلغرام: {r.status_code}", flush=True)
    except Exception as e:
        print(f"خطأ بالإرسال لتلغرام: {e}", flush=True)

def fallback_clean(raw_text):
    """تنظيف فوري للخبر مع الحفاظ على كامل النص"""
    text = re.sub(r'https?://\S+', '', raw_text)
    text = re.sub(r'@\w+', '', text)
    text = text.replace("تابعونا", "").replace("اشترك", "").strip()
    lines = [html.escape(line.strip()) for line in text.split("\n") if line.strip()]
    cleaned = "\n\n".join(lines) # الحفاظ على كل الأسطر كاملة
    return f"🔴 <b>NEWS | عاجل</b>\n\n{cleaned}"

def ask_gemini(raw_text):
    """إعادة صياغة كاملة للخبر عبر الذكاء الاصطناعي"""
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
    for m in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": PROMPT + raw_text}]}]
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                ai_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                if "IGNORE" in ai_text:
                    return "IGNORE"
                return ai_text
        except:
            pass
    return None

def scrape_channel(channel_name):
    """سحب النصوص والصور (مع استبعاد الفيديوهات)"""
    url = f"https://t.me/s/{channel_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ar,en;q=0.9"
    }
    results = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # البحث عن صناديق الرسائل الكاملة
        message_boxes = soup.find_all("div", class_="tgme_widget_message")
        
        for box in message_boxes[-3:]:
            # 1. استبعاد الفيديوهات
            is_video = box.find("i", class_="tgme_widget_message_video_thumb") or box.find("video")
            if is_video:
                photo_url = None
            else:
                # 2. استخراج رابط الصورة إن وجدت
                photo_wrap = box.find("a", class_="tgme_widget_message_photo_wrap")
                photo_url = None
                if photo_wrap and "style" in photo_wrap.attrs:
                    style_text = photo_wrap["style"]
                    match = re.search(r"url\('([^']+)'\)", style_text)
                    if match:
                        photo_url = match.group(1)

            # 3. استخراج النص
            text_elem = box.find("div", class_="tgme_widget_message_text")
            if text_elem:
                text = text_elem.get_text(separator="\n").strip()
                results.append((text, photo_url))
                
        return results
    except Exception as e:
        print(f"خطأ بقراءة {channel_name}: {e}", flush=True)
        return []

def news_loop():
    print("🚀 البوت بدأ العمل مع ميزة الصور وإعادة الصياغة الكاملة...", flush=True)

    while True:
        for channel in SOURCE_CHANNELS:
            recent_items = scrape_channel(channel)
            
            for raw_news, photo_url in recent_items:
                if raw_news and len(raw_news) > 20 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 500:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}، جاري إعادة صياغته بالكامل...", flush=True)
                    
                    final_text = ask_gemini(raw_news)
                    
                    if final_text == "IGNORE":
                        print(f"⛔ تم استبعاد الخبر (إعلان أو غير مناسب).", flush=True)
                        continue

                    if not final_text or len(final_text) < 10:
                        final_text = fallback_clean(raw_news)

                    # إرسال النص مع الصورة
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
