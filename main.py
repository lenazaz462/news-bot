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

# القنوات المصدرية الجديدة بالكامل حسب طلبك
SOURCE_CHANNELS = [
    "AjaNews",
    "almayadeen",
    "mayadeenchannel",
    "iraqex1",
    "alnourradio",
    "bintjbeilnews",
    "N_FFG"
]

# برومبت متخصص بإعادة صياغة الجملة بالكامل
PROMPT = """
أنت محرر صحفي محترف لوكالة أنباء عاجلة.
مهمتك:
1. اقرأ الخبر التالي، وتأكد أنه خبر سياسي أو ميداني يخص: (سوريا، فلسطين وغزة، لبنان، العراق، إيران، أو الشرق الأوسط).
2. قم بإعادة صياغة الجملة بالكامل بأسلوبك الصحفي الرصين والمباشر (لا تنسخ النص كما هو، بل أعد بناء الجملة لتكون قوية ومختصرة في سطرين فقط).
3. احذف تماماً أي أسماء قنوات (مثل الجزيرة، الميادين، النور)، وأي روابط أو توجيهات للمتابعة.
4. إذا كان الخبر إعلاناً، أو غير مهم، رد بكلمة: IGNORE
5. التنسيق الإجباري:
🔴 <b>NEWS | عاجل | [الدولة أو المنطقة]</b>
[الجملة بعد إعادة صياغتها باحترافية]

الخبر الأصلي:
"""

posted_messages = set()

def send_to_telegram(text):
    """إرسال الخبر مع حماية مزدوجة ضد خطأ 400"""
    full_message = text + SIGNATURE
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # المحاولة الأولى بنظام HTML
    payload = {
        "chat_id": TARGET_CHANNEL,
        "text": full_message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        
        # إذا رفض تلغرام بسبب رمز غير متوافق (خطأ 400)، نرسله كنص عادي بدون تشفير
        if r.status_code != 200:
            clean_plain_text = re.sub(r'<[^>]*>', '', full_message)
            fallback_payload = {
                "chat_id": TARGET_CHANNEL,
                "text": clean_plain_text
            }
            r = requests.post(url, json=fallback_payload, timeout=15)
            
        print(f"نتيجة الإرسال لتلغرام: {r.status_code}", flush=True)
    except Exception as e:
        print(f"خطأ بالإرسال لتلغرام: {e}", flush=True)

def fallback_clean(raw_text):
    """صياغة طوارئ في حال تأخر الذكاء الاصطناعي"""
    text = re.sub(r'https?://\S+', '', raw_text)
    text = re.sub(r'@\w+', '', text)
    text = text.replace("تابعونا", "").replace("اشترك", "").strip()
    lines = [html.escape(line.strip()) for line in text.split("\n") if line.strip()]
    cleaned = "\n".join(lines[:2])
    return f"🔴 <b>NEWS | عاجل</b>\n\n{cleaned}"

def ask_gemini(raw_text):
    """إعادة صياغة الجملة عبر Gemini 2.0 و 1.5"""
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
    for m in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": PROMPT + raw_text}]}]
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
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
    """سحب آخر المنشورات"""
    url = f"https://t.me/s/{channel_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ar,en;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message_text")
        if not messages:
            return []
        return [msg.get_text(separator="\n").strip() for msg in messages[-2:]]
    except Exception as e:
        print(f"خطأ بقراءة {channel_name}: {e}", flush=True)
        return []

def news_loop():
    print("🚀 البوت بدأ العمل ومراقبة كل القنوات الجديدة مع إعادة الصياغة...", flush=True)

    while True:
        for channel in SOURCE_CHANNELS:
            recent_news = scrape_channel(channel)
            
            for raw_news in recent_news:
                if raw_news and len(raw_news) > 20 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 500:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}، جاري إعادة صياغته...", flush=True)
                    
                    final_text = ask_gemini(raw_news)
                    
                    if final_text == "IGNORE":
                        print(f"⛔ تم استبعاد الخبر (إعلان أو غير مناسب).", flush=True)
                        continue

                    if not final_text or len(final_text) < 10:
                        final_text = fallback_clean(raw_news)

                    send_to_telegram(final_text)
                    print(f"✅ تم نشر الخبر بعد إعادة الصياغة من {channel}!", flush=True)

            time.sleep(3)

        time.sleep(40) # فحص مستمر كل 40 ثانية

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
