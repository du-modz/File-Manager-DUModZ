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

# Ensure Environment
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)

def init_db(file, default):
    if not os.path.exists(file):
        with open(file, 'w') as f: json.dump(default, f)

init_db(DB_FILE, [])
init_db(BANNED_FILE, [])

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- CORE LOGIC ---
def get_current_files():
    """সরাসরি ডিস্ক থেকে লেটেস্ট ফাইল স্ক্যান করে"""
    try:
        return sorted([f.name for f in os.scandir(FILES_DIR) if f.is_file()])
    except: return []

def load_db(path):
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

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

# --- KEYBOARDS ---
def main_markup(uid):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📂 PREMIUM FILES", callback_data="sync_files"),
        types.InlineKeyboardButton("🌐 WEBSITE", url=WEBSITE_URL)
    )
    mk.add(
        types.InlineKeyboardButton("👤 PROFILE", callback_data="my_stats"),
        types.InlineKeyboardButton("👨‍💻 DEV", url="https://t.me/DarkUnkwon")
    )
    mk.add(types.InlineKeyboardButton("🔄 REFRESH REPOSITORY", callback_data="sync_files"))
    if uid == ADMIN_ID:
        mk.add(types.InlineKeyboardButton("🔐 ADMIN PANEL", callback_data="admin_panel"))
    return mk

def admin_markup():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📣 BROADCAST", callback_data="adm_bc"),
        types.InlineKeyboardButton("📊 STATS", callback_data="adm_stats")
    )
    mk.add(
        types.InlineKeyboardButton("🚫 BAN", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ UNBAN", callback_data="adm_unban")
    )
    mk.add(types.InlineKeyboardButton("🔙 BACK", callback_data="home"))
    return mk

# --- ANIMATION HELPERS ---
def edit_status(call, text, markup=None):
    try:
        bot.edit_message_caption(
            caption=text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except: pass

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if is_banned(uid): return
    
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Save/Update User
    db = load_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().strftime("%Y-%m-%d"))})
        save_db(DB_FILE, db)

    if check_join(uid):
        bot.send_photo(
            message.chat.id, BANNER_URL, 
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\n\nI am the official <b>DUModZ</b> file manager. High-speed premium files are waiting for you.",
            reply_markup=main_markup(uid)
        )
    else:
        force_join_menu(message.chat.id)

def force_join_menu(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the files.", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    uid = call.from_user.id
    if is_banned(uid): return

    if call.data == "home":
        edit_status(call, "🏠 <b>Main Menu</b>\nSelect an option below:", main_markup(uid))

    elif call.data == "verify":
        if check_join(uid):
            bot.answer_callback_query(call.id, "✅ Access Granted!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

    elif call.data == "sync_files":
        bot.answer_callback_query(call.id, "🔄 Syncing database...")
        edit_status(call, "📂 <b>Scanning Repository...</b>\n<i>Please wait while we fetch latest files.</i>")
        time.sleep(1) # Visual effect
        
        files = get_current_files()
        if not files:
            edit_status(call, "📂 <b>Repository is Empty!</b>\nAdd files to 'files' folder.", main_markup(uid))
            return
        
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:20]: # Limit 20 for UI clean
            mk.add(types.InlineKeyboardButton(f"📥 {f.upper()}", callback_data=f"dl_{f}"))
        
        mk.add(types.InlineKeyboardButton("🔄 REFRESH LIST", callback_data="sync_files"))
        mk.add(types.InlineKeyboardButton("🔙 BACK", callback_data="home"))
        
        edit_status(call, f"✅ <b>Files Synced!</b>\nTotal {len(files)} premium files found in server.", mk)

    elif call.data.startswith("dl_"):
        fname = call.data.replace("dl_", "")
        send_file_logic(call.message, fname)

    elif call.data == "my_stats":
        db = load_db(DB_FILE)
        u_info = next((u for u in db if u['id'] == uid), None)
        msg = f"👤 <b>Your Statistics</b>\n\n🆔 <b>ID:</b> <code>{uid}</code>\n📅 <b>Join Date:</b> {u_info['date'] if u_info else 'N/A'}\n⚡ <b>Status:</b> Active"
        edit_status(call, msg, main_markup(uid))

    # --- ADMIN ACTIONS ---
    elif call.data == "admin_panel" and uid == ADMIN_ID:
        edit_status(call, "🔐 <b>Admin Control Center</b>\nManage users and system settings.", admin_markup())

    elif call.data == "adm_stats" and uid == ADMIN_ID:
        u_count = len(load_db(DB_FILE))
        f_count = len(get_current_files())
        bot.answer_callback_query(call.id, f"📊 Stats:\nUsers: {u_count}\nFiles: {f_count}", show_alert=True)

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "📣 <b>Broadcast System</b>\nSend any message (Text/Photo/Video) to all users:")
        bot.register_next_step_handler(m, run_broadcast)

# --- ADVANCED FILE SENDING ---
def send_file_logic(message, fname):
    # Security Check: Prevent Directory Traversal
    if ".." in fname or "/" in fname: return
    
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(message.chat.id, 'upload_document')
        prog = bot.send_message(message.chat.id, f"⚡ <b>Preparing</b> <code>{fname}</code>...")
        
        try:
            with open(path, 'rb') as f:
                bot.send_document(
                    message.chat.id, f, 
                    caption=f"💎 <b>Premium File:</b> <code>{fname}</code>\n🚀 <b>Uploaded By:</b> @DUModZ\n🛡️ <b>Secure Download</b>",
                    reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🌐 Join Website", url=WEBSITE_URL))
                )
            bot.delete_message(message.chat.id, prog.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ <b>Error:</b> {str(e)}", message.chat.id, prog.message_id)
    else:
        bot.send_message(message.chat.id, "⚠️ <b>File Error!</b> This file might have been removed. Please Refresh.")

# --- BROADCAST SYSTEM (COPY LOGIC) ---
def run_broadcast(message):
    users = load_db(DB_FILE)
    success = 0
    fail = 0
    bot.send_message(message.chat.id, f"🚀 <b>Starting Broadcast to {len(users)} users...</b>")
    
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
            time.sleep(0.1) # Flood protection
        except:
            fail += 1
            
    bot.send_message(message.chat.id, f"✅ <b>Broadcast Completed!</b>\n\n🟢 Success: {success}\n🔴 Failed: {fail}")

# --- SEARCH & TEXT COMMANDS ---
@bot.message_handler(func=lambda m: True)
def text_engine(message):
    uid = message.from_user.id
    if is_banned(uid) or not check_join(uid): return

    query = message.text.lower()
    files = get_current_files()
    
    # Check if command like /file_name
    if query.startswith('/'):
        cmd = query[1:]
        for f in files:
            if cmd == os.path.splitext(f.lower())[0]:
                send_file_logic(message, f)
                return

    # Search Logic
    results = [f for f in files if query in f.lower()]
    if results:
        bot.send_chat_action(message.chat.id, 'typing')
        mk = types.InlineKeyboardMarkup(row_width=1)
        for r in results[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {r}", callback_data=f"dl_{r}"))
        bot.reply_to(message, f"🔍 <b>Found {len(results)} matches:</b>", reply_markup=mk)
    elif query == "/list":
        res_text = "📂 <b>Available Repository:</b>\n\n"
        for f in files: res_text += f"🔹 <code>/{os.path.splitext(f)[0]}</code>\n"
        bot.reply_to(message, res_text)

# --- BOOT UP ---
if __name__ == "__main__":
    print("---------------------------------------")
    print("💎 DUModZ ADVANCED PRO SYSTEM ONLINE")
    print("📡 Dynamic Sync Engine: ACTIVE")
    print("---------------------------------------")
    try:
        bot.send_message(LOG_CHANNEL, "🟢 <b>Bot Online</b>\nSystem: <b>Smooth & Secure</b>\nSync: <b>Enabled</b>")
    except: pass
    bot.infinity_polling(skip_pending=True)
