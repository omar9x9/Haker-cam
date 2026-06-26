import sqlite3
import hashlib
import random
import string

# ==================== إعدادات التشفير (نفس SALT المستخدم في البوت) ====================
SALT = "Shadow_Salt_321"  # يجب أن يكون مطابقاً لما في main.py

def hash_password(password: str) -> str:
    return hashlib.sha256((password + SALT).encode()).hexdigest()

def generate_username(index):
    """توليد اسم مستخدم فريد"""
    prefixes = ["hacker", "shadow", "phoenix", "ghost", "cyber", "agent", "knight", "wolf", "eagle", "tiger"]
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"{random.choice(prefixes)}_{suffix}"

def generate_password():
    """توليد كلمة سر قوية (8 أحرف)"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=10))

def add_users(count=100):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    users = []
    for i in range(count):
        username = generate_username(i)
        password = generate_password()
        hashed = hash_password(password)
        
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO bot_users (username, password_hash) VALUES (?, ?)",
                (username, hashed)
            )
            users.append((username, password))
        except Exception as e:
            print(f"⚠️ فشل إضافة {username}: {e}")
    
    conn.commit()
    conn.close()
    
    # طباعة القائمة
    print(f"\n✅ تم إضافة {len(users)} مستخدم بنجاح!\n")
    print("=" * 50)
    print("👤 اسم المستخدم  |  🔑 كلمة السر")
    print("=" * 50)
    for u, p in users:
        print(f"{u:15} | {p}")
    print("=" * 50)
    
    # حفظ القائمة في ملف
    with open("users_list.txt", "w", encoding="utf-8") as f:
        f.write("👤 اسم المستخدم  |  🔑 كلمة السر\n")
        f.write("=" * 40 + "\n")
        for u, p in users:
            f.write(f"{u:15} | {p}\n")
    
    print("\n📁 تم حفظ القائمة في ملف users_list.txt")

if __name__ == "__main__":
    add_users(100)
