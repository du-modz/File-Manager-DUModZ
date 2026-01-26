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
# আপনার দেওয়া URI
MONGO_URI = "mongodb+srv://dumodzinfo_db_user:B0FDJrCeHgr9ufSR@cluster0test.s3jjv7u.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0test"

# Required Channels
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"

# Initialize Bot
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- [ MONGODB DATABASE CONNECTION ] ---
# এখানে certifi ব্যবহার করা হয়েছে SSL এরর ফিক্স করার জন্য
try:
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=10000)
    # ডাটাবেস নাম DUModZ_Database_Live
    db = client['DUModZ_Database_Live']
    users_col = db['users']
    banned_col = db['banned']
    
    # কানেকশন চেক (Heartbeat)
    client.admin.command('ping')
    print("✅ MongoDB Connected Successfully and Database is Ready!")
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}")
    # ডাটাবেস কানেক্ট না হলে বট রান হবে না যাতে এরর না দেয়
    import sys
    sys.exit(1)

# Create files directory if not exists
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

# Global states
user_state = {}

# --- [ CORE DATABASE FUNCTIONS ] ---
def is_banned(user_id):
    try:
        return banned_col.find_one({"id": user_id}) is not None
    except: return False

def save_user_data(user):
    """ইউজার ডাটা ডাটাবেসে সেভ বা আপডেট করার জন্য"""
    try:
        uid = user.id
        full_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
        
        # ডাটাবেস আপডেট লজিক
        users_col.update_one(
            {"id": uid},
            {"$set": {
                "name": full_name,
                "username": user.username or "N/A",
                "last_active": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_member": is_joined(uid)
            }, "$setOnInsert": {
                "join_date": datetime.datetime.now().strftime("%Y-%m-%d")
            }},
            upsert=True
        )
    except Exception as e:
        print(f"Error in saving data: {e}")

# --- [ MEMBERSHIP CHECKER ] ---
def is_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel.strip(), user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

# --- [ KEYBOARDS / UI ] ---
def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("👤 My Profile", callback_data="show_profile")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Bot Stats", callback_data="show_stats"),
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL)
    )
    markup.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_main"))
    return markup

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_member"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("👥 User List", callback_data="admin_list")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home"))
    return markup

# --- [ MESSAGE HANDLERS ] ---
@bot.message_handler(commands=['start'])
def start_msg(message):
    uid = message.from_user.id
    if is_banned(uid):
        bot.send_message(message.chat.id, "❌ <b>You are banned!</b>", parse_mode="HTML")
        return

    # শুরুতে ডাটা সেভ হবে
    save_user_data(message.from_user)
    
    if is_joined(uid):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome, {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>.",
            reply_markup=get_main_markup(uid)
        )
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption="⚠️ <b>Access Denied!</b>\nPlease join our channels to continue.",
            reply_markup=get_join_markup()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    if is_banned(uid):
        bot.answer_callback_query(call.id, "❌ You are banned.", show_alert=True)
        return

    try:
        # User Logic
        if call.data == "verify_member":
            if is_joined(uid):
                bot.answer_callback_query(call.id, "✅ Verified!")
                bot.edit_message_caption("✅ <b>Welcome Back!</b> Access Granted.", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(uid))
                save_user_data(call.from_user)
            else:
                bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

        elif call.data == "list_files":
            files = os.listdir(FILES_DIR)
            if not files:
                bot.answer_callback_query(call.id, "📁 No files found!", show_alert=True)
                return
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files[:10]:
                markup.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            bot.edit_message_caption("📂 <b>Premium Files:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "show_profile":
            user_data = users_col.find_one({"id": uid})
            if user_data:
                profile = (f"👤 <b>User Profile</b>\n\n"
                           f"┣ 🆔 <b>ID:</b> <code>{uid}</code>\n"
                           f"┣ 👤 <b>Name:</b> {user_data['name']}\n"
                           f"┣ 📅 <b>Joined:</b> {user_data.get('join_date', 'N/A')}\n"
                           f"┗ ⭐ <b>Status:</b> Premium")
            else:
                profile = "❌ Profile data not found. Please /start again."
            
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            bot.edit_message_caption(profile, call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "show_stats":
            count = users_col.count_documents({})
            f_count = len(os.listdir(FILES_DIR))
            stats = f"📊 <b>Bot Stats</b>\n\n👥 Total Users: {count}\n📁 Total Files: {f_count}"
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            bot.edit_message_caption(stats, call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif call.data == "back_home":
            bot.edit_message_caption(f"🔥 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(uid))

        elif call.data.startswith("dl_"):
            send_file_logic(call.message, call.data.replace("dl_", ""))

        # Admin Logic
        elif call.data == "admin_main" and uid == ADMIN_ID:
            bot.edit_message_caption("🔐 <b>Admin Panel</b>", call.message.chat.id, call.message.message_id, reply_markup=get_admin_markup())

        elif call.data == "admin_list" and uid == ADMIN_ID:
            users = users_col.find().sort("_id", -1).limit(25)
            text = "👥 <b>Recent 25 Users:</b>\n\n"
            for u in users:
                text += f"• {u['name']} (<code>{u['id']}</code>)\n"
            bot.send_message(uid, text)

        elif call.data == "admin_broadcast" and uid == ADMIN_ID:
            bot.send_message(uid, "📩 <b>Enter message to broadcast:</b>")
            user_state[uid] = "bc"

        elif call.data == "admin_ban" and uid == ADMIN_ID:
            bot.send_message(uid, "🚫 <b>Send User ID to ban:</b>")
            user_state[uid] = "ban"

    except Exception as e:
        print(f"Callback Error: {e}")

def send_file_logic(message, filename):
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        bot.send_chat_action(message.chat.id, 'upload_document')
        with open(path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ <b>{filename}</b>")
    else:
        bot.send_message(message.chat.id, "❌ File not found.")

# --- [ TEXT HANDLER ] ---
@bot.message_handler(func=lambda m: True)
def on_text(message):
    uid = message.from_user.id
    if is_banned(uid): return

    # Admin actions
    if uid == ADMIN_ID and uid in user_state:
        state = user_state.pop(uid)
        if state == "bc":
            users = users_col.find()
            ok = 0
            for u in users:
                try:
                    bot.send_message(u['id'], f"📣 <b>Broadcast</b>\n\n{message.text}")
                    ok += 1
                except: pass
            bot.reply_to(message, f"✅ Sent to {ok} users.")
        elif state == "ban":
            try:
                target = int(message.text)
                banned_col.update_one({"id": target}, {"$set": {"id": target}}, upsert=True)
                bot.reply_to(message, f"🚫 User {target} banned.")
            except: bot.reply_to(message, "❌ Invalid ID.")
        return

    # Search Logic
    if is_joined(uid):
        matches = [f for f in os.listdir(FILES_DIR) if message.text.lower() in f.lower()]
        if matches:
            mk = types.InlineKeyboardMarkup()
            for f in matches[:5]:
                mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
            bot.reply_to(message, f"🔍 Found {len(matches)} files:", reply_markup=mk)

# --- [ START ] ---
if __name__ == "__main__":
    print("🚀 DUModZ Professional Bot Online...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
