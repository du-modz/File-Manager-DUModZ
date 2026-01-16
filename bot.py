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
REQUIRED_CHANNEL_ID = "@Dark_Unkwon_ModZ"
CHANNEL_URL = "https://t.me/Dark_Unkwon_ModZ".strip()
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg".strip()
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com".strip()
FILES_DIR = "files"
DB_FILE = "users.json"

# Ensure directories exist
os.makedirs(FILES_DIR, exist_ok=True)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE HELPERS ---
def load_users():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[ERROR] DB Load Failed: {e}")
        return []
    return []

def save_user(user_id):
    try:
        users = load_users()
        if user_id not in users:
            users.append(user_id)
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] DB Save Failed: {e}")

# --- LOGGING UTILS ---
def log_to_channel(message):
    try:
        bot.send_message(LOG_CHANNEL, message, disable_web_page_preview=True)
    except Exception as e:
        print(f"[LOG ERROR] {e}")

def log_error(error_msg):
    print(f"[ERROR] {error_msg}")
    try:
        bot.send_message(ADMIN_ID, f"⚠️ <b>Error Log</b>\n\n<code>{error_msg}</code>", parse_mode="HTML")
    except: pass

# --- UTILS ---
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        log_error(f"Join Check Failed for {user_id}: {e}")
        return False

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Join Our Official Channel", url=CHANNEL_URL),
        types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user")
    )
    return markup

def get_main_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 All Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL)
    )
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="user_stats"),
        types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon")
    )
    return markup

# --- CORE HANDLERS ---

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    save_user(user_id)
    
    bot.send_chat_action(message.chat.id, 'typing')
    time.sleep(0.3)
    
    if is_user_joined(user_id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome, {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>. You can now download files using buttons or commands (e.g., <code>/filename</code>).",
            reply_markup=get_main_markup()
        )
        log_to_channel(f"✅ <b>New Verified User</b>\nID: <code>{user_id}</code>\nName: {message.from_user.full_name}")
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Restricted!</b>\n\nHi {message.from_user.first_name}, you must join our channel to use this bot and access premium mod files.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    try:
        if call.data == "verify_user":
            if is_user_joined(user_id):
                bot.answer_callback_query(call.id, "✅ Verified Successfully!")
                animations = ["🔍 Checking database...", "🛡️ Verifying access...", "🔓 Unlocking files..."]
                for text in animations:
                    bot.edit_message_caption(f"<b>{text}</b>", call.message.chat.id, call.message.message_id)
                    time.sleep(0.5)
                
                bot.edit_message_caption(
                    f"✅ <b>Verification Complete!</b>\n\nWelcome to <b>Dark Unkwon ModZ</b>. Enjoy your premium experience.", 
                    call.message.chat.id, call.message.message_id, reply_markup=get_main_markup()
                )
                log_to_channel(f"🔓 <b>Verified</b>\nID: <code>{user_id}</code>")
            else:
                bot.answer_callback_query(call.id, "❌ You haven't joined the channel yet!", show_alert=True)

        elif call.data == "list_files":
            bot.send_chat_action(call.message.chat.id, 'typing')
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            
            if not files:
                bot.answer_callback_query(call.id, "📁 No files available yet!", show_alert=True)
                return

            text = "🛠 <b>Available Premium Files:</b>\n\n"
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files:
                name = os.path.splitext(f)[0]
                text += f"🔹 <code>/{name.lower()}</code>\n"
                markup.add(types.InlineKeyboardButton(f"📥 Download {name.replace('_', ' ').title()}", callback_data=f"dl_{f}"))
            
            markup.add(types.InlineKeyboardButton("🔙 Back to Home", callback_data="back_home"))
            bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data.startswith("dl_"):
            file_name = call.data.replace("dl_", "")
            send_file_logic(call.message, file_name)

        elif call.data == "back_home":
            bot.edit_message_caption(
                "🔥 <b>Main Menu</b>\n\nSelect an option below:", 
                call.message.chat.id, call.message.message_id, reply_markup=get_main_markup()
            )

        elif call.data == "user_stats":
            bot.answer_callback_query(call.id, "📊 Loading stats...")
            total_users = len(load_users())
            msg = (
                f"👤 <b>User Info</b>\n\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"🌟 Role: Premium Member\n"
                f"👥 Total Users: {total_users}\n"
                f"⏰ Time: {datetime.datetime.now().strftime('%I:%M %p')}"
            )
            bot.edit_message_caption(msg, call.message.chat.id, call.message.message_id, reply_markup=get_main_markup())

    except Exception as e:
        log_error(f"Callback Error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Something went wrong. Try again.", show_alert=True)

# --- FILE SENDING LOGIC ---
def send_file_logic(message, file_name):
    user_id = message.chat.id if hasattr(message, 'chat') else message.from_user.id
    
    if not is_user_joined(user_id):
        bot.send_message(message.chat.id, "❌ <b>Access Denied!</b> Join the channel first.", reply_markup=get_join_markup())
        return

    file_path = os.path.join(FILES_DIR, file_name)
    
    if os.path.exists(file_path):
        status_msg = bot.send_message(message.chat.id, f"⏳ <b>Preparing <code>{file_name}</code>...</b>")
        bot.send_chat_action(message.chat.id, 'upload_document')
        time.sleep(1)

        try:
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, 
                                  caption=f"✅ <b>File Delivered!</b>\n\n📂 <b>Name:</b> {file_name}\n🚀 <b>From:</b> @Dark_Unkwon_ModZ")
            bot.delete_message(message.chat.id, status_msg.message_id)
            log_to_channel(f"📥 <b>File Sent</b>\nUser: <code>{user_id}</code>\nFile: <code>{file_name}</code>")
        except Exception as e:
            bot.edit_message_text(f"❌ <b>Send Error:</b> {str(e)}", message.chat.id, status_msg.message_id)
            log_error(f"File Send Failed ({file_name}) to {user_id}: {e}")
    else:
        bot.send_message(message.chat.id, f"🚧 <b>File Not Found!</b>\n\n(<code>{file_name}</code>) ইদানীং সার্ভার থেকে সরানো হয়েছে।")

# --- MESSAGE HANDLER (Commands + Search) ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not is_user_joined(user_id):
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, "❌ <b>Access Restricted!</b>\nJoin @Dark_Unkwon_ModZ to use commands.", reply_markup=get_join_markup())
        return

    # Admin Commands (Fixed!)
    if user_id == ADMIN_ID:
        if text.lower() == "/admin":
            users = load_users()
            files = len([f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))])
            bot.reply_to(message, f"⚙️ <b>Admin Panel</b>\n\n👥 Total Users: {len(users)}\n📁 Files: {files}")
            return
        elif text.lower() == "/stats":
            users = load_users()
            bot.reply_to(message, f"📊 <b>Stats</b>\n\n👥 Total Users: {len(users)}\n📁 Files: {len(os.listdir(FILES_DIR))}")
            return
        elif text.lower().startswith("/broadcast "):
            broadcast_msg = text[12:]
            users = load_users()
            success = 0
            for uid in users:
                try:
                    bot.send_message(uid, f"📣 <b>Broadcast</b>\n\n{broadcast_msg}")
                    success += 1
                    time.sleep(0.05)
                except: pass
            bot.reply_to(message, f"✅ Broadcast sent to {success}/{len(users)} users.")
            return

    # Special Commands (Fixed!)
    if text.lower() == "/list":
        files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
        if not files:
            bot.reply_to(message, "📁 No files available.")
            return
        text = "🛠 <b>Available Files:</b>\n\n"
        for f in files:
            name = os.path.splitext(f)[0]
            text += f"🔹 <code>/{name.lower()}</code>\n"
        bot.reply_to(message, text)
        return

    # Command-based file request (e.g., /liteapk)
    if text.startswith('/'):
        cmd = text[1:].lower().split()[0]  # Ignore extra args
        
        if cmd == "start":
            return start_command(message)

        # Admin command check (again, safe guard)
        if user_id == ADMIN_ID and cmd == "admin":
            users = load_users()
            files = len([f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))])
            bot.reply_to(message, f"⚙️ <b>Admin Panel</b>\n\n👥 Total Users: {len(users)}\n📁 Files: {files}")
            return

        # File search
        files = os.listdir(FILES_DIR)
        found = None
        for f in files:
            if f.lower().startswith(cmd + ".") or f.lower() == cmd:
                found = f
                break
        
        if found:
            send_file_logic(message, found)
        else:
            bot.reply_to(message, "❓ <b>Unknown Command!</b>\n\nএই ফাইলটি সার্ভারে নেই। আমাদের /list চেক করুন।")
        return

    # Text search
    query = text.lower()
    files = [f for f in os.listdir(FILES_DIR) if query in f.lower()]
    
    if files:
        markup = types.InlineKeyboardMarkup()
        for f in files[:10]:
            markup.add(types.InlineKeyboardButton(f"📥 Get {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 <b>Found {len(files)} result(s) for '{text}':</b>", reply_markup=markup)
    else:
        bot.reply_to(message, "😔 দুঃখিত, এই নামে কোনো ফাইল পাওয়া যায়নি।")

# --- START BOT ---
if __name__ == "__main__":
    print("🚀 DUModZ-24-7-Bot is Running...")
    log_to_channel("🚀 <b>Bot is Online & Advanced System Loaded ✅</b>")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        log_error(f"Bot Crashed: {e}")
