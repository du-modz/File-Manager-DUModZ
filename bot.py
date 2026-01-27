import telebot
from telebot import types
import os
import json
import time
import re
import threading
from datetime import datetime

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') # আপনার বট টোকেন দিন
ADMIN_ID = 8504263842 # আপনার আইডি
LOG_CHANNEL = "@dumodzbotmanager" # আপনার লগ চ্যানেল ইউজারনেম

REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "users.json"
GROUP_DB = "groups.json"
BANNED_FILE = "banned.json"

# ফোল্ডার তৈরি
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

# --- LOGGING SYSTEM ---
def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"📝 <b>Log:</b>\n{text}")
    except: pass

# --- GROUP MSG TRACKING ---
def track_msg(chat_id, mid):
    if chat_id > 0: return 
    db = load_db(GROUP_DB, dict)
    cid = str(chat_id)
    if cid in db and db.get(cid, {}).get("autoclean"):
        exp = time.time() + (db[cid]["timer"] * 3600)
        db[cid]["msgs"].append({"mid": mid, "exp": exp})
        save_db(GROUP_DB, db)

# --- AUTO CLEANUP THREAD ---
def cleanup_loop():
    while True:
        try:
            db = load_db(GROUP_DB, dict)
            now = time.time()
            for cid, cfg in db.items():
                active_msgs = []
                for m in cfg.get("msgs", []):
                    if now > m["exp"]:
                        try: bot.delete_message(cid, m["mid"])
                        except: pass
                    else: active_msgs.append(m)
                db[cid]["msgs"] = active_msgs
            save_db(GROUP_DB, db)
        except: pass
        time.sleep(60)

threading.Thread(target=cleanup_loop, daemon=True).start()

# --- UTILS ---
def get_files():
    return sorted([f.name for f in os.scandir(FILES_DIR) if f.is_file()])

def to_cmd(name):
    return re.sub(r'[^a-z0-9_]', '_', os.path.splitext(name)[0].lower())

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

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    db = load_db(DB_FILE)
    
    # New User Notification & Logging
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)
        send_log(f"👤 New User Joined: <b>{message.from_user.first_name}</b> (ID: {uid})")

    if message.chat.type == "private":
        bot.send_chat_action(message.chat.id, 'typing')
        if is_joined(uid):
            bot.send_photo(message.chat.id, BANNER_URL, 
                caption=f"👋 <b>Welcome {message.from_user.first_name}!</b>\nDownload High Speed Premium Dialog Boxes.",
                reply_markup=main_kb(uid))
        else:
            show_force_join(message.chat.id)
    else:
        res = bot.reply_to(message, "✅ <b>Bot is Online!</b>\nUse /list to see all files.")
        track_msg(message.chat.id, res.message_id)

def show_force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    uid = message.from_user.id
    bot.send_chat_action(message.chat.id, 'typing')
    db = load_db(DB_FILE)
    u_info = next((u for u in db if u['id'] == uid), {"date": "N/A"})
    
    text = (f"👤 <b>My Profile Stats:</b>\n\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"📅 Joined: {u_info['date']}\n"
            f"🛡️ Membership: {'Premium' if is_joined(uid) else 'Free'}")
    
    res = bot.reply_to(message, text)
    track_msg(message.chat.id, res.message_id)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = ("📖 <b>DUModZ Bot Help</b>\n\n"
            "• /list - Show all file commands\n"
            "• /stats - View your info\n"
            "• Send any word to search files\n\n"
            "<b>Group Admins:</b>\n"
            "• /autoclean on/off\n"
            "• /settime (hours)")
    res = bot.reply_to(message, text)
    track_msg(message.chat.id, res.message_id)

@bot.message_handler(commands=['list'])
def list_files(message):
    if message.chat.type == "private" and not is_joined(message.from_user.id):
        return show_force_join(message.chat.id)
    
    bot.send_chat_action(message.chat.id, 'typing')
    files = get_files()
    if not files:
        res = bot.reply_to(message, "📂 Repository is empty.")
    else:
        text = "📂 <b>Available Premium Files:</b>\n\n"
        for f in files:
            text += f"🔹 <code>/{to_cmd(f)}</code>\n"
        res = bot.send_message(message.chat.id, text)
    track_msg(message.chat.id, res.message_id)

# --- ADMIN ACTIONS ---
@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.reply_to(message, "🚀 Enter the message you want to broadcast:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    db = load_db(DB_FILE)
    count = 0
    bot.send_message(ADMIN_ID, f"🚀 Broadcast started to {len(db)} users...")
    for user in db:
        try:
            bot.copy_message(user['id'], message.chat.id, message.message_id)
            count += 1
            time.sleep(0.1)
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast finished. Sent to {count} users.")

# --- GROUP ADMIN COMMANDS ---
@bot.message_handler(commands=['autoclean', 'settime'])
def group_cmds(message):
    if message.chat.type == "private": return
    status = bot.get_chat_member(message.chat.id, message.from_user.id).status
    if status not in ['administrator', 'creator'] and message.from_user.id != ADMIN_ID: return

    args = message.text.split()
    db = load_db(GROUP_DB, dict)
    cid = str(message.chat.id)
    if cid not in db: db[cid] = {"autoclean": False, "timer": 24, "msgs": []}

    if "autoclean" in args[0]:
        val = args[1].lower() == "on" if len(args) > 1 else False
        db[cid]["autoclean"] = val
        bot.reply_to(message, f"✅ Auto-Clean is <b>{'ON' if val else 'OFF'}</b>")
    elif "settime" in args[0]:
        if len(args) > 1 and args[1].isdigit():
            db[cid]["timer"] = int(args[1])
            bot.reply_to(message, f"⏱️ Timer set to <b>{args[1]} hours</b>")
    
    save_db(GROUP_DB, db)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    if call.data == "verify":
        if is_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start(call.message)
        else: bot.answer_callback_query(call.id, "❌ Not joined!", show_alert=True)
    
    elif call.data == "all_files":
        files = get_files()
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{to_cmd(f)}"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        bot.edit_message_caption("📂 <b>Select a file:</b>", call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_kb(uid))

    elif call.data == "stats":
        stats_cmd(call.message)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("dl_"):
        cmd_name = call.data.replace("dl_", "")
        for f in get_files():
            if to_cmd(f) == cmd_name:
                send_premium_file(call.message.chat.id, f)
                break
        bot.answer_callback_query(call.id)

# --- FILE SENDER ---
def send_premium_file(chat_id, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        st = bot.send_message(chat_id, f"📡 <b>Processing...</b>")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>File:</b> <code>{fname}</code>\n🚀 <b>@DUModZ</b>")
            bot.delete_message(chat_id, st.message_id)
            track_msg(chat_id, doc.message_id)
            send_log(f"📥 File Downloaded: {fname} by {chat_id}")
        except Exception as e:
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
