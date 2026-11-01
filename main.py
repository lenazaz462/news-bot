import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# ================= بياناتك الجاهزة =================
BOT_TOKEN = "9299530952:AAHH4CC0CqT-kfFkyGR97W-W3untPRP8xLI"
GEMINI_API_KEY = "AIzaSyBUHdNuRzGOcBIZTKapO2bSPxnC1NBJWhU"
TARGET_CHANNEL = "@almaydan_news24"

# قنوات السحب
SOURCE_CHANNELS = ["bintjbeilnews", "N_FFG", "sham_fm"]

# ================= إعداد الذكاء الاصطناعي =================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

PROMPT = """
أنت محرر صحفي عاجل ومحترف لقناة إخبارية سريعة.
مهمتك:
1. اقرأ الخبر التالي، وتأكد أنه يتعلق حصراً بإحدى المناطق: (سوريا، فلسطين وغزة، لبنان، العراق، إيران).
2. احذف منه أي إعلانات، روابط، أسماء قنوات ومذيعين، أو عبارات مثل 'تابعونا' أو أسماء مواقع.
3. إذا كان الخبر عبارة عن إعلان، أو خبر تافه، أو خارج نطاق هذه الدول، رد بكلمة واحدة فقط: IGNORE
4. إذا كان خبراً مهماً، أعد صياغته باختصار واحترافية بالتنسيق التالي حصراً:
🔴 **عاجل | [اسم الدولة]**
[نص الخبر بسطرين إلى 3 أسطر بالعامية الراقية أو فصحى مبسطة وسريعة]

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
    """قراءة آخر منشور من القناة عبر المتصفح"""
    url = f"https://t.me/s/{channel_name}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message_text")
        if not messages:
            return None
        return messages[-1].get_text(separator="\n").strip()
    except Exception as e:
        print(f"خطأ بقراءة القناة {channel_name}: {e}")
        return None

def news_loop():
    """حلقة مراقبة الأخبار المستمرة"""
    print("🚀 البوت بدأ العمل ومراقبة القنوات...")
    send_to_telegram("🟢 **تم تشغيل نظام التغطية الإخبارية السحابي بنجاح.**")

    while True:
        for channel in SOURCE_CHANNELS:
            raw_news = scrape_channel(channel)
            
            if raw_news and (raw_news not in posted_messages):
                posted_messages.add(raw_news)
                
                if len(posted_messages) > 300:
                    posted_messages.clear()

                print(f"📌 وصل خبر جديد من {channel}، جاري معالجته...")
                
                try:
                    ai_response = model.generate_content(PROMPT + raw_news)
                    final_text = ai_response.text.strip()
                    
                    if "IGNORE" not in final_text:
                        send_to_telegram(final_text)
                        print("✅ تم نشر الخبر بنجاح!")
                    else:
                        print("❌ تم تجاهل الخبر (إعلان أو غير مناسب).")
                        
                except Exception as e:
                    print(f"خطأ أثناء معالجة الذكاء الاصطناعي: {e}")

            time.sleep(5)

        time.sleep(120)

# سيرفر بسيط ليرضي موقع الاستضافة السحابي
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
