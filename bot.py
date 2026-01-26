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

# --- MONGODB CONNECTION ---
try:
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client['DUModZ_Database']
    users_col = db['users']
    banned_col = db['banned']
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# --- BAN SYSTEM ---
def is_user_banned(user_id):
    return banned_col.find_one({"user_id": user_id}) is not None

# --- DATABASE LOGIC ---
def save_user_to_db(user):
    user_id = user.id
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    joined = is_user_joined(user_id)
    
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "name": name.strip() or f"User {user_id}",
            "username": user.username,
            "joined": joined,
            "last_seen": datetime.datetime.now().isoformat()
        }, "$setOnInsert": {"first_seen": datetime.datetime.now().isoformat()}},
        upsert=True
    )

# --- SAFE EDIT HELPERS ---
def safe_edit_caption(chat_id, message_id, caption, reply_markup=None):
    try:
        bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        if "message is not modified" not in str(e): print(f"[Edit Error] {e}")

# --- LOGGING ---
def log_to_channel(message):
    try:
        bot.send_message(LOG_CHANNEL, message, disable_web_page_preview=True)
    except: pass

# --- MEMBERSHIP CHECK ---
def is_user_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel.strip(), user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

# --- MARKUPS ---
def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for channel in REQUIRED_CHANNELS:
        url = f"https://t.me/{channel.strip().replace('@', '')}"
        markup.add(types.InlineKeyboardButton(f"📢 Join {channel}", url=url))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
    return markup

def get_main_markup(user_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 All Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("👤 My Profile", callback_data="user_profile")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL),
        types.InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats")
    )
    markup.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_bc"),
        types.InlineKeyboardButton("👥 User List", callback_data="admin_ulist")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export DB", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home")
    )
    return markup

# Global State
user_state = {}

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start_command(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "❌ <b>You are banned from using this bot!</b>")
        return
    
    save_user_to_db(message.from_user)
    bot.send_chat_action(message.chat.id, 'typing')
    
    if is_user_joined(message.from_user.id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome Back, {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>. Download the latest mods below.",
            reply_markup=get_main_markup(user_id=message.from_user.id)
        )
        log_to_channel(f"✅ User Start: {message.from_user.full_name} (<code>{message.from_user.id}</code>)")
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Restricted!</b>\n\nJoin our official channels to unlock premium files.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned!", show_alert=True)
        return

    try:
        if call.data == "verify_user":
            if is_user_joined(user_id):
                bot.answer_callback_query(call.id, "✅ Verified!")
                for stage in ["🔍 Checking Membership...", "🛡️ Security Verifying...", "🔓 Access Granted!"]:
                    safe_edit_caption(call.message.chat.id, call.message.message_id, f"<b>{stage}</b>")
                    time.sleep(0.5)
                safe_edit_caption(call.message.chat.id, call.message.message_id, "✅ <b>Verification Successful!</b>", reply_markup=get_main_markup(user_id))
                save_user_to_db(call.from_user)
            else:
                bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

        elif call.data == "list_files":
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📁 No files found!", show_alert=True)
                return
            
            text = "🛠 <b>Available Premium Files:</b>\n\nSelect a file to download:"
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files[:15]:
                markup.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back to Home", callback_data="back_home"))
            safe_edit_caption(call.message.chat.id, call.message.message_id, text, reply_markup=markup)

        elif call.data.startswith("dl_"):
            filename = call.data.replace("dl_", "")
            send_file_logic(call.message, filename)

        elif call.data == "user_profile":
            u = users_col.find_one({"user_id": user_id})
            text = (f"👤 <b>Premium Profile</b>\n\n"
                    f"┣ 🆔 <b>ID:</b> <code>{user_id}</code>\n"
                    f"┣ 👤 <b>Name:</b> {u['name']}\n"
                    f"┣ 📅 <b>Join Date:</b> {u['first_seen'][:10]}\n"
                    f"┗ ⭐ <b>Status:</b> Active")
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            safe_edit_caption(call.message.chat.id, call.message.message_id, text, reply_markup=markup)

        elif call.data == "bot_stats":
            total = users_col.count_documents({})
            msg = f"📊 <b>Stats Info</b>\n\n👥 Total Users: {total}\n📁 Total Files: {len(os.listdir(FILES_DIR))}"
            safe_edit_caption(call.message.chat.id, call.message.message_id, msg, reply_markup=get_main_markup(user_id))

        elif call.data == "back_home":
            safe_edit_caption(call.message.chat.id, call.message.message_id, "🔥 <b>Main Menu</b>", reply_markup=get_main_markup(user_id))

        # --- ADMIN CALLBACKS ---
        elif call.data == "admin_panel" and user_id == ADMIN_ID:
            safe_edit_caption(call.message.chat.id, call.message.message_id, "🔐 <b>Admin Control Panel</b>", reply_markup=get_admin_markup())

        elif call.data == "admin_bc" and user_id == ADMIN_ID:
            bot.send_message(user_id, "📩 <b>Enter Broadcast Message:</b>")
            user_state[user_id] = "bc"

        elif call.data == "admin_ban" and user_id == ADMIN_ID:
            bot.send_message(user_id, "🚫 <b>Send User ID to Ban:</b>")
            user_state[user_id] = "ban"

        elif call.data == "admin_unban" and user_id == ADMIN_ID:
            bot.send_message(user_id, "✅ <b>Send User ID to Unban:</b>")
            user_state[user_id] = "unban"

        elif call.data == "admin_ulist" and user_id == ADMIN_ID:
            users = users_col.find().sort("_id", -1).limit(20)
            text = "👥 <b>Recent Users:</b>\n\n"
            for u in users:
                text += f"• {u['name']} (<code>{u['user_id']}</code>)\n"
            bot.send_message(user_id, text)

        elif call.data == "admin_export" and user_id == ADMIN_ID:
            data = list(users_col.find({}, {"_id": 0}))
            with open("backup.json", "w") as f:
                json.dump(data, f, indent=2)
            with open("backup.json", "rb") as f:
                bot.send_document(user_id, f, caption="📤 DB Backup Exported")
            os.remove("backup.json")

    except Exception as e: print(f"[Callback Error] {e}")

# --- FILE LOGIC ---
def send_file_logic(message, filename):
    user_id = message.chat.id
    if not is_user_joined(user_id):
        bot.send_message(user_id, "❌ Join channels first!", reply_markup=get_join_markup())
        return
    
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        wait_msg = bot.send_message(user_id, f"⏳ Preparing <code>{filename}</code>...")
        bot.send_chat_action(user_id, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(user_id, f, caption=f"✅ <b>{filename}</b>\n\nShared by @Dark_Unkwon_ModZ")
            bot.delete_message(user_id, wait_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", user_id, wait_msg.message_id)
    else:
        bot.send_message(user_id, "🚧 File not found.")

# --- ALL MESSAGES HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if is_user_banned(user_id): return

    # Admin Action States
    if user_id == ADMIN_ID and user_id in user_state:
        state = user_state.pop(user_id)
        if state == "bc":
            all_users = users_col.find()
            count = 0
            for u in all_users:
                try:
                    bot.send_message(u['user_id'], f"📣 <b>Broadcast</b>\n\n{text}")
                    count += 1
                    time.sleep(0.05)
                except: pass
            bot.reply_to(message, f"✅ Broadcast sent to {count} users.")
        elif state == "ban":
            try:
                target = int(text)
                banned_col.update_one({"user_id": target}, {"$set": {"user_id": target, "date": datetime.datetime.now().isoformat()}}, upsert=True)
                bot.reply_to(message, f"🚫 User {target} banned.")
                log_to_channel(f"🚫 <b>Banned</b>: <code>{target}</code> by Admin.")
            except: bot.reply_to(message, "❌ Send a valid User ID.")
        elif state == "unban":
            try:
                target = int(text)
                banned_col.delete_one({"user_id": target})
                bot.reply_to(message, f"✅ User {target} unbanned.")
            except: bot.reply_to(message, "❌ Send a valid User ID.")
        return

    # Regular Commands & File search
    if text.startswith('/'):
        cmd = text[1:].lower()
        if cmd == "start": return start_command(message)
        if cmd == "admin" and user_id == ADMIN_ID:
            bot.send_photo(message.chat.id, BANNER_URL, caption="🔐 <b>Admin Panel</b>", reply_markup=get_admin_markup())
            return
        
        # Command based file finding
        for f in os.listdir(FILES_DIR):
            if f.lower().startswith(cmd):
                send_file_logic(message, f)
                return
    
    # Text Search Logic
    matches = [f for f in os.listdir(FILES_DIR) if text.lower() in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:5]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 Results for '{text}':", reply_markup=mk)

# --- RUN ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot is Online with MongoDB & Advanced UI...")
    log_to_channel("🟢 <b>Bot System Online</b>\nMongoDB Persistence Active.")
    bot.infinity_polling(skip_pending=True)
