import asyncio
import os
import sqlite3
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp

# إعدادات الحساب المساعد الأساسية وتوكن البوت
API_ID = int(os.environ.get("API_ID", "38237681"))
API_HASH = os.environ.get("API_HASH", "b0eef144db9e6cc377d2853fed9007b2")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
DEV_ID = int(os.environ.get("DEV_ID", "105405258"))

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

conn = sqlite3.connect("music_bot.db", check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجداول الأساسية
cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS assistants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_string TEXT
    )
""")
conn.commit()

# القيم الافتراضية للإعدادات
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('free_mode', 'true')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('creator_btn_text', 'قناة البوت')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('creator_btn_link', 'https://t.me/YourChannel')")
conn.commit()

def is_admin(user_id):
    if user_id == DEV_ID:
        return True
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def get_main_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="adv_menu"),
        InlineKeyboardButton("📊 الإحصائيات العامة", callback_data="stats_menu"),
        InlineKeyboardButton("🎛️ نظام التشغيل", callback_data="control_menu"),
        InlineKeyboardButton("📣 قسم النشر والإذاعة", callback_data="publish_menu"),
        InlineKeyboardButton("🤖 إدارة المساعدين", callback_data="assistants_menu"),
    )
    return keyboard

def get_member_keyboard():
    try:
        bot_info = bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "Bot"

    cursor.execute("SELECT value FROM settings WHERE key = 'creator_btn_text'")
    t_res = cursor.fetchone()
    cursor.execute("SELECT value FROM settings WHERE key = 'creator_btn_link'")
    l_res = cursor.fetchone()
    creator_text = t_res[0] if t_res else "قناة البوت"
    creator_link = l_res[0] if l_res else "https://t.me/YourChannel"

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("➕ اضفني لقناتك/كروبك", url=f"https://t.me/{bot_username}?startgroup=true"))
    keyboard.add(InlineKeyboardButton(f"🤖 {creator_text}", url=creator_link))
    return keyboard

def search_and_download_audio(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True
    }
    os.makedirs("downloads", exist_ok=True)
    try:
        with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True}) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in info and info['entries']:
                video_url = info['entries'][0]['url']
                video_title = info['entries'][0]['title']
                video_id = info['entries'][0]['id']
            else:
                return None, None
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            return f"downloads/{video_id}.mp3", video_title
    except:
        return None, None

async def play_in_voice_chat(chat_id, query):
    cursor.execute("SELECT session_string FROM assistants ORDER BY RANDOM() LIMIT 1")
    ast = cursor.fetchone()
    if not ast:
        return None, "⚠️ تنبيه: لا توجد حسابات مساعدين مضافة في النظام! أضف مساعداً من لوحة المشرفين."
    
    session_string = ast[0]
    client = None
    try:
        client = Client(
            f"session_{chat_id}_{os.getpid()}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )
        call_py = PyTgCalls(client)
        
        ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_q = query if query.startswith("http") else f"ytsearch:{query}"
            info = ydl.extract_info(search_q, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            url = info['url']
            title = info.get('title', 'مقطع صوتي')
        
        await client.start()
        await call_py.start()
        await call_py.play(chat_id, AudioPiped(url))
        return title, None
    except Exception as e:
        if client and client.is_connected:
            await client.stop()
        return None, f"❌ خطأ أثناء التشغيل الصوتي: {e}"

@bot.message_handler(commands=['start'])
def start_bot(message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    if is_admin(user_id):
        bot.reply_to(message, "💎 **أهلاً بك يا مطور في لوحة التحكم الرئيسية:**", reply_markup=get_main_admin_keyboard(), parse_mode="Markdown")
    else:
        caption = "🎵 **أهلاً بك في بوت الميوزك الخاص بنا!**\n\n• للتحميل أرسل: `نزل [اسم الأغنية]`\n• للتشغيل بالمكالمة أرسل: `شغل [اسم الأغنية]`"
        image_path = "29038.jpg"
        keyboard = get_member_keyboard()
        if os.path.exists(image_path):
            with open(image_path, "rb") as photo:
                bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            bot.reply_to(message, caption, reply_markup=keyboard, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith("نزل ") or m.text.startswith("تنزيل ")))
def download_song(message):
    query = message.text.split(maxsplit=1)[1]
    sent_msg = bot.reply_to(message, f"🔍 جاري البحث والتحميل: `{query}`...", parse_mode="Markdown")
    
    file_path, title = search_and_download_audio(query)
    keyboard = get_member_keyboard()
    image_path = "29038.jpg"
    caption_text = f"🎵 **تم التحميل بنجاح:** {title}"
    
    if file_path and os.path.exists(file_path):
        if os.path.exists(image_path):
            with open(image_path, "rb") as photo:
                bot.send_audio(message.chat.id, photo, caption=caption_text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            with open(file_path, "rb") as audio:
                bot.send_audio(message.chat.id, audio, caption=caption_text, parse_mode="Markdown", reply_markup=keyboard)
        
        bot.delete_message(message.chat.id, sent_msg.message_id)
        try:
            os.remove(file_path)
        except:
            pass
    else:
        bot.edit_message_text("❌ عذراً، لم يتم العثور على نتائج.", message.chat.id, sent_msg.message_id)

@bot.message_handler(func=lambda m: m.text and (m.text.startswith("شغل ") or m.text.startswith("بحث ")))
def play_voice(message):
    query = message.text.split(maxsplit=1)[1]
    sent = bot.reply_to(message, "🎙️ **جاري استدعاء المساعد والانضمام للمكالمة الصوتية...**", parse_mode="Markdown")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        title, error = loop.run_until_complete(play_in_voice_chat(message.chat.id, query))
        loop.close()
        
        if error:
            bot.edit_message_text(error, message.chat.id, sent.message_id)
        else:
            bot.edit_message_text(f"🎶 **تم بدء التشغيل بنجاح!**\n• الأغنية: `{title}`", message.chat.id, sent.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ فشل التشغيل: {e}", message.chat.id, sent.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ هذه لوحة تحكم خاصة بالمطورين فقط.", show_alert=True)
        return

    if data == "main_admin":
        bot.edit_message_text("💎 **لوحة تحكم المطور الرئيسية:**", call.message.chat.id, call.message.message_id, reply_markup=get_main_admin_keyboard(), parse_mode="Markdown")

    elif data == "adv_menu":
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin_prompt"),
            InlineKeyboardButton("➖ إزالة مشرف", callback_data="remove_admin_prompt"),
            InlineKeyboardButton("📋 قائمة المشرفين", callback_data="list_admins"),
            InlineKeyboardButton("🔙 رجوع", callback_data="main_admin")
        )
        bot.edit_message_text("⚙️ **قسم إدارة المشرفين:**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")

    elif data == "add_admin_prompt":
        user_states[user_id] = "waiting_add_admin"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "👤 أرسل آيدي (ID) المشرف الجديد:", parse_mode="Markdown")

    elif data == "remove_admin_prompt":
        user_states[user_id] = "waiting_remove_admin"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🗑️ أرسل آيدي (ID) المشرف المراد إزالته:", parse_mode="Markdown")

    elif data == "list_admins":
        cursor.execute("SELECT user_id FROM admins")
        admins = cursor.fetchall()
        text = f"👑 **المطور الأساسي:** `{DEV_ID}`\n\n📋 **المشرفون:**\n"
        for adm in admins:
            text += f"• `{adm[0]}`\n"
        keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="adv_menu"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")

    elif data == "stats_menu":
        cursor.execute("SELECT COUNT(*) FROM users")
        u_cnt = cursor.fetchone()[0]
        bot.edit_message_text(f"📊 **الإحصائيات العامة:**\n• إجمالي الأعضاء: `{u_cnt}`", call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="main_admin")), parse_mode="Markdown")

    elif data == "control_menu":
        cursor.execute("SELECT value FROM settings WHERE key = 'free_mode'")
        res = cursor.fetchone()
        status = "مفعل ✅" if res and res[0] == 'true' else "معطل ❌"
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🔴 تعطيل البوت", callback_data="set_free_off"),
            InlineKeyboardButton("🟢 تفعيل البوت", callback_data="set_free_on"),
            InlineKeyboardButton("🔙 رجوع", callback_data="main_admin")
        )
        bot.edit_message_text(f"🎛️ **حالة البوت:** {status}", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")

    elif data == "set_free_off":
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('free_mode', 'false')")
        conn.commit()
        bot.answer_callback_query(call.id, "⚠️ تم تعطيل البوت مؤقتاً.", show_alert=True)

    elif data == "set_free_on":
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('free_mode', 'true')")
        conn.commit()
        bot.answer_callback_query(call.id, "✅ تم تفعيل البوت بنجاح.", show_alert=True)

    elif data == "publish_menu":
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("📤 إذاعة رسالة شاملة", callback_data="pub_broadcast"),
            InlineKeyboardButton("🔄 توجيه رسالة (Forward)", callback_data="pub_forward"),
            InlineKeyboardButton("🔙 رجوع", callback_data="main_admin")
        )
        bot.edit_message_text("📣 **قسم النشر والإذاعة:**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")

    elif data == "pub_broadcast":
        user_states[user_id] = "waiting_broadcast_msg"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📤 أرسل الرسالة المراد إذاعتها لكل الأعضاء:", parse_mode="Markdown")

    elif data == "pub_forward":
        user_states[user_id] = "waiting_forward_msg"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔄 أرسل الرسالة المراد توجيهها للكل:", parse_mode="Markdown")

    elif data == "assistants_menu":
        cursor.execute("SELECT id FROM assistants")
        asts = cursor.fetchall()
        keyboard = InlineKeyboardMarkup(row_width=1)
        for ast in asts:
            keyboard.add(InlineKeyboardButton(f"🗑️ حذف المساعد #{ast[0]}", callback_data=f"del_ast_{ast[0]}"))
        keyboard.add(InlineKeyboardButton("➕ إضافة مساعد جديد", callback_data="add_assistant_prompt"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"))
        bot.edit_message_text(f"🤖 **إدارة الحسابات المساعدة:**\nالمساعدون المفعلون: `{len(asts)}`", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")

    elif data == "add_assistant_prompt":
        user_states[user_id] = "waiting_add_assistant"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🤖 أرسل جلسة الحساب (Session String):", parse_mode="Markdown")

    elif data.startswith("del_ast_"):
        ast_id = data.split("_")[2]
        cursor.execute("DELETE FROM assistants WHERE id = ?", (ast_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ تم حذف المساعد بنجاح.")
        cursor.execute("SELECT id FROM assistants")
        asts = cursor.fetchall()
        keyboard = InlineKeyboardMarkup(row_width=1)
        for ast in asts:
            keyboard.add(InlineKeyboardButton(f"🗑️ حذف المساعد #{ast[0]}", callback_data=f"del_ast_{ast[0]}"))
        keyboard.add(InlineKeyboardButton("➕ إضافة مساعد جديد", callback_data="add_assistant_prompt"))
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"))
        bot.edit_message_text("🤖 **إدارة الحسابات المساعدة:**", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'], func=lambda message: message.from_user.id in user_states)
def handle_states(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text.strip() if message.text else ""
    user_states.pop(user_id, None)

    if not is_admin(user_id):
        return

    if state == "waiting_broadcast_msg":
        cursor.execute("SELECT user_id FROM users")
        sent, failed = 0, 0
        status_msg = bot.reply_to(message, "⏳ جاري الإذاعة...")
        for u in cursor.fetchall():
            try:
                bot.copy_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
                sent += 1
            except:
                failed += 1
        bot.edit_message_text(f"✅ **تمت الإذاعة:**\n• نجاح: `{sent}`\n• فشل: `{failed}`", status_msg.chat.id, status_msg.message_id, parse_mode="Markdown")

    elif state == "waiting_forward_msg":
        cursor.execute("SELECT user_id FROM users")
        sent, failed = 0, 0
        status_msg = bot.reply_to(message, "⏳ جاري التوجيه...")
        for u in cursor.fetchall():
            try:
                bot.forward_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
                sent += 1
            except:
                failed += 1
        bot.edit_message_text(f"✅ **تم التوجيه:**\n• نجاح: `{sent}`\n• فشل: `{failed}`", status_msg.chat.id, status_msg.message_id, parse_mode="Markdown")

    elif state == "waiting_add_admin":
        try:
            new_id = int(text)
            cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,))
            conn.commit()
            bot.reply_to(message, f"✅ تم إضافة المشرف `{new_id}` بنجاح.")
        except:
            bot.reply_to(message, "❌ أرسل الآيدي أرقاماً صحيحة.")

    elif state == "waiting_remove_admin":
        try:
            rem_id = int(text)
            cursor.execute("DELETE FROM admins WHERE user_id = ?", (rem_id,))
            conn.commit()
            bot.reply_to(message, f"🗑️ تم إزالة المشرف `{rem_id}`.")
        except:
            bot.reply_to(message, "❌ أرسل الآيدي أرقاماً صحيحة.")

    elif state == "waiting_add_assistant":
        cursor.execute("INSERT INTO assistants (session_string) VALUES (?)", (text,))
        conn.commit()
        bot.reply_to(message, "✅ تم حفظ وإضافة جلسة المساعد بنجاح.")

print("Music Bot is running completely with all features...")
bot.infinity_polling()
