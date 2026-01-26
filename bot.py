import telebot
from telebot import types
import time
import os
import json
from datetime import datetime

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"

REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "users.json"
BANNED_FILE = "banned.json"

# Ensure directories & files exist
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)
def init_db(file, default):
    if not os.path.exists(file):
        with open(file, 'w') as f: json.dump(default, f)

init_db(DB_FILE, [])
init_db(BANNED_FILE, [])

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- UTILITY FUNCTIONS ---
def get_current_files():
    try:
        return [f.name for f in os.scandir(FILES_DIR) if f.is_file()]
    except: return []

def load_db(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=3)

def is_banned(uid):
    return uid in load_db(BANNED_FILE)

def check_join(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def send_action(chat_id, action="typing"):
    bot.send_chat_action(chat_id, action)

# --- KEYBOARDS ---
def main_markup(uid):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📂 PREMIUM FILES", callback_data="sync_files"),
        types.InlineKeyboardButton("🌐 WEBSITE", url=WEBSITE_URL)
    )
    mk.add(
        types.InlineKeyboardButton("👤 MY PROFILE", callback_data="my_stats"),
        types.InlineKeyboardButton("👨‍💻 DEVELOPER", url="https://t.me/DarkUnkwon")
    )
    mk.add(types.InlineKeyboardButton("📜 FILE LIST", callback_data="list_files"))
    if uid == ADMIN_ID:
        mk.add(types.InlineKeyboardButton("🔐 ADMIN PANEL", callback_data="admin_panel"))
    return mk

def admin_markup():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📣 BROADCAST", callback_data="adm_bc"),
        types.InlineKeyboardButton("📊 BOT STATS", callback_data="adm_stats")
    )
    mk.add(
        types.InlineKeyboardButton("🚫 BAN USER", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ UNBAN", callback_data="adm_unban")
    )
    mk.add(types.InlineKeyboardButton("🔙 BACK HOME", callback_data="home"))
    return mk

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if is_banned(uid): return
    
    send_action(message.chat.id)
    
    # Save User
    db = load_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)

    if check_join(uid):
        bot.send_photo(message.chat.id, BANNER_URL, 
                       caption=f"🔥 <b>Welcome, {message.from_user.first_name}!</b>\n\nI am your Premium File Downloader Bot. Use the buttons below to explore.",
                       reply_markup=main_markup(uid))
    else:
        show_force_join(message.chat.id)

def show_force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 JOIN {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 VERIFY JOIN", callback_data="verify"))
    bot.send_message(chat_id, "❌ <b>Access Denied!</b>\n\nYou must join all our channels to use this bot.", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    if is_banned(uid): 
        bot.answer_callback_query(call.id, "You are banned!", show_alert=True)
        return

    if call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    elif call.data == "verify":
        if check_join(uid):
            bot.answer_callback_query(call.id, "✅ Verified!", show_alert=False)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "⚠️ Please join all channels first!", show_alert=True)

    elif call.data == "sync_files":
        send_action(call.message.chat.id)
        files = get_current_files()
        if not files:
            bot.answer_callback_query(call.id, "No files found in server!")
            return
        
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]: # Show last 15 files
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        mk.add(types.InlineKeyboardButton("🔙 BACK", callback_data="home"))
        
        bot.edit_message_caption(f"📂 <b>Premium Repository</b>\nFound {len(files)} files available for download.", 
                                 call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data.startswith("dl_"):
        fname = call.data.replace("dl_", "")
        send_premium_file(call.message, fname)

    elif call.data == "my_stats":
        db = load_db(DB_FILE)
        user_data = next((u for u in db if u['id'] == uid), None)
        msg = f"👤 <b>User Profile</b>\n\n🆔 <b>ID:</b> <code>{uid}</code>\n📅 <b>Joined:</b> {user_data['date'] if user_data else 'N/A'}\n🌟 <b>Status:</b> Premium User"
        bot.edit_message_caption(msg, call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    # --- ADMIN CALLBACKS ---
    elif call.data == "admin_panel" and uid == ADMIN_ID:
        bot.edit_message_caption("🔐 <b>Welcome Boss!</b>\nSelect an administrative task below.", call.message.chat.id, call.message.message_id, reply_markup=admin_markup())

    elif call.data == "adm_stats" and uid == ADMIN_ID:
        users = len(load_db(DB_FILE))
        files = len(get_current_files())
        bot.answer_callback_query(call.id, f"📊 Users: {users} | Files: {files}", show_alert=True)

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "📩 <b>Send me anything to broadcast:</b>\n(Text, Photo, Video, or File)")
        bot.register_next_step_handler(m, process_broadcast)

# --- FILE SENDING ENGINE ---
def send_premium_file(message, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        send_action(message.chat.id, "upload_document")
        status_msg = bot.send_message(message.chat.id, f"⏳ <b>Encrypting & Preparing:</b> <code>{fname}</code>...")
        
        try:
            with open(path, 'rb') as f:
                bot.send_document(
                    message.chat.id, f, 
                    caption=f"💎 <b>File:</b> <code>{fname}</code>\n🚀 <b>Speed:</b> Max\n🛡️ <b>Scan:</b> Clean\n\n@DUModZ",
                    thumb=BANNER_URL
                )
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ <b>Error:</b> {e}", message.chat.id, status_msg.message_id)
    else:
        bot.send_message(message.chat.id, "⚠️ <b>File not found!</b> Please wait for sync.")

# --- ADVANCED BROADCAST (ANY MEDIA) ---
def process_broadcast(message):
    users = load_db(DB_FILE)
    success = 0
    fail = 0
    bot.send_message(message.chat.id, f"📣 <b>Broadcast Started...</b> Users: {len(users)}")
    
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
            time.sleep(0.1) # Flood prevention
        except:
            fail += 1
            
    bot.send_message(message.chat.id, f"✅ <b>Broadcast Finished!</b>\n\n🟢 Success: {success}\n🔴 Failed: {fail}")

# --- TEXT SEARCH & COMMANDS ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    if is_banned(uid) or not check_join(uid): return

    txt = message.text.lower()
    send_action(message.chat.id)

    if txt == "/list":
        files = get_current_files()
        res = "📂 <b>Available Files:</b>\n\n"
        for f in files: res += f"🔹 <code>/{os.path.splitext(f)[0]}</code>\n"
        bot.reply_to(message, res)
        return

    # Search Logic
    files = get_current_files()
    matches = [f for f in files if txt in f.lower()]
    
    if matches:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 <b>Search Results ({len(matches)}):</b>", reply_markup=mk)
    else:
        # Check if it's a command like /filename
        if txt.startswith('/'):
            cmd = txt[1:]
            for f in files:
                if cmd == os.path.splitext(f.lower())[0]:
                    send_premium_file(message, f)
                    return
        bot.reply_to(message, "❌ <b>No files found!</b> Try another keyword.")

# --- BOT STARTUP ---
if __name__ == "__main__":
    print("---------------------------------------")
    print("🚀 DUModZ ADVANCED SYSTEM IS ONLINE")
    print("✨ Developed by: @DarkUnkwon")
    print("---------------------------------------")
    try:
        bot.send_message(LOG_CHANNEL, f"🟢 <b>Bot Rebooted!</b>\n⏰ Time: {datetime.now().strftime('%H:%M:%S')}\nStatus: 𝗥𝘂𝗻𝗻𝗶𝗻𝗴 ✅")
    except: pass
    bot.infinity_polling(skip_pending=True)
