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
BANNED_FILE = "banned.json"

os.makedirs(FILES_DIR, exist_ok=True)
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# --- BAN SYSTEM ---
def load_banned():
    try:
        if os.path.exists(BANNED_FILE):
            with open(BANNED_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except:
        return set()

def save_banned(banned_set):
    try:
        with open(BANNED_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(banned_set), f, indent=2)
    except Exception as e:
        print(f"[BAN ERROR] {e}")

def is_user_banned(user_id):
    return user_id in load_banned()

# --- SAFE EDIT HELPERS ---
def safe_edit_caption(chat_id, message_id, caption, reply_markup=None):
    try:
        bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=reply_markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e):
            raise e

def safe_edit_text(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e):
            raise e

# --- USER DATABASE (with name, join status) ---
def load_users():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], int):
                    upgraded = []
                    for uid in data:
                        try:
                            user = bot.get_chat(uid)
                            name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
                            joined = is_user_joined(uid)
                            upgraded.append({
                                "id": uid,
                                "name": name.strip() or f"User {uid}",
                                "username": getattr(user, 'username', None),
                                "joined": joined,
                                "first_seen": datetime.datetime.now().isoformat()
                            })
                        except:
                            upgraded.append({
                                "id": uid,
                                "name": f"User {uid}",
                                "username": None,
                                "joined": False,
                                "first_seen": datetime.datetime.now().isoformat()
                            })
                    save_users(upgraded)
                    return upgraded
                return data
        return []
    except Exception as e:
        print(f"[ERROR] Load Users: {e}")
        return []

def save_users(users):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Save Users: {e}")

def save_user(user: types.User):
    users = load_users()
    user_id = user.id
    existing = next((u for u in users if u["id"] == user_id), None)
    if not existing:
        name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
        users.append({
            "id": user_id,
            "name": name.strip() or f"User {user_id}",
            "username": user.username,
            "joined": is_user_joined(user_id),
            "first_seen": datetime.datetime.now().isoformat()
        })
        save_users(users)
    else:
        existing["name"] = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
        existing["username"] = user.username
        existing["joined"] = is_user_joined(user_id)
        save_users(users)

# --- LOGGING ---
def log_to_channel(message):
    try:
        bot.send_message(LOG_CHANNEL, message, disable_web_page_preview=True)
    except: pass

def log_error(e):
    print(f"[ERROR] {e}")
    try:
        bot.send_message(ADMIN_ID, f"⚠️ <code>{str(e)}</code>", parse_mode="HTML")
    except: pass

# --- UTILS ---
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Join Our Official Channel", url=CHANNEL_URL),
        types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user")
    )
    return markup

def get_main_markup(user_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 All Premium Files", callback_data="list_files"),
        types.InlineKeyboardButton("🌐 Official Site", url=WEBSITE_URL)
    )
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="user_stats"),
        types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/DarkUnkwon")
    )
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
        types.InlineKeyboardButton("📤 Export", callback_data="admin_export"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_home")
    )
    return markup

# --- GLOBAL STATE FOR ADMIN INPUT ---
user_state = {}  # {user_id: "broadcast"|"ban"|"unban"}

# --- CORE HANDLERS ---
@bot.message_handler(commands=['start'])
def start_command(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return
    save_user(message.from_user)
    bot.send_chat_action(message.chat.id, 'typing')
    time.sleep(0.3)
    
    if is_user_joined(message.from_user.id):
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"🚀 <b>Welcome, {message.from_user.first_name}!</b>\n\nYour premium access is <b>Active</b>.",
            reply_markup=get_main_markup(user_id=message.from_user.id)
        )
        log_to_channel(f"✅ Verified: {message.from_user.full_name} ({message.from_user.id})")
    else:
        bot.send_photo(
            message.chat.id, BANNER_URL,
            caption=f"⚠️ <b>Access Restricted!</b>\n\nJoin our channel to continue.",
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
                for txt in ["🔍 Checking...", "🛡️ Verifying...", "🔓 Unlocking..."]:
                    safe_edit_caption(call.message.chat.id, call.message.message_id, f"<b>{txt}</b>")
                    time.sleep(0.5)
                safe_edit_caption(
                    call.message.chat.id, call.message.message_id,
                    "✅ <b>Verification Complete!</b>",
                    reply_markup=get_main_markup(user_id=user_id)
                )
                save_user(call.from_user)
            else:
                bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

        elif call.data == "list_files":
            files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
            if not files:
                bot.answer_callback_query(call.id, "📁 No files!", show_alert=True)
                return
            text = "🛠 <b>Available Files:</b>\n\n"
            markup = types.InlineKeyboardMarkup(row_width=1)
            for f in files:
                name = os.path.splitext(f)[0]
                text += f"🔹 <code>/{name.lower()}</code>\n"
                markup.add(types.InlineKeyboardButton(f"📥 {name.replace('_', ' ').title()}", callback_data=f"dl_{f}"))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
            safe_edit_caption(call.message.chat.id, call.message.message_id, text, reply_markup=markup)

        elif call.data.startswith("dl_"):
            send_file_logic(call.message, call.data.replace("dl_", ""))

        elif call.data == "back_home":
            safe_edit_caption(
                call.message.chat.id, call.message.message_id,
                "🔥 <b>Main Menu</b>",
                reply_markup=get_main_markup(user_id=user_id)
            )

        elif call.data == "user_stats":
            total = len(load_users())
            msg = f"👤 <b>Your Info</b>\n🆔 <code>{user_id}</code>\n👥 Total Users: {total}"
            safe_edit_caption(call.message.chat.id, call.message.message_id, msg, reply_markup=get_main_markup(user_id=user_id))

        # --- ADMIN PANEL ---
        elif call.data == "admin_panel":
            if user_id != ADMIN_ID: return
            safe_edit_caption(call.message.chat.id, call.message.message_id, "🔐 <b>Admin Panel</b>", reply_markup=get_admin_markup())

        elif call.data == "admin_broadcast_info":
            if user_id != ADMIN_ID: return
            bot.answer_callback_query(call.id, "📤 Send a message to broadcast (text only).")
            bot.send_message(call.message.chat.id, "📩 <b>Send your broadcast message:</b>\n\n(Only text supported)")
            user_state[user_id] = "broadcast"
            return

        elif call.data == "admin_ban_info":
            if user_id != ADMIN_ID: return
            bot.answer_callback_query(call.id, "🚫 Reply with user ID to ban.")
            bot.send_message(call.message.chat.id, "🔢 <b>Send User ID to Ban:</b>")
            user_state[user_id] = "ban"
            return

        elif call.data == "admin_unban_info":
            if user_id != ADMIN_ID: return
            bot.answer_callback_query(call.id, "✅ Reply with user ID to unban.")
            bot.send_message(call.message.chat.id, "🔢 <b>Send User ID to Unban:</b>")
            user_state[user_id] = "unban"
            return

        elif call.data == "admin_user_list":
            if user_id != ADMIN_ID: return
            users = load_users()
            if not users:
                bot.answer_callback_query(call.id, "📭 No users yet!")
                return
            text = "👥 <b>User List (Last 50):</b>\n\n"
            for u in users[-50:]:
                status = "✅" if u.get("joined", False) else "❌"
                name = u['name'].replace('<', '&lt;').replace('>', '&gt;')
                text += f"{status} <a href='tg://user?id={u['id']}'>{name}</a> (<code>{u['id']}</code>)\n"
            bot.send_message(call.message.chat.id, text, parse_mode="HTML")

        elif call.data == "admin_export":
            if user_id != ADMIN_ID: return
            users = load_users()
            with open("users_export.txt", "w") as f:
                for u in users:
                    f.write(f"ID: {u['id']}, Name: {u['name']}, Joined: {u.get('joined', False)}\n")
            with open("users_export.txt", "rb") as f:
                bot.send_document(call.message.chat.id, f, caption="📤 User List")
            os.remove("users_export.txt")

        elif call.data == "admin_stats":
            if user_id != ADMIN_ID: return
            users = load_users()
            files = len([f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))])
            msg = f"⚙️ <b>Stats</b>\n👥 Users: {len(users)}\n📁 Files: {files}"
            safe_edit_caption(call.message.chat.id, call.message.message_id, msg, reply_markup=get_admin_markup())

    except Exception as e:
        log_error(e)
        bot.answer_callback_query(call.id, "⚠️ Error occurred.", show_alert=True)

# --- FILE SENDING ---
def send_file_logic(message, file_name):
    user_id = message.chat.id if hasattr(message, 'chat') else message.from_user.id
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned.")
        return
    if not is_user_joined(user_id):
        bot.reply_to(message, "❌ Join channel first.", reply_markup=get_join_markup())
        return
    path = os.path.join(FILES_DIR, file_name)
    if os.path.exists(path):
        status = bot.send_message(message.chat.id, f"⏳ Preparing <code>{file_name}</code>...")
        bot.send_chat_action(message.chat.id, 'upload_document')
        time.sleep(1)
        try:
            with open(path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ <b>{file_name}</b>\nFrom @Dark_Unkwon_ModZ")
            bot.delete_message(message.chat.id, status.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", message.chat.id, status.message_id)
    else:
        bot.reply_to(message, "🚧 File not found.")

# --- MESSAGE HANDLER (Commands + Admin Actions) ---
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if is_user_banned(user_id):
        bot.reply_to(message, "❌ You are banned from using this bot.")
        return

    # --- Handle Admin Input State ---
    if user_id == ADMIN_ID and user_id in user_state:
        action = user_state.pop(user_id)
        if action == "broadcast":
            users = load_users()
            success = 0
            for u in users:
                try:
                    bot.send_message(u["id"], f"📣 <b>Broadcast</b>\n\n{text}")
                    success += 1
                    time.sleep(0.05)
                except: pass
            bot.reply_to(message, f"✅ Broadcast sent to {success}/{len(users)} users.")
            return
        elif action == "ban":
            try:
                target_id = int(text)
                banned = load_banned()
                banned.add(target_id)
                save_banned(banned)
                bot.reply_to(message, f"🚫 User <code>{target_id}</code> banned successfully.")
                log_to_channel(f"🚫 <b>Banned</b>\nAdmin: {user_id}\nUser: {target_id}")
            except ValueError:
                bot.reply_to(message, "❌ Invalid User ID. Please send a number.")
            except Exception as e:
                bot.reply_to(message, f"❌ Error: {e}")
            return
        elif action == "unban":
            try:
                target_id = int(text)
                banned = load_banned()
                if target_id in banned:
                    banned.remove(target_id)
                    save_banned(banned)
                    bot.reply_to(message, f"✅ User <code>{target_id}</code> unbanned.")
                    log_to_channel(f"✅ <b>Unbanned</b>\nAdmin: {user_id}\nUser: {target_id}")
                else:
                    bot.reply_to(message, "ℹ️ User not banned.")
            except ValueError:
                bot.reply_to(message, "❌ Invalid User ID. Please send a number.")
            except Exception as e:
                bot.reply_to(message, f"❌ Error: {e}")
            return

    # --- Regular User Commands ---
    if not is_user_joined(user_id):
        bot.reply_to(message, "❌ Join channel first.", reply_markup=get_join_markup())
        return

    # Admin Commands (Non-State)
    if user_id == ADMIN_ID:
        if text.lower() == "/admin":
            bot.send_photo(message.chat.id, BANNER_URL, caption="🔐 <b>Admin Panel</b>", reply_markup=get_admin_markup())
            return
        elif text.lower() == "/statsuser":
            users = load_users()
            if not users:
                bot.reply_to(message, "📭 No users.")
                return
            text_resp = "👥 <b>All Users (Max 100):</b>\n\n"
            for u in users[-100:]:
                status = "✅" if u.get("joined", False) else "❌"
                name = u['name'].replace('<', '&lt;').replace('>', '&gt;')
                text_resp += f"{status} <a href='tg://user?id={u['id']}'>{name}</a> (<code>{u['id']}</code>)\n"
            bot.send_message(message.chat.id, text_resp, parse_mode="HTML")
            return

    # Public Commands
    if text.lower() == "/list":
        files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
        if not files:
            bot.reply_to(message, "📁 No files.")
            return
        resp = "🛠 <b>Files:</b>\n\n" + "\n".join(f"🔹 <code>/{os.path.splitext(f)[0].lower()}</code>" for f in files)
        bot.reply_to(message, resp)
        return

    if text.startswith('/'):
        cmd = text[1:].lower().split()[0]
        if cmd == "start":
            return start_command(message)
        for f in os.listdir(FILES_DIR):
            if f.lower().startswith(cmd + ".") or f.lower() == cmd:
                return send_file_logic(message, f)
        bot.reply_to(message, "❓ Unknown command. Use /list")

    # Text search
    query = text.lower()
    matches = [f for f in os.listdir(FILES_DIR) if query in f.lower()]
    if matches:
        mk = types.InlineKeyboardMarkup()
        for f in matches[:10]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dl_{f}"))
        bot.reply_to(message, f"🔍 Found {len(matches)} result(s):", reply_markup=mk)
    else:
        bot.reply_to(message, "😔 No matching file.")

# --- RUN ---
if __name__ == "__main__":
    print("🚀 DUModZ Bot Running...")
    log_to_channel("🟢 Bot Online with Advanced Admin Panel ✅")
    bot.infinity_polling(skip_pending=True)
