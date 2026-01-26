import telebot
from telebot import types
import os
import json
import time
from datetime import datetime

# --- SYSTEM CONFIGURATION ---
# আপনার সেনসিটিভ তথ্যগুলো এখানে দিন
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"

REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "database.json"
BAN_FILE = "blacklist.json"

# ফোল্ডার এবং ফাইল সেটআপ
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)

def initialize_storage():
    for file in [DB_FILE, BAN_FILE]:
        if not os.path.exists(file):
            with open(file, 'w') as f: json.dump([], f)

initialize_storage()

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE ENGINE ---
def get_db(file):
    try:
        with open(file, 'r') as f: return json.load(f)
    except: return []

def save_db(file, data):
    with open(file, 'w') as f: json.dump(data, f, indent=4)

def is_joined(uid):
    for channel in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(channel, uid).status
            if status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- KEYBOARDS & MENUS ---

# ১. স্থায়ী মেনু বাটন (Reply Keyboard)
def persistent_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📂 Premium Files")
    btn2 = types.KeyboardButton("👤 My Profile")
    btn3 = types.KeyboardButton("🌐 Website")
    btn4 = types.KeyboardButton("🔍 Search File")
    markup.add(btn1, btn2, btn3, btn4)
    if uid == ADMIN_ID:
        markup.add(types.KeyboardButton("🔐 Admin Panel"))
    return markup

# ২. কমান্ড মেনু (Telegram Sidebar Menu)
def set_bot_commands():
    bot.set_my_commands([
        types.BotCommand("start", "🚀 Start the Bot"),
        types.BotCommand("files", "📂 View All Files"),
        types.BotCommand("profile", "👤 View My Info"),
        types.BotCommand("help", "🆘 Get Assistance")
    ])

# ৩. ইনলাইন বাটন (Inline Keyboard)
def inline_files(files):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in files[:15]:
        markup.add(types.InlineKeyboardButton(f"📥 {f.upper()}", callback_data=f"get_{f}"))
    markup.add(types.InlineKeyboardButton("🔄 Refresh Repository", callback_data="refresh_files"))
    return markup

# --- CORE FUNCTIONS ---
def send_visual_action(chat_id, action="typing"):
    bot.send_chat_action(chat_id, action)

def scan_files():
    return sorted([f.name for f in os.scandir(FILES_DIR) if f.is_file()])

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    if uid in get_db(BAN_FILE): return

    # ইউজার রেজিস্ট্রেশন
    db = get_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)

    set_bot_commands()
    send_visual_action(message.chat.id)

    if is_joined(uid):
        bot.send_photo(
            message.chat.id, BANNER,
            caption=f"👋 <b>Hello {message.from_user.first_name}!</b>\n\nWelcome to <b>DUModZ Premium System</b>. Your one-stop destination for premium resources.",
            reply_markup=persistent_menu(uid)
        )
    else:
        force_join(message.chat.id)

def force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\n\nYou must join our official channels to access premium files.", reply_markup=mk)

# --- REPLY KEYBOARD LOGIC ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    if uid in get_db(BAN_FILE): return
    if not is_joined(uid): return force_join(message.chat.id)

    text = message.text
    send_visual_action(message.chat.id)

    if text == "📂 Premium Files":
        files = scan_files()
        if not files:
            bot.reply_to(message, "📂 <b>Repository is currently empty!</b>")
        else:
            bot.send_message(message.chat.id, f"✅ <b>Synced! {len(files)} files found.</b>\nSelect a file to download:", reply_markup=inline_files(files))

    elif text == "👤 My Profile":
        db = get_db(DB_FILE)
        user = next((u for u in db if u['id'] == uid), None)
        info = f"👤 <b>Account Info</b>\n\n🆔 ID: <code>{uid}</code>\n📅 Joined: {user['date'] if user else 'N/A'}\n🛡️ Rank: Premium Member"
        bot.reply_to(message, info)

    elif text == "🌐 Website":
        bot.reply_to(message, f"🔗 <b>Visit our official site:</b>\n{WEBSITE}")

    elif text == "🔍 Search File":
        m = bot.reply_to(message, "🔍 <b>Type the file name or keyword:</b>")
        bot.register_next_step_handler(m, process_search)

    elif text == "🔐 Admin Panel" and uid == ADMIN_ID:
        admin_mk = types.InlineKeyboardMarkup(row_width=2)
        admin_mk.add(
            types.InlineKeyboardButton("📣 Broadcast", callback_data="adm_bc"),
            types.InlineKeyboardButton("📊 Stats", callback_data="adm_st")
        )
        admin_mk.add(types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"))
        bot.send_message(message.chat.id, "🔐 <b>Admin Control Panel</b>", reply_markup=admin_mk)

    elif text.startswith('/'): # কমান্ড হিসেবে ফাইল খোঁজা
        cmd = text[1:].lower()
        for f in scan_files():
            if cmd == os.path.splitext(f.lower())[0]:
                send_file(message.chat.id, f)
                return

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    
    if call.data == "verify":
        if is_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

    elif call.data == "refresh_files":
        files = scan_files()
        bot.edit_message_text(f"🔄 <b>Repository Refreshed!</b>\nTotal: {len(files)} files found.", 
                              call.message.chat.id, call.message.message_id, reply_markup=inline_files(files))

    elif call.data.startswith("get_"):
        fname = call.data.replace("get_", "")
        send_file(call.message.chat.id, fname)

    elif call.data == "adm_st" and uid == ADMIN_ID:
        u_count = len(get_db(DB_FILE))
        f_count = len(scan_files())
        bot.answer_callback_query(call.id, f"Users: {u_count} | Files: {f_count}", show_alert=True)

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "📣 <b>Send the message you want to broadcast:</b>\n(Supports Text, Photo, Video)")
        bot.register_next_step_handler(m, broadcast_engine)

# --- ENGINE FUNCTIONS ---
def process_search(message):
    query = message.text.lower()
    files = scan_files()
    matches = [f for f in files if query in f.lower()]
    
    if matches:
        bot.send_message(message.chat.id, f"🔍 <b>Found {len(matches)} results:</b>", reply_markup=inline_files(matches))
    else:
        bot.send_message(message.chat.id, "❌ <b>No files match your search!</b>")

def send_file(chat_id, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        send_visual_action(chat_id, "upload_document")
        tmp = bot.send_message(chat_id, "📡 <b>Processing file for secure download...</b>")
        try:
            with open(path, 'rb') as f:
                bot.send_document(chat_id, f, caption=f"💎 <b>File:</b> <code>{fname}</code>\n🛡️ <b>Securely delivered by @DUModZ</b>")
            bot.delete_message(chat_id, tmp.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, tmp.message_id)
    else:
        bot.send_message(chat_id, "⚠️ File not found in server.")

def broadcast_engine(message):
    users = get_db(DB_FILE)
    count = 0
    bot.send_message(message.chat.id, f"🚀 <b>Broadcast started for {len(users)} users...</b>")
    
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            count += 1
            time.sleep(0.1)
        except: pass
    
    bot.send_message(message.chat.id, f"✅ <b>Successfully sent to {count} users.</b>")

# --- STEALTH BOOT ---
if __name__ == "__main__":
    # হোস্টিং সংক্রান্ত কোনো প্রিন্ট নেই
    try:
        bot.send_message(LOG_CHANNEL, "🟢 <b>DUModZ System: Online</b>\nStatus: 100% Secure\nSync: Active")
    except: pass
    bot.infinity_polling(skip_pending=True)
