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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9"
}

# ================= قاموس التبديل الصحفي الضخم (قرابة 300 كلمة) =================
SYNONYMS = {
    # أفعال القول والإعلان والتصريح
    r"\bأعلن\b": "كشف", r"\bوأعلن\b": "وكشف", r"\bأعلنت\b": "أفادت", r"\bوأعلنت\b": "وأفادت",
    r"\bيعلن\b": "يكشف", r"\bتعلن\b": "تفيد", r"\bقال\b": "أكد", r"\bوقال\b": "وأكد",
    r"\bقالت\b": "أوضحت", r"\bوقالت\b": "وأوضحت", r"\bيقول\b": "يؤكد", r"\bتقول\b": "توضح",
    r"\bصرح\b": "بيّن", r"\bوصرح\b": "وبيّن", r"\bصرحت\b": "أشارت", r"\bوصرحت\b": "وأشارت",
    r"\bذكر\b": "أورد", r"\bوذكر\b": "وأورد", r"\bذكرت\b": "أشارت", r"\bوذكرت\b": "وأشارت",
    r"\bأفاد\b": "أوضح", r"\bوأفاد\b": "وأوضح", r"\bأفادت\b": "نقلت مصادر أن", r"\bوأفادت\b": "ونقلت مصادر أن",
    r"\bأكد\b": "شدد على أن", r"\bوأكد\b": "وشدد على أن", r"\bأكدت\b": "جددت التأكيد أن", r"\bوأكدت\b": "وجددت التأكيد أن",
    r"\bطالب\b": "دعا إلى", r"\bوطالب\b": "ودعا إلى", r"\bطالبت\b": "حثت على", r"\bوطالبت\b": "وحثت على",
    r"\bحذر\b": "نبه من", r"\bوحذر\b": "ونبه من", r"\bحذرت\b": "لوّحت بـ", r"\bوحذرت\b": "ولوّحت بـ",
    r"\bأشار\b": "لمّح إلى", r"\bوأشار\b": "ولمّح إلى", r"\bأشارت\b": "ألمحت إلى", r"\bوأشارت\b": "وألمحت إلى",
    r"\bأوضح\b": "شرح", r"\bوأوضح\b": "وشرح", r"\bأوضحت\b": "بيّنت المعطيات", r"\bوأوضحت\b": "وبيّنت المعطيات",
    r"\bكشف\b": "أماط اللثام عن", r"\bوكشف\b": "وأماط اللثام عن", r"\bكشفت\b": "أظهرت", r"\bوكشفت\b": "وأظهرت",
    r"\bتابع\b": "استطرد", r"\bوتابع\b": "واستطرد", r"\bتابعت\b": "واصلت", r"\bوتابعت\b": "وواصلت",

    # أحداث الميدان والحرب والاستهداف
    r"\bقصف\b": "استهداف وقصف", r"\bوقصف\b": "واستهداف", r"\bقصفاً\b": "ضربات مكثفة",
    r"\bاستهدف\b": "طال", r"\bواستهدف\b": "وطال", r"\bاستهدفت\b": "ضربت", r"\bواستهدفت\b": "وضربت",
    r"\bيستهدف\b": "يطال", r"\bتستهدف\b": "تطال", r"\bاستهداف\b": "قصف مباشر لـ",
    r"\bغارة\b": "ضربة جوية", r"\bوغارة\b": "وضربة جوية", r"\bغارات\b": "هجمات جوية مكثفة", r"\bوغارات\b": "وهجمات جوية",
    r"\bشن\b": "نفذ", r"\bوشن\b": "ونفذ", r"\bشنت\b": "أطلقت", r"\bوشنت\b": "وأطلقت",
    r"\bاشتباكات\b": "مواجهات مسلحة", r"\bواشتباكات\b": "ومواجهات عنيفة", r"\bمواجهات\b": "تصدٍ واشتباك",
    r"\bاندلعت\b": "نشبت", r"\bواندلعت\b": "ونشبت", r"\bانفجار\b": "دوي انفجار عنيف", r"\bوانفجار\b": "ودوي انفجار",
    r"\bانفجارات\b": "سلسلة انفجارات", r"\bوانفجارات\b": "وانفجارات متتالية",
    r"\bتصدت\b": "أحبطت", r"\bوتصدت\b": "وأحبطت", r"\bتصدى\b": "واجه", r"\bوتصدى\b": "وواجه",
    r"\bإطلاق نار\b": "رشقات نارية مكثفة", r"\bرصاص\b": "أعيرة نارية",
    r"\bتوغل\b": "تقدم بري", r"\bوتوغل\b": "وتقدم لآليات", r"\bاقتحام\b": "دهم واقتحام", r"\bواقتحام\b": "ودهم",
    r"\bاقتحمت\b": "داهمت", r"\bواقحتمت\b": "وداهمت", r"\bانسحاب\b": "تراجع ميداني", r"\bوانسحاب\b": "وتراجع",
    r"\bدمار\b": "أضرار بالغة وتدمير", r"\bودمار\b": "وأضرار مادية واسعة",

    # الضحايا والشهداء والمصابين
    r"\bاستشهاد\b": "ارتقاء", r"\bواستشهاد\b": "وارتقاء",
    r"\bشهيد\b": "شهيد ارتقى", r"\bوشهيد\b": "وشهيد",
    r"\bشهداء\b": "ضحايا وشهداء", r"\bوشهداء\b": "وشهداء أبرار",
    r"\bشهيدين\b": "شهيدين ارتقيا", r"\bوشهيدين\b": "وشهيدين",
    r"\bشهداء وجرحى\b": "ارتقاء شهداء ووقوع جرحى",
    r"\bمقتل\b": "مصرع وهلاك", r"\bومقتل\b": "ومصرع", r"\bقتلى\b": "صروع وهلكى", r"\bوقتلى\b": "وهلكى",
    r"\bإصابة\b": "جرح", r"\bوإصابة\b": "وجرح", r"\bإصابات\b": "جرحى ومصابين", r"\bوإصابات\b": "وجرحى",
    r"\bجرحى\b": "مصابين بجروح متفرقة", r"\bوجرحى\b": "ومصابين",
    r"\bجثمان\b": "جسد", r"\bجثامين\b": "أجساد الشهداء", r"\bجثث\b": "جثامين قتلى",
    r"\bمفقودين\b": "عالقين تحت الركام", r"\bومفقودين\b": "وعالقين",

    # الأسلحة والقوات والآليات
    r"\bقوات الاحتلال\b": "جيش الاحتلال", r"\bجنود الاحتلال\b": "عناصر الاحتلال",
    r"\bجيش الاحتلال\b": "القوات الإسرائيلية", r"\bقوات العدو\b": "جيش العدو",
    r"\bطائرات الاحتلال\b": "سلاح الجو الإسرائيلي", r"\bطيران الاحتلال\b": "المقاتلات الإسرائيلية",
    r"\bطائرات مسيرة\b": "طائرات درون مسيرة", r"\bمسيرة\b": "طائرة انقضاضية مسيرة", r"\bمسيرات\b": "طائرات بدون طيار",
    r"\bطائرات حربية\b": "مقاتلات حربية", r"\bمروحيات\b": "طائرات هليكوبتر هجومية",
    r"\bدبابات\b": "مدرعات ودبابات", r"\bآليات\b": "مركبات ومدرعات عسكرية",
    r"\bمدفعية\b": "سلاح المدفعية الثقيلة", r"\bقذائف\b": "حمم مدفعية وصاروخية",
    r"\bصاروخ\b": "مقذوف صاروخي", r"\bصواريخ\b": "رشقات صاروخية",
    r"\bرشقة صاروخية\b": "صلية صواريخ مكثفة", r"\bرشقة\b": "دفعة صاروخية",

    # حروف الربط والظروف والكلمات الانتقالية
    r"\bجراء\b": "إثر", r"\bبسبب\b": "على خلفية", r"\bإثر\b": "في أعقاب",
    r"\bعقب\b": "بعد وقت قصير من", r"\bفي إطار\b": "ضمن سياق", r"\bفي سياق\b": "على وقع",
    r"\bفي ظل\b": "وسط أجواء", r"\bحالياً\b": "في هذه الأثناء", r"\bالآن\b": "في هذا الوقت",
    r"\bمنذ قليل\b": "قبل قليل", r"\bبشكل مباشر\b": "بصورة مباشرة",
    r"\bالعشرات\b": "أعداد كبيرة من المواطنين", r"\bالمئات\b": "مئات الأشخاص",
    r"\bالعديد من\b": "جملة من", r"\bعدة\b": "بضعة",
    r"\bمنازل\b": "بيوت ومساكن المواطنين", r"\bمنزل\b": "مبنى سكني",
    r"\bمستشفى\b": "مجمع طبي ومستشفى", r"\bمحيط\b": "جواري وأطراف",

    # شطب أسماء القنوات والعبارات غير المرغوبة
    r"عاجل": "", r"الجزيرة": "", r"الميادين": "", r"النور": "",
    r"تابعونا": "", r"اشترك": "", r"المزيد من التفاصيل": ""
}

def clean_and_replace_synonyms(raw_text):
    """محرك التبديل المباشر بدون مقدمات وبدون أي حذف للتفاصيل"""
    # 1. إزالة الروابط والمعرفات
    text = re.sub(r'https?://\S+', '', raw_text)
    text = re.sub(r'@\w+', '', text)

    # 2. تطبيق التبديل بالقاموس الضخم
    for pattern, replacement in SYNONYMS.items():
        text = re.sub(pattern, replacement, text)

    # 3. إزالة الأسطر الفارغة الزائدة
    lines = [html.escape(line.strip()) for line in text.split("\n") if len(line.strip()) > 3]
    if not lines:
        return None

    cleaned_body = "\n\n".join(lines)
    
    # التنسيق النهائي: ترويسة + الخبر المبدل كلماته مباشرة + التوقيع
    return f"🔴 <b>NEWS | عاجل</b>\n\n{cleaned_body}"

def send_to_telegram(text, photo_url=None):
    """إرسال الخبر مع الصورة إن وجدت"""
    full_message = text + SIGNATURE
    
    if photo_url:
        try:
            print("جاري رفع الصورة للقناة...", flush=True)
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
    print("🚀 البوت بدأ العمل بنظام استبدال الكلمات الفوري (بدون مقدمات وبسرعة قصوى)...", flush=True)

    while True:
        for channel in SOURCE_CHANNELS:
            recent_items = scrape_channel(channel)
            
            for raw_news, photo_url in recent_items:
                if raw_news and len(raw_news) > 25 and (raw_news not in posted_messages):
                    posted_messages.add(raw_news)
                    
                    if len(posted_messages) > 500:
                        posted_messages.clear()

                    print(f"📥 خبر جديد من {channel}... جاري تبديل الكلمات والنشر...", flush=True)
                    
                    final_text = clean_and_replace_synonyms(raw_news)
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
