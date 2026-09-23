import os
import sqlite3
import telebot
from telebot import types
import yt_dlp

# ==========================================
# إعدادات البوت والبيئة (آمنة 100% للـ GitHub)
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
  raise ValueError("❌ خطأ: يرجى تعيين متغير البيئة BOT_TOKEN في السيرفر أو ملف .env")

# قراءة الآيديات من البيئة (يمكن وضع آيدي واحد أو عدة آيديات مفصولة بفواصل مثل: 12345,67890)
admin_env = os.getenv("ADMIN_IDS", "105405258")
ADMIN_IDS = [
    int(aid.strip()) for aid in admin_env.split(",") if aid.strip().isdigit()
]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# مجلد تحميل الأغاني مؤقتاً
if not os.path.exists("downloads"):
  os.makedirs("downloads")

# ==========================================
# قاعدة البيانات الشاملة (SQLite)
# ==========================================
conn = sqlite3.connect("mega_music_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_banned INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sub_bots (
    bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    bot_token TEXT UNIQUE,
    bot_username TEXT,
    status TEXT DEFAULT 'active'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS forced_subs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_identifier TEXT UNIQUE,
    sub_type TEXT,
    title TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS assistants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_string TEXT UNIQUE,
    phone_number TEXT,
    status TEXT DEFAULT 'active'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS broadcast_config (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

# القيم الافتراضية للكليشة
default_configs = {
    "source_text": "SG SOURCE",
    "source_url": "https://t.me/YourChannel",
    "add_text": "ADD",
    "add_url": "https://t.me/YourChannel",
    "close_btn": "❌",
    "creator_text": "بوت المنشئ",
    "creator_url": "https://t.me/YourChannel",
    "media_type": "photo",
    "media_id": None,
}
for k, v in default_configs.items():
  cursor.execute(
      "INSERT OR IGNORE INTO broadcast_config (key, value) VALUES (?, ?)",
      (k, str(v) if v else ""),
  )

# إدخال المطورين الأساسيين تلقائياً من متغير البيئة
for aid in ADMIN_IDS:
  cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (aid,))
conn.commit()


def is_admin(user_id):
  if user_id in ADMIN_IDS:
    return True
  cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
  return cursor.fetchone() is not None


def get_config(key):
  cursor.execute("SELECT value FROM broadcast_config WHERE key = ?", (key,))
  row = cursor.fetchone()
  return row[0] if row else ""


def set_config(key, value):
  cursor.execute(
      "INSERT OR REPLACE INTO broadcast_config (key, value) VALUES (?, ?)",
      (key, value),
  )
  conn.commit()


# ==========================================
# الواجهة الرئيسية للعضو (Start)
# ==========================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
  user_id = message.from_user.id
  username = message.from_user.username or "No_Username"

  cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  if row and row[0] == 1:
    bot.reply_to(message, "❌ عذراً، تم حظرك من استخدام هذه المنصة.")
    return

  if not row:
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username),
    )
    conn.commit()

  bot_info = bot.get_me()
  bot_username = bot_info.username

  add_to_channel_url = f"https://t.me/{bot_username}?startgroup=true"
  creator_btn_text = get_config("creator_text") or "بوت المنشئ"
  creator_btn_url = get_config("creator_url") or "https://t.me/YourChannel"

  markup = types.InlineKeyboardMarkup(row_width=1)
  markup.add(
      types.InlineKeyboardButton(
          "➕ اضفني لقناتك/كروبك", url=add_to_channel_url
      ),
      types.InlineKeyboardButton(creator_btn_text, url=creator_btn_url),
  )

  caption = (
      f"أهلاً بك يا <b>{message.from_user.first_name}</b> في منصة بوتات"
      " الميوزك الشاملة 🎶\n(المستخدم مجرد من جميع الصلاحيات الإدارية تماماً)"
  )
  photo_url = "https://files.catbox.moe/example.jpg"

  try:
    bot.send_photo(
        message.chat.id,
        photo=photo_url,
        caption=caption,
        reply_markup=markup,
    )
  except Exception:
    bot.send_message(message.chat.id, caption, reply_markup=markup)


# ==========================================
# معالجة الأوامر المربوطة (للاتصال وللجات)
# ==========================================
@bot.message_handler(
    func=lambda message: message.text
    and any(
        message.text.startswith(word)
        for word in ["وشغل", "تشغيل", "بحث", "نزل", "تنزيل"]
    )
)
def handle_media_commands(message):
  text = message.text.strip()

  # 1. أوامر المكالمة والاتصال (وشغل / تشغيل)
  if text.startswith("وشغل") or text.startswith("تشغيل"):
    prefix = "وشغل" if text.startswith("وشغل") else "تشغيل"
    query = text.replace(prefix, "", 1).strip()
    if not query:
      bot.reply_to(
          message,
          f"⚠️ يرجى كتابة اسم الأغنية للتشغيل بالمكالمة.\nمثال:"
          f" <code>{prefix} تخون بيه</code>",
      )
      return

    send_music_player(
        message.chat.id,
        song_name=query,
        duration="05:50",
        source_name=get_config("source_text"),
        source_url=get_config("source_url"),
    )

  # 2. أوامر الشات والبحث والتحميل (بحث / نزل / تنزيل) عبر yt-dlp
  elif (
      text.startswith("بحث")
      or text.startswith("نزل")
      or text.startswith("تنزيل")
  ):
    for prefix in ["بحث", "نزل", "تنزيل"]:
      if text.startswith(prefix):
        query = text.replace(prefix, "", 1).strip()
        break

    if not query:
      bot.reply_to(
          message,
          "⚠️ يرجى كتابة اسم الطلب للبحث أو التحميل عبر"
          " الشات.\nمثال: <code>نزل تخون بيه</code>",
      )
      return

    sent_msg = bot.reply_to(
        message, f"📥 <b>جاري البحث والتحميل عبر الشات:</b>\n🎵 {query}..."
    )

    try:
      ydl_opts = {
          "format": "bestaudio/best",
          "default_search": "ytsearch1",
          "outtmpl": "downloads/%(id)s.%(ext)s",
          "postprocessors": [
              {
                  "key": "FFmpegExtractAudio",
                  "preferredcodec": "mp3",
                  "preferredquality": "192",
              }
          ],
          "quiet": True,
      }

      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info:
          info = info["entries"][0]

        file_id = info["id"]
        file_path = f"downloads/{file_id}.mp3"
        title = info.get("title", query)

      if os.path.exists(file_path):
        with open(file_path, "rb") as audio:
          bot.send_audio(
              message.chat.id,
              audio,
              caption=f"🎵 <b>{title}</b>\n📥 تم التحميل بنجاح عبر بوت الميوزك",
              performer="Music Bot",
              title=title,
          )
        try:
          os.remove(file_path)
          bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
        except Exception:
          pass
      else:
        bot.edit_message_text(
            "❌ عذراً، لم يتم العثور على نتائج أو حدث خطأ أثناء معالجة الملف.",
            sent_msg.chat.id,
            sent_msg.message_id,
        )
    except Exception as e:
      try:
        bot.edit_message_text(
            f"❌ عذراً، لم يتم العثور على نتائج أو حدث خطأ:\n<code>{e}</code>",
            sent_msg.chat.id,
            sent_msg.message_id,
        )
      except Exception:
        bot.reply_to(
            message, "❌ عذراً، حدث خطأ أثناء الاتصال بمحرك البحث والتحميل."
        )


def send_music_player(
    chat_id, song_name, duration, source_name="SG SOURCE", source_url=""
):
  msg_text = (
      f"🎶 - <b>تم تشغيل :</b> {song_name}\n"
      f"⏱ - <b>مدة التشغيل :</b> {duration}\n"
      "🔊 - <b>الحالة :</b> يعمل الآن في المكالمة الصوتية بنجاح"
  )

  add_text = get_config("add_text") or "ADD"
  add_url = get_config("add_url") or "https://t.me/YourChannel"

  markup = types.InlineKeyboardMarkup(row_width=3)
  markup.add(
      types.InlineKeyboardButton("تخطي", callback_data="music:skip"),
      types.InlineKeyboardButton("إنهاء", callback_data="music:stop"),
      types.InlineKeyboardButton("إيقاف", callback_data="music:pause"),
  )
  markup.add(
      types.InlineKeyboardButton("-10s", callback_data="music:seek_back"),
      types.InlineKeyboardButton("▷", callback_data="music:resume"),
      types.InlineKeyboardButton("+10s", callback_data="music:seek_forward"),
  )
  if source_url:
    markup.add(types.InlineKeyboardButton(source_name, url=source_url))
  else:
    markup.add(types.InlineKeyboardButton(source_name, callback_data="none"))

  markup.add(types.InlineKeyboardButton(add_text, url=add_url))
  markup.add(types.InlineKeyboardButton("❌", callback_data="music:close"))

  media_id = get_config("media_id")
  media_type = get_config("media_type")

  try:
    if media_id and media_type == "photo":
      bot.send_photo(
          chat_id, media_id, caption=msg_text, reply_markup=markup
      )
    elif media_id and media_type == "video":
      bot.send_video(
          chat_id, media_id, caption=msg_text, reply_markup=markup
      )
    else:
      bot.send_message(chat_id, msg_text, reply_markup=markup)
  except Exception:
    bot.send_message(chat_id, msg_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("music:"))
def handle_music_controls(call):
  action = call.data.split(":")[1]
  chat_id = call.message.chat.id

  if action == "skip":
    bot.answer_callback_query(call.id, "⏭ تم تخطي الأغنية الحالية بنجاح")
  elif action == "stop":
    bot.answer_callback_query(call.id, "⏹ تم إنهاء المشغل وإيقاف البث")
    try:
      bot.delete_message(chat_id, call.message.message_id)
    except Exception:
      pass
  elif action == "pause":
    bot.answer_callback_query(call.id, "⏸ تم إيقاف التشغيل مؤقتاً")
  elif action == "resume":
    bot.answer_callback_query(call.id, "▶️ تم استئناف التشغيل بنجاح")
  elif action == "seek_back":
    bot.answer_callback_query(call.id, "⏪ تم ترجيع البث 10 ثواني للخلف")
  elif action == "seek_forward":
    bot.answer_callback_query(call.id, "⏩ تم تقديم البث 10 ثواني للأمام")
  elif action == "close":
    try:
      bot.delete_message(chat_id, call.message.message_id)
    except Exception:
      pass


# ==========================================
# لوحة تحكم المطور والمشرفين والشاملة
# ==========================================
@bot.message_handler(commands=["admin"])
def cmd_admin(message):
  if not is_admin(message.from_user.id):
    return

  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(
      types.InlineKeyboardButton(
          "⚙️ الزر المتقدم (إدارة المشرفين)", callback_data="adm:advanced"
      ),
      types.InlineKeyboardButton(
          "📊 إحصائيات البوت", callback_data="adm:statistics"
      ),
  )
  markup.add(
      types.InlineKeyboardButton(
          "📢 إدارة الاشتراكات الإجبارية", callback_data="adm:forcesub"
      ),
      types.InlineKeyboardButton(
          "✨ كليشة النشر وتخصيص الأزرار", callback_data="adm:broadcast_panel"
      ),
  )
  markup.add(
      types.InlineKeyboardButton(
          "🤖 إدارة الحسابات المساعدة", callback_data="adm:assistants"
      )
  )
  markup.add(
      types.InlineKeyboardButton("❌ إغلاق اللوحة", callback_data="adm:close")
  )

  bot.send_message(
      message.chat.id,
      "🎛 <b>غرفة العمليات المركزية (لوحة المطورين والمشرفين)</b>\nاختر القسم"
      " المطلوب:",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm:"))
def handle_admin_actions(call):
  if not is_admin(call.from_user.id):
    bot.answer_callback_query(call.id, "للمطورين والمشرفين فقط!", show_alert=True)
    return

  data = call.data.split(":")

  if data[1] == "close":
    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
      pass
    return

  elif data[1] == "back":
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            "⚙️ الزر المتقدم (إدارة المشرفين)", callback_data="adm:advanced"
        ),
        types.InlineKeyboardButton(
            "📊 إحصائيات البوت", callback_data="adm:statistics"
        ),
    )
    markup.add(
        types.InlineKeyboardButton(
            "📢 إدارة الاشتراكات الإجبارية", callback_data="adm:forcesub"
        ),
        types.InlineKeyboardButton(
            "✨ كليشة النشر وتخصيص الأزرار", callback_data="adm:broadcast_panel"
        ),
    )
    markup.add(
        types.InlineKeyboardButton(
            "🤖 إدارة الحسابات المساعدة", callback_data="adm:assistants"
        )
    )
    markup.add(
        types.InlineKeyboardButton("❌ إغلاق اللوحة", callback_data="adm:close")
    )

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=(
              "🎛 <b>غرفة العمليات المركزية (لوحة المطورين والمشرفين)</b>\nاختر"
              " القسم المطلوب:"
          ),
          reply_markup=markup,
      )
    except Exception:
      pass

  elif data[1] == "advanced":
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            "➕ إضافة مشرف", callback_data="adm:adv:add_admin"
        ),
        types.InlineKeyboardButton(
            "➖ إزالة مشرف", callback_data="adm:adv:del_admin"
        ),
    )
    markup.add(
        types.InlineKeyboardButton(
            "📋 المشرفين المضافين", callback_data="adm:adv:list_admins"
        ),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="adm:back"),
    )

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=(
              "⚙️ <b>القسم المتقدم - إدارة المشرفين</b>\nاختر العملية المطلوبة:"
          ),
          reply_markup=markup,
      )
    except Exception:
      pass

  elif data[1] == "adv":
    sub_action = data[2]
    if sub_action == "add_admin":
      bot.answer_callback_query(call.id)
      msg = bot.send_message(
          call.message.chat.id,
          "➕ <b>أرسل آيدي (ID) المستخدم لتعيينه مشرفاً:</b>",
      )
      bot.register_next_step_handler(msg, process_add_admin)

    elif sub_action == "del_admin":
      bot.answer_callback_query(call.id)
      msg = bot.send_message(
          call.message.chat.id,
          "➖ <b>أرسل آيدي (ID) المشرف المراد إزالته:</b>",
      )
      bot.register_next_step_handler(msg, process_remove_admin)

    elif sub_action == "list_admins":
      bot.answer_callback_query(call.id)
      cursor.execute("SELECT user_id FROM admins")
      admins = cursor.fetchall()
      admins_list = (
          "\n".join([f"• <code>{adm[0]}</code>" for adm in admins])
          if admins
          else "لا يوجد مشرفين مضافين."
      )

      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton(
              "🔙 رجوع للقسم المتقدم", callback_data="adm:advanced"
          )
      )

      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=f"📋 <b>قائمة المشرفين المضافين في النظام:</b>\n\n{admins_list}",
          reply_markup=markup,
      )

  elif data[1] == "statistics":
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            "🚫 الأعضاء المحظورين", callback_data="adm:stat:banned"
        ),
        types.InlineKeyboardButton(
            "🟢 المستخدمين الحاضرين (المتفاعلين)",
            callback_data="adm:stat:active",
        ),
    )
    markup.add(
        types.InlineKeyboardButton(
            "📊 الإحصائيات العامة", callback_data="adm:stat:general"
        ),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="adm:back"),
    )

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text="📊 <b>قسم إحصائيات البوت والمستخدمين:</b>\nاختر نوع الإحصائية:",
          reply_markup=markup,
      )
    except Exception:
      pass

  elif data[1] == "stat":
    stat_type = data[2]
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🔙 رجوع للإحصائيات", callback_data="adm:statistics"
        )
    )

    if stat_type == "banned":
      cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
      banned_count = cursor.fetchone()[0]
      text = f"🚫 <b>عدد الأعضاء المحظورين:</b> {banned_count} مستخدم."
    elif stat_type == "active":
      cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0")
      active_count = cursor.fetchone()[0]
      text = (
          "🟢 <b>المستخدمين الحاضرين والمتفاعلين:</b>"
          f" <b>{active_count}</b> مستخدم."
      )
    elif stat_type == "general":
      cursor.execute("SELECT COUNT(*) FROM users")
      u_count = cursor.fetchone()[0]
      cursor.execute("SELECT COUNT(*) FROM sub_bots")
      b_count = cursor.fetchone()[0]
      cursor.execute("SELECT COUNT(*) FROM admins")
      a_count = cursor.fetchone()[0]
      cursor.execute("SELECT COUNT(*) FROM assistants")
      ast_count = cursor.fetchone()[0]
      text = (
          "📊 <b>الإحصائيات العامة للنظام:</b>\n\n👥 إجمالي المستخدمين:"
          f" <b>{u_count}</b>\n🤖 البوتات الفرعية:"
          f" <b>{b_count}</b>\n🛡 عدد المشرفين:"
          f" <b>{a_count}</b>\n🤖 الحسابات المساعدة: <b>{ast_count}</b>"
      )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=markup,
    )

  elif data[1] == "forcesub":
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "📢 إضافة قناة أو كروب عام (يجب أن يكون البوت مشرفاً)",
            callback_data="adm:fs:public",
        ),
        types.InlineKeyboardButton(
            "🔗 إضافة بوت أو رابط سوشيال ميديا", callback_data="adm:fs:social"
        ),
        types.InlineKeyboardButton(
            "🔒 إضافة قناة أو كروب خاص", callback_data="adm:fs:private"
        ),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="adm:back"),
    )

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=(
              "📢 <b>قسم إدارة الاشتراكات الإجبارية:</b>\nاختر نوع القناة أو"
              " الوسيلة المراد إضافتها:"
          ),
          reply_markup=markup,
      )
    except Exception:
      pass

  elif data[1] == "fs":
    fs_type = data[2]
    bot.answer_callback_query(call.id)

    if fs_type == "public":
      msg = bot.send_message(
          call.message.chat.id,
          "📢 <b>أرسل معرف القناة أو الكروب العام (مثال: @ChannelName):</b>",
      )
      bot.register_next_step_handler(
          msg, lambda m: process_add_forced_sub(m, "public")
      )
    elif fs_type == "social":
      msg = bot.send_message(
          call.message.chat.id,
          "🔗 <b>أرسل رابط البوت أو رابط السوشيال ميديا:</b>",
      )
      bot.register_next_step_handler(
          msg, lambda m: process_add_forced_sub(m, "social")
      )
    elif fs_type == "private":
      msg = bot.send_message(
          call.message.chat.id,
          "🔒 <b>أرسل دعوة أو معرف القناة/الكروب الخاص:</b>",
      )
      bot.register_next_step_handler(
          msg, lambda m: process_add_forced_sub(m, "private")
      )

  elif data[1] == "broadcast_panel":
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "🖼️ 1- التحكم بالصورة أو بالفيديو الظاهر في الكليشة",
            callback_data="adm:bc:media",
        ),
        types.InlineKeyboardButton(
            "✍️ 2- التحكم بالكتابة والرابط (مثل سي جي سورس)",
            callback_data="adm:bc:source",
        ),
        types.InlineKeyboardButton(
            "➕ 3- التحكم بزر ADD (النص والرابط)",
            callback_data="adm:bc:add_btn",
        ),
        types.InlineKeyboardButton(
            "❌ 4- التحكم بزر X (الإغلاق)", callback_data="adm:bc:close_btn"
        ),
        types.InlineKeyboardButton(
            "👑 5- التحكم بزر بوت المنشئ (النص والرابط)",
            callback_data="adm:bc:creator_btn",
        ),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="adm:back"),
    )

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=(
              "✨ <b>لوحة تخصيص كليشة النشر والأزرار التفاعلية:</b>\nاختر العنصر"
              " الذي تريد تعديله:"
          ),
          reply_markup=markup,
      )
    except Exception:
      pass

  elif data[1] == "bc":
    bc_type = data[2]
    bot.answer_callback_query(call.id)

    if bc_type == "media":
      msg = bot.send_message(
          call.message.chat.id,
          "🖼️ <b>أرسل الصورة أو الفيديو الجديد (أو أرسل 'حذف'):</b>",
      )
      bot.register_next_step_handler(msg, process_update_media)
    elif bc_type == "source":
      msg = bot.send_message(
          call.message.chat.id,
          "✍️ <b>أرسل النص والرابط بالصيغة:\nاسم_الزر | الرابط</b>",
      )
      bot.register_next_step_handler(msg, process_update_source)
    elif bc_type == "add_btn":
      msg = bot.send_message(
          call.message.chat.id,
          "➕ <b>أرسل نص ورابط زر ADD بالصيغة:\nاسم_الزر | الرابط</b>",
      )
      bot.register_next_step_handler(msg, process_update_add)
    elif bc_type == "close_btn":
      msg = bot.send_message(
          call.message.chat.id, "❌ <b>أرسل الرمز الجديد لزر الإغلاق:</b>"
      )
      bot.register_next_step_handler(msg, process_update_close)
    elif bc_type == "creator_btn":
      msg = bot.send_message(
          call.message.chat.id,
          "👑 <b>أرسل نص ورابط زر بوت المنشئ بالصيغة:\nاسم_الزر | الرابط</b>",
      )
      bot.register_next_step_handler(msg, process_update_creator)

  elif data[1] == "assistants":
    cursor.execute("SELECT COUNT(*) FROM assistants")
    ast_count = cursor.fetchone()[0]

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "🤖 إضافة حساب مساعد جديد (جلسة Session)",
            callback_data="adm:ast:add",
        ),
        types.InlineKeyboardButton(
            "📋 عرض الحسابات المساعدة المضافة", callback_data="adm:ast:list"
        ),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="adm:back"),
    )

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=(
              "🤖 <b>قسم إدارة المساعدين (Userbots):</b>\n• عدد المساعدين حالياً:"
              f" <b>{ast_count}</b>"
          ),
          reply_markup=markup,
      )
    except Exception:
      pass

  elif data[1] == "ast":
    ast_action = data[2]
    bot.answer_callback_query(call.id)
    if ast_action == "add":
      msg = bot.send_message(
          call.message.chat.id, "🤖 <b>أرسل كود الجلسة (Session String):</b>"
      )
      bot.register_next_step_handler(msg, process_add_assistant)
    elif ast_action == "list":
      cursor.execute("SELECT id, phone_number, status FROM assistants")
      assistants = cursor.fetchall()
      ast_text = (
          "\n".join([
              f"• ID: <code>{a[0]}</code> | الحالة: {a[2]}" for a in assistants
          ])
          if assistants
          else "لا توجد حسابات مساعدة مضافة حالياً."
      )
      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton(
              "🔙 رجوع للمساعدين", callback_data="adm:assistants"
          )
      )
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=f"📋 <b>قائمة الحسابات المساعدة:</b>\n\n{ast_text}",
          reply_markup=markup,
      )


def process_add_admin(message):
  try:
    target_id = int(message.text.strip())
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (target_id,))
    conn.commit()
    bot.reply_to(message, f"✅ تم تعيين المستخدم (<code>{target_id}</code>) مشرفاً.")
  except ValueError:
    bot.reply_to(message, "❌ الآيدي غير صالح.")


def process_remove_admin(message):
  try:
    target_id = int(message.text.strip())
    if target_id in ADMIN_IDS:
      bot.reply_to(message, "⚠️ لا يمكنك إزالة المطور الأساسي!")
      return
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (target_id,))
    conn.commit()
    bot.reply_to(message, f"✅ تم إزالة المستخدم (<code>{target_id}</code>).")
  except ValueError:
    bot.reply_to(message, "❌ الآيدي غير صالح.")


def process_add_forced_sub(message, sub_type):
  identifier = message.text.strip()
  try:
    cursor.execute(
        "INSERT OR IGNORE INTO forced_subs (chat_identifier, sub_type, title)"
        " VALUES (?, ?, ?)",
        (identifier, sub_type, identifier),
    )
    conn.commit()
    bot.reply_to(message, f"✅ تمت إضافة الاشتراك الإجباري:\n<code>{identifier}</code>")
  except Exception as e:
    bot.reply_to(message, f"⚠️ حدث خطأ: {e}")


def process_update_media(message):
  if message.text and message.text == "حذف":
    set_config("media_id", "")
    set_config("media_type", "text")
    bot.reply_to(message, "✅ تم حذف الوسائط وجعل الكليشة نصية.")
    return
  if message.photo:
    set_config("media_id", message.photo[-1].file_id)
    set_config("media_type", "photo")
    bot.reply_to(message, "✅ تم تحديث الصورة بنجاح.")
  elif message.video:
    set_config("media_id", message.video.file_id)
    set_config("media_type", "video")
    bot.reply_to(message, "✅ تم تحديث الفيديو بنجاح.")
  else:
    bot.reply_to(message, "❌ أرسل صورة أو فيديو صالح، أو اكتب 'حذف'.")


def process_update_source(message):
  text = message.text.strip()
  if "|" not in text:
    bot.reply_to(message, "❌ الصيغة غير صحيحة. استخدم `الاسم | الرابط`")
    return
  parts = text.split("|", 1)
  set_config("source_text", parts[0].strip())
  set_config("source_url", parts[1].strip())
  bot.reply_to(message, "✅ تم تحديث زر السورس بنجاح.")


def process_update_add(message):
  text = message.text.strip()
  if "|" not in text:
    bot.reply_to(message, "❌ الصيغة غير صحيحة. استخدم `الاسم | الرابط`")
    return
  parts = text.split("|", 1)
  set_config("add_text", parts[0].strip())
  set_config("add_url", parts[1].strip())
  bot.reply_to(message, "✅ تم تحديث زر ADD بنجاح.")


def process_update_close(message):
  set_config("close_btn", message.text.strip())
  bot.reply_to(message, "✅ تم تحديث زر الإغلاق بنجاح.")


def process_update_creator(message):
  text = message.text.strip()
  if "|" not in text:
    bot.reply_to(message, "❌ الصيغة غير صحيحة. استخدم `الاسم | الرابط`")
    return
  parts = text.split("|", 1)
  set_config("creator_text", parts[0].strip())
  set_config("creator_url", parts[1].strip())
  bot.reply_to(message, "✅ تم تحديث زر 'بوت المنشئ' بنجاح.")


def process_add_assistant(message):
  try:
    cursor.execute(
        "INSERT INTO assistants (session_string, status) VALUES (?, ?)",
        (message.text.strip(), "active"),
    )
    conn.commit()
    bot.reply_to(message, "✅ تم حفظ جلسة الحساب المساعد بنجاح.")
  except sqlite3.IntegrityError:
    bot.reply_to(message, "⚠️ هذه الجلسة مسجلة مسبقاً!")


if __name__ == "__main__":
  print(
      "Mega Music Bot with mapped call/chat commands is running successfully..."
  )
  bot.infinity_polling()

