import telebot
from telebot import types
import os
import json
import time
import re
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
CACHE_FILE = "sync_cache.json"

# ফোল্ডার চেক
if not os.path.exists(FILES_DIR): os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE ENGINE ---
def load_db(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []

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

# --- FILE LOGIC ---
def get_clean_files():
    """ফাইল লিস্ট রিটার্ন করে এবং কমান্ড ফ্রেন্ডলি নাম তৈরি করে"""
    files = [f.name for f in os.scandir(FILES_DIR) if f.is_file()]
    return sorted(files)

def name_to_cmd(name):
    """ফাইলের নামকে কমান্ডে রূপান্তর (Space -> Underscore, No extension)"""
    base = os.path.splitext(name)[0].lower()
    return re.sub(r'[^a-z0-9_]', '_', base)

# --- KEYBOARDS ---
def main_markup(uid):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📂 View All Files", callback_data="all_files"),
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL)
    )
    mk.add(
        types.InlineKeyboardButton("📊 My Stats", callback_data="stats"),
        types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon")
    )
    if uid == ADMIN_ID:
        mk.add(types.InlineKeyboardButton("🔐 Admin Control", callback_data="admin_panel"))
    return mk

def admin_markup():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("🔄 Sync & Notify", callback_data="adm_sync")
    )
    mk.add(types.InlineKeyboardButton("🔙 Back to Home", callback_data="home"))
    return mk

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid in load_db(BANNED_FILE): return

    # ইউজার সেভ
    db = load_db(DB_FILE)
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name, "date": str(datetime.now().date())})
        save_db(DB_FILE, db)

    if is_joined(uid):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\n\nHigh-speed premium files are ready. You can use /list to see all commands or click the button below.",
            reply_markup=main_markup(uid)
        )
    else:
        force_join(message.chat.id)

def force_join(chat_id):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    mk.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
    bot.send_message(chat_id, "⚠️ <b>Access Restricted!</b>\nPlease join our channels to unlock the bot.", reply_markup=mk)

@bot.message_handler(commands=['list'])
def list_files(message):
    if not is_joined(message.from_user.id): return force_join(message.chat.id)
    
    files = get_clean_files()
    if not files:
        bot.reply_to(message, "📂 Repository is empty.")
        return
    
    msg = "📂 <b>Available Premium Files:</b>\n\n"
    for f in files:
        cmd = name_to_cmd(f)
        msg += f"🔹 <code>/{cmd}</code>\n"
    
    msg += "\n💡 <i>Click any command to download.</i>"
    bot.send_message(message.chat.id, msg)

# --- CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    if uid in load_db(BANNED_FILE): return

    if call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    elif call.data == "verify":
        if is_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_cmd(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

    elif call.data == "all_files":
        files = get_clean_files()
        if not files:
            bot.answer_callback_query(call.id, "No files found!")
            return
        
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        bot.edit_message_caption(f"📂 <b>Select a file to download:</b>", call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data.startswith("dl_"):
        fname = call.data.replace("dl_", "")
        send_premium_file(call.message.chat.id, fname)

    elif call.data == "stats":
        db = load_db(DB_FILE)
        u_info = next((u for u in db if u['id'] == uid), None)
        text = f"👤 <b>My Stats</b>\n\n🆔 ID: <code>{uid}</code>\n📅 Joined: {u_info['date'] if u_info else 'N/A'}\n🛡️ Status: Premium Member"
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    # --- ADMIN ACTIONS ---
    elif call.data == "admin_panel" and uid == ADMIN_ID:
        bot.edit_message_caption("🔐 <b>Admin Control Center</b>", call.message.chat.id, call.message.message_id, reply_markup=admin_markup())

    elif call.data == "adm_sync" and uid == ADMIN_ID:
        bot.answer_callback_query(call.id, "🔄 Syncing...")
        all_f = get_clean_files()
        cache = load_db(CACHE_FILE)
        new_f = [f for f in all_f if f not in cache]
        
        if new_f:
            save_db(CACHE_FILE, all_f)
            users = load_db(DB_FILE)
            success = 0
            for u in users:
                try:
                    bot.send_message(u['id'], f"🔥 <b>New Update!</b>\n\n{len(new_f)} new files added to repository.\nUse /list to check them out!")
                    success += 1
                    time.sleep(0.05)
                except: pass
            bot.send_message(call.message.chat.id, f"✅ Sync Complete. Notified {success} users.")
        else:
            bot.answer_callback_query(call.id, "✅ Repository is already up to date!", show_alert=True)

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "📣 <b>Broadcast:</b> Send me the message (Text/Media).")
        bot.register_next_step_handler(m, process_broadcast)

# --- CORE FILE SENDER ---
def send_premium_file(chat_id, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        bot.send_chat_action(chat_id, 'upload_document')
        st = bot.send_message(chat_id, f"📡 <b>Processing:</b> <code>{fname}</code>...")
        try:
            with open(path, 'rb') as f:
                bot.send_document(chat_id, f, caption=f"💎 <b>File:</b> <code>{fname}</code>\n🚀 <b>Delivered by: @DUModZ</b>")
            bot.delete_message(chat_id, st.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id, st.message_id)
    else:
        bot.send_message(chat_id, "⚠️ File not found. Use /list to refresh.")

# --- DYNAMIC COMMAND & SEARCH HANDLER ---
@bot.message_handler(func=lambda m: True)
def text_handler(message):
    uid = message.from_user.id
    if uid in load_db(BANNED_FILE): return
    if not is_joined(uid): return force_join(message.chat.id)

    text = message.text.lower()
    files = get_clean_files()

    # ১. কমান্ড দিয়ে ডাউনলোড (e.g. /my_file)
    if text.startswith('/'):
        target = text[1:]
        for f in files:
            if target == name_to_cmd(f):
                send_premium_file(message.chat.id, f)
                return
        bot.reply_to(message, "❌ Unknown command. Use /list for all files.")
        return

    # ২. নাম দিয়ে সার্চ
    matches = [f for f in files if text in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for m in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {m}", callback_data=f"dl_{m}"))
        bot.reply_to(message, f"🔍 <b>Found {len(matches)} matches:</b>", reply_markup=mk)

def process_broadcast(message):
    users = load_db(DB_FILE)
    bot.send_message(message.chat.id, "🚀 Broadcast started...")
    count = 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            count += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(message.chat.id, f"✅ Sent to {count} users.")

# --- BOOT ---
if __name__ == "__main__":
    print("🚀 DUModZ PRO System: Online")
    try: bot.send_message(LOG_CHANNEL, "🟢 <b>Bot Rebooted</b>\nSync Engine: <b>Perfect</b>")
    except: pass
    bot.infinity_polling(skip_pending=True)_id, tmp.message_id)
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
