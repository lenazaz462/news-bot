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

# قنوات السحب
SOURCE_CHANNELS = ["bintjbeilnews", "N_FFG", "sham_fm"]

# ================= إعداد الذكاء الاصطناعي مع إلغاء الحظر الإخباري =================
genai.configure(api_key=GEMINI_API_KEY)

# تعطيل الفلاتر مشان أخبار القصف والميدان ما يحظرها
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)

PROMPT = """
أنت محرر صحفي عاجل ومحترف لقناة إخبارية سريعة.
مهمتك:
1. اقرأ الخبر التالي، وتأكد أنه يتعلق حصراً بإحدى المناطق: (سوريا، فلسطين وغزة، لبنان، العراق، إيران).
2. احذف منه أي إعلانات، روابط، أسماء قنوات ومذيعين، أو عبارات مثل 'تابعونا' أو أسماء مواقع ومجموعات واتساب.
3. إذا كان الخبر عبارة عن إعلان، أو خبر تافه، أو خارج نطاق هذه الدول، رد بكلمة واحدة فقط: IGNORE
4. إذا كان خبراً مهماً، أعد صياغته باختصار واحترافية بالتنسيق التالي حصراً:
🔴 **عاجل | [اسم الدولة]**
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
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ بالإرسال لتلغرام: {e}")

def scrape_channel(channel_name):
    """قراءة آخر المنشورات من القناة"""
    url = f"https://t.me/s/{channel_name}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message_text")
        if not messages:
            return []
        
        # جلب نصوص آخر 3 رسائل للتأكد من عدم تفويت أي عاجل
        return [msg.get_text(separator="\n").strip() for msg in messages[-3:]]
    except Exception as e:
        print(f"خطأ بقراءة القناة {channel_name}: {e}")
        return []

def news_loop():
    print("🚀 البوت بدأ العمل ومراقبة القنوات...")

    while True:
        for channel in SOURCE_CHANNELS:
            recent_news = scrape_channel(channel)
            
            for raw_news in recent_news:
                # التأكد أن النص حقيقي وليس قصيراً جداً
                if raw_news and len(raw_news) > 25 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 300:
                        posted_messages.clear()

                    print(f"📌 وصل خبر جديد من {channel}، جاري معالجته...")
                    
                    try:
                        ai_response = model.generate_content(PROMPT + raw_news)
                        final_text = ai_response.text.strip()
                        
                        # التأكد أنه ليس إعلاناً وليس مجرد نقطة أو نص فارغ
                        if "IGNORE" not in final_text and len(final_text) > 15:
                            send_to_telegram(final_text)
                            print("✅ تم نشر الخبر بنجاح في القناة!")
                        else:
                            print("❌ تم تجاهل الخبر (إعلان أو غير مناسب).")
                            
                    except Exception as e:
                        print(f"خطأ أثناء معالجة الذكاء الاصطناعي: {e}")

            time.sleep(3)

        time.sleep(60) # فحص القنوات كل دقيقة

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
