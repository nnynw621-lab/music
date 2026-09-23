import asyncio
import json
import os
from pyrogram import Client, filters, idle
from pyrogram.errors import SessionPasswordNeeded
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
import yt_dlp

# --- قراءة المتغيرات من البيئة (أمان وسهولة تامة) ---
API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "ضع_توكن_البوت_هنا_إذا_لم_تحب_استخدام_متغيرات_البيئة")
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "123456789")) # أيدي المطور الخاص بك

SESSION_FILE = "assistant_session.txt"
DATA_FILE = "bot_data.json"

# تشغيل البوت الرئيسي مع التوكن
app = Client(
    "music_bot_main",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = None
user_states = {}  
temp_logins = {}  


# --- نظام قاعدة البيانات المحلية ---
def load_data():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return {
      "developer_id": DEVELOPER_ID,
      "admins": [],
      "banned_users": [],
      "users": [],
      "forced_subs": [],  
      "broadcast_config": {
          "media_url": "https://envs.sh/i/XYZ.jpg",
          "btn1_text": "SG SOURCE",
          "btn1_url": "https://t.me/YourDeveloperChannel",
          "btn2_text": "ADD",
          "btn2_url": "https://t.me/YourBot?startgroup=true",
          "btn3_text": "X",
          "btn3_url": "https://t.me/YourChannel",
      },
      "assistants": [],
  }


def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def is_admin_or_dev(user_id):
  data = load_data()
  return user_id == data["developer_id"] or user_id in data["admins"]


# ==========================================
# لوحات التحكم الرئيسية والأقسام الملونة المطلوبة
# ==========================================

def main_admin_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🔵 1- القسم المتقدم (المشرفين)", callback_data="adv_menu"), InlineKeyboardButton("🟡 2- لوحة الإحصائيات العامة", callback_data="stats_menu")],
      [InlineKeyboardButton("🔴 4- إدارة الاشتراكات الإجبارية", callback_data="sub_menu"), InlineKeyboardButton("🎨 تعديل كليشة النشر", callback_data="broadcast_menu")],
      [InlineKeyboardButton("🤖 إدارة حسابات المساعدين", callback_data="assistants_menu")],
      [InlineKeyboardButton("❌ إغلاق القائمة", callback_data="close")],
  ])


def advanced_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🟢 إضافة مشرف", callback_data="add_admin"), InlineKeyboardButton("🔴 إزالة مشرف", callback_data="remove_admin")],
      [InlineKeyboardButton("🟡 المشرفين المضافين", callback_data="list_admins"), InlineKeyboardButton("🔙 رجوع للخطوة السابقة", callback_data="main_menu")],
  ])


def stats_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🔴 الأعضاء المحظورين", callback_data="stat_banned"), InlineKeyboardButton("🟢 الأعضاء المتواجدين (الحاضرين)", callback_data="stat_active")],
      [InlineKeyboardButton("🔵 الإحصائيات العامة", callback_data="stat_general"), InlineKeyboardButton("🔙 رجوع للخطوة السابقة", callback_data="main_menu")],
  ])


def forced_sub_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🟢 إضافة قناة أو كروب عام (يجب أن يكون البوت مشرفاً)", callback_data="sub_add_public")],
      [InlineKeyboardButton("🔵 إضافة بوت أو رابط سوشيال ميديا", callback_data="sub_add_social")],
      [InlineKeyboardButton("🟡 إضافة قناة أو كروب خاص", callback_data="sub_add_private")],
      [InlineKeyboardButton("🔙 رجوع للخطوة السابقة", callback_data="main_menu")],
  ])


def broadcast_template_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🖼️ 1- التحكم بالصورة أو الفيديو", callback_data="edit_media")],
      [InlineKeyboardButton("💬 2- التحكم بزر الكليشة (SG SOURCE)", callback_data="edit_btn1")],
      [InlineKeyboardButton("➕ 3- التحكم بزر (ADD)", callback_data="edit_btn2")],
      [InlineKeyboardButton("❌ 4- التحكم بزر (X)", callback_data="edit_btn3")],
      [InlineKeyboardButton("🔙 عودة للوحة الرئيسية", callback_data="main_menu")],
  ])


def assistants_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("➕ إضافة مساعد جديد (تفاعلي)", callback_data="add_assistant_interactive")],
      [InlineKeyboardButton("📋 عرض المساعدين المضافين", callback_data="list_assistants")],
      [InlineKeyboardButton("🔙 عودة للوحة الرئيسية", callback_data="main_menu")],
  ])


def get_player_keyboard():
  data = load_data()
  bc = data["broadcast_config"]
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("⏭ تخطي", callback_data="skip"), InlineKeyboardButton("⏹ إنهاء", callback_data="end"), InlineKeyboardButton("⏸ إيقاف", callback_data="pause")],
      [InlineKeyboardButton("⏪ -10s", callback_data="seek_back"), InlineKeyboardButton("▶", callback_data="resume"), InlineKeyboardButton("⏩ +10s", callback_data="seek_forward")],
      [InlineKeyboardButton(bc["btn1_text"], url=bc["btn1_url"])],
      [InlineKeyboardButton(bc["btn2_text"], url=bc["btn2_url"])],
      [InlineKeyboardButton(bc["btn3_text"], url=bc["btn3_url"])],
  ])


# ==========================================
# دالة التحقق من الاشتراك الإجباري
# ==========================================
async def check_forced_subscriptions(client, user_id):
  data = load_data()
  subs = data.get("forced_subs", [])
  if not subs or is_admin_or_dev(user_id):
    return True

  not_subscribed_channels = []
  for sub in subs:
    chat_id = sub.get("chat_id")
    invite_link = sub.get("link")
    title = sub.get("title", "قناة البوت")
    try:
      member = await client.get_chat_member(chat_id, user_id)
      if member.status in ["left", "banned"]:
        not_subscribed_channels.append(InlineKeyboardButton(f"🔔 اشترك في {title}", url=invite_link))
    except Exception:
      not_subscribed_channels.append(InlineKeyboardButton(f"🔔 اشترك في {title}", url=invite_link))

  if not_subscribed_channels:
    not_subscribed_channels.append([InlineKeyboardButton("✅ لقد اشتركت، حاول مرة أخرى", callback_data="check_sub")])
    return not_subscribed_channels
  return True


# ==========================================
# أوامر البدء واللوحات
# ==========================================
@app.on_message(filters.command("start"))
async def start_command(client, message):
  user_id = message.from_user.id
  data = load_data()

  if user_id not in data["users"]:
    data["users"].append(user_id)
    save_data(data)

  sub_check = await check_forced_subscriptions(client, user_id)
  if sub_check is not True:
    await message.reply(
        "⚠️ **عذراً عزيزي، عليك الاشتراك في قنوات البوت لتتمكن من استخدامه!**\n\n"
        "يرجى الاشتراك في القنوات أدناه ثم اضغط على زر التحقق:",
        reply_markup=InlineKeyboardMarkup(sub_check),
    )
    return

  bot_username = (await client.get_me()).username

  if is_admin_or_dev(user_id):
    await message.reply(
        f"مرحباً بك يا مطور/مشرف {message.from_user.mention} ⚡️\nإليك لوحة التحكم الخاصة بك:",
        reply_markup=main_admin_keyboard(),
    )
    return

  bc = data["broadcast_config"]
  member_keyboard = InlineKeyboardMarkup([
      [InlineKeyboardButton("➕ اضفني لقناتك/كروبك", url=f"https://t.me/{bot_username}?startgroup=true")],
      [InlineKeyboardButton(bc["btn1_text"], url=bc["btn1_url"])],
      [InlineKeyboardButton("❌ إغلاق", callback_data="close")],
  ])

  caption = (
      f"أهلاً بك عزيزي {message.from_user.mention} في بوت الأغاني والمكالمات الصوتية 🎧\n\n"
      "اختر أحد الأزرار أدناه للبدء أو استخدم الأوامر المباشرة (`تشغيل`، `بحث`، `تنزيل`)."
  )

  try:
    await message.reply_photo(photo=bc["media_url"], caption=caption, reply_markup=member_keyboard)
  except Exception:
    await message.reply(caption, reply_markup=member_keyboard)


# ==========================================
# معالجة الأزرار التفاعلية للأدممنية
# ==========================================
@app.on_callback_query()
async def panel_callback_handler(client, callback_query):
  data_cb = callback_query.data
  user_id = callback_query.from_user.id

  if data_cb == "close":
    await callback_query.message.delete()
    return

  if data_cb == "check_sub":
    sub_check = await check_forced_subscriptions(client, user_id)
    if sub_check is True:
      await callback_query.message.edit_text("✅ تم التحقق من اشتراكك بنجاح! أرسل /start للبدء.")
    else:
      await callback_query.answer("⚠️ لم تقم بالاشتراك في كافة القنوات المطلوبة بعد!", show_alert=True)
    return

  if not is_admin_or_dev(user_id):
    await callback_query.answer("⚠️ عذراً، هذه الأزرار مخصصة للمشرفين والمطور فقط!", show_alert=True)
    return

  if data_cb == "main_menu":
    await callback_query.message.edit_text("🎛️ **لوحة التحكم الرئيسية للإدارة:**", reply_markup=main_admin_keyboard())

  elif data_cb == "adv_menu":
    await callback_query.message.edit_text(
        "⚙️ **القسم المتقدم (إدارة المشرفين):**\nاختر العملية المطلوبة:",
        reply_markup=advanced_keyboard(),
    )

  elif data_cb == "add_admin":
    await callback_query.message.edit_text(
        "🟢 **إضافة مشرف:**\nأرسل الآن (أيدي المستخدم - ID) المراد تعيينه مشرفاً في البوت:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adv_menu")]]),
    )
    user_states[user_id] = "waiting_add_admin"

  elif data_cb == "remove_admin":
    await callback_query.message.edit_text(
        "🔴 **إزالة مشرف:**\nأرسل الآن (أيدي المستخدم - ID) المراد إزالته من قائمة المشرفين:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adv_menu")]]),
    )
    user_states[user_id] = "waiting_remove_admin"

  elif data_cb == "list_admins":
    data = load_data()
    admins = data["admins"]
    dev_id = data["developer_id"]
    text = f"👑 **المطور الأساسي:** `{dev_id}`\n\n🛡️ **المشرفون المضافون:**\n"
    if admins:
      for adm in admins:
        text += f"• `{adm}`\n"
    else:
      text += "لا يوجد مشرفين مضافين حالياً."
    await callback_query.message.edit_text(text, reply_markup=advanced_keyboard())

  elif data_cb == "stats_menu":
    await callback_query.message.edit_text(
        "📊 **لوحة الإحصائيات العامة:**\nاختر القسم المطلوب لعرضه:",
        reply_markup=stats_keyboard(),
    )

  elif data_cb == "stat_banned":
    data = load_data()
    await callback_query.message.edit_text(
        f"🔴 **الأعضاء المحظورين:**\nالعدد الإجمالي: `{len(data['banned_users'])}`",
        reply_markup=stats_keyboard(),
    )

  elif data_cb == "stat_active":
    data = load_data()
    await callback_query.message.edit_text(
        f"🟢 **الأعضاء الحاضرين للبوت (المسجلين):**\nالعدد الإجمالي: `{len(data['users'])}`",
        reply_markup=stats_keyboard(),
    )

  elif data_cb == "stat_general":
    data = load_data()
    text = (
        f"🔵 **الإحصائيات العامة الشاملة:**\n\n"
        f"👥 إجمالي المستخدمين: `{len(data['users'])}`\n"
        f"🛡️ عدد المشرفين: `{len(data['admins'])}`\n"
        f"🚫 الأعضاء المحظورين: `{len(data['banned_users'])}`\n"
        f"📢 قنوات الاشتراك الإجباري: `{len(data['forced_subs'])}`"
    )
    await callback_query.message.edit_text(text, reply_markup=stats_keyboard())

  elif data_cb == "sub_menu":
    await callback_query.message.edit_text(
        "📢 **إدارة الاشتراكات الإجبارية:**\nاختر نوع الاشتراك المراد إضافته:",
        reply_markup=forced_sub_keyboard(),
    )

  elif data_cb == "sub_add_public":
    await callback_query.message.edit_text(
        "🟢 **إضافة قناة أو كروب عام:**\n"
        "تأكد أن البوت مشرف فيها.\n"
        "أرسل المعرف ورابط الدعوة بالشكل التالي:\n`معرف_القناة | رابط_الدعوة | اسم_القناة`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="sub_menu")]]),
    )
    user_states[user_id] = "waiting_sub_public"

  elif data_cb == "sub_add_social":
    await callback_query.message.edit_text(
        "🔵 **إضافة بوت أو رابط سوشيال ميديا:**\n"
        "أرسل الرابط والاسم بالشكل التالي:\n`رابط_المنصة | اسم_الزر`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="sub_menu")]]),
    )
    user_states[user_id] = "waiting_sub_social"

  elif data_cb == "sub_add_private":
    await callback_query.message.edit_text(
        "🟡 **إضافة قناة أو كروب خاص:**\n"
        "أرسل رابط الدعوة الخاص والاسم بالشكل التالي:\n`رابط_خاص | اسم_الجهة`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="sub_menu")]]),
    )
    user_states[user_id] = "waiting_sub_private"

  elif data_cb == "broadcast_menu":
    await callback_query.message.edit_text(
        "🎨 **قسم التحكم بكليشة النشر والأزرار:**\nاختر العنصر الذي تريد تعديله:",
        reply_markup=broadcast_template_keyboard(),
    )

  elif data_cb == "assistants_menu":
    await callback_query.message.edit_text(
        "🤖 **قسم إدارة حسابات المساعدين المستقلة:**\nيسمح لك بربط حسابات مساعدين جدد لتشغيل الأغاني:",
        reply_markup=assistants_keyboard(),
    )

  elif data_cb == "add_assistant_interactive":
    await callback_query.message.edit_text(
        "📱 **إضافة حساب مساعد جديد:**\n\n"
        "يرجى إرسال **رقم الهاتف** الخاص بالحساب المراد إضافته مع رمز الدولة (مثال: `+9647700000000`):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="assistants_menu")]]),
    )
    user_states[user_id] = "waiting_assistant_phone"

  elif data_cb == "list_assistants":
    data = load_data()
    asts = data["assistants"]
    text = "📋 **قائمة المساعدين المضافين:**\n\n"
    if asts:
      for idx, ast in enumerate(asts, 1):
        text += f"{idx}- `{ast[:15]}...`\n"
    else:
      text += "لا يوجد مساعدين إضافيين مسجلين حالياً."
    await callback_query.message.edit_text(text, reply_markup=assistants_keyboard())

  elif data_cb in ["edit_media", "edit_btn1", "edit_btn2", "edit_btn3"]:
    state_map = {
        "edit_media": ("waiting_media", "أرسل رابط الصورة أو الفيديو المتحرك الجديد لكليشة النشر:"),
        "edit_btn1": ("waiting_btn1", "أرسل النص والرابط الجديد للزر الأول (مثال: النص | الرابط):"),
        "edit_btn2": ("waiting_btn2", "أرسل النص والرابط الجديد لزر ADD (مثال: النص | الرابط):"),
        "edit_btn3": ("waiting_btn3", "أرسل النص والرابط الجديد لزر X (مثال: النص | الرابط):"),
    }
    state_key, prompt_text = state_map[data_cb]
    user_states[user_id] = state_key
    await callback_query.message.edit_text(
        prompt_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="broadcast_menu")]]))
  else:
    await callback_query.answer("⚙️ جاري معالجة الطلب...", show_short=True)


# ==========================================
# المدخلات النصية وتسجيل المساعد التفاعلي
# ==========================================
@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_admin_text_inputs(client, message):
  user_id = message.from_user.id
  if user_id not in user_states:
    return

  state = user_states[user_id]
  data = load_data()

  if state == "waiting_assistant_phone":
    phone_number = message.text.strip()
    msg_wait = await message.reply("⏳ جاري إرسال كود التحقق إلى حسابك على تليجرام...")
    try:
      temp_client = Client(f"temp_ast_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
      await temp_client.connect()
      sent_code = await temp_client.send_code(phone_number)

      temp_logins[user_id] = {
          "client": temp_client,
          "phone": phone_number,
          "phone_code_hash": sent_code.phone_code_hash,
      }
      user_states[user_id] = "waiting_assistant_code"
      await msg_wait.edit_text(
          "✅ **تم إرسال كود التحقق بنجاح إلى رسائل تليجرام الرسمية.**\n\n"
          "يرجى إرسال كود التحقق الآن (يمكنك وضع مسافات أو كتابته مباشرة):"
      )
    except Exception as e:
      await msg_wait.edit_text(f"❌ حدث خطأ أثناء إرسال الكود:\n`{e}`\n\nأرسل /start للعودة.")
      del user_states[user_id]

  elif state == "waiting_assistant_code":
    code = message.text.strip().replace(" ", "")
    login_info = temp_logins.get(user_id)
    if not login_info:
      await message.reply("⚠️ انتهت صلاحية الجلسة المؤقتة. يرجى بدء العملية من جديد.")
      del user_states[user_id]
      return

    temp_client = login_info["client"]
    phone = login_info["phone"]
    phone_code_hash = login_info["phone_code_hash"]

    msg_wait = await message.reply("⏳ جاري التحقق من الكود وتسجيل الدخول...")
    try:
      await temp_client.sign_in(phone, phone_code_hash, code)
      session_string = await temp_client.export_session_string()
      data["assistants"].append(session_string)
      save_data(data)

      await temp_client.disconnect()
      del user_states[user_id]
      del temp_logins[user_id]

      await msg_wait.edit_text(
          "🎉 **تم تسجيل حساب المساعد بنجاح وحفظ الجلسة في البوت!**", reply_markup=main_admin_keyboard()
      )
    except SessionPasswordNeeded:
      user_states[user_id] = "waiting_assistant_password"
      await msg_wait.edit_text(
          "🔒 **هذا الحساب محمي بكلمة مرور (التحقق بخطوتين - 2FA).**\n\n"
          "يرجى إرسال كلمة المرور الخاصة بحسابك الآن:"
      )
    except Exception as e:
      await msg_wait.edit_text(f"❌ الكود غير صحيح أو حدث خطأ:\n`{e}`")

  elif state == "waiting_assistant_password":
    password = message.text.strip()
    login_info = temp_logins.get(user_id)
    if not login_info:
      await message.reply("⚠️ انتهت صلاحية الجلسة المؤقتة.")
      del user_states[user_id]
      return

    temp_client = login_info["client"]
    msg_wait = await message.reply("⏳ جاري التحقق من كلمة المرور...")
    try:
      await temp_client.check_password(password)
      session_string = await temp_client.export_session_string()
      data["assistants"].append(session_string)
      save_data(data)

      await temp_client.disconnect()
      del user_states[user_id]
      del temp_logins[user_id]

      await msg_wait.edit_text(
          "🎉 **تم التحقق بنجاح وإضافة حساب المساعد إلى البوت!**", reply_markup=main_admin_keyboard()
      )
    except Exception as e:
      await msg_wait.edit_text(f"❌ كلمة المرور غير صحيحة أو حدث خطأ:\n`{e}`")

  elif state == "waiting_add_admin":
    try:
      new_adm = int(message.text.strip())
      if new_adm not in data["admins"]:
        data["admins"].append(new_adm)
        save_data(data)
      del user_states[user_id]
      await message.reply(f"✅ تم بنجاح إضافة المستخدم `{new_adm}` إلى قائمة المشرفين!", reply_markup=main_admin_keyboard())
    except ValueError:
      await message.reply("⚠️ يرجى إرسال أيدي (ID) صحيح بالأرقام فقط.")

  elif state == "waiting_remove_admin":
    try:
      rem_adm = int(message.text.strip())
      if rem_adm in data["admins"]:
        data["admins"].remove(rem_adm)
        save_data(data)
      del user_states[user_id]
      await message.reply(f"✅ تم إزالة المستخدم `{rem_adm}` من المشرفين بنجاح.", reply_markup=main_admin_keyboard())
    except ValueError:
      await message.reply("⚠️ يرجى إرسال أيدي (ID) صحيح بالأرقام فقط.")

  elif state in ["waiting_sub_public", "waiting_sub_social", "waiting_sub_private"]:
    try:
      parts = message.text.split("|")
      if state == "waiting_sub_public":
        chat_id = parts[0].strip()
        link = parts[1].strip()
        title = parts[2].strip() if len(parts) > 2 else "قناة عامة"
        data["forced_subs"].append({"chat_id": chat_id, "link": link, "title": title})
      elif state == "waiting_sub_social":
        link = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else "منصة اجتماعية"
        data["forced_subs"].append({"chat_id": "@forced_social", "link": link, "title": title})
      elif state == "waiting_sub_private":
        link = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else "قناة خاصة"
        data["forced_subs"].append({"chat_id": -1000000000000, "link": link, "title": title})

      save_data(data)
      del user_states[user_id]
      await message.reply("✅ تمت إضافة الاشتراك الإجباري بنجاح وتفعيله!", reply_markup=main_admin_keyboard())
    except Exception:
      await message.reply("⚠️ حدث خطأ في صيغة الإرسال. يرجى مراجعة المثال الموضح وإعادة المحاولة بالشكل الصحيح.")

  elif state == "waiting_media":
    data["broadcast_config"]["media_url"] = message.text.strip()
    save_data(data)
    del user_states[user_id]
    await message.reply("✅ تم تحديث ميديا الكليشة بنجاح!", reply_markup=main_admin_keyboard())

  elif state in ["waiting_btn1", "waiting_btn2", "waiting_btn3"]:
    try:
      parts = message.text.split("|")
      btn_text = parts[0].strip()
      btn_url = parts[1].strip()
      key_map = {"waiting_btn1": "btn1", "waiting_btn2": "btn2", "waiting_btn3": "btn3"}
      key = key_map[state]
      data["broadcast_config"][f"{key}_text"] = btn_text
      data["broadcast_config"][f"{key}_url"] = btn_url
      save_data(data)
      del user_states[user_id]
      await message.reply(f"✅ تم تحديث الزر بنجاح:\nالنص: {btn_text}\nالرابط: {btn_url}", reply_markup=main_admin_keyboard())
    except Exception:
      await message.reply("⚠️ خطأ في الصيغة. يرجى الإرسال هكذا: `النص | الرابط`")


# ==========================================
# تشغيل الأغاني والبحث والتنزيل
# ==========================================
@app.on_message(filters.command(["تشغيل", "شغل", "بحث", "play"], prefixes=["/", "!", ""]) & filters.group)
async def play_music_handler(client, message):
  user_id = message.from_user.id
  sub_check = await check_forced_subscriptions(client, user_id)
  if sub_check is not True:
    await message.reply("⚠️ عليك الاشتراك في قنوات البوت الإجبارية أولاً لاستخدام أوامر التشغيل!", reply_markup=InlineKeyboardMarkup(sub_check))
    return

  query = message.text
  for prefix in ["تشغيل", "شغل", "بحث", "play"]:
    query = query.replace(prefix, "", 1)
  query = query.strip()

  if not query:
    await message.reply("⚠️ يرجى كتابة اسم الأغنية بعد الأمر.\nمثال: `تشغيل تخون بيه`")
    return

  msg = await message.reply(f"🔍 **جاري البحث وجلب الأغنية من يوتيوب:**\n🎵 {query}...")

  try:
    ydl_opts = {
        "format": "bestaudio/best",
        "default_search": "ytsearch1",
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(query, download=False)
      if "entries" in info:
        info = info["entries"][0]

      audio_url = info["url"]
      title = info.get("title", query)
      duration_sec = info.get("duration", 0)

      if duration_sec:
        mins, secs = divmod(int(duration_sec), 60)
        duration_str = f"{mins:02d}:{secs:02d}"
      else:
        duration_str = "03:45"

    chat_id = message.chat.id
    if not os.path.exists(SESSION_FILE):
      data_check = load_data()
      if not data_check["assistants"]:
        await msg.edit_text("❌ **لم يتم تسجيل أي حساب مساعد للبوت بعد! أضف مساعداً من لوحة المطور.**")
        return
      session_str = data_check["assistants"][0]
    else:
      with open(SESSION_FILE, "r") as f:
        session_str = f.read().strip()

    global call_py
    if call_py is None:
      assistant_client = Client(
          "assistant_session_name", api_id=API_ID, api_hash=API_HASH, session_string=session_str
      )
      await assistant_client.start()
      call_py = PyTgCalls(assistant_client)
      await call_py.start()

    await call_py.join_group_call(chat_id, AudioPiped(audio_url))

    data = load_data()
    bc = data["broadcast_config"]
    caption_text = (
        f"🎵 - تم تشغيل : <b>{title}</b>\n"
        f"⏱ - مدة التشغيل : <b>{duration_str}</b> #\n"
        f"🔊 - الحالة : يعمل الآن في المكالمة الصوتية 🟢"
    )

    await msg.delete()
    try:
      await message.reply_photo(
          photo=bc["media_url"], caption=caption_text, reply_markup=get_player_keyboard()
      )
    except Exception:
      await message.reply(caption_text, reply_markup=get_player_keyboard())

  except Exception as e:
    await msg.edit_text(f"❌ حدث خطأ أثناء التشغيل:\n`{e}`")


@app.on_message(filters.command(["تنزيل", "نزل", "download"], prefixes=["/", "!", ""]))
async def download_audio_handler(client, message):
  user_id = message.from_user.id
  sub_check = await check_forced_subscriptions(client, user_id)
  if sub_check is not True:
    await message.reply("⚠️ عليك الاشتراك في قنوات البوت الإجبارية أولاً للاستفادة من ميزة التنزيل!", reply_markup=InlineKeyboardMarkup(sub_check))
    return

  query = message.text
  for prefix in ["تنزيل", "نزل", "download"]:
    query = query.replace(prefix, "", 1)
  query = query.strip()

  if not query:
    await message.reply("⚠️ يرجى كتابة اسم الأغنية بعد الأمر للتنزيل.\nمثال: `تنزيل تخون بيه`")
    return

  msg = await message.reply(f"📥 **جاري تحميل وإرسال الملف الصوتي:**\n🎵 {query}...")

  try:
    ydl_opts = {
        "format": "bestaudio/best",
        "default_search": "ytsearch1",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
    }

    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
      ydl_opts["outtmpl"] = os.path.join(temp_dir, "%(id)s.%(ext)s")
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info:
          info = info["entries"][0]

        filename = ydl.prepare_filename(info)
        audio_file = os.path.splitext(filename)[0] + ".mp3"
        title = info.get("title", query)
        duration = info.get("duration", 0)

        await message.reply_audio(
            audio=audio_file, caption=f"🎵 **{title}**\n📥 تم التنزيل بنجاح عبر البوت.", duration=duration
        )
        await msg.delete()

  except Exception as e:
    await msg.edit_text(f"❌ حدث خطأ أثناء التنزيل:\n`{e}`")


async def main():
  await app.start()
  print("🚀 البوت يعمل بنجاح باستخدام متغيرات البيئة!")
  await idle()
  await app.stop()


if __name__ == "__main__":
  asyncio.get_event_loop().run_until_complete(main())
