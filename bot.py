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

# Required Channels
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"

os.makedirs(FILES_DIR, exist_ok=True)
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- MONGODB DATABASE SETUP ---
try:
    # Use certifi for secure connection
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client['DUModZ_Cloud_V2']
    users_col = db['users']
    banned_col = db['banned']
    client.server_info() # Connection check
    print("✅ MongoDB Connected: All Systems Go!")
except Exception as e:
    print(f"❌ Database Error: {e}")

# --- GLOBAL STATE ---
user_state = {}

# --- HELPER FUNCTIONS ---
def is_user_banned(user_id):
    try:
        return banned_col.find_one({"id": user_id}) is not None
    except: return False

def is_user_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel.strip(), user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

def save_user(user):
    """Saves or updates user data in MongoDB"""
    try:
        uid = user.id
        name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
        users_col.update_one(
            {"id": uid},
            {"$set": {
                "name": name.strip(),
                "username": user.username,
                "last_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, "$setOnInsert": {"first_seen": datetime.datetime.now().strftime("%Y-%m-%d")}},
            upsert=True
        )
    except Exception as e: print(f"DB Update Error: {e}")

def get_stats():
    """Returns total users and files"""
    try:
        total_users = users_col.count_documents({})
        total_files = len([f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))])
        return total_users, total_files
    except: return 0, 0

# --- MARKUPS (UI DESIGN) ---
def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 All Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL),
        types.InlineKeyboardButton("📊 Bot Stats", callback_data="user_stats")
    )
    markup.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_bc"),
        types.InlineKeyboardButton("👥 User List", callback_data="admin_user_list")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_ui"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_ui")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export DB", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")
    )
    return markup

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
    return markup

# --- CORE HANDLERS ---
@bot.message_handler(commands=['start'])
def start_command(message):
    uid = message.from_user.id
    if is_user_banned(uid):
        bot.reply_to(message, "❌ <b>You are banned from using this bot!</b>")
        return
    
    save_user(message.from_user)
    
    if is_user_joined(uid):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome, {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>. Explore our latest mods below.",
            reply_markup=get_main_markup(uid)
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Restricted!</b>\n\nYou must join all our required channels to continue using this bot.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    if is_user_banned(uid):
        bot.answer_callback_query(call.id, "❌ Banned.")
        return

    try:
        if call.data == "verify_user":
            if is_user_joined(uid):
                bot.answer_callback_query(call.id, "✅ Verified!")
                bot.edit_message_caption("✅ <b>Verification Successful!</b>\nWelcome to DUModZ Premium.", 
                                         call.message.chat.id, call.message.message_id, 
                                         reply_markup=get_main_markup(uid))
                save_user(call.from_user)
            else:
                bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

        elif call.data == "list_files":
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📁 No files found!", show_alert=True)
                return
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files[:15]:
                markup.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            bot.edit_message_caption("🛠 <b>Premium Files:</b>\nSelect a file to download:", 
                                     call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "my_profile":
            u_data = users_col.find_one({"id": uid})
            if u_data:
                profile_text = (
                    f"👤 <b>Your Premium Profile</b>\n\n"
                    f"┣ 🆔 <b>ID:</b> <code>{uid}</code>\n"
                    f"┣ 👤 <b>Name:</b> {u_data['name']}\n"
                    f"┣ 📅 <b>Joined:</b> {u_data.get('first_seen', 'N/A')}\n"
                    f"┗ ⭐ <b>Status:</b> {'Active User' if is_user_joined(uid) else 'Guest'}"
                )
            else:
                profile_text = "❌ <b>Profile Data Not Found!</b> Please /start again."
            
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            bot.edit_message_caption(profile_text, call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "user_stats":
            total_u, total_f = get_stats()
            stats_text = (
                f"📊 <b>Bot Global Statistics</b>\n\n"
                f"┣ 👥 <b>Total Users:</b> {total_u}\n"
                f"┣ 📁 <b>Total Files:</b> {total_f}\n"
                f"┗ 🛡️ <b>Database:</b> MongoDB Cloud"
            )
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            bot.edit_message_caption(stats_text, call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "back_home":
            bot.edit_message_caption(f"🔥 <b>Main Menu</b>\nChoose an option below:", 
                                     call.message.chat.id, call.message.message_id, 
                                     reply_markup=get_main_markup(uid))

        elif call.data.startswith("dl_"):
            send_file_logic(call.message, call.data.replace("dl_", ""))

        # --- ADMIN CALLBACKS ---
        elif call.data == "admin_panel" and uid == ADMIN_ID:
            bot.edit_message_caption("🔐 <b>Admin Control Panel</b>", 
                                     call.message.chat.id, call.message.message_id, 
                                     reply_markup=get_admin_markup())

        elif call.data == "admin_user_list" and uid == ADMIN_ID:
            users = users_col.find().sort("_id", -1).limit(25)
            user_list_text = "👥 <b>Recent 25 Users:</b>\n\n"
            for u in users:
                user_list_text += f"• <a href='tg://user?id={u['id']}'>{u['name']}</a> (<code>{u['id']}</code>)\n"
            bot.send_message(uid, user_list_text)

        elif call.data == "admin_bc" and uid == ADMIN_ID:
            bot.send_message(uid, "📩 <b>Send broadcast message:</b>")
            user_state[uid] = "broadcasting"

        elif call.data == "admin_ban_ui" and uid == ADMIN_ID:
            bot.send_message(uid, "🚫 <b>Send User ID to ban:</b>")
            user_state[uid] = "banning"

        elif call.data == "admin_export" and uid == ADMIN_ID:
            data = list(users_col.find({}, {"_id": 0}))
            with open("users_backup.json", "w") as f:
                json.dump(data, f, indent=2)
            with open("users_backup.json", "rb") as f:
                bot.send_document(uid, f, caption="📂 Database Backup")
            os.remove("users_backup.json")

    except Exception as e: print(f"Callback Error: {e}")

# --- FILE LOGIC ---
def send_file_logic(message, filename):
    uid = message.chat.id
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        bot.send_chat_action(uid, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(uid, f, caption=f"✅ <b>{filename}</b>\nShared by @Dark_Unkwon_ModZ")
        except Exception as e: bot.send_message(uid, f"❌ Send Error: {e}")
    else:
        bot.send_message(uid, "🚧 File not found.")

# --- MESSAGE HANDLER ---
@bot.message_handler(func=lambda m: True)
def message_handler(message):
    uid = message.from_user.id
    text = message.text

    # Admin Input States
    if uid == ADMIN_ID and uid in user_state:
        state = user_state.pop(uid)
        if state == "broadcasting":
            all_users = users_col.find()
            count = 0
            for u in all_users:
                try:
                    bot.send_message(u['id'], f"📣 <b>Broadcast Notice</b>\n\n{text}")
                    count += 1
                except: pass
            bot.reply_to(message, f"✅ Broadcast sent to {count} users.")
        elif state == "banning":
            try:
                target = int(text)
                banned_col.update_one({"id": target}, {"$set": {"id": target}}, upsert=True)
                bot.reply_to(message, f"🚫 User {target} banned.")
            except: bot.reply_to(message, "❌ Invalid ID.")
        return

    # User Commands
    if text.startswith('/'):
        cmd = text[1:].lower()
        if cmd == "start": return start_command(message)
        if cmd == "admin" and uid == ADMIN_ID:
            bot.send_photo(message.chat.id, BANNER_URL, caption="🔐 <b>Admin Panel</b>", reply_markup=get_admin_markup())
            return
        
        # Command search
        for f in os.listdir(FILES_DIR):
            if f.lower().startswith(cmd):
                send_file_logic(message, f)
                return

    # Normal Search
    matches = [f for f in os.listdir(FILES_DIR) if text.lower() in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:5]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 Found {len(matches)} files for '{text}':", reply_markup=mk)

# --- RUN ---
if __name__ == "__main__":
    print("🚀 DUModZ Professional Bot Started...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
