import telebot
from telebot import types
import os
import json
import time
import re
import threading
from datetime import datetime

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') # এনভায়রনমেন্ট ভেরিয়েবল থেকে টোকেন নিন
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"

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

# --- GROUP CONFIG LOGIC ---
def get_group_config(chat_id):
    db = load_db(GROUP_DB, dict)
    cid = str(chat_id)
    if cid not in db:
        db[cid] = {"autoclean": False, "timer": 24, "msgs": []}
        save_db(GROUP_DB, db)
    return db[cid]

def track_msg(chat_id, mid):
    if chat_id > 0: return 
    db = load_db(GROUP_DB, dict)
    cid = str(chat_id)
    if cid in db and db[cid]["autoclean"]:
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
                for m in cfg["msgs"]:
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
           types.InlineKeyboardButton("❓ Help", callback_data="help_menu"))
    if uid == ADMIN_ID:
        mk.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return mk

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_chat_action(message.chat.id, 'typing')
    uid = message.from_user.id
    
    # User Logging
    db = load_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)

    if message.chat.type == "private":
        if is_joined(uid):
            bot.send_photo(message.chat.id, BANNER_URL, 
                caption=f"👋 <b>Hello {message.from_user.first_name}!</b>\nWelcome to DUModZ Premium File Manager.",
                reply_markup=main_kb(uid))
        else:
            show_force_join(message.chat.id)
    else:
        res = bot.reply_to(message, "✅ <b>Bot is Online!</b>\nUse /list to see files or /help for group commands.")
        track_msg(message.chat.id, res.message_id)

def show_force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock premium files.", reply_markup=mk)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_chat_action(message.chat.id, 'typing')
    help_text = (
        "📖 <b>DUModZ Bot Help Menu</b>\n\n"
        "👤 <b>Private Commands:</b>\n"
        "• /start - Start the bot\n"
        "• /list - Show all available files\n"
        "• /stats - Check your profile info\n\n"
        "👥 <b>Group Commands (Admins Only):</b>\n"
        "• /autoclean on/off - Toggle auto message delete\n"
        "• /settime (hours) - Set delete timer (Default 24h)\n"
        "• /list - Get file commands in group\n\n"
        "💡 <i>Just send any keyword to search for files!</i>"
    )
    res = bot.send_message(message.chat.id, help_text)
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
        text += "\n💡 Click a command to download."
        res = bot.send_message(message.chat.id, text)
    track_msg(message.chat.id, res.message_id)

# --- GROUP ADMIN COMMANDS ---
@bot.message_handler(commands=['autoclean', 'settime'])
def group_admin_cmds(message):
    if message.chat.type == "private": return
    
    # Admin Check
    u_status = bot.get_chat_member(message.chat.id, message.from_user.id).status
    if u_status not in ['administrator', 'creator'] and message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin access required.")

    cmd = message.text.split()
    if 'autoclean' in cmd[0]:
        if len(cmd) < 2: return bot.reply_to(message, "Use: /autoclean on or off")
        val = cmd[1].lower() == "on"
        db = load_db(GROUP_DB, dict)
        db[str(message.chat.id)]["autoclean"] = val
        save_db(GROUP_DB, db)
        bot.reply_to(message, f"✅ Auto-Clean is <b>{'Enabled' if val else 'Disabled'}</b>")
    
    elif 'settime' in cmd[0]:
        if len(cmd) < 2 or not cmd[1].isdigit(): return bot.reply_to(message, "Use: /settime 24")
        hrs = int(cmd[1])
        db = load_db(GROUP_DB, dict)
        db[str(message.chat.id)]["timer"] = hrs
        save_db(GROUP_DB, db)
        bot.reply_to(message, f"⏱️ Auto-Clean timer set to <b>{hrs} hours</b>.")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    mid = call.message.message_id

    if call.data == "verify":
        if is_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(cid, mid)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

    elif call.data == "all_files":
        files = get_files()
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{to_cmd(f)}"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        bot.edit_message_caption("📂 <b>Select a file to download:</b>", cid, mid, reply_markup=mk)

    elif call.data == "home":
        bot.edit_message_caption(f"🏠 <b>Main Menu</b>", cid, mid, reply_markup=main_kb(uid))

    elif call.data == "stats":
        db = load_db(DB_FILE)
        u = next((i for i in db if i['id'] == uid), {"date": "N/A"})
        text = f"👤 <b>Your Profile</b>\n\n🆔 ID: <code>{uid}</code>\n📅 Joined: {u['date']}\n🌟 Rank: Premium"
        bot.edit_message_caption(text, cid, mid, reply_markup=main_kb(uid))

    elif call.data == "help_menu":
        help_cmd(call.message)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("dl_"):
        target_cmd = call.data.replace("dl_", "")
        files = get_files()
        for f in files:
            if to_cmd(f) == target_cmd:
                send_file(cid, f)
                break
        bot.answer_callback_query(call.id)

# --- FILE SENDER CORE ---
def send_file(chat_id, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        tmp = bot.send_message(chat_id, f"📡 <b>Fetching:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>File:</b> <code>{fname}</code>\n🚀 <b>By @DUModZ</b>")
            bot.delete_message(chat_id, tmp.message_id)
            track_msg(chat_id, doc.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, tmp.message_id)
    else:
        bot.send_message(chat_id, "⚠️ File not found.")

# --- TEXT & SEARCH HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    if message.chat.type != "private":
        # গ্রুপে শুধু কমান্ড রিপ্লাই দিবে
        if message.text.startswith('/'):
            files = get_files()
            cmd = message.text.split('@')[0][1:].lower()
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
    bot.infinity_polling(skip_pending=True)= types.InlineKeyboardMarkup(row_width=1)
        for m in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{name_to_cmd(m)}"))
        res = bot.reply_to(message, f"🔍 <b>Found {len(matches)} files:</b>", reply_markup=mk)
        track_message(message.chat.id, res.message_id)
    elif message.chat.type == "private":
        bot.reply_to(message, "❌ No files found.")

# --- CORE FILE SENDER ---
def send_premium_file(chat_id, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        st = bot.send_message(chat_id, f"📡 <b>Fetching:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>{fname}</b>\n🚀 <b>@DUModZ</b>")
            bot.delete_message(chat_id, st.message_id)
            track_message(chat_id, doc.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, st.message_id)
    else: bot.send_message(chat_id, "⚠️ File not found.")

def force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

# --- BOOT ---
if __name__ == "__main__":
    print("🚀 DUModZ System: ONLINE")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        tmp = bot.send_message(chat_id, f"📡 <b>Preparing:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>{fname}</b>\n🚀 <b>@DUModZ</b>")
            bot.delete_message(chat_id, tmp.message_id)
            track_msg(chat_id, doc.message_id)
            send_log(f"File sent: {fname} to {uid}")
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, tmp.message_id)
    else: bot.send_message(chat_id, "⚠️ File not found.")

def force_join_msg(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

# --- PERSISTENT BOOT ENGINE ---
if __name__ == "__main__":
    print("🚀 DUModZ PRO v3.0: BOOTING...")
    while True:
        try:
            send_log("🟢 Bot Rebooted & Online")
            bot.remove_webhook()
            bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
        except Exception as e:
            print(f"Polling crashed: {e}")
            time.sleep(5)ame)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        tmp = bot.send_message(chat_id, f"📡 <b>Preparing:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>{fname}</b>\n🚀 <b>@DUModZ</b>")
            bot.delete_message(chat_id, tmp.message_id)
            track_msg(chat_id, doc.message_id)
            send_log(f"File Downloaded: {fname} by {uid}")
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, tmp.message_id)
    else: bot.send_message(chat_id, "⚠️ File not found.")

def force_join_msg(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

# --- BOOT ---
if __name__ == "__main__":
    print("🚀 DUModZ System: ONLINE")
    try:
        # কোনো পুরনো ওয়েব হুক থাকলে তা ডিলিট করে ফ্রেশ স্টার্ট করবে
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Polling Error: {e}")
        time.sleep(5)age)
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
