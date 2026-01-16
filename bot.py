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
CHANNEL_URL = "https://t.me/Dark_Unkwon_ModZ"
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"
DB_FILE = "users.json"

# ফোল্ডার চেক
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- DATABASE HELPERS ---
def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return []

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(DB_FILE, 'w') as f: json.dump(users, f)

# --- UTILS ---
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

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
    time.sleep(0.5)
    
    if is_user_joined(user_id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome, {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>. You can now download files using buttons or commands (e.g., <code>/filename</code>).",
            reply_markup=get_main_markup()
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Restricted!</b>\n\nHi {message.from_user.first_name}, you must join our channel to use this bot and access premium mod files.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if call.data == "verify_user":
        if is_user_joined(user_id):
            bot.answer_callback_query(call.id, "✅ Verified Successfully!")
            # Animation effect
            animations = ["🔍 Checking database...", "🛡️ Verifying access...", "🔓 Unlocking files..."]
            for text in animations:
                bot.edit_message_caption(f"<b>{text}</b>", call.message.chat.id, call.message.message_id)
                time.sleep(0.6)
            
            bot.edit_message_caption(f"✅ <b>Verification Complete!</b>\n\nWelcome to <b>Dark Unkwon ModZ</b>. Enjoy your premium experience.", 
                                     call.message.chat.id, call.message.message_id, reply_markup=get_main_markup())
        else:
            bot.answer_callback_query(call.id, "❌ Error: You haven't joined yet!", show_alert=True)

    elif call.data == "list_files":
        bot.send_chat_action(call.message.chat.id, 'typing')
        files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
        
        if not files:
            bot.answer_callback_query(call.id, "📁 Database is empty!", show_alert=True)
            return

        text = "🛠 <b>Available Premium Files:</b>\n\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        for f in files:
            name = os.path.splitext(f)[0]
            text += f"🔹 <code>/{name}</code>\n"
            markup.add(types.InlineKeyboardButton(f"📥 Download {name.replace('_', ' ').title()}", callback_data=f"dl_{f}"))
        
        markup.add(types.InlineKeyboardButton("🔙 Back to Home", callback_data="back_home"))
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("dl_"):
        file_name = call.data.replace("dl_", "")
        send_file_logic(call.message, file_name)

    elif call.data == "back_home":
        bot.edit_message_caption("🔥 <b>Main Menu</b>\n\nSelect an option below:", 
                                 call.message.chat.id, call.message.message_id, reply_markup=get_main_markup())

    elif call.data == "user_stats":
        bot.answer_callback_query(call.id, "📊 Generating Stats...")
        msg = f"👤 <b>User Info</b>\n\n🆔 ID: <code>{user_id}</code>\n🌟 Role: Premium Member\n⏰ Time: {datetime.datetime.now().strftime('%I:%M %p')}"
        bot.edit_message_caption(msg, call.message.chat.id, call.message.message_id, reply_markup=get_main_markup())

# --- FILE SENDING LOGIC (With Animations) ---
def send_file_logic(message, file_name):
    user_id = message.chat.id if hasattr(message, 'chat') else message.from_user.id
    
    if not is_user_joined(user_id):
        bot.send_message(message.chat.id, "❌ <b>Access Denied!</b> Join the channel first.", reply_markup=get_join_markup())
        return

    file_path = os.path.join(FILES_DIR, file_name)
    
    if os.path.exists(file_path):
        # Notify user that bot is uploading
        status_msg = bot.send_message(message.chat.id, f"⏳ <b>Preparing <code>{file_name}</code>...</b>")
        bot.send_chat_action(message.chat.id, 'upload_document')
        time.sleep(1.5)
        
        try:
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, 
                                  caption=f"✅ <b>File Delivered!</b>\n\n📂 <b>Name:</b> {file_name}\n🚀 <b>From:</b> @Dark_Unkwon_ModZ")
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ <b>Error:</b> {str(e)}", message.chat.id, status_msg.message_id)
    else:
        bot.send_message(message.chat.id, f"🚧 <b>File Not Found!</b>\n\n(<code>{file_name}</code>) ইদানীং সার্ভার থেকে সরানো হয়েছে।")

# --- SLASH COMMAND & AUTO-FILE HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    if not is_user_joined(user_id):
        bot.send_chat_action(message.chat.id, 'typing')
        return bot.reply_to(message, "❌ <b>Access Restricted!</b>\nJoin @Dark_Unkwon_ModZ to use commands.", reply_markup=get_join_markup())

    # যদি কমান্ড হয় (যেমন /liteapk)
    if text.startswith('/'):
        cmd = text[1:].lower()
        
        # অ্যাডমিন কমান্ড চেক
        if cmd == "admin" and user_id == ADMIN_ID:
            users = load_users()
            bot.reply_to(message, f"⚙️ <b>Admin Panel</b>\n\n👥 Total Users: {len(users)}\n📁 Files: {len(os.listdir(FILES_DIR))}")
            return

        # ফাইল কমান্ড চেক (Dynamic)
        files = os.listdir(FILES_DIR)
        found = False
        for f in files:
            if f.lower().startswith(cmd):
                send_file_logic(message, f)
                found = True
                break
        
        if not found and cmd != "start":
            bot.reply_to(message, "❓ <b>Unknown Command!</b>\n\nএই ফাইলটি সার্ভারে নেই। আমাদের /list চেক করুন।")
    
    # সাধারণ টেক্সট সার্চ
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        query = text.lower()
        files = [f for f in os.listdir(FILES_DIR) if query in f.lower()]
        
        if files:
            markup = types.InlineKeyboardMarkup()
            for f in files:
                markup.add(types.InlineKeyboardButton(f"📥 Get {f}", callback_data=f"dl_{f}"))
            bot.reply_to(message, f"🔍 <b>Matching files found for '{text}':</b>", reply_markup=markup)
        else:
            bot.reply_to(message, "😔 দুঃখিত, এই নামে কোনো ফাইল পাওয়া যায়নি।")

# --- LOGGING ---
def send_log(status):
    try:
        now = datetime.datetime.now().strftime("%I:%M %p | %d-%m-%Y")
        msg = f"🚀 <b>Bot Update</b>\n\n📡 <b>Status:</b> {status}\n⏰ <b>Time:</b> {now}"
        bot.send_message(LOG_CHANNEL, msg)
    except: pass

# --- START BOT ---
if __name__ == "__main__":
    print("🚀 Premium Bot is Running...")
    send_log("Bot is Online & Advanced System Loaded ✅")
    bot.infinity_polling()
