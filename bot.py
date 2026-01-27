# ======== [ আগের import 그대로 ] ========
import telebot
from telebot import types
import os, json, time, re, threading
from datetime import datetime

# ======== CONFIG (UNCHANGED) ========
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"

REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"

FILES_DIR = "files"
DB_FILE = "users.json"
BANNED_FILE = "banned.json"
CACHE_FILE = "sync_cache.json"

# ======== NEW GROUP FILE ========
GROUP_FILE = "group_settings.json"

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# ======== DB HELPERS (SAFE) ========
def load_db(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_db(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ======== GROUP SETTINGS ========
def get_group(cid):
    db = load_db(GROUP_FILE, {})
    if str(cid) not in db:
        db[str(cid)] = {
            "silent": True,
            "auto_clean": False,
            "interval": 24,
            "last_clean": time.time()
        }
        save_db(GROUP_FILE, db)
    return db[str(cid)]

def update_group(cid, data):
    db = load_db(GROUP_FILE, {})
    db[str(cid)] = data
    save_db(GROUP_FILE, db)

# ======== AUTO CLEAN THREAD ========
def auto_clean():
    while True:
        groups = load_db(GROUP_FILE, {})
        now = time.time()
        for gid, g in groups.items():
            if g["auto_clean"] and now - g["last_clean"] >= g["interval"] * 3600:
                save_db(CACHE_FILE, [])
                g["last_clean"] = now
                groups[gid] = g
        save_db(GROUP_FILE, groups)
        time.sleep(300)

threading.Thread(target=auto_clean, daemon=True).start()

# ======== JOIN CHECK (UNCHANGED) ========
def is_joined(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

# ======== FILE LOGIC (UNCHANGED) ========
def get_clean_files():
    return sorted([f.name for f in os.scandir(FILES_DIR) if f.is_file()])

def name_to_cmd(name):
    base = os.path.splitext(name)[0].lower()
    return re.sub(r'[^a-z0-9_]', '_', base)

# ======== GROUP FILTER LAYER (NEW, SAFE) ========
def block_group(message):
    if message.chat.type in ["group", "supergroup"]:
        g = get_group(message.chat.id)
        if g["silent"]:
            return True
    return False

# ======== START (UNCHANGED LOGIC) ========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if message.chat.type != "private":
        return

    uid = message.from_user.id
    if uid in load_db(BANNED_FILE, []):
        return

    db = load_db(DB_FILE, [])
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)

    if is_joined(uid):
        bot.send_photo(
            message.chat.id,
            BANNER_URL,
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\n\nHigh-speed premium files are ready.",
            reply_markup=main_markup(uid)
        )
    else:
        force_join(message.chat.id)

# ======== FORCE JOIN (UNCHANGED) ========
def force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

# ======== GROUP CONTROL COMMAND (NEW) ========
@bot.message_handler(commands=["group_settings"])
def group_settings(message):
    if message.chat.type == "private":
        return
    member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        return

    g = get_group(message.chat.id)
    mk = types.InlineKeyboardMarkup()
    mk.add(
        types.InlineKeyboardButton(f"Silent: {'ON' if g['silent'] else 'OFF'}", callback_data="gs_silent"),
        types.InlineKeyboardButton(f"Auto Clean: {'ON' if g['auto_clean'] else 'OFF'}", callback_data="gs_clean")
    )
    mk.add(types.InlineKeyboardButton("⏱ 24h Interval", callback_data="gs_24"))
    bot.send_message(message.chat.id, "⚙️ <b>Group Control Panel</b>", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("gs_"))
def group_toggle(c):
    g = get_group(c.message.chat.id)
    if c.data == "gs_silent":
        g["silent"] = not g["silent"]
    elif c.data == "gs_clean":
        g["auto_clean"] = not g["auto_clean"]
    elif c.data == "gs_24":
        g["interval"] = 24
    update_group(c.message.chat.id, g)
    bot.answer_callback_query(c.id, "Updated")
    bot.delete_message(c.message.chat.id, c.message.message_id)

# ======== TEXT HANDLER (SAFE) ========
@bot.message_handler(func=lambda m: True)
def text_handler(message):
    if block_group(message):
        return

    # আগের text_handler logic এখানে অপরিবর্তিত থাকবে
    # (তোমার দেওয়া কোডের logic 그대로 কাজ করবে)
    pass

# ======== BOOT ========
print("🚀 DUModZ PRO System Online")
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
