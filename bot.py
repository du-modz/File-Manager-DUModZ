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
LOG_CHANNEL = "@dumodzbotmanager" # নিশ্চিত করুন বট এখানে অ্যাডমিন

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
    """লগ চ্যানেলে মেসেজ পাঠানোর ফাংশন"""
    try:
        bot.send_message(LOG_CHANNEL, f"📜 <b>LOG SYSTEM:</b>\n{text}")
    except Exception as e:
        print(f"Logging failed: {e}")

# --- AUTO CLEANUP ENGINE ---
def cleanup_thread():
    while True:
        try:
            db = load_db(GROUP_DB, dict)
            now = time.time()
            changed = False
            for cid, config in db.items():
                if config.get("autoclean"):
                    active_msgs = []
                    for m in config.get("msgs", []):
                        if now > m["exp"]:
                            try: bot.delete_message(cid, m["mid"])
                            except: pass
                            changed = True
                        else: active_msgs.append(m)
                    db[cid]["msgs"] = active_msgs
            if changed: save_db(GROUP_DB, db)
        except: pass
        time.sleep(60)

threading.Thread(target=cleanup_thread, daemon=True).start()

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
        mk.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return mk

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    db = load_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)
        send_log(f"New User: <b>{message.from_user.first_name}</b> (<code>{uid}</code>)")

    if is_joined(uid):
        res = bot.send_photo(message.chat.id, BANNER_URL, 
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\nPremium repository is ready. Use /list for all commands.",
            reply_markup=main_kb(uid))
        track_msg(message.chat.id, res.message_id)
    else:
        force_join_msg(message.chat.id)

@bot.message_handler(commands=['stats'])
def stats_msg(message):
    uid = message.from_user.id
    db = load_db(DB_FILE)
    u = next((i for i in db if i['id'] == uid), {"date": "N/A"})
    text = f"👤 <b>User Stats</b>\n🆔 ID: <code>{uid}</code>\n📅 Joined: {u['date']}\n🛡️ Rank: Premium"
    res = bot.reply_to(message, text, reply_markup=main_kb(uid) if message.chat.type == "private" else None)
    track_msg(message.chat.id, res.message_id)

@bot.message_handler(commands=['list'])
def list_msg(message):
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

@bot.message_handler(commands=['autoclean', 'settime'])
def group_config(message):
    if message.chat.type == "private": return
    status = bot.get_chat_member(message.chat.id, message.from_user.id).status
    if status not in ['administrator', 'creator'] and message.from_user.id != ADMIN_ID: return

    db = load_db(GROUP_DB, dict)
    cid = str(message.chat.id)
    if cid not in db: db[cid] = {"autoclean": False, "timer": 24, "msgs": []}
    
    cmd = message.text.split()
    if 'autoclean' in cmd[0] and len(cmd) > 1:
        db[cid]["autoclean"] = cmd[1].lower() == "on"
        bot.reply_to(message, f"✅ Auto-Clean: <b>{'ON' if db[cid]['autoclean'] else 'OFF'}</b>")
    elif 'settime' in cmd[0] and len(cmd) > 1 and cmd[1].isdigit():
        db[cid]["timer"] = int(cmd[1])
        bot.reply_to(message, f"⏱️ Timer set to: <b>{cmd[1]} hours</b>")
    save_db(GROUP_DB, db)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    mid = call.message.message_id

    if call.data == "verify":
        if is_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(cid, mid)
            start_cmd(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Join all channels!", show_alert=True)
            return

    if not is_joined(uid):
        bot.answer_callback_query(call.id, "❌ Please join channels first!", show_alert=True)
        return

    if call.data == "all_files":
        files = get_files()
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{to_cmd(f)}"))
        mk.add(types.InlineKeyboardButton("🔙 Back Home", callback_data="home"))
        bot.edit_message_caption("📂 <b>Select a file:</b>", cid, mid, reply_markup=mk)

    elif call.data == "stats":
        stats_msg(call.message)

    elif call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", cid, mid, reply_markup=main_kb(uid))

    elif call.data == "admin_panel" and uid == ADMIN_ID:
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(types.InlineKeyboardButton("📣 Broadcast", callback_data="adm_bc"),
               types.InlineKeyboardButton("🔄 Sync Engine", callback_data="adm_sync"))
        bot.edit_message_caption("🔐 <b>Admin Control Panel</b>", cid, mid, reply_markup=mk)

    elif call.data == "adm_sync" and uid == ADMIN_ID:
        all_f = get_files()
        cache = load_db(CACHE_FILE)
        new_f = [f for f in all_f if f not in cache]
        if new_f:
            save_db(CACHE_FILE, all_f)
            users = load_db(DB_FILE)
            for u in users:
                try: bot.send_message(u['id'], "🔥 <b>Update!</b>\nNew premium files added. Use /list.")
                except: pass
            bot.answer_callback_query(call.id, "✅ Sync Done & Users Notified!")
        else: bot.answer_callback_query(call.id, "✅ Up to date", show_alert=True)

    elif call.data.startswith("dl_"):
        target = call.data.replace("dl_", "")
        for f in get_files():
            if to_cmd(f) == target:
                send_f(cid, f, uid)
                break

# --- MESSAGE HANDLER (Commands & Search) ---
@bot.message_handler(func=lambda m: True)
def main_msg_handler(message):
    uid = message.from_user.id
    text = message.text.lower()

    if text.startswith('/'):
        # কমান্ড হিসেবে চেক করা
        clean_cmd = text.split('@')[0][1:]
        for f in get_files():
            if to_cmd(f) == clean_cmd:
                return send_f(message.chat.id, f, uid)
        return # কমান্ড না মিললে ইগনোর করবে যাতে লুপ না হয়

    if not is_joined(uid): return force_join_msg(message.chat.id)

    if message.chat.type == "private":
        bot.send_chat_action(message.chat.id, 'typing')
        matches = [f for f in get_files() if text in f.lower()]
        if matches:
            mk = types.InlineKeyboardMarkup(row_width=1)
            for m in matches[:10]:
                mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{to_cmd(m)}"))
            res = bot.reply_to(message, f"🔍 <b>Found {len(matches)} matches:</b>", reply_markup=mk)
            track_msg(message.chat.id, res.message_id)
        else:
            bot.reply_to(message, "❌ No files found for your search.")

def send_f(chat_id, fname, uid):
    if not is_joined(uid): return force_join_msg(chat_id)
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        tmp = bot.send_message(chat_id, f"📡 <b>Preparing:</b> {fname}...")
        try:
            with open(path, 'rb') as f:
                doc = bot.send_document(chat_id, f, caption=f"💎 <b>{fname}</b>\n🚀 <b>By @DUModZ</b>")
            bot.delete_message(chat_id, tmp.message_id)
            track_msg(chat_id, doc.message_id)
            send_log(f"File Downloaded: <code>{fname}</code> by (<code>{uid}</code>)")
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, tmp.message_id)
    else: bot.send_message(chat_id, "⚠️ File not found.")

def force_join_msg(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

# --- BOOT ENGINE ---
if __name__ == "__main__":
    print("🚀 DUModZ Ultimate: Online")
    send_log("🟢 <b>Bot Rebooted Successfully</b>")
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)গ ফিক্সড: অতিরিক্ত 'age)' মুছে ফেলা হয়েছে.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
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
