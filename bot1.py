import asyncio
import json
import os
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
import yt_dlp

API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
SESSION_FILE = os.getenv("SESSION_FILE", "assistant_session.txt")
DATA_FILE = os.getenv("DATA_FILE", "bot_data.json")
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "123456789"))

app = Client("music_bot_main", api_id=API_ID, api_hash=API_HASH)
call_py = None


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
  }


def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def is_admin_or_dev(user_id):
  data = load_data()
  return user_id == data["developer_id"] or user_id in data["admins"]


def main_admin_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🔵 1- القسم المتقدم (المشرفين)", callback_data="adv_menu")],
      [InlineKeyboardButton("🟡 2- لوحة الإحصائيات العامة", callback_data="stats_menu")],
      [InlineKeyboardButton("🔴 4- إدارة الاشتراكات الإجبارية", callback_data="sub_menu")],
      [InlineKeyboardButton("❌ إغلاق القائمة", callback_data="close")],
  ])


def advanced_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🟢 إضافة مشرف", callback_data="add_admin")],
      [InlineKeyboardButton("🔴 إزالة مشرف", callback_data="remove_admin")],
      [InlineKeyboardButton("🟡 المشرفين المضافين", callback_data="list_admins")],
      [InlineKeyboardButton("🔙 رجوع للخطوة السابقة", callback_data="main_menu")],
  ])


def stats_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🔴 الأعضاء المحظورين", callback_data="stat_banned")],
      [InlineKeyboardButton("🟢 الأعضاء الذين حاضرين البوت", callback_data="stat_active")],
      [InlineKeyboardButton("🔵 الإحصائيات العامة", callback_data="stat_general")],
      [InlineKeyboardButton("🔙 رجوع للخطوة السابقة", callback_data="main_menu")],
  ])


def forced_sub_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🟢 إضافة قناة أو كروب عام (يجب أن يكون مشرفاً)", callback_data="sub_add_public")],
      [InlineKeyboardButton("🔵 إضافة بوت أو رابط سشويسل ميديا", callback_data="sub_add_social")],
      [InlineKeyboardButton("🟡 إضافة قناة أو كروب خاص", callback_data="sub_add_private")],
      [InlineKeyboardButton("🔙 رجوع للخطوة السابقة", callback_data="main_menu")],
  ])


@app.on_message(filters.command("start"))
async def start_command(client, message):
  user_id = message.from_user.id
  data = load_data()
  if user_id not in data["users"]:
    data["users"].append(user_id)
    save_data(data)

  bot_username = (await client.get_me()).username
  if is_admin_or_dev(user_id):
    await message.reply(
        f"مرحباً بك يا مطور/مشرف {message.from_user.mention} ⚡️\nإليك لوحة التحكم الخاصة بالإدارة:",
        reply_markup=main_admin_keyboard(),
    )
    return

  member_keyboard = InlineKeyboardMarkup([
      [InlineKeyboardButton("➕ اضفني لقناتك/كروبك", url=f"https://t.me/{bot_username}?startgroup=true")],
      [InlineKeyboardButton("🎵 شغل", url="https://t.me/YourDeveloperChannel")],
      [InlineKeyboardButton("❌ إغلاق", callback_data="close")],
  ])
  caption = (
      f"أهلاً بك عزيزي {message.from_user.mention} في بوت الأغاني والمكالمات الصوتية 🎧\n\n"
      "اختر أحد الأزرار أدناه للبدء:"
  )
  await message.reply(caption, reply_markup=member_keyboard)


@app.on_callback_query()
async def panel_callback_handler(client, callback_query):
  data_cb = callback_query.data
  user_id = callback_query.from_user.id

  if data_cb == "close":
    await callback_query.message.delete()
    return
  if not is_admin_or_dev(user_id):
    await callback_query.answer("⚠️ هذه الأزرار مخصصة للمشرفين والمطور فقط!", show_alert=True)
    return

  if data_cb == "main_menu":
    await callback_query.message.edit_text("🎛️ **لوحة التحكم الرئيسية للإدارة:**", reply_markup=main_admin_keyboard())
  elif data_cb == "adv_menu":
    await callback_query.message.edit_text("⚙️ **القسم المتقدم:**\nاختر العملية المطلوبة:", reply_markup=advanced_keyboard())
  elif data_cb == "stats_menu":
    await callback_query.message.edit_text("📊 **لوحة الإحصائيات العامة:**", reply_markup=stats_keyboard())
  elif data_cb == "sub_menu":
    await callback_query.message.edit_text("📢 **إدارة الاشتراكات الإجبارية:**", reply_markup=forced_sub_keyboard())
  elif data_cb == "list_admins":
    data = load_data()
    admins = data["admins"]
    text = f"👑 **المطور الأساسي:** `{data['developer_id']}`\n\n🛡️ **المشرفون المضافون:**\n"
    text += "".join(f"• `{adm}`\n" for adm in admins) if admins else "لا يوجد مشرفون مضافون حالياً."
    await callback_query.message.edit_text(text, reply_markup=advanced_keyboard())
  elif data_cb == "stat_general":
    data = load_data()
    text = (
        f"📊 **الإحصائيات العامة للبوت:**\n\n"
        f"👥 إجمالي المستخدمين: `{len(data['users'])}`\n"
        f"🛡️ عدد المشرفين: `{len(data['admins'])}`\n"
        f"🚫 الأعضاء المحظورين: `{len(data['banned_users'])}`\n"
        f"📢 قنوات الاشتراك الإجباري: `{len(data['forced_subs'])}`"
    )
    await callback_query.message.edit_text(text, reply_markup=stats_keyboard())
  else:
    await callback_query.answer("⚙️ هذا القسم قيد التطوير حالياً.", show_alert=True)


@app.on_message(filters.command(["تشغيل", "شغل", "play"], prefixes=["/", "!", ""]) & filters.group)
async def play_music_handler(client, message):
  query = message.text
  for prefix in ["تشغيل", "شغل", "play"]:
    query = query.replace(prefix, "", 1)
  query = query.strip()

  if not query:
    await message.reply("⚠️ اكتب اسم الأغنية بعد الأمر.\nمثال: `تشغيل تخون بيه`")
    return

  msg = await message.reply(f"🔍 **جاري البحث بدون كوكيز:**\n🎵 {query}...")

  try:
    # يعمل بدون cookies.txt. YouTube قد يحظر بعض الطلبات، لذلك نعرض رسالة مفهومة.
    ydl_opts = {
        "format": "bestaudio/best",
        "default_search": "ytsearch1",
        "quiet": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web_safari", "tv_embedded"]
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(f"ytsearch1:{query}", download=False)
      entries = info.get("entries") or []
      if not entries or not entries[0]:
        await msg.edit_text("❌ لم يتم العثور على نتيجة. جرّب اسم أغنية آخر.")
        return
      info = entries[0]
      audio_url = info.get("url")
      if not audio_url:
        await msg.edit_text("❌ لم يتم العثور على رابط صوت صالح لهذه الأغنية.")
        return
      title = info.get("title", query)
      duration_sec = info.get("duration") or 0
      mins, secs = divmod(int(duration_sec), 60)
      duration_str = f"{mins:02d}:{secs:02d}" if duration_sec else "غير معروف"

    if not os.path.exists(SESSION_FILE):
      await msg.edit_text("❌ ملف assistant_session.txt غير موجود. سجّل حساب المساعد أولاً.")
      return

    global call_py
    if call_py is None:
      with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session_str = f.read().strip()
      assistant_client = Client(
          "assistant_session_name", api_id=API_ID, api_hash=API_HASH, session_string=session_str
      )
      await assistant_client.start()
      call_py = PyTgCalls(assistant_client)
      await call_py.start()

    await call_py.join_group_call(message.chat.id, AudioPiped(audio_url))
    player_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("تخطي ⏭", callback_data="skip"),
            InlineKeyboardButton("إنهاء ⏹", callback_data="end"),
            InlineKeyboardButton("إيقاف ⏸", callback_data="pause"),
        ],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close")],
    ])
    await msg.edit_text(
        f"🎵 - تم تشغيل: <b>{title}</b>\n⏱ - المدة: <b>{duration_str}</b>\n🔊 - الحالة: يعمل الآن 🟢",
        reply_markup=player_keyboard,
    )

  except yt_dlp.utils.DownloadError:
    await msg.edit_text(
        "❌ YouTube رفض الطلب لأنه يريد التحقق من أنك لست روبوتاً.\n"
        "جرّب أغنية أخرى أو رابطاً مباشراً؛ هذا الإصدار يعمل بدون كوكيز، لكن YouTube لا يضمن السماح لكل الطلبات."
    )
  except Exception as error:
    print(f"playback error: {error}")
    await msg.edit_text("❌ تعذر تشغيل الأغنية حالياً. تأكد من FFmpeg وملف جلسة المساعد ثم جرّب مرة أخرى.")


async def main():
  await app.start()
  print("🚀 البوت يعمل بدون cookies.txt")
  await idle()
  await app.stop()


if __name__ == "__main__":
  asyncio.get_event_loop().run_until_complete(main())
