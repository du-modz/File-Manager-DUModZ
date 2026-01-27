import telebot
from telebot import types
import os
import json
import time
import re
import threading
from datetime import datetime

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager" # নিশ্চিত করুন বট এখানে এডমিন

REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "users.json"
GROUP_DB = "groups.json"
CACHE_FILE = "sync_cache.json"

if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE ENGINE ---
def load_db(path, default_type=list):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return default_type()
    return default_type()

def save_db(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def is_joined(uid):
    if uid == ADMIN_ID: return True
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"📜 <b>LOG:</b>\n{text}")
    except: print("Log sending failed. Check channel username and Admin rights.")

# --- AUTO CLEANUP THREAD ---
def cleanup_loop():
    while True:
        try:
            db = load_db(GROUP_DB, dict)
            now = time.time()
            changed = False
            for cid, cfg in db.items():
                active_msgs = []
                for m in cfg.get("msgs", []):
                    if now > m["exp"]:
                        try: bot.delete_message(cid, m["mid"])
                        except: pass
                        changed = True
                    else: active_msgs.append(m)
                db[cid]["msgs"] = active_msgs
            if changed: save_db(GROUP_DB, db)
        except: pass
        time.sleep(60)

threading.Thread(target=cleanup_loop, daemon=True).start()

# --- UTILS ---
def get_files():
    return sorted([f.name for f in os.scandir(FILES_DIR) if f.is_file()])

def to_cmd(name):
    return re.sub(r'[^a-z0-9_]', '_', os.path.splitext(name)[0].lower())

def track_msg(chat_id, mid):
    if chat_id > 0: return 
    db = load_db(GROUP_DB, dict)
    cid = str(chat_id)
    if cid in db and db[cid].get("autoclean"):
        exp = time.time() + (db[cid].get("timer", 24) * 3600)
        if "msgs" not in db[cid]: db[cid]["msgs"] = []
        db[cid]["msgs"].append({"mid": mid, "exp": exp})
        save_db(GROUP_DB, db)

# --- KEYBOARDS ---
def main_kb(uid):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(types.InlineKeyboardButton("📂 View Files", callback_data="all_files"),
           types.InlineKeyboardButton("🌐 Website", url=WEBSITE_URL))
    mk.add(types.InlineKeyboardButton("📊 My Stats", callback_data="stats"),
           types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon"))
    if uid == ADMIN_ID:
        mk.add(types.InlineKeyboardButton("🔐 Admin Control", callback_data="admin_panel"))
    return mk

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    db = load_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)
        send_log(f"New User: {message.from_user.first_name} ({uid})")

    if message.chat.type == "private":
        if is_joined(uid):
            bot.send_photo(message.chat.id, BANNER_URL, 
                caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\nPremium High Speed files are ready for you.",
                reply_markup=main_kb(uid))
        else: force_join_msg(message.chat.id)
    else:
        res = bot.reply_to(message, "✅ Bot is active in this group.")
        track_msg(message.chat.id, res.message_id)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    bot.send_chat_action(message.chat.id, 'typing')
    uid = message.from_user.id
    db = load_db(DB_FILE)
    u = next((i for i in db if i['id'] == uid), {"date": "N/A"})
    text = f"👤 <b>Your Profile</b>\n\n🆔 ID: <code>{uid}</code>\n📅 Joined: {u['date']}\n🌟 Status: Premium Member"
    res = bot.reply_to(message, text, reply_markup=main_kb(uid) if message.chat.type == "private" else None)
    track_msg(message.chat.id, res.message_id)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = (
        "📖 <b>DUModZ Help Menu</b>\n\n"
        "<b>Private Commands:</b>\n"
        "• /start - Start Bot\n"
        "• /list - Show Files\n"
        "• /stats - User Info\n\n"
        "<b>Group Commands:</b>\n"
        "• /autoclean on/off - Auto Delete\n"
        "• /settime (hrs) - Timer\n\n"
        "💡 Search any file by typing its name!"
    )
    res = bot.reply_to(message, text)
    track_msg(message.chat.id, res.message_id)

@bot.message_handler(commands=['list'])
def list_files(message):
    if not is_joined(message.from_user.id): return force_join_msg(message.chat.id)
    files = get_files()
    if not files:
        res = bot.reply_to(message, "📂 Repository is empty.")
    else:
        text = "📂 <b>Available Premium Files:</b>\n\n"
        for f in files:
            text += f"🔹 <code>/{to_cmd(f)}</code>\n"
        res = bot.send_message(message.chat.id, text)
    track_msg(message.chat.id, res.message_id)

# --- ADMIN FUNCTIONS ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_p(call):
    if call.from_user.id != ADMIN_ID: return
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(types.InlineKeyboardButton("📣 Broadcast", callback_data="adm_bc"),
           types.InlineKeyboardButton("🔄 Sync & Notify", callback_data="adm_sync"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
    bot.edit_message_caption("🔐 <b>Admin Control Center</b>", call.message.chat.id, call.message.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data == "adm_sync")
def sync_engine(call):
    bot.answer_callback_query(call.id, "🔄 Syncing Files...")
    all_f = get_files()
    cache = load_db(CACHE_FILE)
    new_f = [f for f in all_f if f not in cache]
    
    if new_f:
        save_db(CACHE_FILE, all_f)
        users = load_db(DB_FILE)
        count = 0
        for u in users:
            try:
                bot.send_message(u['id'], f"🔥 <b>New Files Added!</b>\n\n{len(new_f)} new items in repository.\nUse /list to check.")
                count += 1
                time.sleep(0.05)
            except: pass
        bot.send_message(call.message.chat.id, f"✅ Sync Done. Notified {count} users.")
    else:
        bot.answer_callback_query(call.id, "✅ No new files found.", show_alert=True)

# --- TEXT & FILE HANDLER ---
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    uid = message.from_user.id
    text = message.text.lower()

    # ১. কমান্ড দিয়ে ডাউনলোড (e.g. /style_v1_...)
    if text.startswith('/'):
        clean_cmd = text.split('@')[0][1:]
        files = get_files()
        for f in files:
            if to_cmd(f) == clean_cmd:
                return send_file(message.chat.id, f, uid)
        
        # যদি কমান্ড না মিলে তবে কিছু করবে না (যাতে বাগ না হয়)
        return

    # ২. জয়েন চেক (শুধু ফাইল বা সার্চের জন্য)
    if not is_joined(uid): return force_join_msg(message.chat.id)

    # ৩. সার্চ ইঞ্জিন
    bot.send_chat_action(message.chat.id, 'typing')
    matches = [f for f in get_files() if text in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for m in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{to_cmd(m)}"))
        res = bot.reply_to(message, f"🔍 <b>Found {len(matches)} files:</b>", reply_markup=mk)
        track_msg(message.chat.id, res.message_id)
    else:
        if message.chat.type == "private":
            bot.reply_to(message, "❌ No files found for your search.")

# --- FILE SENDER ---
def send_file(chat_id, fname, uid):
    if not is_joined(uid): return force_join_msg(chat_id)
    
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        st = bot.send_message(chat_id, f"📡 <b>Preparing:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>{fname}</b>\n🚀 <b>@DUModZ</b>")
            bot.delete_message(chat_id, st.message_id)
            track_msg(chat_id, doc.message_id)
            send_log(f"File Downloaded: {fname}\nUser: {uid}")
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, st.message_id)
    else:
        bot.send_message(chat_id, "⚠️ File not found.")

def force_join_msg(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

# --- CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    uid = call.from_user.id
    if call.data == "verify":
        if is_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start(call.message)
        else: bot.answer_callback_query(call.id, "❌ Join all channels!", show_alert=True)
    
    elif call.data == "all_files":
        files = get_files()
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{to_cmd(f)}"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        bot.edit_message_caption("📂 <b>Select File:</b>", call.message.chat.id, call.message.message_id, reply_markup=mk)
    
    elif call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_kb(uid))

    elif call.data == "stats":
        stats_cmd(call.message)

    elif call.data.startswith("dl_"):
        target = call.data.replace("dl_", "")
        for f in get_files():
            if to_cmd(f) == target:
                send_file(call.message.chat.id, f, uid)
                break

# --- BOOT ---
if __name__ == "__main__":
    print("🚀 DUModZ PRO v2.0: ONLINE")
    send_log("🟢 Bot Rebooted Successfully")
    bot.infinity_polling(skip_pending=True)Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, st.message_id)

# --- TEXT & SEARCH ---
@bot.message_handler(func=lambda m: True)
def text_handler(message):
    uid = message.from_user.id
    # যদি কোনো কমান্ড হয় এবং কমান্ড হ্যান্ডলারে না থাকে, তবে ইগনোর করবে (যাতে সার্চে না যায়)
    if message.text.startswith('/'):
        files = get_files()
        cmd = message.text.split('@')[0][1:].lower()
        for f in files:
            if to_cmd(f) == cmd:
                if message.chat.type == "private" and not is_joined(uid):
                    return show_force_join(message.chat.id)
                send_premium_file(message.chat.id, f)
                return
        if message.chat.type == "private":
            bot.reply_to(message, "❌ Unknown command. Use /list")
        return

    # সার্চ লজিক
    if message.chat.type != "private": return # গ্রুপে সার্চ বন্ধ
    if not is_joined(uid): return show_force_join(message.chat.id)

    query = message.text.lower()
    matches = [f for f in get_files() if query in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for m in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{to_cmd(m)}"))
        res = bot.reply_to(message, f"🔍 <b>Found {len(matches)} files:</b>", reply_markup=mk)
        track_msg(message.chat.id, res.message_id)
    else:
        bot.reply_to(message, "❌ No files found for your search.")

# --- BOOT ---
if __name__ == "__main__":
    print("🚀 DUModZ Fix-System Online")
    send_log("🟢 <b>Bot Rebooted & Fixes Applied!</b>")
    bot.infinity_polling(skip_pending=True)     cmd = message.text.split('@')[0][1:].lower()
            for f in files:
                if to_cmd(f) == cmd:
                    send_file(message.chat.id, f)
                    return
        return

    if not is_joined(uid): return show_force_join(message.chat.id)

    # সার্চ লজিক
    bot.send_chat_action(message.chat.id, 'typing')
    query = message.text.lower()
    matches = [f for f in get_files() if query in f.lower()]
    
    if matches:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for m in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{to_cmd(m)}"))
        bot.reply_to(message, f"🔍 <b>Found {len(matches)} files:</b>", reply_markup=mk)
    else:
        bot.reply_to(message, "❌ No files found for your search.")

# --- BOOT ---
if __name__ == "__main__":
    print("🚀 DUModZ Ultimate System: Online")
    bot.infinity_polling(skip_pending=True)
