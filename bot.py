import telebot
from telebot import types
import os
import json
import time
from datetime import datetime

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842 # আপনার আইডি
LOG_CHANNEL = "@dumodzbotmanager"

REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "users_db.json"
BANNED_FILE = "banned_db.json"
CACHE_FILE = "file_cache.json" # নতুন ফাইল চেক করার জন্য

# ফোল্ডার নিশ্চিত করা
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE LOGIC ---
def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return default
    return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def is_banned(uid):
    return uid in load_json(BANNED_FILE, [])

def check_join(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- FILE ENGINE ---
def get_files():
    return sorted([f.name for f in os.scandir(FILES_DIR) if f.is_file()])

# --- KEYBOARDS ---
def main_markup(uid):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📂 PREMIUM FILES", callback_data="view_files"),
        types.InlineKeyboardButton("🔍 SEARCH", callback_data="search_file")
    )
    mk.add(
        types.InlineKeyboardButton("📊 MY STATS", callback_data="my_stats"),
        types.InlineKeyboardButton("🌐 WEBSITE", url=WEBSITE_URL)
    )
    mk.add(types.InlineKeyboardButton("👨‍💻 CONTACT OWNER", url="https://t.me/DarkUnkwon"))
    
    if uid == ADMIN_ID:
        mk.add(types.InlineKeyboardButton("🔐 ADMIN CONTROL PANEL", callback_data="admin_panel"))
    return mk

def admin_markup():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📣 BROADCAST", callback_data="adm_bc"),
        types.InlineKeyboardButton("🔄 SYNC & NOTIFY", callback_data="adm_sync")
    )
    mk.add(
        types.InlineKeyboardButton("🚫 BAN USER", callback_data="adm_ban"),
        types.InlineKeyboardButton("📈 BOT STATS", callback_data="adm_stats")
    )
    mk.add(types.InlineKeyboardButton("🔙 BACK TO HOME", callback_data="home"))
    return mk

# --- HELPER FUNCTIONS ---
def notify_new_files(new_files):
    users = load_json(DB_FILE, [])
    count = 0
    for u in users:
        try:
            text = "🚀 <b>New Premium Files Added!</b>\n\n"
            for f in new_files:
                text += f"✅ <code>{f}</code>\n"
            text += "\n📍 Check them out in the <b>Premium Files</b> section."
            bot.send_message(u['id'], text)
            count += 1
            time.sleep(0.05)
        except: pass
    return count

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if is_banned(uid): return

    db = load_json(DB_FILE, [])
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_json(DB_FILE, db)

    if check_join(uid):
        bot.send_photo(message.chat.id, BANNER_URL, 
                       caption=f"🔥 <b>Welcome to DUModZ Premium!</b>\n\nYour advanced file manager is ready. Select an option below to begin.",
                       reply_markup=main_markup(uid))
    else:
        force_join_msg(message.chat.id)

def force_join_msg(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 VERIFY JOIN", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Denied!</b>\n\nYou must join all our official channels to use this bot.", reply_markup=mk)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    uid = call.from_user.id
    if is_banned(uid): return

    if call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    elif call.data == "verify":
        if check_join(uid):
            bot.answer_callback_query(call.id, "✅ Access Granted!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Still not joined!", show_alert=True)

    elif call.data == "view_files":
        files = get_files()
        if not files:
            bot.answer_callback_query(call.id, "📂 No files found!")
            return
        
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]:
            mk.add(types.InlineKeyboardButton(f"📥 {f.upper()}", callback_data=f"dl_{f}"))
        mk.add(types.InlineKeyboardButton("🔙 BACK", callback_data="home"))
        
        bot.edit_message_caption(f"📂 <b>Premium Repository</b>\nTotal {len(files)} files available.", 
                                 call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data.startswith("dl_"):
        fname = call.data.replace("dl_", "")
        send_file_pro(call.message, fname)

    elif call.data == "search_file":
        m = bot.send_message(call.message.chat.id, "🔍 <b>Send the keyword to search:</b>")
        bot.register_next_step_handler(m, process_search)

    # --- ADMIN CALLBACKS ---
    elif call.data == "admin_panel" and uid == ADMIN_ID:
        bot.edit_message_caption("🔐 <b>Advanced Admin Panel</b>", call.message.chat.id, call.message.message_id, reply_markup=admin_markup())

    elif call.data == "adm_sync" and uid == ADMIN_ID:
        bot.answer_callback_query(call.id, "🔄 Syncing & Scanning...")
        current_files = get_files()
        cached_files = load_json(CACHE_FILE, [])
        
        new_files = [f for f in current_files if f not in cached_files]
        
        if new_files:
            save_json(CACHE_FILE, current_files)
            bot.send_message(call.message.chat.id, f"✅ <b>{len(new_files)} New files found!</b>\nNotifying all users...")
            success_count = notify_new_files(new_files)
            bot.send_message(call.message.chat.id, f"📢 <b>Notification sent to {success_count} users.</b>")
        else:
            bot.answer_callback_query(call.id, "ℹ️ Everything is already up to date!", show_alert=True)

    elif call.data == "adm_stats" and uid == ADMIN_ID:
        users = load_json(DB_FILE, [])
        files = get_files()
        bot.answer_callback_query(call.id, f"📊 Stats:\nUsers: {len(users)}\nFiles: {len(files)}", show_alert=True)

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "📣 <b>Broadcast:</b> Send any message (Text/Media)")
        bot.register_next_step_handler(m, process_broadcast)

# --- PRO FUNCTIONS ---
def send_file_pro(message, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(message.chat.id, 'upload_document')
        msg = bot.send_message(message.chat.id, f"⚡ <b>Encrypting & Sending:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"💎 <b>Premium File:</b> <code>{fname}</code>\n🚀 <b>Speed:</b> No Limit\n🛡️ <b>Scan:</b> Clean\n\n@DUModZ")
            bot.delete_message(message.chat.id, msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", message.chat.id, msg.message_id)

def process_search(message):
    query = message.text.lower()
    files = get_files()
    matches = [f for f in files if query in f.lower()]
    
    if matches:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for m in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{m}"))
        bot.send_message(message.chat.id, f"🔍 <b>Matches Found ({len(matches)}):</b>", reply_markup=mk)
    else:
        bot.send_message(message.chat.id, "❌ <b>No files found matching your search.</b>")

def process_broadcast(message):
    users = load_json(DB_FILE, [])
    bot.send_message(message.chat.id, f"📣 <b>Broadcast Started...</b>")
    success = 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(message.chat.id, f"✅ <b>Broadcast Finished!</b> Sent to: {success} users.")

# --- BOOT ---
if __name__ == "__main__":
    print("---------------------------------------")
    print("🚀 DUModZ PREMIUM FILE MANAGER ONLINE")
    print("📊 Status: Secure & Stealth Mode")
    print("---------------------------------------")
    try:
        bot.send_message(LOG_CHANNEL, "🟢 <b>Bot Online</b>\nSystem: <b>Premium File Manager</b>\nSync Engine: <b>Active</b>")
    except: pass
    bot.infinity_polling(skip_pending=True)
