import asyncio
import os
import sqlite3
import subprocess
import sys
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import yt_dlp

# إعدادات الحساب المساعد الأساسية
API_ID = int(os.environ.get("API_ID", "38237681"))
API_HASH = os.environ.get("API_HASH", "b0eef144db9e6cc377d2853fed9007b2")

# ==================== التحقق من وضع التشغيل (صانع أم بوت فرعي) ====================
if len(sys.argv) >= 2:
  # ======== تشغيل بوت الميوزك الفرعي (مجاني أو VIP) ========
  TOKEN = sys.argv[1]
  bot = telebot.TeleBot(TOKEN)

  conn = sqlite3.connect("bot_maker.db", check_same_thread=False)
  cursor = conn.cursor()

  try:
    bot_info = bot.get_me()
    BOT_USERNAME = bot_info.username
  except:
    BOT_USERNAME = "Bot"


  def get_bot_keyboard():
    cursor.execute(
        "SELECT rights, bot_type FROM created_bots WHERE bot_token = ?",
        (TOKEN,),
    )
    row = cursor.fetchone()
    bot_rights = row[0] if row else "with_rights"
    bot_type = row[1] if row else "free"

    # إذا كان البوت VIP خالي من الحقوق تماماً
    if bot_rights == "no_rights":
      return None

    # جلب بيانات الأزرار العامة من قاعدة البيانات
    cursor.execute("SELECT value FROM settings WHERE key = 'creator_btn_text'")
    t_res = cursor.fetchone()
    cursor.execute("SELECT value FROM settings WHERE key = 'creator_btn_link'")
    l_res = cursor.fetchone()
    creator_text = t_res[0] if t_res else "بوت المنشئ"
    creator_link = l_res[0] if l_res else "https://t.me/YourCreatorBot"

    cursor.execute("SELECT value FROM settings WHERE key = 'nino_btn_text'")
    n_res = cursor.fetchone()
    cursor.execute("SELECT value FROM settings WHERE key = 'nino_btn_link'")
    nl_res = cursor.fetchone()
    nino_text = n_res[0] if n_res else "نينو"
    nino_link = nl_res[0] if nl_res else "https://t.me/YourChannel"

    keyboard = InlineKeyboardMarkup(row_width=2)

    if bot_type == "vip":
      keyboard.add(InlineKeyboardButton(f"🤖 {creator_text}", url=creator_link))
      keyboard.add(
          InlineKeyboardButton(
              "➕ اضفني لقناتك/كروبك",
              url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
          )
      )
      keyboard.add(InlineKeyboardButton(f"💎 {nino_text}", url=nino_link))
    else:
      keyboard.add(
          InlineKeyboardButton(
              "➕ اضفني لقناتك/كروبك",
              url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
          )
      )
      keyboard.add(InlineKeyboardButton(f"🤖 {creator_text}", url=creator_link))

      cursor.execute("SELECT value FROM settings WHERE key = 'sg_source_btn'")
      sg = cursor.fetchone()
      if sg and sg[0] == "true":
        keyboard.add(
            InlineKeyboardButton(
                "SG SOURCE", url="https://t.me/YourSourceChannel"
            )
        )

      cursor.execute("SELECT value FROM settings WHERE key = 'add_btn'")
      add = cursor.fetchone()
      if add and add[0] == "true":
        keyboard.add(
            InlineKeyboardButton(
                "ADD", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
            )
        )

      cursor.execute("SELECT value FROM settings WHERE key = 'x_btn'")
      x = cursor.fetchone()
      if x and x[0] == "true":
        keyboard.add(
            InlineKeyboardButton("X", url="https://t.me/YourDeveloperAccount")
        )

    return keyboard


  def search_and_download_audio(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "quiet": True,
    }
    os.makedirs("downloads", exist_ok=True)
    try:
      with yt_dlp.YoutubeDL({"format": "bestaudio", "quiet": True}) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        if "entries" in info and info["entries"]:
          video_url = info["entries"][0]["url"]
          video_title = info["entries"][0]["title"]
          video_id = info["entries"][0]["id"]
        else:
          return None, None

      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        return f"downloads/{video_id}.mp3", video_title
    except:
      return None, None


  async def play_in_voice_chat(chat_id, query):
    cursor.execute(
        "SELECT session_string FROM assistants ORDER BY RANDOM() LIMIT 1"
    )
    ast = cursor.fetchone()
    if not ast:
      return None, "⚠️ تنبيه: لا توجد حسابات مساعدين مضافة في النظام!"

    session_string = ast[0]
    client = None
    try:
      client = Client(
          f"session_{chat_id}_{os.getpid()}",
          api_id=API_ID,
          api_hash=API_HASH,
          session_string=session_string,
          in_memory=True,
      )
      call_py = PyTgCalls(client)

      ydl_opts = {"format": "bestaudio/best", "noplaylist": True, "quiet": True}
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_q = query if query.startswith("http") else f"ytsearch:{query}"
        info = ydl.extract_info(search_q, download=False)
        if "entries" in info:
          info = info["entries"][0]
        url = info["url"]
        title = info.get("title", "مقطع صوتي")

      await client.start()
      await call_py.start()
      await call_py.play(chat_id, AudioPiped(url))
      return title, None
    except Exception as e:
      if client and client.is_connected:
        await client.stop()
      return None, f"❌ خطأ أثناء التشغيل الصوتي: {e}"


  @bot.message_handler(commands=["start"])
  def start_bot(message):
    keyboard = get_bot_keyboard()
    caption = (
        "🎵 **أهلاً بك في بوت الميوزك الخاص بك!**\n\n• للتحميل أرسل: `نزل"
        " [اسم الأغنية]`\n• للتشغيل بالمكالمة أرسل: `شغل [اسم الأغنية]`"
    )

    cursor.execute(
        "SELECT bot_type FROM created_bots WHERE bot_token = ?", (TOKEN,)
    )
    row = cursor.fetchone()
    b_type = row[0] if row else "free"
    image_path = "29038_2.jpg" if b_type == "vip" else "29038.jpg"

    if os.path.exists(image_path):
      with open(image_path, "rb") as photo:
        bot.send_photo(
            message.chat.id,
            photo,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    else:
      bot.reply_to(
          message, caption, reply_markup=keyboard, parse_mode="Markdown"
      )


  @bot.message_handler(
      func=lambda m: m.text
      and (m.text.startswith("نزل ") or m.text.startswith("تنزيل "))
  )
  def download_song(message):
    query = message.text.split(maxsplit=1)[1]
    sent_msg = bot.reply_to(
        message, f"🔍 جاري البحث والتحميل: `{query}`...", parse_mode="Markdown"
    )

    file_path, title = search_and_download_audio(query)
    keyboard = get_bot_keyboard()

    cursor.execute(
        "SELECT bot_type FROM created_bots WHERE bot_token = ?", (TOKEN,)
    )
    row = cursor.fetchone()
    b_type = row[0] if row else "free"
    image_path = "29038_2.jpg" if b_type == "vip" else "29038.jpg"
    caption_text = f"🎵 **تم التحميل بنجاح:** {title}"

    if file_path and os.path.exists(file_path):
      if os.path.exists(image_path):
        with open(image_path, "rb") as photo:
          bot.send_audio(
              message.chat.id,
              photo,
              caption=caption_text,
              parse_mode="Markdown",
              reply_markup=keyboard,
          )
      else:
        with open(file_path, "rb") as audio:
          bot.send_audio(
              message.chat.id,
              audio,
              caption=caption_text,
              parse_mode="Markdown",
              reply_markup=keyboard,
          )

      bot.delete_message(message.chat.id, sent_msg.message_id)
      try:
        os.remove(file_path)
      except:
        pass
    else:
      bot.edit_message_text(
          "❌ عذراً، لم يتم العثور على نتائج.",
          message.chat.id,
          sent_msg.message_id,
      )


  @bot.message_handler(
      func=lambda m: m.text
      and (m.text.startswith("شغل ") or m.text.startswith("بحث "))
  )
  def play_voice(message):
    query = message.text.split(maxsplit=1)[1]
    sent = bot.reply_to(
        message,
        "🎙️ **جاري استدعاء المساعد والانضمام للمكالمة الصوتية...**",
        parse_mode="Markdown",
    )

    try:
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      title, error = loop.run_until_complete(
          play_in_voice_chat(message.chat.id, query)
      )
      loop.close()

      if error:
        bot.edit_message_text(error, message.chat.id, sent.message_id)
      else:
        bot.edit_message_text(
            f"🎶 **تم بدء التشغيل بنجاح!**\n• الأغنية: `{title}`",
            message.chat.id,
            sent.message_id,
            parse_mode="Markdown",
        )
    except Exception as e:
      bot.edit_message_text(
          f"❌ فشل التشغيل: {e}", message.chat.id, sent.message_id
      )


  print("Music Bot Worker is running...")
  bot.infinity_polling()

else:
  # ======== تشغيل بوت المصنع الرئيسي (Creator Bot) ========
  CREATOR_BOT_TOKEN = os.environ.get("CREATOR_BOT_TOKEN", "YOUR_CREATOR_TOKEN")
  DEV_ID = int(os.environ.get("DEV_ID", "105405258"))

  bot = telebot.TeleBot(CREATOR_BOT_TOKEN)
  active_bots = {}
  user_states = {}

  conn = sqlite3.connect("bot_maker.db", check_same_thread=False)
  cursor = conn.cursor()

  # إنشاء الجداول الأساسية
  cursor.execute(
      "CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)"
  )
  cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS created_bots (
            bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_token TEXT,
            bot_type TEXT,
            rights TEXT DEFAULT 'with_rights'
        )
    """)
  cursor.execute(
      "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
  )
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS assistants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_string TEXT
        )
    """)
  conn.commit()

  # القيم الافتراضية للإعدادات
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('free_mode',"
      " 'true')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_btn_text',"
      " 'المطور')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_btn_link',"
      " 'https://t.me/YourUsername')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('creator_btn_text',"
      " 'بوت المنشئ')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('creator_btn_link',"
      " 'https://t.me/YourCreatorBot')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('nino_btn_text',"
      " 'نينو')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('nino_btn_link',"
      " 'https://t.me/YourChannel')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('sg_source_btn',"
      " 'true')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('add_btn', 'true')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('x_btn', 'true')"
  )
  conn.commit()

  # إعادة تشغيل البوتات الفرعية عند الإقلاع
  cursor.execute("SELECT bot_token FROM created_bots")
  for row in cursor.fetchall():
    b_token = row[0]
    if b_token not in active_bots:
      try:
        p = subprocess.Popen(["python", __file__, b_token])
        active_bots[b_token] = p
      except Exception:
        pass


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
        InlineKeyboardButton(
            "📣 قسم النشر والإذاعة", callback_data="publish_menu"
        ),
        InlineKeyboardButton(
            "🎨 تخصيص أزرار الحقوق", callback_data="rights_menu"
        ),
        InlineKeyboardButton(
            "⭐ تخصيص زر اصنع VIP", callback_data="vip_btn_config"
        ),
        InlineKeyboardButton(
            "💎 إدارة بوتات الـ VIP", callback_data="admin_vip_manager"
        ),
        InlineKeyboardButton(
            "🤖 إدارة المساعدين", callback_data="assistants_menu"
        ),
    )
    return keyboard


  def get_member_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "🤖 اصنع بوتك مجاناً", callback_data="member_free_create"
        ),
        InlineKeyboardButton("💎 اصنع VIP", callback_data="member_vip"),
    )
    return keyboard


  @bot.message_handler(commands=["start"])
  def send_welcome(message):
    user_id = message.from_user.id
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
    )
    conn.commit()

    if is_admin(user_id):
      bot.reply_to(
          message,
          "💎 **أهلاً بك يا مطور في لوحة التحكم الرئيسية:**",
          reply_markup=get_main_admin_keyboard(),
          parse_mode="Markdown",
      )
    else:
      welcome_text = (
          "مرحباً بك في نظام صنع بوتات الميوزك 🎵\n\n• للتحميل أرسل: `نزل [اسم"
          " الأغنية]`\n• للتشغيل بالمكالمة أرسل: `شغل [اسم الأغنية]`\n\nاختر من"
          " الأزرار أدناه:"
      )
      bot.reply_to(
          message,
          welcome_text,
          reply_markup=get_member_main_keyboard(),
          parse_mode="Markdown",
      )


  @bot.callback_query_handler(func=lambda call: True)
  def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    if data == "member_main":
      bot.edit_message_text(
          "مرحباً بك مجدداً في نظام صنع بوتات الميوزك 🎵\nاختر من الأزرار أدناه:",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=get_member_main_keyboard(),
      )
    elif data == "member_free_create":
      cursor.execute(
          "SELECT bot_token FROM created_bots WHERE user_id = ?", (user_id,)
      )
      existing_bot = cursor.fetchone()
      keyboard = InlineKeyboardMarkup().add(
          InlineKeyboardButton("🔙 رجوع", callback_data="member_main")
      )
      if existing_bot:
        text = (
            "🎉 **مبروك عزيزي بوتك صار جاهزاً!** 🎶\nأنت تمتلك بوت ميوزك بالفعل"
            " قيد التشغيل."
        )
      else:
        text = (
            "🤖 **خطوات إنشاء بوت ميوزك مجاني:**\n\n1. اذهب إلى بوت صنع بوتات"
            " الرسمي: @BotFather\n2. أنشئ بوت جديد واحصل على الـ"
            " (Token).\n3. أرسل التوكن هنا بالشكل التالي:\n\n`/create [التوكن"
            " الخاص بك]`"
        )
      bot.edit_message_text(
          text,
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data == "member_vip":
      cursor.execute("SELECT value FROM settings WHERE key = 'vip_btn_text'")
      t_res = cursor.fetchone()
      cursor.execute("SELECT value FROM settings WHERE key = 'vip_btn_link'")
      l_res = cursor.fetchone()
      btn_text = t_res[0] if t_res else "المطور"
      btn_link = l_res[0] if l_res else "https://t.me/YourUsername"

      keyboard = InlineKeyboardMarkup(row_width=1).add(
          InlineKeyboardButton(f"👤 {btn_text}", url=btn_link),
          InlineKeyboardButton("🔙 رجوع", callback_data="member_main"),
      )
      bot.edit_message_text(
          "💎 **خدمة بوتات الـ VIP المدفوعة:**\n\nاحصل على بوت ميوزك بمميزات إضافية"
          " وبدون حقوق.\nللاشتراك أو الاستفسار تواصل عبر الزر أدناه:",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    if not is_admin(user_id):
      return

    if data == "main_admin":
      bot.edit_message_text(
          "💎 **لوحة تحكم المطور الرئيسية:**",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=get_main_admin_keyboard(),
          parse_mode="Markdown",
      )

    elif data == "adv_menu":
      keyboard = InlineKeyboardMarkup(row_width=2)
      keyboard.add(
          InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin_prompt"),
          InlineKeyboardButton("➖ إزالة مشرف", callback_data="remove_admin_prompt"),
          InlineKeyboardButton("📋 قائمة المشرفين", callback_data="list_admins"),
          InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"),
      )
      bot.edit_message_text(
          "⚙️ **قسم إدارة المشرفين:**",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data == "add_admin_prompt":
      user_states[user_id] = "waiting_add_admin"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "👤 أرسل آيدي (ID) المشرف الجديد:",
          parse_mode="Markdown",
      )

    elif data == "remove_admin_prompt":
      user_states[user_id] = "waiting_remove_admin"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "🗑️ أرسل آيدي (ID) المشرف المراد إزالته:",
          parse_mode="Markdown",
      )

    elif data == "list_admins":
      cursor.execute("SELECT user_id FROM admins")
      admins = cursor.fetchall()
      text = f"👑 **المطور الأساسي:** `{DEV_ID}`\n\n📋 **المشرفون:**\n"
      for adm in admins:
        text += f"• `{adm[0]}`\n"
      keyboard = InlineKeyboardMarkup().add(
          InlineKeyboardButton("🔙 رجوع", callback_data="adv_menu")
      )
      bot.edit_message_text(
          text,
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data == "stats_menu":
      cursor.execute("SELECT COUNT(*) FROM users")
      u_cnt = cursor.fetchone()[0]
      cursor.execute("SELECT COUNT(*) FROM created_bots")
      b_cnt = cursor.fetchone()[0]
      bot.edit_message_text(
          f"📊 **الإحصائيات العامة:**\n• إجمالي الأعضاء: `{u_cnt}`\n• البوتات"
          f" المنشأة: `{b_cnt}`",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=InlineKeyboardMarkup().add(
              InlineKeyboardButton("🔙 رجوع", callback_data="main_admin")
          ),
          parse_mode="Markdown",
      )

    elif data == "control_menu":
      cursor.execute("SELECT value FROM settings WHERE key = 'free_mode'")
      res = cursor.fetchone()
      status = "مفعل ✅" if res and res[0] == "true" else "معطل ❌"
      keyboard = InlineKeyboardMarkup(row_width=1)
      keyboard.add(
          InlineKeyboardButton("🔴 تعطيل الوضع المجاني", callback_data="set_free_off"),
          InlineKeyboardButton("🟢 تفعيل الوضع المجاني", callback_data="set_free_on"),
          InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"),
      )
      bot.edit_message_text(
          f"🎛️ **الوضع المجاني:** {status}",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data == "set_free_off":
      cursor.execute(
          "INSERT OR REPLACE INTO settings (key, value) VALUES ('free_mode',"
          " 'false')"
      )
      conn.commit()
      bot.answer_callback_query(call.id, "⚠️ تم تعطيل الوضع المجاني.", show_alert=True)

    elif data == "set_free_on":
      cursor.execute(
          "INSERT OR REPLACE INTO settings (key, value) VALUES ('free_mode',"
          " 'true')"
      )
      conn.commit()
      bot.answer_callback_query(call.id, "✅ تم تفعيل الوضع المجاني.", show_alert=True)

    elif data == "publish_menu":
      keyboard = InlineKeyboardMarkup(row_width=1)
      keyboard.add(
          InlineKeyboardButton(
              "📤 إذاعة رسالة شاملة", callback_data="pub_broadcast"
          ),
          InlineKeyboardButton(
              "🔄 توجيه رسالة (Forward)", callback_data="pub_forward"
          ),
          InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"),
      )
      bot.edit_message_text(
          "📣 **قسم النشر والإذاعة:**",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data == "pub_broadcast":
      user_states[user_id] = "waiting_broadcast_msg"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "📤 أرسل الرسالة المراد إذاعتها لكل الأعضاء:",
          parse_mode="Markdown",
      )

    elif data == "pub_forward":
      user_states[user_id] = "waiting_forward_msg"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "🔄 أرسل الرسالة المراد توجيهها للكل:",
          parse_mode="Markdown",
      )

    elif data == "rights_menu":
      cursor.execute("SELECT value FROM settings WHERE key = 'sg_source_btn'")
      sg = cursor.fetchone()[0] == "true"
      cursor.execute("SELECT value FROM settings WHERE key = 'add_btn'")
      add = cursor.fetchone()[0] == "true"
      cursor.execute("SELECT value FROM settings WHERE key = 'x_btn'")
      x = cursor.fetchone()[0] == "true"

      keyboard = InlineKeyboardMarkup(row_width=2)
      keyboard.add(
          InlineKeyboardButton(
              f"زر SG SOURCE: {'مفعل ✅' if sg else 'معطل ❌'}",
              callback_data="toggle_sg",
          ),
          InlineKeyboardButton(
              f"زر ADD: {'مفعل ✅' if add else 'معطل ❌'}",
              callback_data="toggle_add",
          ),
          InlineKeyboardButton(
              f"زر X: {'مفعل ✅' if x else 'معطل ❌'}", callback_data="toggle_x"
          ),
          InlineKeyboardButton(
              "✏️ تعديل زر 'نينو'", callback_data="set_nino_config"
          ),
          InlineKeyboardButton(
              "✏️ تعديل زر 'بوت المنشئ'", callback_data="set_creator_btn"
          ),
          InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"),
      )
      bot.edit_message_text(
          "🎨 **تخصيص أزرار الحقوق والمصدر:**",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data in ["toggle_sg", "toggle_add", "toggle_x"]:
      key_map = {
          "toggle_sg": "sg_source_btn",
          "toggle_add": "add_btn",
          "toggle_x": "x_btn",
      }
      db_key = key_map[data]
      cursor.execute("SELECT value FROM settings WHERE key = ?", (db_key,))
      current = cursor.fetchone()[0] == "true"
      new_val = "false" if current else "true"
      cursor.execute(
          "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
          (db_key, new_val),
      )
      conn.commit()
      bot.answer_callback_query(call.id, "✅ تم تغيير حالة الزر بنجاح.")

    elif data == "set_nino_config":
      user_states[user_id] = "waiting_nino_text"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "✏️ أرسل اسم الزر ورابطه بالشكل الآتي:\n`الاسم | الرابط`",
          parse_mode="Markdown",
      )

    elif data == "set_creator_btn":
      user_states[user_id] = "waiting_creator_btn"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "✏️ أرسل اسم ورابط زر بوت المنشئ بالشكل الآتي:\n`الاسم | الرابط`",
          parse_mode="Markdown",
      )

    elif data == "vip_btn_config":
      user_states[user_id] = "waiting_vip_text"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "✏️ أرسل اسم الزر الجديد لـ VIP (مثال: معرفك):",
          parse_mode="Markdown",
      )

    elif data == "admin_vip_manager":
      keyboard = InlineKeyboardMarkup(row_width=1)
      keyboard.add(
          InlineKeyboardButton(
              "👑 إنشاء بوت VIP خالي من الحقوق تماماً",
              callback_data="create_norights_bot",
          ),
          InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"),
      )
      bot.edit_message_text(
          "💎 **إدارة بوتات الـ VIP:**",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data == "create_norights_bot":
      user_states[user_id] = "waiting_norights_token"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "👑 أرسل توكن البوت الجديد (من @BotFather) لبيئة العمل ليتم تشغيله"
          " خالي من الحقوق:",
          parse_mode="Markdown",
      )

    elif data == "assistants_menu":
      cursor.execute("SELECT id FROM assistants")
      asts = cursor.fetchall()
      keyboard = InlineKeyboardMarkup(row_width=1)
      for ast in asts:
        keyboard.add(
            InlineKeyboardButton(
                f"🗑️ حذف المساعد #{ast[0]}",
                callback_data=f"del_ast_{ast[0]}",
            )
        )
      keyboard.add(
          InlineKeyboardButton("➕ إضافة مساعد جديد", callback_data="add_assistant_prompt")
      )
      keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"))
      bot.edit_message_text(
          f"🤖 **إدارة الحسابات المساعدة:**\nالمساعدون المفعلون:"
          f" `{len(asts)}`",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
          parse_mode="Markdown",
      )

    elif data == "add_assistant_prompt":
      user_states[user_id] = "waiting_add_assistant"
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "🤖 أرسل جلسة الحساب (Session String):",
          parse_mode="Markdown",
      )

    elif data.startswith("del_ast_"):
      ast_id = data.split("_")[2]
      cursor.execute("DELETE FROM assistants WHERE id = ?", (ast_id,))
      conn.commit()
      bot.answer_callback_query(call.id, "✅ تم حذف المساعد بنجاح.")
      cursor.execute("SELECT id FROM assistants")
      asts = cursor.fetchall()
      keyboard = InlineKeyboardMarkup(row_width=1)
      for ast in asts:
        keyboard.add(
            InlineKeyboardButton(
                f"🗑️ حذف المساعد #{ast[0]}",
                callback_data=f"del_ast_{ast[0]}",
            )
        )
      keyboard.add(
          InlineKeyboardButton("➕ إضافة مساعد جديد", callback_data="add_assistant_prompt")
      )
      keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"))
      bot.edit_message_text(
          "🤖 **إدارة الحسابات المساعدة:**",
          call.message.chat.id,
          call.message.message_id,
          reply_markup=keyboard,
      )


  @bot.message_handler(
      content_types=[
          "text",
          "photo",
          "video",
          "document",
          "audio",
          "voice",
          "sticker",
          "animation",
      ],
      func=lambda message: message.from_user.id in user_states,
  )
  def handle_states(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text.strip() if message.text else ""
    user_states.pop(user_id, None)

    if state == "waiting_vip_text" and is_admin(user_id):
      cursor.execute(
          "INSERT OR REPLACE INTO settings (key, value) VALUES ('vip_btn_text',"
          " ?)",
          (text,),
      )
      conn.commit()
      user_states[user_id] = "waiting_vip_link"
      bot.reply_to(
          message,
          "🔗 أرسل الرابط أو اليوزر الجديد للزر (مثال:"
          " `https://t.me/Username`):",
          parse_mode="Markdown",
      )
      return

    elif state == "waiting_vip_link" and is_admin(user_id):
      cursor.execute(
          "INSERT OR REPLACE INTO settings (key, value) VALUES ('vip_btn_link',"
          " ?)",
          (text,),
      )
      conn.commit()
      bot.reply_to(message, "✅ **تم تحديث زر اصنع VIP بنجاح!**", parse_mode="Markdown")
      return

    elif state == "waiting_nino_text" and is_admin(user_id):
      try:
        name, link = text.split("|")
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('nino_btn_text',"
            " ?)",
            (name.strip(),),
        )
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('nino_btn_link',"
            " ?)",
            (link.strip(),),
        )
        conn.commit()
        bot.reply_to(message, "✅ تم تحديث زر 'نينو' ورابطه بنجاح.")
      except:
        bot.reply_to(message, "❌ خطأ بالصيغة. استخدم: الاسم | الرابط")
      return

    elif state == "waiting_creator_btn" and is_admin(user_id):
      try:
        name, link = text.split("|")
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES"
            " ('creator_btn_text', ?)",
            (name.strip(),),
        )
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES"
            " ('creator_btn_link', ?)",
            (link.strip(),),
        )
        conn.commit()
        bot.reply_to(message, "✅ تم تحديث زر 'بوت المنشئ' ورابطه بنجاح.")
      except:
        bot.reply_to(message, "❌ خطأ بالصيغة. استخدم: الاسم | الرابط")
      return

    elif state == "waiting_norights_token" and is_admin(user_id):
      try:
        process = subprocess.Popen(["python", __file__, text])
        active_bots[text] = process
        cursor.execute(
            "INSERT INTO created_bots (user_id, bot_token, bot_type, rights)"
            " VALUES (?, ?, ?, ?)",
            (user_id, text, "vip", "no_rights"),
        )
        conn.commit()
        bot.reply_to(
            message,
            "👑 **تم إنشاء وتشغيل بوت الـ VIP الخالي من الحقوق تماماً بنجاح!**",
            parse_mode="Markdown",
        )
      except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}")
      return

    if not is_admin(user_id):
      return

    if state == "waiting_broadcast_msg":
      cursor.execute("SELECT user_id FROM users")
      sent, failed = 0, 0
      status_msg = bot.reply_to(message, "⏳ جاري الإذاعة...")
      for u in cursor.fetchall():
        try:
          bot.copy_message(
              chat_id=u[0],
              from_chat_id=message.chat.id,
              message_id=message.message_id,
          )
          sent += 1
        except:
          failed += 1
      bot.edit_message_text(
          f"✅ **تمت الإذاعة:**\n• نجاح: `{sent}`\n• فشل: `{failed}`",
          status_msg.chat.id,
          status_msg.message_id,
          parse_mode="Markdown",
      )

    elif state == "waiting_forward_msg":
      cursor.execute("SELECT user_id FROM users")
      sent, failed = 0, 0
      status_msg = bot.reply_to(message, "⏳ جاري التوجيه...")
      for u in cursor.fetchall():
        try:
          bot.forward_message(
              chat_id=u[0],
              from_chat_id=message.chat.id,
              message_id=message.message_id,
          )
          sent += 1
        except:
          failed += 1
      bot.edit_message_text(
          f"✅ **تم التوجيه:**\n• نجاح: `{sent}`\n• فشل: `{failed}`",
          status_msg.chat.id,
          status_msg.message_id,
          parse_mode="Markdown",
      )

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
      cursor.execute(
          "INSERT INTO assistants (session_string) VALUES (?)", (text,)
      )
      conn.commit()
      bot.reply_to(message, "✅ تم حفظ وإضافة جلسة المساعد بنجاح.")


  @bot.message_handler(commands=["create"])
  def create_music_bot(message):
    try:
      parts = message.text.split(maxsplit=1)
      if len(parts) < 2:
        bot.reply_to(
            message,
            "⚠️ أرسل التوكن هكذا:\n`/create [Token]`",
            parse_mode="Markdown",
        )
        return

      token = parts[1].strip()
      user_id = message.from_user.id

      if token in active_bots:
        bot.reply_to(message, "⚠️ هذا البوت يعمل بالفعل!")
        return

      process = subprocess.Popen(["python", __file__, token])
      active_bots[token] = process

      bot_rights = "no_rights" if is_admin(user_id) else "with_rights"
      cursor.execute(
          "INSERT INTO created_bots (user_id, bot_token, bot_type, rights)"
          " VALUES (?, ?, ?, ?)",
          (user_id, token, "free", bot_rights),
      )
      conn.commit()

      bot.reply_to(
          message,
          "✅ **تم إنشاء وتشغيل بوت الميوزك المجاني بنجاح!** 🎶",
          parse_mode="Markdown",
      )
    except Exception as e:
      bot.reply_to(message, f"❌ حدث خطأ: {e}")


  print("Main Creator Bot is running completely with all features...")
  bot.infinity_polling()

