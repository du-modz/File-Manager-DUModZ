import telebot
from telebot import types
import os
import json
import time
import re
import threading
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"

REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "users.json"
GROUP_DB = "groups.json"
BANNED_FILE = "banned.json"
CACHE_FILE = "sync_cache.json"

# ফোল্ডার চেক
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE ENGINE ---
def load_db(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return {} if "groups" in path else []
    return {} if "groups" in path else []

def save_db(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def is_joined(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- GROUP SETTINGS LOGIC ---
def get_group_config(chat_id):
    db = load_db(GROUP_DB)
    cid = str(chat_id)
    if cid not in db:
        db[cid] = {"autoclean": False, "timer": 24, "msg_list": []}
        save_db(GROUP_DB, db)
    return db[cid]

def update_group_config(chat_id, key, value):
    db = load_db(GROUP_DB)
    db[str(chat_id)][key] = value
    save_db(GROUP_DB, db)

def track_message(chat_id, message_id):
    """মেসেজ ডিলিট করার জন্য ট্র্যাকিং লিস্টে যোগ করা"""
    if chat_id > 0: return # প্রাইভেট চ্যাটে দরকার নেই
    db = load_db(GROUP_DB)
    cid = str(chat_id)
    if cid in db and db[cid]["autoclean"]:
        expiry = time.time() + (db[cid]["timer"] * 3600)
        db[cid]["msg_list"].append({"mid": message_id, "exp": expiry})
        save_db(GROUP_DB, db)

# --- AUTO-CLEAN BACKGROUND TASK ---
def cleanup_worker():
    while True:
        try:
            db = load_db(GROUP_DB)
            changed = False
            now = time.time()
            for cid, config in db.items():
                remaining_msgs = []
                for msg in config["msg_list"]:
                    if now > msg["exp"]:
                        try: bot.delete_message(cid, msg["mid"])
                        except: pass
                        changed = True
                    else:
                        remaining_msgs.append(msg)
                db[cid]["msg_list"] = remaining_msgs
            if changed: save_db(GROUP_DB, db)
        except Exception as e: print(f"Cleanup Error: {e}")
        time.sleep(60) # প্রতি ১ মিনিট পর পর চেক করবে

threading.Thread(target=cleanup_worker, daemon=True).start()

# --- UTILS ---
def get_clean_files():
    files = [f.name for f in os.scandir(FILES_DIR) if f.is_file()]
    return sorted(files)

def name_to_cmd(name):
    base = os.path.splitext(name)[0].lower()
    return re.sub(r'[^a-z0-9_]', '_', base)

# --- KEYBOARDS ---
def main_markup(uid):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(types.InlineKeyboardButton("📂 View All Files", callback_data="all_files"),
           types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL))
    mk.add(types.InlineKeyboardButton("📊 My Stats", callback_data="stats"),
           types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon"))
    if uid == ADMIN_ID:
        mk.add(types.InlineKeyboardButton("🔐 Admin Control", callback_data="admin_panel"))
    return mk

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in load_db(BANNED_FILE): return

    # গ্রুপে স্টার্ট কমান্ড দিলে অযথা রিপ্লাই বন্ধ (ঐচ্ছিক)
    if message.chat.type != "private":
        res = bot.reply_to(message, "🚀 I'm active! Use /list to see files or /help for group settings.")
        track_message(message.chat.id, res.message_id)
        return

    db = load_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)

    if is_joined(uid):
        bot.send_photo(message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\n\nHigh-speed premium files are ready.",
            reply_markup=main_markup(uid))
    else:
        force_join(message.chat.id)

def force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

# --- GROUP CONTROL COMMANDS ---
@bot.message_handler(commands=['autoclean'])
def toggle_clean(message):
    if message.chat.type == "private": return
    # চেক এডমিন কি না
    status = bot.get_chat_member(message.chat.id, message.from_user.id).status
    if status not in ['administrator', 'creator'] and message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Only admins can use this command.")

    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Usage: <code>/autoclean on</code> or <code>/autoclean off</code>")
    
    val = args[1].lower() == "on"
    update_group_config(message.chat.id, "autoclean", val)
    bot.reply_to(message, f"✅ Auto-Clean is now <b>{'ON' if val else 'OFF'}</b>")

@bot.message_handler(commands=['settime'])
def set_timer(message):
    if message.chat.type == "private": return
    status = bot.get_chat_member(message.chat.id, message.from_user.id).status
    if status not in ['administrator', 'creator']: return

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return bot.reply_to(message, "Usage: <code>/settime 24</code> (in hours)")
    
    hrs = int(args[1])
    update_group_config(message.chat.id, "timer", hrs)
    bot.reply_to(message, f"✅ Auto-Clean timer set to <b>{hrs} hours</b>.")

# --- FILE LOGIC ---
@bot.message_handler(commands=['list'])
def list_files(message):
    if message.chat.type == "private" and not is_joined(message.from_user.id): 
        return force_join(message.chat.id)
    
    files = get_clean_files()
    if not files:
        res = bot.reply_to(message, "📂 Repository is empty.")
    else:
        msg = "📂 <b>Available Premium Files:</b>\n\n"
        for f in files:
            msg += f"🔹 <code>/{name_to_cmd(f)}</code>\n"
        res = bot.send_message(message.chat.id, msg)
    
    track_message(message.chat.id, res.message_id)

# --- CORE FILE SENDER ---
def send_premium_file(chat_id, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        st = bot.send_message(chat_id, f"📡 <b>Processing:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>File:</b> <code>{fname}</code>\n🚀 <b>@DUModZ</b>")
            bot.delete_message(chat_id, st.message_id)
            track_message(chat_id, doc.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, st.message_id)
    else:
        bot.send_message(chat_id, "⚠️ File not found.")

# --- SMART TEXT HANDLER ---
@bot.message_handler(func=lambda m: True)
def text_handler(message):
    uid = message.from_user.id
    if uid in load_db(BANNED_FILE): return

    # গ্রুপ প্রাইভেসী: কমান্ড ছাড়া টেক্সট ইগনোর করবে
    if message.chat.type != "private":
        if not message.text.startswith('/') and f"@{bot.get_me().username}" not in message.text:
            return

    text = message.text.lower()
    files = get_clean_files()

    # কমান্ড প্রসেসিং
    if text.startswith('/'):
        target = text.split('@')[0][1:] # @botname রিমুভ করার জন্য
        for f in files:
            if target == name_to_cmd(f):
                send_premium_file(message.chat.id, f)
                return
        if message.chat.type == "private":
            bot.reply_to(message, "❌ Unknown command.")
        return

    # সার্চ লজিক (শুধুমাত্র প্রাইভেট চ্যাট অথবা মেনশন করলে)
    matches = [f for f in files if text in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for m in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{m}"))
        res = bot.reply_to(message, f"🔍 <b>Found {len(matches)} matches:</b>", reply_markup=mk)
        track_message(message.chat.id, res.message_id)

# --- CALLBACKS (Previous Logic) ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    # ... (আগের কলব্যাক লজিকগুলো এখানে থাকবে)
    if call.data == "verify":
        if is_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_cmd(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)
    # ... (বাকিগুলো একই থাকবে)

# --- BOOT ---
if __name__ == "__main__":
    print("🚀 DUModZ PRO System: Online with Group Control")
    bot.infinity_polling(skip_pending=True) Exception as e:
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
