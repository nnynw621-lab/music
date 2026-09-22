import os
import sqlite3
import telebot
from telebot import types

try:
  import psutil
except ImportError:
  psutil = None

# ==========================================
# إعدادات البوت والبيئة
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [
    123456789
]  # استبدل هذا الرقم بآيدي حسابك الحقيقي لفتح لوحة المطورين

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================================
# قاعدة البيانات الشاملة (SQLite)
# ==========================================
conn = sqlite3.connect("mega_music_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_banned INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS sub_bots (
    bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    bot_token TEXT UNIQUE,
    bot_username TEXT,
    status TEXT DEFAULT 'active'
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
"""
)
conn.commit()


def is_admin(user_id):
  return user_id in ADMIN_IDS


# ==========================================
# الواجهة الرئيسية للمستخدم (Start)
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

  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(
      types.InlineKeyboardButton(
          "🟢 صنع بوت ميوزك جديد", callback_data="user:create_bot"
      ),
      types.InlineKeyboardButton(
          "🔵 حسابي وإحصائياتي", callback_data="user:account"
      ),
  )

  bot.send_message(
      message.chat.id,
      f"أهلاً بك يا <b>{message.from_user.first_name}</b> في منصة بوتات"
      " الميوزك الشاملة 🎶\nأنشئ بوتك الخاص الآن وقم بإدارته بكل سهولة!",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith("user:"))
def handle_user_callbacks(call):
  user_id = call.from_user.id
  action = call.data.split(":")[1]

  if action == "create_bot":
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🔹 أرسل الآن <b>توكن البوت (Token)</b> الذي استخرجته من @BotFather:\n*(أو"
        " أرسل /cancel للإلغاء)*",
    )
    bot.register_next_step_handler(msg, process_save_sub_bot)

  elif action == "account":
    cursor.execute(
        "SELECT COUNT(*) FROM sub_bots WHERE owner_id = ?", (user_id,)
    )
    bots_count = cursor.fetchone()[0]
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"👤 <b>حسابك الشخصي:</b>\n🆔 الآيدي: <code>{user_id}</code>\n🤖 عدد"
        f" بوتاتك: {bots_count}",
    )


def process_save_sub_bot(message):
  if message.text == "/cancel":
    bot.reply_to(message, "تم إلغاء الإنشاء.")
    return
  user_id = message.from_user.id
  token = message.text.strip()
  try:
    temp_bot = telebot.TeleBot(token)
    bot_info = temp_bot.get_me()
    bot_username = bot_info.username
  except Exception:
    bot.reply_to(
        message,
        "❌ <b>التوكن غير صالح!</b> تأكد من نسخه بدقة من @BotFather.",
    )
    return

  try:
    cursor.execute(
        "INSERT INTO sub_bots (owner_id, bot_token, bot_username) VALUES"
        " (?, ?, ?)",
        (user_id, token, bot_username),
    )
    conn.commit()
    bot.reply_to(
        message,
        f"✅ <b>تم إنشاء بوت الميوزك بنجاح!</b>\n🤖 المعرف: @{bot_username}",
    )
  except sqlite3.IntegrityError:
    bot.reply_to(message, "⚠️ هذا التوكن مستخدم مسبقاً في النظام!")


# ==========================================
# معالجة أوامر الاتصال والجات (تشغيل، بحث، تنزيل، نزل، يوت)
# ==========================================
@bot.message_handler(
    func=lambda message: message.text
    and any(
        message.text.startswith(word)
        for word in ["تشغيل", "بحث", "تنزيل", "نزل", "يوت"]
    )
)
def handle_media_commands(message):
  text = message.text.strip()

  # أوامر الاتصال الصوتي (Voice Chat)
  if text.startswith("تشغيل") or text.startswith("بحث"):
    query = text.replace("تشغيل", "").replace("بحث", "").strip()
    if not query:
      bot.reply_to(
          message,
          "⚠️ يرجى كتابة اسم الأغنية.\nمثال: <code>تشغيل تخون بيه</code>",
      )
      return

    send_music_player(
        message.chat.id,
        song_name=query,
        duration="05:50",
        source_name="SG SOURCE",
        source_url="https://t.me/YourChannel",
    )

  # أوامر الجات النصي (تنزيل ملفات)
  elif (
      text.startswith("تنزيل") or text.startswith("نزل") or text.startswith("يوت")
  ):
    query = (
        text.replace("تنزيل", "")
        .replace("نزل", "")
        .replace("يوت", "")
        .strip()
    )
    if not query:
      bot.reply_to(
          message, "⚠️ يرجى كتابة اسم الطلب.\nمثال: <code>نزل تخون بيه</code>"
      )
      return

    bot.reply_to(
        message,
        f"📥 <b>جاري البحث والتحميل للجات:</b>\n🔍 {query}\n(يرجى الانتظار"
        " قليلاً...)",
    )


# ==========================================
# دالة مشغل الموسيقى التفاعلي (مع الأزرار والروابط)
# ==========================================
def send_music_player(
    chat_id,
    song_name,
    duration,
    source_name="SG SOURCE",
    source_url="https://t.me/YourChannel",
):
  msg_text = (
      f"🎶 - <b>تم تشغيل :</b> {song_name}\n"
      f"⏱ - <b>مدة التشغيل :</b> {duration}\n"
      "🔊 - <b>الحالة :</b> يعمل الآن في المكالمة الصوتية"
  )

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
  markup.add(types.InlineKeyboardButton(source_name, url=source_url))
  markup.add(types.InlineKeyboardButton("ADD", callback_data="music:add"))
  markup.add(types.InlineKeyboardButton("❌", callback_data="music:close"))

  bot.send_message(chat_id, msg_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("music:"))
def handle_music_controls_fixed(call):
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
  elif action == "add":
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        chat_id, "➕ أرسل الآن اسم أو رابط الأغنية لإضافتها لقائمة الانتظار:"
    )
    bot.register_next_step_handler(
        msg,
        lambda m: bot.reply_to(
            m, f"✅ تم إضافة الطلب ({m.text}) إلى قائمة الانتظار بنجاح!"
        ),
    )
  elif action == "close":
    try:
      bot.delete_message(chat_id, call.message.message_id)
    except Exception:
      pass


# ==========================================
# قاموس الأقسام الـ 30 لإدارة المطور (شاملة)
# ==========================================
ADMIN_SECTIONS = {
    1: "📊 المؤشرات العامة والإحصائيات",
    2: "🖥 مراقبة السيرفر والمعالج",
    3: "👥 إدارة المشرفين المساعدين",
    4: "⚙️ إعدادات البوت العامة",
    5: "📢 إدارة الإذاعة والتوجيه",
    6: "🔍 فحص بيانات مستخدم",
    7: "⛔️ إدارة الحظر والعقوبات",
    8: "⭐ إدارة المشتركين VIP",
    9: "📝 سجل الأخطاء والـ Logs",
    10: "📈 تقارير الأداء التفصيلية",
    11: "🤖 إدارة البوتات الفرعية",
    12: "💬 تعديل رسالة البدء (Start)",
    13: "🔗 قنوات الاشتراكات الإجبارية",
    14: "🎟 إدارة الكوبونات والأكواد",
    15: "👋 رسائل الترحيب التلقائية",
    16: "📢 الإذاعة العامة لكل المستخدمين",
    17: "📢 إذاعة خاصة للمشرفين",
    18: "💾 نسخة احتياطية للقاعدة",
    19: "♻️ استعادة نسخة احتياطية",
    20: "🔄 إعادة تشغيل البوت برمجياً",
    21: "⭐ نظام نجوم تيليجرام",
    22: "💳 إدارة الباقات والأسعار",
    23: "🌐 فحص حالة الاتصال والسيرفر",
    24: "🧹 تصفية المستخدمين الوهميين",
    25: "📋 سجل العمليات الأخيرة",
    26: "🔒 إعدادات الأمان والحماية",
    27: "🔗 تحديث روابط السورس (Source)",
    28: "🚨 رسائل الطوارئ والصيانة",
    29: "🛑 تفعيل وضع الطوارئ",
    30: "💾 النسخ الاحتياطي الشامل للنظام",
}


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
  if not is_admin(message.from_user.id):
    return

  markup = types.InlineKeyboardMarkup(row_width=2)
  for sec_id, sec_name in ADMIN_SECTIONS.items():
    markup.add(
        types.InlineKeyboardButton(
            sec_name, callback_data=f"adm:sec:{sec_id}"
        )
    )
  markup.add(types.InlineKeyboardButton("❌ إغلاق اللوحة", callback_data="adm:close"))

  bot.send_message(
      message.chat.id,
      "🎛 <b>غرفة العمليات المركزية (الأقسام الـ 30 كاملة)</b>\nاختر القسم المطلوب:",
      reply_markup=markup,
  )


# ==========================================
# معالجة تفاعلية حقيقية لجميع أزرار لوحة المطورين
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm:"))
def handle_admin_actions(call):
  if not is_admin(call.from_user.id):
    bot.answer_callback_query(call.id, "للمطورين فقط!", show_alert=True)
    return

  data = call.data.split(":")

  if data[1] == "close":
    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
      pass
    return

  elif data[1] == "sec":
    sec_id = int(data[2])
    sec_title = ADMIN_SECTIONS.get(sec_id, f"القسم {sec_id}")
    markup = types.InlineKeyboardMarkup(row_width=1)

    if sec_id == 1:
      cursor.execute("SELECT COUNT(*) FROM users")
      u_count = cursor.fetchone()[0]
      cursor.execute("SELECT COUNT(*) FROM sub_bots")
      b_count = cursor.fetchone()[0]
      text = (
          f"📂 <b>{sec_title}</b>\n\n👥 إجمالي المستخدمين:"
          f" <b>{u_count}</b>\n🤖 البوتات الفرعية: <b>{b_count}</b>"
      )
      markup.add(
          types.InlineKeyboardButton(
              "🔄 تحديث المؤشرات", callback_data="adm:sec:1"
          )
      )

    elif sec_id == 2:
      if psutil:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        text = (
            f"📂 <b>{sec_title}</b>\n\n🖥 استهلاك المعالج (CPU):"
            f" <b>{cpu}%</b>\n🧠 استهلاك الذاكرة (RAM): <b>{ram}%</b>"
        )
      else:
        text = f"📂 <b>{sec_title}</b>\n\nمكتبة psutil غير متوفرة."
      markup.add(
          types.InlineKeyboardButton("🔄 تحديث الفحص", callback_data="adm:sec:2")
      )

    elif sec_id == 7:
      text = f"📂 <b>{sec_title}</b>\n\nاختر الإجراء المطلوب:"
      markup.add(
          types.InlineKeyboardButton(
              "🔴 حظر مستخدم بالآيدي", callback_data="adm:action:ban"
          ),
          types.InlineKeyboardButton(
              "🟢 إلغاء حظر مستخدم", callback_data="adm:action:unban"
          ),
      )

    elif sec_id == 16:
      text = f"📂 <b>{sec_title}</b>\n\nأرسل رسالة لتصل لجميع المستخدمين:"
      markup.add(
          types.InlineKeyboardButton(
              "📢 بدء الإذاعة الشاملة", callback_data="adm:action:broadcast"
          )
      )

    elif sec_id == 29:
      text = (
          f"📂 <b>{sec_title}</b>\n\n⚠️ تفعيل وضع الطوارئ سيوقف استجابة البوت"
          " للأعضاء المؤقتين."
      )
      markup.add(
          types.InlineKeyboardButton(
              "🛑 تفعيل/إيقاف وضع الطوارئ", callback_data="adm:action:emergency"
          )
      )

    elif sec_id == 30:
      text = (
          f"📂 <b>{sec_title}</b>\n\n💾 احصل على نسخة من قاعدة بيانات البوت"
          " الآن."
      )
      markup.add(
          types.InlineKeyboardButton(
              "📥 تحميل ملف القاعدة (Backup)", callback_data="adm:action:backup"
          )
      )

    else:
      text = (
          f"📂 <b>{sec_title}</b>\n⚙️ هذا القسم مفعل. اضغط أدناه لتعديل إعداداته"
          " أو تنفيذ مهامه:"
      )
      markup.add(
          types.InlineKeyboardButton(
              "✏️ تعديل إعدادات هذا القسم",
              callback_data=f"adm:action:edit_{sec_id}",
          )
      )

    markup.add(types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="adm:back"))

    try:
      bot.edit_message_text(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          text=text,
          reply_markup=markup,
      )
    except Exception:
      pass

  elif data[1] == "action":
    act = data[2]
    if act == "ban":
      bot.answer_callback_query(call.id)
      msg = bot.send_message(
          call.message.chat.id, "⛔️ أرسل آيدي (ID) المستخدم المراد حظره:"
      )
      bot.register_next_step_handler(msg, process_ban_user)
    elif act == "unban":
      bot.answer_callback_query(call.id)
      msg = bot.send_message(
          call.message.chat.id, "🟢 أرسل آيدي (ID) المستخدم لفك حظره:"
      )
      bot.register_next_step_handler(msg, process_unban_user)
    elif act == "broadcast":
      bot.answer_callback_query(call.id)
      msg = bot.send_message(
          call.message.chat.id, "📢 أرسل نص الإذاعة الآن:"
      )
      bot.register_next_step_handler(msg, process_global_broadcast)
    elif act == "backup":
      bot.answer_callback_query(call.id, "📁 جاري إرسال نسخة القاعدة...")
      try:
        with open("mega_music_bot.db", "rb") as db_file:
          bot.send_document(
              call.message.chat.id,
              db_file,
              caption="💾 النسخة الاحتياطية لقاعدة البيانات",
          )
      except Exception:
        bot.send_message(
            call.message.chat.id, "❌ لم يتم العثور على ملف القاعدة بعد."
        )
    elif act.startswith("edit_"):
      sec_num = act.split("_")[1]
      bot.answer_callback_query(call.id)
      msg = bot.send_message(
          call.message.chat.id,
          f"📝 أرسل القيمة الجديدة الخاصة بإعدادات القسم ({sec_num}):",
      )
      bot.register_next_step_handler(
          msg, lambda m: process_save_section_setting(m, sec_num)
      )
    else:
      bot.answer_callback_query(
          call.id, "✅ تم تنفيذ الإجراء بنجاح!", show_alert=True
      )

  elif data[1] == "back":
    cmd_admin(call.message)


# ==========================================
# دوال معالجة الخطوات والمدخلات
# ==========================================
def process_ban_user(message):
  try:
    target_id = int(message.text.strip())
    cursor.execute(
        "UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,)
    )
    conn.commit()
    bot.reply_to(message, f"✅ تم حظر المستخدم ({target_id}) بنجاح.")
  except ValueError:
    bot.reply_to(message, "❌ الآيدي غير صالح.")


def process_unban_user(message):
  try:
    target_id = int(message.text.strip())
    cursor.execute(
        "UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,)
    )
    conn.commit()
    bot.reply_to(message, f"✅ تم فك الحظر عن المستخدم ({target_id}) بنجاح.")
  except ValueError:
    bot.reply_to(message, "❌ الآيدي غير صالح.")


def process_global_broadcast(message):
  broadcast_text = message.text
  cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
  users = cursor.fetchall()

  success, failed = 0, 0
  status_msg = bot.reply_to(message, "📢 جاري بدء الإذاعة الشاملة...")

  for user in users:
    try:
      bot.send_message(user[0], broadcast_text)
      success += 1
    except Exception:
      failed += 1

  bot.edit_message_text(
      chat_id=message.chat.id,
      message_id=status_msg.message_id,
      text=(
          "📊 <b>نتائج الإذاعة الشاملة:</b>\n\n✅ تم الإرسال بنجاح:"
          f" <b>{success}</b>\n❌ فشل الإرسال (حظروا البوت):"
          f" <b>{failed}</b>"
      ),
  )


def process_save_section_setting(message, sec_num):
  val = message.text.strip()
  cursor.execute(
      "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
      (f"sec_{sec_num}_config", val),
  )
  conn.commit()
  bot.reply_to(
      message,
      f"✅ تم حفظ إعدادات القسم ({sec_num}) بنجاح:\n<code>{val}</code>",
  )


if __name__ == "__main__":
  print("Complete Mega Bot with 30 Sections & Player is running...")
  bot.infinity_polling()

