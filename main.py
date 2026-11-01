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

PROMPT = """
أنت محرر صحفي خبير. أعد كتابة وصياغة هذا الخبر بالكامل بأسلوب إخباري جديد، رصين، وقوي.
شروط إجبارية:
1. احتفظ بكل التفاصيل والأسماء والأرقام كاملة دون أي حذف.
2. غيّر صياغة الجمل والكلمات بالكامل لتكون بأسلوبك الصحفي المستقل.
3. احذف أسماء القنوات الأصلية وروابطها وإعلاناتها.
4. التنسيق:
🔴 <b>NEWS | عاجل | [الدولة]</b>

[الخبر بعد إعادة صياغته بالكامل]

الخبر:
"""

posted_messages = set()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def send_to_telegram(text, photo_url=None):
    """إرسال الخبر مع تحميل ورفع الصورة كملف حقيقي"""
    full_message = text + SIGNATURE
    
    # إذا في صورة، نحملها ونرفعها رفع كملف حقيقي مشان ما يرفضها تلغرام
    if photo_url:
        try:
            img_res = requests.get(photo_url, headers=HEADERS, timeout=10)
            if img_res.status_code == 200:
                caption_text = full_message if len(full_message) <= 1024 else full_message[:1020] + "..."
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                files = {'photo': ('image.jpg', img_res.content, 'image/jpeg')}
                data = {'chat_id': TARGET_CHANNEL, 'caption': caption_text, 'parse_mode': 'HTML'}
                
                r = requests.post(url, data=data, files=files, timeout=15)
                if r.status_code == 200:
                    print("✅ تم رفع الصورة الحقيقية مع الخبر بنجاح!", flush=True)
                    return
                else:
                    print(f"⚠️ فشل رفع الصورة: {r.text}", flush=True)
        except Exception as e:
            print(f"خطأ بتحميل الصورة: {e}", flush=True)

    # إذا ما في صورة أو فشل رفعها، ننشر كنص
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

def ask_gemini(raw_text):
    """صياغة الخبر عبر Google Gemini مع طباعة الخطأ الحقيقي إن وجد"""
    # استخدام الموديل الرسمي المستقر في سيرفرات أوروبا v1
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": PROMPT + raw_text}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    try:
        res = requests.post(url, json=payload, timeout=12)
        if res.status_code == 200:
            data = res.json()
            ai_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            print("✨ نجح الذكاء الاصطناعي في إعادة الصياغة بالكامل!", flush=True)
            return ai_text
        else:
            print(f"❌ خطأ من جوجل ({res.status_code}): {res.text[:150]}", flush=True)
    except Exception as e:
        print(f"خطأ بالاتصال بـ Gemini: {e}", flush=True)
    return None

def fallback_clean(raw_text):
    """تنظيف الطوارئ"""
    text = re.sub(r'https?://\S+', '', raw_text)
    text = re.sub(r'@\w+', '', text)
    text = text.replace("تابعونا", "").replace("اشترك", "").strip()
    lines = [html.escape(line.strip()) for line in text.split("\n") if line.strip()]
    return f"🔴 <b>NEWS | عاجل</b>\n\n" + "\n\n".join(lines)

def scrape_channel(channel_name):
    """سحب النصوص والصور المباشرة"""
    url = f"https://t.me/s/{channel_name}"
    results = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        message_boxes = soup.find_all("div", class_="tgme_widget_message")
        
        for box in message_boxes[-3:]:
            # تجاهل الفيديوهات
            if box.find("i", class_="tgme_widget_message_video_thumb") or box.find("video"):
                continue

            # استخراج رابط الصورة
            photo_url = None
            photo_wrap = box.find("a", class_="tgme_widget_message_photo_wrap")
            if photo_wrap and "style" in photo_wrap.attrs:
                match = re.search(r"url\('([^']+)'\)", photo_wrap["style"])
                if match:
                    photo_url = match.group(1)

            # استخراج النص
            text_elem = box.find("div", class_="tgme_widget_message_text")
            if text_elem:
                text = text_elem.get_text(separator="\n").strip()
                results.append((text, photo_url))
                
        return results
    except Exception as e:
        print(f"خطأ بقراءة {channel_name}: {e}", flush=True)
        return []

def news_loop():
    print("🚀 البوت بدأ العمل الحقيقي بنظام رفع الصور المباشر...", flush=True)

    while True:
        for channel in SOURCE_CHANNELS:
            recent_items = scrape_channel(channel)
            
            for raw_news, photo_url in recent_items:
                if raw_news and len(raw_news) > 25 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 500:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}... جاري الصياغة ورفع الصورة...", flush=True)
                    
                    final_text = ask_gemini(raw_news)
                    
                    # إذا تعطل Gemini نستخدم التنظيف العادي
                    if not final_text or len(final_text) < 15:
                        final_text = fallback_clean(raw_news)

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
