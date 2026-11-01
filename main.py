import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ================= بياناتك الجاهزة =================
BOT_TOKEN = "9299530952:AAHH4CC0CqT-kfFkyGR97W-W3untPRP8xLI"
GEMINI_API_KEY = "AIzaSyBUHdNuRzGOcBIZTKapO2bSPxnC1NBJWhU"
TARGET_CHANNEL = "@almaydan_news24"

# القنوات المصدرية (ضفنا الجزيرة عاجل + العربية عاجل + القنوات المحلية)
SOURCE_CHANNELS = [
    "AJA_Breaking",     # الجزيرة - عاجل
    "AlArabiya_Brk",    # العربية - عاجل
    "sham_fm",          # شام إف إم (سوريا)
    "bintjbeilnews",    # بنت جبيل (لبنان)
    "N_FFG"             # أخبار لبنان وغزة
]

# ================= إعداد الذكاء الاصطناعي =================
genai.configure(api_key=GEMINI_API_KEY)

safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)

PROMPT = """
أنت محرر صحفي عاجل ومحترف لقناة إخبارية سريعة اسمها (الميدان نيوز).
مهمتك:
1. اقرأ الخبر التالي، وتأكد أنه يتعلق حصراً بإحدى المناطق: (سوريا، فلسطين وغزة، لبنان، العراق، إيران، أو قضايا الشرق الأوسط الهامة).
2. احذف منه أي إعلانات، روابط، أسماء قنوات (مثل الجزيرة أو العربية)، أسماء مذيعين، أو عبارات مثل 'تابعونا'.
3. إذا كان الخبر عبارة عن إعلان، أو خبر تافه، أو خارج نطاق هذه الدول، رد بكلمة واحدة فقط: IGNORE
4. إذا كان خبراً مهماً، أعد صياغته باختصار واحترافية بالتنسيق التالي حصراً مع كلمة NEWS:
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

def scrape_channel(channel_name):
    """قراءة آخر المنشورات"""
    url = f"https://t.me/s/{channel_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.7,en;q=0.3"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message_text")
        
        if not messages:
            print(f"⚠️ لم يتم العثور على رسائل في {channel_name}", flush=True)
            return []
            
        return [msg.get_text(separator="\n").strip() for msg in messages[-2:]]
    except Exception as e:
        print(f"❌ خطأ بقراءة القناة {channel_name}: {e}", flush=True)
        return []

def news_loop():
    print("🚀 البوت بدأ العمل ومراقبة الجزيرة، العربية، وباقي القنوات...", flush=True)
    send_to_telegram("🔄 **تم تحديث النظام: جاري مراقبة الجزيرة والعربية وباقي المصادر الآن...**")

    while True:
        for channel in SOURCE_CHANNELS:
            print(f"🔍 فحص: {channel}...", flush=True)
            recent_news = scrape_channel(channel)
            
            for raw_news in recent_news:
                if raw_news and len(raw_news) > 20 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 400:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}، جاري صياغته بـ Gemini...", flush=True)
                    
                    try:
                        ai_response = model.generate_content(PROMPT + raw_news)
                        final_text = ai_response.text.strip()
                        
                        if "IGNORE" not in final_text and len(final_text) > 10:
                            send_to_telegram(final_text)
                            print(f"✅ تم نشر الخبر بنجاح من {channel}!", flush=True)
                        else:
                            print(f"⛔ تم تجاهل الخبر من {channel}.", flush=True)
                            
                    except Exception as e:
                        print(f"⚠️ خطأ بالذكاء الاصطناعي: {e}", flush=True)

            time.sleep(2)

        time.sleep(45) # فحص القنوات كل 45 ثانية لمواكبة العاجل

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
