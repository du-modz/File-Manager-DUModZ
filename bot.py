import telebot
from telebot import types
import time
import os
import json
import datetime
import pymongo
import certifi
import sys

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 8504263842
LOG_CHANNEL = "@dumodzbotmanager"
MONGO_URI = "mongodb+srv://dumodzinfo_db_user:B0FDJrCeHgr9ufSR@cluster0test.s3jjv7u.mongodb.net/?appName=Cluster0test"

# Required channels
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]

BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
WEBSITE_URL = "https://darkunkwon-modz.blogspot.com"
FILES_DIR = "files"

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- MONGODB CONNECTION ---
try:
    # Adding timeout to prevent hanging
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client['DUModZ_Cloud_DB']
    users_col = db['users']
    banned_col = db['banned']
    client.server_info() # Test connection
    print("✅ MongoDB Connected!")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")
    print("⚠️ Continuing without DB persistence (Limited Mode)...")

# --- CORE UTILS ---
def is_user_banned(user_id):
    try:
        return banned_col.find_one({"user_id": user_id}) is not None
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
            {"user_id": user.id},
            {"$set": {
                "name": user.first_name,
                "username": user.username,
                "last_seen": datetime.datetime.now().isoformat()
            }, "$setOnInsert": {"first_seen": datetime.datetime.now().isoformat()}},
            upsert=True
        )
    except: pass

# --- UI MARKUPS ---
def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 All Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL),
        types.InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return markup

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if is_user_banned(uid):
        bot.send_message(message.chat.id, "❌ You are banned.")
        return
    
    save_user(message.from_user)
    
    if is_user_joined(uid):
        bot.send_photo(message.chat.id, BANNER_URL, 
                       caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\nPremium access is active.", 
                       reply_markup=get_main_markup(uid))
    else:
        bot.send_photo(message.chat.id, BANNER_URL, 
                       caption="⚠️ <b>Access Denied!</b>\nJoin all channels to unlock.", 
                       reply_markup=get_join_markup())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    if is_user_banned(uid): return

    if call.data == "verify_user":
        if is_user_joined(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.edit_message_caption("✅ <b>Access Granted!</b>", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(uid))
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

    elif call.data == "list_files":
        files = os.listdir(FILES_DIR)
        if not files:
            bot.answer_callback_query(call.id, "📂 No files found!")
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for f in files[:15]:
            markup.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
        bot.edit_message_caption("📂 <b>Premium Files:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("dl_"):
        filename = call.data.replace("dl_", "")
        send_file(call.message, filename)

    elif call.data == "back_home":
        bot.edit_message_caption("🔥 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(uid))

    elif call.data == "admin_panel" and uid == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_bc"),
                   types.InlineKeyboardButton("🚫 Ban", callback_data="admin_ban"),
                   types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
        bot.edit_message_caption("🔐 <b>Admin Control</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

def send_file(message, filename):
    path = os.path.join(FILES_DIR, filename)
    if os.path.exists(path):
        bot.send_chat_action(message.chat.id, 'upload_document')
        with open(path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ <b>{filename}</b>")
    else:
        bot.send_message(message.chat.id, "❌ File not found.")

# --- SEARCH & AUTO COMMAND ---
@bot.message_handler(func=lambda m: True)
def text_handler(message):
    uid = message.from_user.id
    if is_user_banned(uid): return
    if not is_user_joined(uid): return

    text = message.text.lower()
    
    # Check if text is a command for a file
    clean_cmd = text.replace('/', '')
    for f in os.listdir(FILES_DIR):
        if f.lower().startswith(clean_cmd):
            send_file(message, f)
            return

    # Normal Search
    matches = [f for f in os.listdir(FILES_DIR) if text in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:5]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 Results for '{text}':", reply_markup=mk)

# --- START BOT ---
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    try:
        bot.remove_webhook() # Webhook রিমুভ করা হচ্ছে যাতে পোলিং কাজ করে
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Critical Error: {e}")
