import time
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

# ================= بياناتك =================
BOT_TOKEN = "9299530952:AAHH4CC0CqT-kfFkyGR97W-W3untPRP8xLI"
GEMINI_API_KEY = "AIzaSyBUHdNuRzGOcBIZTKapO2bSPxnC1NBJWhU"
TARGET_CHANNEL = "@almaydan_news24"

SOURCE_CHANNELS = ["bintjbeilnews", "N_FFG", "sham_fm", "AJA_Breaking"]

PROMPT = """
أنت محرر صحفي عاجل ومحترف لقناة إخبارية سريعة اسمها (الميدان نيوز).
مهمتك:
1. اقرأ الخبر التالي، وتأكد أنه يتعلق بإحدى المناطق: (سوريا، فلسطين وغزة، لبنان، العراق، إيران، الشرق الأوسط).
2. احذف منه أي إعلانات، روابط، أسماء قنوات أو مواقع، وأسماء مذيعين.
3. إذا كان الخبر عبارة عن إعلان، أو خبر تافه، رد بكلمة: IGNORE
4. إذا كان خبراً مهماً، أعد صياغته باختصار بالتنسيق التالي حصراً:
🔴 **NEWS | عاجل | [اسم الدولة]**
[نص الخبر بسطرين إلى 3 أسطر بأسلوب إخباري رصين وسريع]

الخبر:
"""

posted_messages = set()

def send_to_telegram(text):
    """إرسال الخبر لقناتك"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TARGET_CHANNEL,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        print(f"نتيجة الإرسال لتلغرام: {r.status_code}", flush=True)
    except Exception as e:
        print(f"خطأ بالإرسال لتلغرام: {e}", flush=True)

def fallback_clean(raw_text):
    """تنظيف فوري للخبر ونشره في حال تأخر أو تعطل الذكاء الاصطناعي"""
    text = re.sub(r'https?://\S+', '', raw_text)
    text = re.sub(r'@\w+', '', text)
    text = text.replace("تابعونا", "").replace("اشترك", "").strip()
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned = "\n".join(lines[:3])
    return f"🔴 **NEWS | عاجل**\n\n{cleaned}"

def ask_gemini(raw_text):
    """طلب الصياغة من Gemini عبر الرابط المباشر الرسمي"""
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
    for m in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_API_KEY}"
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
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except:
            pass
    return None

def scrape_channel(channel_name):
    """قراءة آخر المنشورات"""
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
    print("🚀 البوت بدأ العمل الحقيقي بالنظام المباشر...", flush=True)

    while True:
        for channel in SOURCE_CHANNELS:
            recent_news = scrape_channel(channel)
            
            for raw_news in recent_news:
                if raw_news and len(raw_news) > 20 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 400:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}، جاري معالجته...", flush=True)
                    
                    # محاولة الصياغة بالذكاء الاصطناعي
                    final_text = ask_gemini(raw_news)
                    
                    # إذا الذكاء الاصطناعي تجاهل الخبر لأنه إعلان
                    if final_text and "IGNORE" in final_text:
                        print(f"⛔ إعلان تم استبعاده من {channel}.", flush=True)
                        continue

                    # إذا ما اشتغل الذكاء الاصطناعي، بنشغّل نظام التنظيف الفوري وما منضيع الخبر
                    if not final_text or len(final_text) < 10:
                        print("⚠️ الذكاء الاصطناعي تعطل، سيتم النشر عبر نظام التنظيف الفوري المباشر!", flush=True)
                        final_text = fallback_clean(raw_news)

                    send_to_telegram(final_text)
                    print(f"✅ تم نشر الخبر بنجاح في قناتك من {channel}!", flush=True)

            time.sleep(4)

        time.sleep(45)

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
