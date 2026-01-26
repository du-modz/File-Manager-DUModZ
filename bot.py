import telebot
from telebot import types
import time
import os
import json
import datetime
import pymongo
import certifi

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"
MONGO_URI = "mongodb+srv://dumodzinfo_db_user:B0FDJrCeHgr9ufSR@cluster0test.s3jjv7u.mongodb.net/?appName=Cluster0test"

# List of all required channels
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"

os.makedirs(FILES_DIR, exist_ok=True)
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- MONGODB SETUP ---
client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['DUModZ_DB']
users_col = db['users']
banned_col = db['banned']

# --- DATA LOGIC ---
def is_user_banned(user_id):
    return banned_col.find_one({"id": user_id}) is not None

def save_user(user: types.User):
    user_id = user.id
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    joined = is_user_joined(user_id)
    
    users_col.update_one(
        {"id": user_id},
        {"$set": {
            "name": name.strip(),
            "username": user.username,
            "joined": joined,
            "last_seen": datetime.datetime.now().isoformat()
        }, "$setOnInsert": {"first_seen": datetime.datetime.now().isoformat()}},
        upsert=True
    )

# --- UI HELPERS ---
def safe_edit_caption(chat_id, message_id, caption, reply_markup=None):
    try:
        bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        if "message is not modified" not in str(e): print(f"Edit Error: {e}")

# --- UTILS ---
def is_user_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel.strip(), user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for channel in REQUIRED_CHANNELS:
        url = f"https://t.me/{channel.replace('@', '')}"
        markup.add(types.InlineKeyboardButton(f"📢 Join {channel}", url=url))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
    return markup

def get_main_markup(user_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 All Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL),
        types.InlineKeyboardButton("📊 Stats", callback_data="user_stats")
    )
    markup.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast_info"),
        types.InlineKeyboardButton("👥 User List", callback_data="admin_user_list")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban", callback_data="admin_ban_info"),
        types.InlineKeyboardButton("✅ Unban", callback_data="admin_unban_info")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export Data", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home")
    )
    return markup

# Global state for admin input
user_state = {}

# --- CORE HANDLERS ---
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ <b>You are banned from using this bot.</b>")
        return
    
    save_user(message.from_user)
    bot.send_chat_action(message.chat.id, 'typing')
    
    if is_user_joined(user_id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome, {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>. Use the buttons below to explore.",
            reply_markup=get_main_markup(user_id=user_id)
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Restricted!</b>\n\nYou must join all our required channels to continue using this bot.",
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
                bot.answer_callback_query(call.id, "✅ Verified!")
                for txt in ["🔍 Checking database...", "🛡️ Security Bypass...", "🔓 Access Granted!"]:
                    safe_edit_caption(call.message.chat.id, call.message.message_id, f"<b>{txt}</b>")
                    time.sleep(0.5)
                safe_edit_caption(call.message.chat.id, call.message.message_id, "✅ <b>Verification Complete!</b>", reply_markup=get_main_markup(user_id=user_id))
                save_user(call.from_user)
            else:
                bot.answer_callback_query(call.id, "❌ Not joined all channels!", show_alert=True)

        elif call.data == "list_files":
            # AUTO-REFRESH: Dynamic scanning of the 'files' folder
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📁 No files found in the folder!", show_alert=True)
                return
            
            text = "🛠 <b>Available Premium Files:</b>\n\n"
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files[:20]: # Limit 20 for UI
                name = os.path.splitext(f)[0].replace('_', ' ').title()
                markup.add(types.InlineKeyboardButton(f"📥 {name}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home"))
            safe_edit_caption(call.message.chat.id, call.message.message_id, text, reply_markup=markup)

        elif call.data.startswith("dl_"):
            send_file_logic(call.message, call.data.replace("dl_", ""))

        elif call.data == "back_home":
            safe_edit_caption(call.message.chat.id, call.message.message_id, "🔥 <b>Main Menu</b>", reply_markup=get_main_markup(user_id=user_id))

        elif call.data == "my_profile":
            u = users_col.find_one({"id": user_id})
            text = (f"👤 <b>Your Premium Profile</b>\n\n"
                    f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                    f"👤 <b>Name:</b> {u['name']}\n"
                    f"📅 <b>Joined:</b> {u['first_seen'][:10]}\n"
                    f"⭐ <b>Status:</b> {'Active' if is_user_joined(user_id) else 'Inactive'}")
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            safe_edit_caption(call.message.chat.id, call.message.message_id, text, reply_markup=markup)

        elif call.data == "user_stats":
            total = users_col.count_documents({})
            msg = f"📊 <b>Bot Statistics</b>\n\n👥 Total Users: {total}\n📁 Files Available: {len(os.listdir(FILES_DIR))}"
            safe_edit_caption(call.message.chat.id, call.message.message_id, msg, reply_markup=get_main_markup(user_id=user_id))

        # --- ADMIN PANEL LOGIC ---
        elif call.data == "admin_panel":
            if user_id != ADMIN_ID: return
            safe_edit_caption(call.message.chat.id, call.message.message_id, "🔐 <b>Admin Control Panel</b>", reply_markup=get_admin_markup())

        elif call.data == "admin_broadcast_info":
            bot.send_message(user_id, "📩 <b>Send me the message for broadcast:</b>")
            user_state[user_id] = "broadcast"

        elif call.data == "admin_ban_info":
            bot.send_message(user_id, "🚫 <b>Send User ID to Ban:</b>")
            user_state[user_id] = "ban"

        elif call.data == "admin_unban_info":
            bot.send_message(user_id, "✅ <b>Send User ID to Unban:</b>")
            user_state[user_id] = "unban"

        elif call.data == "admin_user_list":
            users = users_col.find().sort("_id", -1).limit(30)
            text = "👥 <b>Recent 30 Users:</b>\n\n"
            for u in users:
                text += f"• <a href='tg://user?id={u['id']}'>{u['name']}</a> (<code>{u['id']}</code>)\n"
            bot.send_message(user_id, text)

        elif call.data == "admin_export":
            all_users = list(users_col.find())
            with open("users_db.json", "w") as f:
                json.dump(all_users, f, default=str, indent=2)
            with open("users_db.json", "rb") as f:
                bot.send_document(user_id, f, caption="📤 Database Backup")
            os.remove("users_db.json")

    except Exception as e:
        print(f"Error: {e}")

# --- FILE SENDING ---
def send_file_logic(message, file_name):
    user_id = message.chat.id
    if not is_user_joined(user_id):
        bot.send_message(user_id, "❌ Join channel first!", reply_markup=get_join_markup())
        return
    
    path = os.path.join(FILES_DIR, file_name)
    if os.path.exists(path):
        prep = bot.send_message(user_id, f"⏳ Preparing <code>{file_name}</code>...")
        bot.send_chat_action(user_id, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(user_id, f, caption=f"✅ <b>{file_name}</b>\nFrom @Dark_Unkwon_ModZ")
            bot.delete_message(user_id, prep.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", user_id, prep.message_id)
    else:
        bot.send_message(user_id, "🚧 File not found.")

# --- MESSAGE HANDLER (Commands + Admin) ---
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if is_user_banned(user_id): return

    # Admin State Logic
    if user_id == ADMIN_ID and user_id in user_state:
        state = user_state.pop(user_id)
        if state == "broadcast":
            all_u = users_col.find()
            success = 0
            for u in all_u:
                try:
                    bot.send_message(u['id'], f"📣 <b>Broadcast Notice</b>\n\n{text}")
                    success += 1
                    time.sleep(0.05)
                except: pass
            bot.reply_to(message, f"✅ Broadcast sent to {success} users.")
        elif state == "ban":
            try:
                target = int(text)
                banned_col.update_one({"id": target}, {"$set": {"id": target, "by": user_id}}, upsert=True)
                bot.reply_to(message, f"🚫 User {target} banned.")
            except: bot.reply_to(message, "❌ Invalid ID.")
        elif state == "unban":
            try:
                target = int(text)
                banned_col.delete_one({"id": target})
                bot.reply_to(message, f"✅ User {target} unbanned.")
            except: bot.reply_to(message, "❌ Invalid ID.")
        return

    # User Commands
    if text.startswith('/'):
        cmd = text[1:].lower()
        if cmd == "start": return start_command(message)
        if cmd == "list":
            files = os.listdir(FILES_DIR)
            bot.reply_to(message, "📂 <b>Files:</b>\n" + "\n".join([f"• <code>/{os.path.splitext(f)[0]}</code>" for f in files]))
            return
        # Automatic folder-based command response
        for f in os.listdir(FILES_DIR):
            if f.lower().startswith(cmd):
                send_file_logic(message, f)
                return

    # Text search logic
    matches = [f for f in os.listdir(FILES_DIR) if text.lower() in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:5]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 Results for '{text}':", reply_markup=mk)

# --- START ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot Running with MongoDB Persistence...")
    bot.infinity_polling(skip_pending=True)
