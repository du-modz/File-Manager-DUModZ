import telebot
from telebot import types
import time
import os
import json
import datetime

# --- CONFIGURATION (Environment Variables) ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"

# Required Channels for Force Join
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "users.json"
BANNED_FILE = "banned.json"

# Ensure directories and files exist
os.makedirs(FILES_DIR, exist_ok=True)
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as f: json.dump([], f)
if not os.path.exists(BANNED_FILE):
    with open(BANNED_FILE, 'w') as f: json.dump([], f)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE HELPERS ---
def get_db(file):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def set_db(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=3, ensure_ascii=False)

def is_banned(user_id):
    return user_id in get_db(BANNED_FILE)

def register_user(user):
    users = get_db(DB_FILE)
    if not any(u['id'] == user.id for u in users):
        users.append({
            "id": user.id,
            "name": user.first_name,
            "username": user.username,
            "joined_at": str(datetime.datetime.now())
        })
        set_db(DB_FILE, users)

# --- UI & ANIMATION HELPERS ---
def safe_edit(call, text, reply_markup=None):
    try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=text,
            reply_markup=reply_markup
        )
    except:
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=reply_markup
            )
        except: pass

def loading_anim(call, final_text, markup=None):
    frames = ["⏳ 𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙞𝙣𝙜.", "⏳ 𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙞𝙣𝙜..", "⏳ 𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙞𝙣𝙜..."]
    for frame in frames:
        safe_edit(call, f"<b>{frame}</b>")
        time.sleep(0.3)
    safe_edit(call, final_text, markup)

# --- SECURITY & JOIN CHECK ---
def check_join(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- KEYBOARDS ---
def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗙𝗶𝗹𝗲𝘀", callback_data="view_files"),
        types.InlineKeyboardButton("🌐 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹 𝗦𝗶𝘁𝗲", url=WEBSITE_URL)
    )
    markup.add(
        types.InlineKeyboardButton("👤 𝗠𝘆 𝗦𝘁𝗮𝘁𝘀", callback_data="my_stats"),
        types.InlineKeyboardButton("👨‍💻 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿", url="https://t.me/DarkUnkwon")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹", callback_data="admin_main"))
    return markup

def join_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 𝗝𝗼𝗶𝗻 {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    markup.add(types.InlineKeyboardButton("🔄 𝗩𝗲𝗿𝗶𝗳𝘆 𝗠𝗲𝗺𝗯𝗲𝗿𝘀𝗵𝗶𝗽", callback_data="verify_me"))
    return markup

def admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", callback_data="adm_bc"),
        types.InlineKeyboardButton("📊 𝗨𝘀𝗲𝗿 𝗗𝗮𝘁𝗮", callback_data="adm_users")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 𝗕𝗮𝗻", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ 𝗨𝗻𝗯𝗮𝗻", callback_data="adm_unban")
    )
    markup.add(types.InlineKeyboardButton("🔙 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗛𝗼𝗺𝗲", callback_data="home"))
    return markup

# --- MAIN HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    if is_banned(message.from_user.id): return
    register_user(message.from_user)
    
    if check_join(message.from_user.id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🔥 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲, {message.from_user.first_name}!</b>\n\nYou have unlocked the <b>DUModZ Premium Interface</b>. Download any premium tools safely.\n\n🛡 𝙎𝙩𝙖𝙩𝙪𝙨: 𝙑𝙚𝙧𝙞𝙛𝙞𝙚𝙙 𝙐𝙨𝙚𝙧",
            reply_markup=main_menu(message.from_user.id)
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption="⚠️ <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱!</b>\n\nYou must join all our official channels to use this bot. Click the buttons below to join.",
            reply_markup=join_menu()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_queries(call):
    uid = call.from_user.id
    if is_banned(uid): return

    if call.data == "verify_me":
        if check_join(uid):
            bot.answer_callback_query(call.id, "✅ Verified Successfully!")
            loading_anim(call, "🔥 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗕𝗮𝗰𝗸!</b>\nAccess has been granted.", main_menu(uid))
        else:
            bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

    elif call.data == "home":
        safe_edit(call, "🏠 <b>𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂</b>\nChoose an option below:", main_menu(uid))

    elif call.data == "view_files":
        # Dynamic Refreshing List
        files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
        if not files:
            bot.answer_callback_query(call.id, "📁 No files found in repository.", show_alert=True)
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for f in files:
            markup.add(types.InlineKeyboardButton(f"📥 {f.upper()}", callback_data=f"get_{f}"))
        markup.add(types.InlineKeyboardButton("🔙 𝗕𝗮𝗰𝗸", callback_data="home"))
        
        safe_edit(call, f"📂 <b>𝗔𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗥𝗲𝘀𝗼𝘂𝗿𝗰𝗲𝘀 ({len(files)}):</b>\n\nSelect a file to start downloading.", markup)

    elif call.data.startswith("get_"):
        filename = call.data.replace("get_", "")
        send_file_logic(call.message, filename)

    elif call.data == "my_stats":
        users = get_db(DB_FILE)
        txt = f"👤 <b>𝗬𝗼𝘂𝗿 𝗣𝗿𝗼𝗳𝗶𝗹𝗲</b>\n\n🆔 𝗜𝗗: <code>{uid}</code>\n👥 𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀: {len(users)}\n📅 𝗗𝗮𝘁𝗲: {datetime.date.today()}"
        safe_edit(call, txt, main_menu(uid))

    # --- ADMIN ACTIONS ---
    elif call.data == "admin_main" and uid == ADMIN_ID:
        safe_edit(call, "🔐 <b>𝗔𝗱𝗺𝗶𝗻 𝗖𝗼𝗻𝘁𝗿𝗼𝗹 𝗣𝗮𝗻𝗲𝗹</b>\nManage system settings and users.", admin_menu())

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "📩 <b>Enter Broadcast Message:</b>\n(Type 'cancel' to abort)")
        bot.register_next_step_handler(msg, do_broadcast)

    elif call.data == "adm_ban" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "🚫 <b>Enter User ID to Ban:</b>")
        bot.register_next_step_handler(msg, do_ban)

    elif call.data == "adm_unban" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "✅ <b>Enter User ID to Unban:</b>")
        bot.register_next_step_handler(msg, do_unban)

    elif call.data == "adm_users" and uid == ADMIN_ID:
        users = get_db(DB_FILE)
        txt = f"👥 <b>𝗨𝘀𝗲𝗿 𝗟𝗶𝘀𝘁 (𝗟𝗮𝘀𝘁 𝟮𝟬):</b>\n\n"
        for u in users[-20:]:
            txt += f"• <a href='tg://user?id={u['id']}'>{u['name']}</a> (<code>{u['id']}</code>)\n"
        bot.send_message(call.message.chat.id, txt)

# --- LOGIC FUNCTIONS ---
def send_file_logic(message, filename):
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        status = bot.send_message(message.chat.id, f"⚡ <b>𝙋𝙧𝙚𝙥𝙖𝙧𝙞𝙣𝙜:</b> <code>{filename}</code>")
        bot.send_chat_action(message.chat.id, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"💎 <b>𝗙𝗶𝗹𝗲:</b> <code>{filename}</code>\n🚀 <b>𝗕𝘆 @DUModZ</b>")
            bot.delete_message(message.chat.id, status.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", message.chat.id, status.message_id)
    else:
        bot.send_message(message.chat.id, "❌ File not found.")

def do_broadcast(message):
    if message.text.lower() == 'cancel': return
    users = get_db(DB_FILE)
    count = 0
    for u in users:
        try:
            bot.send_message(u['id'], f"📢 <b>𝗔𝗻𝗻𝗼𝘂𝗻𝗰𝗲𝗺𝗲𝗻𝘁</b>\n\n{message.text}")
            count += 1
            time.sleep(0.05)
        except: pass
    bot.reply_to(message, f"✅ Broadcast sent to {count} users.")

def do_ban(message):
    try:
        target = int(message.text)
        banned = get_db(BANNED_FILE)
        if target not in banned:
            banned.append(target)
            set_db(BANNED_FILE, banned)
            bot.reply_to(message, f"🚫 User {target} banned.")
    except: bot.reply_to(message, "❌ Invalid ID.")

def do_unban(message):
    try:
        target = int(message.text)
        banned = get_db(BANNED_FILE)
        if target in banned:
            banned.remove(target)
            set_db(BANNED_FILE, banned)
            bot.reply_to(message, f"✅ User {target} unbanned.")
    except: bot.reply_to(message, "❌ Invalid ID.")

# --- SEARCH & AUTO COMMANDS ---
@bot.message_handler(func=lambda m: True)
def text_commands(message):
    uid = message.from_user.id
    if is_banned(uid): return
    if not check_join(uid):
        bot.reply_to(message, "⚠️ <b>Join our channels first!</b>", reply_markup=join_menu())
        return

    text = message.text.lower()
    
    # Check for direct file commands (/pubg, /hack etc)
    if text.startswith('/'):
        cmd = text[1:]
        files = os.listdir(FILES_DIR)
        for f in files:
            if cmd == os.path.splitext(f.lower())[0]:
                send_file_logic(message, f)
                return

    # List command
    if text == "/list":
        files = os.listdir(FILES_DIR)
        if not files:
            bot.reply_to(message, "📁 Repo is empty.")
            return
        res = "🛠 <b>Available Commands:</b>\n\n"
        for f in files:
            res += f"🔹 <code>/{os.path.splitext(f.lower())[0]}</code>\n"
        bot.reply_to(message, res)
        return

    # Admin quick access
    if text == "/admin" and uid == ADMIN_ID:
        bot.send_photo(message.chat.id, BANNER_URL, caption="🔐 <b>Admin Access</b>", reply_markup=admin_menu())
        return

    # General Search
    matches = [f for f in os.listdir(FILES_DIR) if text in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"get_{f}"))
        bot.reply_to(message, f"🔍 <b>Found {len(matches)} results:</b>", reply_markup=mk)
    else:
        bot.reply_to(message, "😔 No files found. Use /list to see all.")

# --- START BOT ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot System: ACTIVE")
    try: bot.send_message(LOG_CHANNEL, "🟢 <b>Bot System Online</b>\nSecurity Layer: 𝟭𝟬𝟬% 𝗦𝗮𝗳𝗲\nRepo Sync: 𝗘𝗻𝗮𝗯𝗹𝗲𝗱")
    except: pass
    bot.infinity_polling(skip_pending=True)
