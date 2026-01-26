import telebot
from telebot import types
import os
import datetime
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIGURATION ---
API_TOKEN = "8501641088:AAGoN3in84hJAeRTWmmmG0Omj_50oUmf54E" # এখানে টোকেন দিন
ADMIN_ID = 8504263842
FIREBASE_URL = "https://file-manager-bot-default-rtdb.firebaseio.com/" # যেমন: https://project-id.firebaseio.com/
LOG_CHANNEL = "@dumodzbotmanager"
REQUIRED_CHANNELS = ["@DUModZ", "@DU_MODZ", "@Dark_Unkwon_ModZ", "@DU_MODZ_CHAT"]
BANNER_URL = "https://raw.githubusercontent.com/DarkUnkwon-ModZ/DUModZ-Resource/refs/heads/main/Img/darkunkwonmodz-banner.jpg"
FILES_DIR = "files"

# --- FIREBASE INITIALIZATION ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    print("✅ Firebase Connection Established!")
except Exception as e:
    print(f"❌ Firebase Error: {e}")

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- REAL-TIME DATABASE FUNCTIONS ---
def sync_user_data(user):
    """ইউজারের ডেটা ফায়ারবেসে সিঙ্ক করে"""
    try:
        user_ref = db.reference(f'users/{user.id}')
        data = {
            'id': user.id,
            'name': user.first_name,
            'username': user.username if user.username else "N/A",
            'last_seen': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'active'
        }
        # update() ব্যবহার করলে আগের ডেটা ডিলিট হয় না, শুধু নতুনগুলো যোগ হয়
        user_ref.update(data)
        return True
    except Exception as e:
        print(f"❌ Sync Error: {e}")
        return False

def is_banned(uid):
    try:
        ban_status = db.reference(f'banned/{uid}').get()
        return ban_status is not None
    except:
        return False

def get_total_users_count():
    try:
        users = db.reference('users').get()
        return len(users) if users else 0
    except:
        return 0

# --- HELPERS ---
def check_join(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- KEYBOARDS ---
def main_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 Premium Files", callback_data="sync_files"),
        types.InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
    )
    markup.add(
        types.InlineKeyboardButton("👨‍💻 Dev", url="https://t.me/DarkUnkwon"),
        types.InlineKeyboardButton("🌐 Website", url="https://darkunkwon-modz.blogspot.com")
    )
    if uid == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    
    # ইউজারকে ডেটাবেসে সেভ করা (Real-time Update)
    sync_user_data(message.from_user)

    if is_banned(uid):
        bot.reply_to(message, "🚫 You are banned from this bot.")
        return

    if check_join(uid):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome {message.from_user.first_name}!</b>\n\nDatabase Status: 🟢 Connected\nFiles Status: ⚡ Ready",
            reply_markup=main_markup(uid)
        )
    else:
        mk = types.InlineKeyboardMarkup(row_width=1)
        for ch in REQUIRED_CHANNELS:
            mk.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        mk.add(types.InlineKeyboardButton("🔄 Verify Join", callback_data="verify"))
        bot.send_photo(message.chat.id, BANNER_URL, caption="⚠️ <b>Access Denied!</b>\nPlease join our channels first.", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    
    # প্রতি ক্লিকেও ইউজার ডেটা আপডেট হবে
    sync_user_data(call.from_user)

    if call.data == "verify":
        if check_join(uid):
            bot.answer_callback_query(call.id, "✅ Verified Successfully!")
            bot.edit_message_caption("🔓 <b>Welcome Back!</b>\nAccess Granted.", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))
        else:
            bot.answer_callback_query(call.id, "❌ Still not joined!", show_alert=True)

    elif call.data == "my_stats":
        total = get_total_users_count()
        text = f"👤 <b>User Profile</b>\n\n🆔 ID: <code>{uid}</code>\n📛 Name: {call.from_user.first_name}\n📊 Total Bot Users: {total}\n📅 Sync: Real-time"
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

    elif call.data == "admin_panel" and uid == ADMIN_ID:
        total = get_total_users_count()
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("📣 Broadcast", callback_data="adm_bc"),
            types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban")
        )
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
        bot.edit_message_caption(f"🔐 <b>Admin Panel</b>\n\nTotal Registered Users: {total}", call.message.chat.id, call.message.message_id, reply_markup=mk)

    elif call.data == "home":
        bot.edit_message_caption("🏠 <b>Main Menu</b>", call.message.chat.id, call.message.message_id, reply_markup=main_markup(uid))

# --- BROADCAST SYSTEM ---
def broadcast_step(message):
    if message.text == "/cancel": return
    users = db.reference('users').get()
    if not users: return
    
    msg = bot.send_message(message.chat.id, "⏳ <b>Sending messages...</b>")
    success = 0
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 <b>Announcement</b>\n\n{message.text}")
            success += 1
        except: pass
    bot.edit_message_text(f"✅ Broadcast Done! Sent to {success} users.", message.chat.id, msg.message_id)

# --- START BOT ---
if __name__ == "__main__":
    print("✅ DUModZ Bot is Live!")
    bot.infinity_polling(skip_pending=True)
