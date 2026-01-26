import telebot
from telebot import types
import pymongo
import certifi
import os
import time
import datetime
import json

# --- [ CONFIGURATION ] ---
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"
MONGO_URI = "mongodb+srv://dumodzinfo_db_user:B0FDJrCeHgr9ufSR@cluster0test.s3jjv7u.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0test"

# Required Channels
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"

# Initialize Bot
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- [ MONGODB SETUP ] ---
try:
    # Adding certifi for CA Bundle issues and dns timeout
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client['DUModZ_Cloud_Final']
    users_col = db['users']
    banned_col = db['banned']
    client.server_info() # Connection check
    print("✅ MongoDB Connection Successful!")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")

# Create files directory if not exists
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

# Global states for Admin
user_state = {} # {user_id: action}

# --- [ DATABASE UTILS ] ---
def is_banned(user_id):
    try:
        return banned_col.find_one({"id": user_id}) is not None
    except: return False

def save_user(user):
    try:
        uid = user.id
        name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
        users_col.update_one(
            {"id": uid},
            {"$set": {
                "name": name,
                "username": user.username or "N/A",
                "last_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, "$setOnInsert": {"first_seen": datetime.datetime.now().strftime("%Y-%m-%d")}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving user: {e}")

# --- [ JOIN CHECKER ] ---
def is_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel.strip(), user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

# --- [ UI MARKUPS ] ---
def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 All Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats"),
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL)
    )
    markup.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return markup

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_bc"),
        types.InlineKeyboardButton("👥 User List", callback_data="admin_ulist")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Unban", callback_data="admin_unban")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export DB", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home")
    )
    return markup

# --- [ CORE LOGIC ] ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    uid = message.from_user.id
    if is_banned(uid):
        bot.send_message(message.chat.id, "❌ <b>Access Denied: You are banned!</b>", parse_mode="HTML")
        return

    save_user(message.from_user)
    
    if is_joined(uid):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>. Explore our latest mods below.",
            reply_markup=get_main_markup(uid)
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption="⚠️ <b>Access Restricted!</b>\n\nYou must join all our official channels to continue using this bot.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_manager(call):
    uid = call.from_user.id
    if is_banned(uid):
        bot.answer_callback_query(call.id, "❌ Banned.")
        return

    try:
        # User Actions
        if call.data == "verify_user":
            if is_joined(uid):
                bot.answer_callback_query(call.id, "✅ Verified!")
                bot.edit_message_caption("✅ <b>Verified! Access Granted.</b>", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(uid))
            else:
                bot.answer_callback_query(call.id, "❌ Not joined all channels!", show_alert=True)

        elif call.data == "list_files":
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📁 No files found in directory!", show_alert=True)
                return
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files[:15]:
                markup.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home"))
            bot.edit_message_caption("🛠 <b>Premium Files Ready:</b>\nSelect a file to download:", call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "my_profile":
            data = users_col.find_one({"id": uid})
            profile = (f"👤 <b>Premium Profile Info</b>\n\n"
                       f"┣ 🆔 <b>ID:</b> <code>{uid}</code>\n"
                       f"┣ 👤 <b>Name:</b> {data['name']}\n"
                       f"┣ 📅 <b>Joined:</b> {data.get('first_seen', 'N/A')}\n"
                       f"┗ ⭐ <b>Status:</b> {'Premium Member' if is_joined(uid) else 'Basic Member'}")
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home"))
            bot.edit_message_caption(profile, call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "bot_stats":
            total_u = users_col.count_documents({})
            total_f = len(os.listdir(FILES_DIR))
            stats = (f"📊 <b>Bot Live Statistics</b>\n\n"
                     f"┣ 👥 <b>Total Users:</b> {total_u}\n"
                     f"┣ 📁 <b>Files Stored:</b> {total_f}\n"
                     f"┗ 🛡️ <b>Database:</b> MongoDB Cloud")
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home"))
            bot.edit_message_caption(stats, call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "back_home":
            bot.edit_message_caption(f"🔥 <b>Main Menu</b>\nSelect an option to proceed:", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(uid))

        elif call.data.startswith("dl_"):
            filename = call.data.replace("dl_", "")
            send_file_logic(call.message, filename)

        # Admin Actions
        elif call.data == "admin_panel" and uid == ADMIN_ID:
            bot.edit_message_caption("🔐 <b>Admin Control Panel</b>", call.message.chat.id, call.message.message_id, reply_markup=get_admin_markup())

        elif call.data == "admin_ulist" and uid == ADMIN_ID:
            users = users_col.find().sort("_id", -1).limit(30)
            txt = "👥 <b>Recent 30 Users:</b>\n\n"
            for u in users:
                txt += f"• <a href='tg://user?id={u['id']}'>{u['name']}</a> (<code>{u['id']}</code>)\n"
            bot.send_message(uid, txt)

        elif call.data == "admin_bc" and uid == ADMIN_ID:
            bot.send_message(uid, "📩 <b>Enter Broadcast Message:</b>")
            user_state[uid] = "broadcasting"

        elif call.data == "admin_ban" and uid == ADMIN_ID:
            bot.send_message(uid, "🚫 <b>Send User ID to ban:</b>")
            user_state[uid] = "banning"

        elif call.data == "admin_unban" and uid == ADMIN_ID:
            bot.send_message(uid, "✅ <b>Send User ID to unban:</b>")
            user_state[uid] = "unbanning"

        elif call.data == "admin_export" and uid == ADMIN_ID:
            data = list(users_col.find({}, {"_id": 0}))
            with open("users_dump.json", "w") as f:
                json.dump(data, f, indent=2, default=str)
            with open("users_dump.json", "rb") as f:
                bot.send_document(uid, f, caption="📂 Full User DB Backup")
            os.remove("users_dump.json")

    except Exception as e: print(f"Callback Error: {e}")

# --- [ FILE DOWNLOADER ] ---
def send_file_logic(message, filename):
    uid = message.chat.id
    if not is_joined(uid):
        bot.send_message(uid, "❌ Join channels first!", reply_markup=get_join_markup())
        return
    
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        bot.send_chat_action(uid, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(uid, f, caption=f"✅ <b>{filename}</b>\nUploaded by @Dark_Unkwon_ModZ")
        except Exception as e:
            bot.send_message(uid, f"❌ Send Error: {e}")
    else:
        bot.send_message(uid, "🚧 File not found.")

# --- [ MESSAGE HANDLER (SEARCH + ADMIN INPUT) ] ---
@bot.message_handler(func=lambda m: True)
def text_manager(message):
    uid = message.from_user.id
    text = message.text

    if is_banned(uid): return

    # Admin Logic
    if uid == ADMIN_ID and uid in user_state:
        action = user_state.pop(uid)
        if action == "broadcasting":
            all_users = users_col.find()
            count = 0
            for u in all_users:
                try:
                    bot.send_message(u['id'], f"📣 <b>Broadcast Notice</b>\n\n{text}")
                    count += 1
                except: pass
            bot.reply_to(message, f"✅ Sent to {count} users.")
        elif action == "banning":
            try:
                target = int(text)
                banned_col.update_one({"id": target}, {"$set": {"id": target}}, upsert=True)
                bot.reply_to(message, f"🚫 User {target} Banned.")
            except: bot.reply_to(message, "❌ Invalid ID.")
        elif action == "unbanning":
            try:
                target = int(text)
                banned_col.delete_one({"id": target})
                bot.reply_to(message, f"✅ User {target} Unbanned.")
            except: bot.reply_to(message, "❌ Invalid ID.")
        return

    # Regular Search Logic
    if not is_joined(uid): return

    if text.startswith('/'):
        cmd = text[1:].lower()
        if cmd == "admin" and uid == ADMIN_ID:
            bot.send_photo(message.chat.id, BANNER_URL, caption="🔐 <b>Admin Control</b>", reply_markup=get_admin_markup())
            return
        # Slash command file search
        for f in os.listdir(FILES_DIR):
            if f.lower().startswith(cmd):
                send_file_logic(message, f)
                return

    # Keyword Search
    matches = [f for f in os.listdir(FILES_DIR) if text.lower() in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 Results for '{text}':", reply_markup=mk)

# --- [ START BOT ] ---
if __name__ == "__main__":
    print("🚀 DUModZ Professional Bot Online...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
