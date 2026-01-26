import telebot
from telebot import types
import os
import time
import datetime
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') or "8501641088:AAGoN3in84hJAeRTWmmmG0Omj_50oUmf54E"
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"

# --- FIREBASE INITIALIZATION (FIXED) ---
ref = None
try:
    if os.path.exists("firebase-key.json"):
        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://file-manager-bot-default-rtdb.firebaseio.com/' 
        })
        ref = db.reference('/')
        print("✅ Firebase Connected Successfully!")
    else:
        print("❌ Error: 'firebase-key.json' not found! Database won't work.")
except Exception as e:
    print(f"❌ Firebase Initialization Error: {e}")

# ফোল্ডার চেক
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE FUNCTIONS (SAFETY ADDED) ---
def add_user(uid, first_name):
    if ref:
        try:
            user_ref = ref.child('users').child(str(uid))
            if not user_ref.get():
                user_ref.set({
                    'id': uid,
                    'name': first_name,
                    'joined_at': str(datetime.datetime.now()),
                    'status': 'active'
                })
                return True
        except Exception as e:
            print(f"DB Error: {e}")
    return False

def is_banned(uid):
    if ref:
        try:
            ban_ref = ref.child('banned').child(str(uid)).get()
            return ban_ref is not None
        except: return False
    return False

# --- HELPERS ---
def get_current_files():
    try:
        return [f.name for f in os.scandir(FILES_DIR) if f.is_file()]
    except: return []

def check_join(uid):
    # যদি চ্যানেল লিস্ট খালি থাকে বা চেক করার প্রয়োজন না হয় তবে True দিন
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except Exception as e:
            print(f"Join Check Error for {ch}: {e}")
            # যদি বট চ্যানেলে এডমিন না থাকে তবে এই চেকটি কাজ করবে না
            continue 
    return True

# --- KEYBOARDS ---
def main_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 Premium Files", callback_data="sync_files"),
        types.InlineKeyboardButton("🌐 Website", url=WEBSITE_URL)
    )
    markup.add(
        types.InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
        types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon")
    )
    if uid == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    
    print(f"--- Start Command Received from {name} ({uid}) ---")

    if is_banned(uid):
        bot.send_message(message.chat.id, "❌ You are banned from using this bot.")
        return
    
    add_user(uid, name)

    if check_join(uid):
        bot.send_photo(message.chat.id, BANNER_URL, 
                       caption=f"🚀 <b>Welcome {name}!</b>\nPremium files are ready for you.\n\nUse /list to see all files.",
                       reply_markup=main_markup(uid))
    else:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for ch in REQUIRED_CHANNELS:
            mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        mk.add(types.InlineKeyboardButton("🔄 Verify", callback_data="verify"))
        bot.send_photo(message.chat.id, BANNER_URL, caption="⚠️ <b>Please join our channels to unlock the bot!</b>", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    if is_banned(uid): return

    if call.data == "verify":
        if check_join(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.edit_message_caption("🔓 <b>Access Granted!</b>", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))
        else:
            bot.answer_callback_query(call.id, "❌ Please join all channels first!", show_alert=True)

    elif call.data == "sync_files":
        files = get_current_files()
        if not files:
            bot.answer_callback_query(call.id, "No files found in folder!")
            return
        
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        
        bot.edit_message_caption(f"📂 <b>Available Premium Files:</b> ({len(files)})", call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data.startswith("dl_"):
        fname = call.data.replace("dl_", "")
        send_premium_file(call.message, fname)

    elif call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

# --- FILE SENDING LOGIC ---
def send_premium_file(message, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(message.chat.id, 'upload_document')
        with open(path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"💎 <b>File:</b> <code>{fname}</code>\n🚀 <b>By @DUModZ</b>")
    else:
        bot.send_message(message.chat.id, "⚠️ File not found on server.")

# --- START BOT ---
if __name__ == "__main__":
    print("---------------------------------------")
    print("🚀 DUModZ Bot System is Starting...")
    print("---------------------------------------")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Critical Error: {e}")
        time.sleep(5)
