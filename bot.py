import telebot
from telebot import types
import time
import os
import json
import datetime
import pymongo
import certifi
import threading

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

# --- DATABASE CONNECTION ---
try:
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client['DUModZ_Premium_DB']
    users_col = db['users']
    banned_col = db['banned']
    client.server_info()
    print("✅ MongoDB Connected Successfully")
except Exception as e:
    print(f"❌ DB Error: {e}")

# --- GLOBAL STATE ---
user_state = {} # {user_id: "action"}

# --- UTILS & HELPERS ---
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
    try:
        users_col.update_one(
            {"id": user.id},
            {"$set": {
                "name": (user.first_name or "") + (" " + user.last_name if user.last_name else ""),
                "username": user.username,
                "joined": is_user_joined(user.id),
                "last_seen": datetime.datetime.now().isoformat()
            }, "$setOnInsert": {"first_seen": datetime.datetime.now().isoformat()}},
            upsert=True
        )
    except Exception as e: print(f"Save Error: {e}")

def safe_edit(call, text, markup=None):
    try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=text,
            reply_markup=markup
        )
    except:
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
        except: pass

# --- MARKUPS (UI) ---
def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
    return markup

def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 Premium Files", callback_data="list_files"),
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
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_bc"),
        types.InlineKeyboardButton("👥 User List", callback_data="admin_users")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban", callback_data="admin_ban_info"),
        types.InlineKeyboardButton("✅ Unban", callback_data="admin_unban_info")
    )
    markup.add(
        types.InlineKeyboardButton("📤 Export DB", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home")
    )
    return markup

# --- CORE HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
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
def handle_queries(call):
    uid = call.from_user.id
    if is_user_banned(uid):
        bot.answer_callback_query(call.id, "❌ Banned.", show_alert=True)
        return

    try:
        if call.data == "verify_user":
            if is_user_joined(uid):
                bot.answer_callback_query(call.id, "✅ Verified!")
                for t in ["🔍 Checking Membership...", "🛡️ Security Syncing...", "🔓 Access Granted!"]:
                    safe_edit(call, f"<b>{t}</b>")
                    time.sleep(0.4)
                safe_edit(call, "✅ <b>Verification Successful!</b>", get_main_markup(uid))
                save_user(call.from_user)
            else:
                bot.answer_callback_query(call.id, "❌ Please join all channels!", show_alert=True)

        elif call.data == "list_files":
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📁 No files available!", show_alert=True)
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files[:15]:
                markup.add(types.InlineKeyboardButton(f"📥 {f.replace('_',' ')}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home"))
            safe_edit(call, "🛠 <b>Available Premium Files:</b>\n\nChoose a file to download:", markup)

        elif call.data.startswith("dl_"):
            filename = call.data.replace("dl_", "")
            send_file_logic(call.message, filename)

        elif call.data == "my_profile":
            u = users_col.find_one({"id": uid})
            text = (f"👤 <b>Premium Profile</b>\n\n"
                    f"┣ 🆔 <b>ID:</b> <code>{uid}</code>\n"
                    f"┣ 👤 <b>Name:</b> {u['name']}\n"
                    f"┣ 📅 <b>Joined:</b> {u['first_seen'][:10]}\n"
                    f"┗ ⭐ <b>Status:</b> Active")
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home"))
            safe_edit(call, text, markup)

        elif call.data == "user_stats":
            total = users_col.count_documents({})
            msg = f"📊 <b>Bot Statistics</b>\n\n👥 Total Users: {total}\n📁 Available Files: {len(os.listdir(FILES_DIR))}"
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back Home", callback_data="back_home"))
            safe_edit(call, msg, markup)

        elif call.data == "back_home":
            safe_edit(call, "🔥 <b>Main Menu</b>\nSelect an option to proceed:", get_main_markup(uid))

        # --- ADMIN PANEL ---
        elif call.data == "admin_panel" and uid == ADMIN_ID:
            safe_edit(call, "🔐 <b>Admin Control Panel</b>", get_admin_markup())

        elif call.data == "admin_bc" and uid == ADMIN_ID:
            bot.send_message(uid, "📩 <b>Enter Broadcast Message (Text Only):</b>")
            user_state[uid] = "bc"

        elif call.data == "admin_ban_info" and uid == ADMIN_ID:
            bot.send_message(uid, "🚫 <b>Send User ID to Ban:</b>")
            user_state[uid] = "ban"

        elif call.data == "admin_unban_info" and uid == ADMIN_ID:
            bot.send_message(uid, "✅ <b>Send User ID to Unban:</b>")
            user_state[uid] = "unban"

        elif call.data == "admin_users" and uid == ADMIN_ID:
            users = users_col.find().sort("_id", -1).limit(20)
            txt = "👥 <b>Recent Users:</b>\n\n"
            for u in users:
                txt += f"• <a href='tg://user?id={u['id']}'>{u['name']}</a> (<code>{u['id']}</code>)\n"
            bot.send_message(uid, txt)

        elif call.data == "admin_export" and uid == ADMIN_ID:
            data = list(users_col.find({}, {"_id": 0}))
            with open("users.json", "w") as f:
                json.dump(data, f, indent=2, default=str)
            with open("users.json", "rb") as f:
                bot.send_document(uid, f, caption="📤 Database Export Successful.")
            os.remove("users.json")

    except Exception as e: print(f"Callback Error: {e}")

# --- FILE SENDING ---
def send_file_logic(message, filename):
    uid = message.chat.id
    if not is_user_joined(uid):
        bot.send_message(uid, "❌ Join channels first!", reply_markup=get_join_markup())
        return
    
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        wait = bot.send_message(uid, f"⏳ Preparing <code>{filename}</code>...")
        bot.send_chat_action(uid, 'upload_document')
        try:
            with open(path, 'rb') as f:
                bot.send_document(uid, f, caption=f"✅ <b>{filename}</b>\nUploaded by @Dark_Unkwon_ModZ")
            bot.delete_message(uid, wait.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", uid, wait.message_id)
    else:
        bot.send_message(uid, "🚧 File not found.")

# --- ALL MESSAGES & SEARCH ---
@bot.message_handler(func=lambda m: True)
def on_message(message):
    uid = message.from_user.id
    text = message.text.strip()

    if is_user_banned(uid): return

    # Admin Action
    if uid == ADMIN_ID and uid in user_state:
        state = user_state.pop(uid)
        if state == "bc":
            all_u = users_col.find()
            count = 0
            for u in all_u:
                try:
                    bot.send_message(u['id'], f"📣 <b>Broadcast Notice</b>\n\n{text}")
                    count += 1
                    time.sleep(0.05)
                except: pass
            bot.reply_to(message, f"✅ Sent to {count} users.")
        elif state == "ban":
            try:
                target = int(text)
                banned_col.update_one({"id": target}, {"$set": {"id": target, "by": uid}}, upsert=True)
                bot.reply_to(message, f"🚫 User {target} banned.")
            except: bot.reply_to(message, "❌ Invalid User ID.")
        elif state == "unban":
            try:
                target = int(text)
                banned_col.delete_one({"id": target})
                bot.reply_to(message, f"✅ User {target} unbanned.")
            except: bot.reply_to(message, "❌ Invalid User ID.")
        return

    # User Command & Search
    if not is_user_joined(uid):
        bot.reply_to(message, "❌ Join channels first.", reply_markup=get_join_markup())
        return

    if text.startswith('/'):
        cmd = text[1:].lower()
        if cmd == "start": return start_cmd(message)
        if cmd == "admin" and uid == ADMIN_ID:
            bot.send_photo(message.chat.id, BANNER_URL, caption="🔐 <b>Admin Panel</b>", reply_markup=get_admin_markup())
            return
        # Slash Command File Search
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
        bot.reply_to(message, f"🔍 Found {len(matches)} results for '{text}':", reply_markup=mk)
    else:
        bot.reply_to(message, "😔 No files matching your search.")

# --- RUN BOT ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot Started...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
