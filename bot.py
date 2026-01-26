import telebot
from telebot import types
import os
import time
import datetime
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') # এনভায়রনমেন্ট ভ্যারিয়েবল না থাকলে সরাসরি টোকেন দিন
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"

# --- FIREBASE INITIALIZATION ---
try:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://file-manager-bot-default-rtdb.firebaseio.com/' 
    })
    ref = db.reference('/')
except Exception as e:
    print(f"Firebase Error: {e}")

# ফোল্ডার চেক
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE FUNCTIONS ---
def add_user(uid, first_name):
    user_ref = ref.child('users').child(str(uid))
    if not user_ref.get():
        user_ref.set({
            'id': uid,
            'name': first_name,
            'joined_at': str(datetime.datetime.now()),
            'status': 'active'
        })
        return True
    return False

def is_banned(uid):
    ban_ref = ref.child('banned').child(str(uid)).get()
    return ban_ref is not None

def get_total_users():
    users = ref.child('users').get()
    return len(users) if users else 0

# --- HELPERS ---
def get_current_files():
    try:
        return [f.name for f in os.scandir(FILES_DIR) if f.is_file()]
    except: return []

def check_join(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except: return False
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
    if is_banned(uid):
        bot.send_message(message.chat.id, "❌ You are banned from using this bot.")
        return
    
    # Firebase-এ ইউজার সেভ
    is_new = add_user(uid, message.from_user.first_name)
    if is_new:
        try: bot.send_message(LOG_CHANNEL, f"🆕 <b>New User Joined!</b>\nName: {message.from_user.first_name}\nID: <code>{uid}</code>")
        except: pass

    if check_join(uid):
        bot.send_photo(message.chat.id, BANNER_URL, 
                       caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\nPremium files are ready for you. Use /list to see all commands.",
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
            bot.answer_callback_query(call.id, "No files found!")
            return
        
        mk = types.InlineKeyboardMarkup(row_width=2)
        for f in files:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        
        bot.edit_message_caption(f"📂 <b>Available Premium Files:</b> ({len(files)})", call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data.startswith("dl_"):
        fname = call.data.replace("dl_", "")
        send_premium_file(call.message, fname)

    elif call.data == "my_stats":
        total = get_total_users()
        stat_text = f"📊 <b>Your Account Stats:</b>\n\n👤 Name: {call.from_user.first_name}\n🆔 ID: <code>{uid}</code>\n🌍 Total Bot Users: {total}"
        bot.edit_message_caption(stat_text, call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    elif call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    elif call.data == "admin_panel" and uid == ADMIN_ID:
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("📣 Broadcast", callback_data="adm_bc"),
            types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
            types.InlineKeyboardButton("✅ Unban User", callback_data="adm_unban"),
            types.InlineKeyboardButton("📊 Users List", callback_data="adm_list")
        )
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        bot.edit_message_caption("🔐 <b>Admin Control Panel</b>", call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "📩 Send me the message for broadcast:")
        bot.register_next_step_handler(m, broadcast_step)

    elif call.data == "adm_ban" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "🚫 Send the User ID to ban:")
        bot.register_next_step_handler(m, ban_step)

# --- FILE SENDING LOGIC ---
def send_premium_file(message, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(message.chat.id, 'upload_document')
        with open(path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"💎 <b>File:</b> <code>{fname}</code>\n🚀 <b>By @DUModZ</b>")
    else:
        bot.send_message(message.chat.id, "⚠️ File not found on server.")

# --- ADMIN STEPS ---
def broadcast_step(message):
    users = ref.child('users').get()
    if not users: return
    count = 0
    for uid_str in users:
        try:
            bot.send_message(int(uid_str), f"📢 <b>Important Announcement:</b>\n\n{message.text}")
            count += 1
            time.sleep(0.1)
        except: pass
    bot.reply_to(message, f"✅ Broadcast finished. Sent to {count} users.")

def ban_step(message):
    try:
        target_id = message.text.strip()
        ref.child('banned').child(target_id).set(True)
        bot.reply_to(message, f"🚫 User {target_id} has been banned.")
    except:
        bot.reply_to(message, "❌ Error in banning.")

# --- AUTO SEARCH & COMMANDS ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    if is_banned(uid) or not check_join(uid): return

    txt = message.text.lower()
    files = get_current_files()

    # /command style access (e.g., /file_name)
    if txt.startswith('/'):
        cmd = txt[1:]
        for f in files:
            if cmd == os.path.splitext(f.lower())[0]:
                send_premium_file(message, f)
                return

    # Search Logic
    matches = [f for f in files if txt in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 <b>Found {len(matches)} matching files:</b>", reply_markup=mk)

# --- START BOT ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot with Firebase is running...")
    bot.infinity_polling(skip_pending=True)
