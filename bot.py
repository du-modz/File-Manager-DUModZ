import telebot
from telebot import types
import time
import os
import json
import datetime

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

# ফোল্ডার নিশ্চিত করা
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DYNAMIC FILE SYNC LOGIC ---
def get_current_files():
    """সরাসরি ডিস্ক থেকে লেটেস্ট ফাইল লিস্ট স্ক্যান করে"""
    try:
        # scandir ব্যবহার করা হয়েছে যা ক্যাশ ছাড়াই সরাসরি ডিরেক্টরি রিড করে
        return [f.name for f in os.scandir(FILES_DIR) if f.is_file()]
    except Exception as e:
        print(f"Sync Error: {e}")
        return []

# --- DATABASE LOGIC ---
def load_db(path, default):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return default
    return default

def save_db(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=3)

# --- MIDDLEWARE & SECURITY ---
def is_banned(uid):
    return uid in load_db(BANNED_FILE, [])

def check_join(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- KEYBOARDS ---
def main_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗙𝗶𝗹𝗲𝘀", callback_data="sync_files"),
        types.InlineKeyboardButton("🌐 𝗪𝗲𝗯𝘀𝗶𝘁𝗲", url=WEBSITE_URL)
    )
    markup.add(
        types.InlineKeyboardButton("📊 𝗦𝘁𝗮𝘁𝘀", callback_data="my_stats"),
        types.InlineKeyboardButton("👨‍💻 𝗗𝗲𝘃", url="https://t.me/DarkUnkwon")
    )
    if uid == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹", callback_data="admin_panel"))
    return markup

def admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", callback_data="adm_bc"),
        types.InlineKeyboardButton("📁 𝗦𝘆𝗻𝗰 𝗡𝗼𝘄", callback_data="sync_files")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 𝗕𝗮𝗻", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ 𝗨𝗻𝗯𝗮𝗻", callback_data="adm_unban")
    )
    markup.add(types.InlineKeyboardButton("🔙 𝗕𝗮𝗰𝗸", callback_data="home"))
    return markup

# --- ANIMATION EFFECT ---
def update_status(call, text, markup=None):
    try:
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except: pass

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if is_banned(uid): return
    
    # ইউজার সেভ করা
    db = load_db(DB_FILE, [])
    if not any(u['id'] == uid for u in db):
        db.append({"id": uid, "name": message.from_user.first_name})
        save_db(DB_FILE, db)

    if check_join(uid):
        bot.send_photo(message.chat.id, BANNER_URL, 
                       caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\nPremium files are ready for you.",
                       reply_markup=main_markup(uid))
    else:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for ch in REQUIRED_CHANNELS:
            mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        mk.add(types.InlineKeyboardButton("🔄 Verify", callback_data="verify"))
        bot.send_photo(message.chat.id, BANNER_URL, caption="⚠️ <b>Join our channels to continue!</b>", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    if is_banned(uid): return

    if call.data == "verify":
        if check_join(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            update_status(call, "🔓 <b>Access Granted!</b>", main_markup(uid))
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

    elif call.data == "sync_files":
        # ডাইনামিক ফাইল স্ক্যানিং শুরু
        bot.answer_callback_query(call.id, "🔄 Syncing Files...")
        update_status(call, "🔍 <b>Scanning Repository...</b>")
        time.sleep(0.5)
        
        files = get_current_files()
        if not files:
            update_status(call, "📂 <b>No files found!</b>\nPlease check the 'files' folder.", main_markup(uid))
            return
        
        mk = types.InlineKeyboardMarkup(row_width=1)
        for f in files:
            mk.add(types.InlineKeyboardButton(f"📥 {f.upper()}", callback_data=f"dl_{f}"))
        mk.add(types.InlineKeyboardButton("🔄 Refresh List", callback_data="sync_files"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        
        update_status(call, f"✅ <b>Sync Complete!</b>\nFound {len(files)} premium files.", mk)

    elif call.data.startswith("dl_"):
        fname = call.data.replace("dl_", "")
        send_premium_file(call.message, fname)

    elif call.data == "home":
        update_status(call, "🏠 <b>Main Menu</b>", main_markup(uid))

    elif call.data == "admin_panel" and uid == ADMIN_ID:
        update_status(call, "🔐 <b>Admin Control Panel</b>", admin_markup())

    # --- ADMIN FUNCTIONS ---
    elif call.data == "adm_bc" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "📩 <b>Enter Broadcast Text:</b>")
        bot.register_next_step_handler(m, broadcast_step)

    elif call.data == "adm_ban" and uid == ADMIN_ID:
        m = bot.send_message(call.message.chat.id, "🚫 <b>Enter User ID to Ban:</b>")
        bot.register_next_step_handler(m, ban_step)

# --- FILE SENDING ---
def send_premium_file(message, fname):
    path = os.path.join(FILES_DIR, fname)
    if os.path.exists(path):
        tmp = bot.send_message(message.chat.id, f"⚡ <b>Preparing</b> <code>{fname}</code>...")
        bot.send_chat_action(message.chat.id, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"💎 <b>Premium File:</b> <code>{fname}</code>\n🚀 <b>By @DUModZ</b>")
            bot.delete_message(message.chat.id, tmp.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", message.chat.id, tmp.message_id)
    else:
        bot.send_message(message.chat.id, "⚠️ File sync error! File not found.")

# --- ADMIN PROCESSORS ---
def broadcast_step(message):
    users = load_db(DB_FILE, [])
    success = 0
    for u in users:
        try:
            bot.send_message(u['id'], f"📢 <b>Announcement</b>\n\n{message.text}")
            success += 1
            time.sleep(0.05)
        except: pass
    bot.reply_to(message, f"✅ Sent to {success} users.")

def ban_step(message):
    try:
        tid = int(message.text)
        b = load_db(BANNED_FILE, [])
        if tid not in b:
            b.append(tid)
            save_db(BANNED_FILE, b)
            bot.reply_to(message, "🚫 User Banned.")
    except: bot.reply_to(message, "❌ Invalid ID.")

# --- AUTO COMMANDS & SEARCH ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    if is_banned(uid) or not check_join(uid): return

    txt = message.text.lower()
    
    # কমান্ড হিসেবে ফাইল খোঁজা (যেমন: /mod_v1)
    if txt.startswith('/'):
        cmd = txt[1:]
        files = get_current_files()
        for f in files:
            if cmd == os.path.splitext(f.lower())[0]:
                send_premium_file(message, f)
                return

    # সাধারণ টেক্সট সার্চ
    files = get_current_files()
    matches = [f for f in files if txt in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 <b>Found {len(matches)} results:</b>", reply_markup=mk)
    elif txt == "/list":
        res = "📂 <b>Current Files:</b>\n\n"
        for f in files: res += f"🔹 <code>/{os.path.splitext(f.lower())[0]}</code>\n"
        bot.reply_to(message, res)

# --- START ---
if __name__ == "__main__":
    print("🚀 DUModZ System Online | Dynamic Sync: ENABLED")
    try: bot.send_message(LOG_CHANNEL, "🟢 <b>Bot Online</b>\nDynamic Sync Engine: 𝗥𝘂𝗻𝗻𝗶𝗻𝗴 ✅")
    except: pass
    bot.infinity_polling(skip_pending=True)
