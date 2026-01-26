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

# Required Channels
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg".strip()
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com".strip()
FILES_DIR = "files"
DB_FILE = "users.json"
BANNED_FILE = "banned.json"

os.makedirs(FILES_DIR, exist_ok=True)
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE & BAN SYSTEM ---
def load_banned():
    try:
        if os.path.exists(BANNED_FILE):
            with open(BANNED_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except: return set()

def save_banned(banned_set):
    with open(BANNED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(banned_set), f, indent=2)

def is_user_banned(user_id):
    return user_id in load_banned()

def load_users():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except: return []

def save_users(users):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_user(user: types.User):
    users = load_users()
    user_id = user.id
    existing = next((u for u in users if u["id"] == user_id), None)
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    
    if not existing:
        users.append({
            "id": user_id,
            "name": name.strip(),
            "username": user.username,
            "joined": is_user_joined(user_id),
            "first_seen": datetime.datetime.now().isoformat()
        })
    else:
        existing["name"] = name.strip()
        existing["username"] = user.username
        existing["joined"] = is_user_joined(user_id)
    save_users(users)

# --- UTILS ---
def is_user_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for channel in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
    return markup

def get_main_markup(user_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL)
    )
    markup.add(
        types.InlineKeyboardButton("📊 My Stats", callback_data="user_stats"),
        types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Control Panel", callback_data="admin_panel"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast_info"),
        types.InlineKeyboardButton("👥 User List", callback_data="admin_user_list")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_info"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_info")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export DB", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")
    )
    return markup

# --- CORE HANDLERS ---
@bot.message_handler(commands=['start'])
def start_command(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "<b>❌ Access Denied! You are banned.</b>")
        return
    
    save_user(message.from_user)
    
    if is_user_joined(message.from_user.id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"👋 <b>Hey {message.from_user.first_name}!</b>\n\nWelcome to <b>DU ModZ Premium Hub</b>. Your subscription is active. Enjoy our premium services!\n\n⚡ <i>Status: Premium User ✅</i>",
            reply_markup=get_main_markup(user_id=message.from_user.id)
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Restricted!</b>\n\nTo use this bot, you must join our official channels. This helps us maintain our service.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned.", show_alert=True)
        return

    try:
        if call.data == "verify_user":
            if is_user_joined(user_id):
                bot.answer_callback_query(call.id, "✅ Verification Successful!")
                # Animation
                frames = ["🔍 Checking...", "🛡️ Verifying...", "🔓 Unlocking Access..."]
                for frame in frames:
                    bot.edit_message_caption(frame, call.message.chat.id, call.message.message_id)
                    time.sleep(0.4)
                
                bot.edit_message_caption(
                    "✅ <b>Access Granted!</b>\n\nWelcome to the premium community.",
                    call.message.chat.id, call.message.message_id,
                    reply_markup=get_main_markup(user_id=user_id)
                )
            else:
                bot.answer_callback_query(call.id, "❌ Please join all channels first!", show_alert=True)

        elif call.data == "list_files":
            # Dynamic Refresh: Scans folder every time button is clicked
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📂 No files available at the moment.", show_alert=True)
                return
            
            text = "💎 <b>Premium File Repository</b>\n\n"
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files:
                name = os.path.splitext(f)[0].replace('_', ' ').title()
                markup.add(types.InlineKeyboardButton(f"📥 {name}", callback_data=f"dl_{f}"))
            
            markup.add(types.InlineKeyboardButton("🔙 Back to Home", callback_data="back_home"))
            bot.edit_message_caption(text + "<i>Select a file to download:</i>", call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data.startswith("dl_"):
            filename = call.data.replace("dl_", "")
            send_file_logic(call.message, filename)

        elif call.data == "back_home":
            bot.edit_message_caption(
                f"🏠 <b>Main Menu</b>\n\nWelcome back, {call.from_user.first_name}!",
                call.message.chat.id, call.message.message_id,
                reply_markup=get_main_markup(user_id=user_id)
            )

        elif call.data == "user_stats":
            total_users = len(load_users())
            stats_text = (
                f"👤 <b>User Information</b>\n\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                f"👑 <b>Status:</b> Premium\n"
                f"👥 <b>Total Bot Users:</b> {total_users}\n"
                f"📅 <b>Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d')}"
            )
            bot.edit_message_caption(stats_text, call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(user_id=user_id))

        # --- ADMIN CALLBACKS ---
        elif call.data == "admin_panel" and user_id == ADMIN_ID:
            bot.edit_message_caption("🔐 <b>Admin Control Panel</b>\nManage your users and files here.", call.message.chat.id, call.message.message_id, reply_markup=get_admin_markup())

        elif call.data == "admin_broadcast_info":
            msg = bot.send_message(call.message.chat.id, "📨 <b>Send the text for broadcast:</b>")
            bot.register_next_step_handler(msg, process_broadcast)

        elif call.data == "admin_ban_info":
            msg = bot.send_message(call.message.chat.id, "🚫 <b>Enter the User ID to Ban:</b>")
            bot.register_next_step_handler(msg, process_ban)

        elif call.data == "admin_unban_info":
            msg = bot.send_message(call.message.chat.id, "✅ <b>Enter the User ID to Unban:</b>")
            bot.register_next_step_handler(msg, process_unban)

    except Exception as e:
        print(f"Error: {e}")

# --- ADMIN PROCESSORS ---
def process_broadcast(message):
    if message.text.lower() == 'cancel': return
    users = load_users()
    count = 0
    for u in users:
        try:
            bot.send_message(u['id'], f"📢 <b>Important Update</b>\n\n{message.text}")
            count += 1
            time.sleep(0.05)
        except: pass
    bot.reply_to(message, f"✅ Broadcast completed! Sent to {count} users.")

def process_ban(message):
    try:
        target = int(message.text)
        banned = load_banned()
        banned.add(target)
        save_banned(banned)
        bot.reply_to(message, f"🚫 User {target} has been banned.")
    except: bot.reply_to(message, "❌ Invalid ID.")

def process_unban(message):
    try:
        target = int(message.text)
        banned = load_banned()
        if target in banned:
            banned.remove(target)
            save_banned(banned)
            bot.reply_to(message, f"✅ User {target} unbanned.")
        else: bot.reply_to(message, "ℹ️ User wasn't banned.")
    except: bot.reply_to(message, "❌ Invalid ID.")

# --- FILE SENDING LOGIC ---
def send_file_logic(message, file_name):
    chat_id = message.chat.id
    path = os.path.join(FILES_DIR, file_name)
    
    if os.path.exists(path):
        temp_msg = bot.send_message(chat_id, f"⏳ <b>Encrypting & Preparing:</b> <code>{file_name}</code>")
        bot.send_chat_action(chat_id, 'upload_document')
        time.sleep(1.5)
        
        try:
            with open(path, 'rb') as f:
                bot.send_document(
                    chat_id, f, 
                    caption=f"<b>💎 Premium File:</b> <code>{file_name}</code>\n\n🚀 <b>Uploaded by:</b> @DUModZ\n🛡️ <b>Safety:</b> Verified ✅",
                    parse_mode="HTML"
                )
            bot.delete_message(chat_id, temp_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error sending file: {e}", chat_id, temp_msg.message_id)
    else:
        bot.send_message(chat_id, "⚠️ <b>Error:</b> File not found on server.")

# --- SEARCH & AUTO COMMANDS ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return

    if not is_user_joined(user_id):
        bot.reply_to(message, "❌ <b>Join our channels first!</b>", reply_markup=get_join_markup())
        return

    query = message.text.lower()
    
    # Check if it's a command for a specific file
    files = os.listdir(FILES_DIR)
    for f in files:
        if query == f"/{os.path.splitext(f)[0].lower()}":
            send_file_logic(message, f)
            return

    # Regular Search
    matches = [f for f in files if query in f.lower()]
    if matches:
        markup = types.InlineKeyboardMarkup()
        for f in matches[:8]:
            markup.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 <b>Found {len(matches)} matches for your search:</b>", reply_markup=markup)
    else:
        bot.reply_to(message, "😔 <b>No files found matching your search.</b>\nTry /list to see all files.")

# --- RUN BOT ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot is Online...")
    # Logging to channel
    try: bot.send_message(LOG_CHANNEL, "<b>🟢 Bot Online</b>\nStatus: <i>Scanning files dynamically...</i>")
    except: pass
    bot.infinity_polling(skip_pending=True)
