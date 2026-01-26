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

# Required Channels for Force Join
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg".strip()
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com".strip()
FILES_DIR = "files"
DB_FILE = "users.json"
BANNED_FILE = "banned.json"

os.makedirs(FILES_DIR, exist_ok=True)
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE LOGIC ---
def load_data(file, default):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_data(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_user_banned(user_id):
    banned = load_data(BANNED_FILE, [])
    return user_id in banned

def save_user(user: types.User):
    users = load_data(DB_FILE, [])
    user_id = user.id
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    
    existing = next((u for u in users if u["id"] == user_id), None)
    if not existing:
        users.append({
            "id": user_id,
            "name": name.strip(),
            "username": user.username,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_data(DB_FILE, users)

# --- UTILS ---
def is_user_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

# --- KEYBOARDS ---
def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for channel in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("🔄 Click to Verify", callback_data="verify_user"))
    return markup

def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL)
    )
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="user_stats"),
        types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Control Panel", callback_data="admin_panel"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("👥 Users List", callback_data="admin_user_list")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export Data", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_home")
    )
    return markup

def get_back_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home"))
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "<b>❌ You are banned from using this bot!</b>")
        return

    save_user(message.from_user)
    
    if is_user_joined(user_id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\n\nYou have <b>Premium Access</b> to all DUModZ files. Use the buttons below to explore.",
            reply_markup=get_main_markup(user_id)
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Denied!</b>\n\nPlease join our channels to unlock the bot features.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ Banned", show_alert=True)
        return

    try:
        if call.data == "verify_user":
            if is_user_joined(user_id):
                bot.answer_callback_query(call.id, "✅ Verified!")
                frames = ["🔍 Checking...", "🛡️ Verifying Membership...", "🔓 Unlocking..."]
                for frame in frames:
                    bot.edit_message_caption(f"<b>{frame}</b>", call.message.chat.id, call.message.message_id)
                    time.sleep(0.3)
                bot.edit_message_caption("✅ <b>Verified Successfully!</b>", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(user_id))
            else:
                bot.answer_callback_query(call.id, "❌ Still not joined!", show_alert=True)

        elif call.data == "list_files":
            # Dynamic Scan of Folder
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📁 No files found in server.", show_alert=True)
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            text = "🛠 <b>Available Premium Files:</b>\n\n"
            for f in files:
                btn_name = os.path.splitext(f)[0].replace('_', ' ').upper()
                markup.add(types.InlineKeyboardButton(f"📥 {btn_name}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back to Home", callback_data="back_home"))
            
            bot.edit_message_caption(text + "<i>Select a file to get download link:</i>", call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data.startswith("dl_"):
            filename = call.data.replace("dl_", "")
            send_file(call.message, filename)

        elif call.data == "user_stats":
            users = load_data(DB_FILE, [])
            stat_msg = f"👤 <b>User Info:</b>\n\n🆔 ID: <code>{user_id}</code>\n👥 Total Users: {len(users)}\n📅 Date: {datetime.date.today()}"
            bot.edit_message_caption(stat_msg, call.message.chat.id, call.message.message_id, reply_markup=get_back_markup())

        elif call.data == "back_home":
            bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(user_id))

        # --- ADMIN CALLBACKS ---
        elif call.data == "admin_panel" and user_id == ADMIN_ID:
            bot.edit_message_caption("🔐 <b>Advanced Admin Panel</b>", call.message.chat.id, call.message.message_id, reply_markup=get_admin_markup())

        elif call.data == "admin_broadcast" and user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "📩 <b>Enter text for broadcast (type 'cancel' to stop):</b>")
            bot.register_next_step_handler(msg, run_broadcast)

        elif call.data == "admin_ban" and user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "🚫 <b>Enter User ID to Ban:</b>")
            bot.register_next_step_handler(msg, run_ban)

        elif call.data == "admin_unban" and user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "✅ <b>Enter User ID to Unban:</b>")
            bot.register_next_step_handler(msg, run_unban)

        elif call.data == "admin_user_list" and user_id == ADMIN_ID:
            users = load_data(DB_FILE, [])
            text = f"👥 <b>Total Users: {len(users)}</b>\n\n"
            for u in users[-20:]: # Last 20
                text += f"• <a href='tg://user?id={u['id']}'>{u['name']}</a> (<code>{u['id']}</code>)\n"
            bot.send_message(call.message.chat.id, text)

        elif call.data == "admin_export" and user_id == ADMIN_ID:
            with open(DB_FILE, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="📂 User Database Export")

    except Exception as e:
        print(f"Callback Error: {e}")

# --- ADMIN LOGIC ---
def run_broadcast(message):
    if message.text.lower() == 'cancel':
        bot.reply_to(message, "❌ Broadcast Cancelled.")
        return
    users = load_data(DB_FILE, [])
    success = 0
    bot.send_message(message.chat.id, f"⏳ Broadcasting to {len(users)} users...")
    for u in users:
        try:
            bot.send_message(u['id'], f"📢 <b>Notification</b>\n\n{message.text}")
            success += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(message.chat.id, f"✅ Broadcast finished! Successful: {success}")

def run_ban(message):
    try:
        uid = int(message.text)
        banned = load_data(BANNED_FILE, [])
        if uid not in banned:
            banned.append(uid)
            save_data(BANNED_FILE, banned)
            bot.reply_to(message, f"🚫 User <code>{uid}</code> Banned.")
        else: bot.reply_to(message, "User already banned.")
    except: bot.reply_to(message, "❌ Invalid ID.")

def run_unban(message):
    try:
        uid = int(message.text)
        banned = load_data(BANNED_FILE, [])
        if uid in banned:
            banned.remove(uid)
            save_data(BANNED_FILE, banned)
            bot.reply_to(message, f"✅ User <code>{uid}</code> Unbanned.")
        else: bot.reply_to(message, "User is not in ban list.")
    except: bot.reply_to(message, "❌ Invalid ID.")

# --- FILE LOGIC ---
def send_file(message, filename):
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        wait = bot.send_message(message.chat.id, f"⏳ <b>Preparing</b> <code>{filename}</code>...")
        bot.send_chat_action(message.chat.id, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ <b>File:</b> <code>{filename}</code>\n⚡ <b>Powered by: @DUModZ</b>")
            bot.delete_message(message.chat.id, wait.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", message.chat.id, wait.message_id)
    else:
        bot.send_message(message.chat.id, "🚧 File not found.")

# --- TEXT SEARCH & CMDS ---
@bot.message_handler(func=lambda m: True)
def text_handler(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    if not is_user_joined(user_id):
        bot.reply_to(message, "⚠️ Join channel first!", reply_markup=get_join_markup())
        return

    query = message.text.lower()
    
    # Handle direct file command like /modname
    if query.startswith('/'):
        cmd = query[1:]
        files = os.listdir(FILES_DIR)
        for f in files:
            if cmd == os.path.splitext(f)[0].lower():
                send_file(message, f)
                return

    # Search Logic
    matches = [f for f in os.listdir(FILES_DIR) if query in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 <b>Search results for '{message.text}':</b>", reply_markup=mk)
    else:
        bot.reply_to(message, "😔 No files found. Try /list")

# --- START ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot Started Successfully!")
    try: bot.send_message(LOG_CHANNEL, "🟢 <b>Bot Online</b>\nDynamic File Loading: Active ✅")
    except: pass
    bot.infinity_polling(skip_pending=True)
