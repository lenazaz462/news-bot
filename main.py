import time
import re
import html
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def send_to_telegram(text, photo_url=None):
    """إرسال الخبر مع الصورة الحقيقية"""
    full_message = text + SIGNATURE
    
    if photo_url:
        try:
            print(f"جاري رفع الصورة للقناة...", flush=True)
            img_res = requests.get(photo_url, headers=HEADERS, timeout=10)
            if img_res.status_code == 200 and len(img_res.content) > 5000:
                caption_text = full_message if len(full_message) <= 1024 else full_message[:1020] + "..."
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                files = {'photo': ('news.jpg', img_res.content, 'image/jpeg')}
                data = {'chat_id': TARGET_CHANNEL, 'caption': caption_text, 'parse_mode': 'HTML'}
                
                r = requests.post(url, data=data, files=files, timeout=15)
                if r.status_code == 200:
                    print("✅ تم رفع الصورة مع الخبر بنجاح!", flush=True)
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

def free_ai_rephrase(raw_text):
    """إعادة صياغة سريعة بذكاء اصطناعي مفتوح مع مهلة 25 ثانية"""
    clean_input = re.sub(r'https?://\S+', '', raw_text)
    clean_input = re.sub(r'@\w+', '', clean_input).replace("تابعونا", "").replace("اشترك", "").strip()
    
    prompt = (
        "أنت محرر صحفي محترف. أعد صياغة هذا الخبر بأسلوب صحفي جديد كلياً ومحترف مع الحفاظ على كل التفاصيل والأسماء بدقة وبدون اختصار. "
        "احذف أي أسماء قنوات أو إعلانات، وابدأ المنشور حصراً بـ 🔴 <b>NEWS | عاجل</b>:\n\n" + clean_input
    )
    
    # المحاولة الأولى عبر سيرفر الذكاء الاصطناعي السريع
    try:
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "mistral"  # موديل سريع جداً واستجابته فورية بالعربي
        }
        res = requests.post(url, json=payload, timeout=25) # زيادة المهلة لـ 25 ثانية
        if res.status_code == 200 and len(res.text) > 30:
            print("✨ نجح الذكاء الاصطناعي في إعادة الصياغة بالكامل وبدون أخطاء!", flush=True)
            return res.text.strip()
    except Exception as e:
        print(f"تم استخدام الصياغة المباشرة بسبب الضغط: {e}", flush=True)

    # في حال التأخر الشديد، صياغة سريعة بدون إعلانات
    lines = [html.escape(line.strip()) for line in clean_input.split("\n") if line.strip()]
    return f"🔴 <b>NEWS | عاجل</b>\n\n" + "\n\n".join(lines)

def scrape_channel(channel_name):
    """سحب النصوص والصور"""
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
    print("🚀 البوت يعمل الآن بأقصى سرعة مع الصياغة الذكية المحدثة...", flush=True)

    while True:
        for channel in SOURCE_CHANNELS:
            recent_items = scrape_channel(channel)
            
            for raw_news, photo_url in recent_items:
                if raw_news and len(raw_news) > 25 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 500:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}... جاري الصياغة الفورية...", flush=True)
                    
                    final_text = free_ai_rephrase(raw_news)
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
