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
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")

app = Client("music_bot_main", api_id=API_ID, api_hash=API_HASH)
call_py = None


def load_data():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return {"developer_id": DEVELOPER_ID, "admins": [], "banned_users": [], "users": [], "forced_subs": []}


def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


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
      [InlineKeyboardButton("🟢 الأعضاء النشطون", callback_data="stat_active")],
      [InlineKeyboardButton("🔵 الإحصائيات العامة", callback_data="stat_general")],
      [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
  ])


def forced_sub_keyboard():
  return InlineKeyboardMarkup([
      [InlineKeyboardButton("🟢 إضافة قناة أو كروب عام", callback_data="sub_add_public")],
      [InlineKeyboardButton("🔵 إضافة رابط", callback_data="sub_add_social")],
      [InlineKeyboardButton("🟡 إضافة قناة أو كروب خاص", callback_data="sub_add_private")],
      [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
  ])


@app.on_message(filters.command("start"))
async def start_command(client, message):
  user_id = message.from_user.id
  data = load_data()
  if user_id not in data["users"]:
    data["users"].append(user_id)
    save_data(data)

  if is_admin_or_dev(user_id):
    await message.reply(
        f"مرحباً بك يا مطور/مشرف {message.from_user.mention} ⚡️\nإليك لوحة التحكم:",
        reply_markup=main_admin_keyboard(),
    )
    return

  bot_username = (await client.get_me()).username
  keyboard = InlineKeyboardMarkup([
      [InlineKeyboardButton("➕ أضفني لمجموعتك", url=f"https://t.me/{bot_username}?startgroup=true")],
      [InlineKeyboardButton("❌ إغلاق", callback_data="close")],
  ])
  await message.reply(
      f"أهلاً بك عزيزي {message.from_user.mention} في بوت الأغاني 🎧\n\nاختر أحد الأزرار للبدء:",
      reply_markup=keyboard,
  )


@app.on_callback_query()
async def panel_callback_handler(client, callback_query):
  data_cb = callback_query.data
  user_id = callback_query.from_user.id
  if data_cb == "close":
    await callback_query.message.delete()
    return
  if not is_admin_or_dev(user_id):
    await callback_query.answer("⚠️ هذه الأزرار للمشرفين والمطور فقط!", show_alert=True)
    return
  if data_cb == "main_menu":
    await callback_query.message.edit_text("🎛️ لوحة التحكم الرئيسية:", reply_markup=main_admin_keyboard())
  elif data_cb == "adv_menu":
    await callback_query.message.edit_text("⚙��� القسم المتقدم:", reply_markup=advanced_keyboard())
  elif data_cb == "stats_menu":
    await callback_query.message.edit_text("📊 الإحصائيات العامة:", reply_markup=stats_keyboard())
  elif data_cb == "sub_menu":
    await callback_query.message.edit_text("📢 إدارة الاشتراكات الإجبارية:", reply_markup=forced_sub_keyboard())
  elif data_cb == "list_admins":
    data = load_data()
    admins = data["admins"]
    text = f"👑 المطور الأساسي: `{data['developer_id']}`\n\n🛡️ المشرفون:\n"
    text += "".join(f"• `{admin}`\n" for admin in admins) if admins else "لا يوجد مشرفون حالياً."
    await callback_query.message.edit_text(text, reply_markup=advanced_keyboard())
  elif data_cb == "stat_general":
    data = load_data()
    await callback_query.message.edit_text(
        f"📊 الإحصائيات:\n\n👥 المستخدمون: `{len(data['users'])}`\n"
        f"🛡️ المشرفون: `{len(data['admins'])}`\n"
        f"🚫 المحظورون: `{len(data['banned_users'])}`\n"
        f"📢 الاشتراكات: `{len(data['forced_subs'])}`",
        reply_markup=stats_keyboard(),
    )
  else:
    await callback_query.answer("⚙️ هذا القسم قيد التطوير.", show_alert=True)


@app.on_message(filters.command(["تشغيل", "شغل", "play"], prefixes=["/", "!", ""]) & filters.group)
async def play_music_handler(client, message):
  query = message.text
  for prefix in ["تشغيل", "شغل", "play"]:
    query = query.replace(prefix, "", 1)
  query = query.strip()
  if not query:
    await message.reply("⚠️ اكتب اسم الأغنية بعد الأمر.\nمثال: `تشغيل تخون بيه`")
    return

  msg = await message.reply(f"🔍 جاري البحث عن: {query}...")
  try:
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web_safari", "tv_embedded"]}},
    }
    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
      ydl_opts["cookiefile"] = COOKIES_FILE
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(f"ytsearch1:{query}", download=False)
      entries = info.get("entries") or []
      if not entries or not entries[0]:
        await msg.edit_text("❌ لم يتم العثور على الأغنية.")
        return
      info = entries[0]
      audio_url = info.get("url")
      if not audio_url:
        await msg.edit_text("❌ لم يتم العثور على رابط صوت صالح.")
        return
      title = info.get("title", query)
      duration = info.get("duration") or 0
      minutes, seconds = divmod(int(duration), 60)
      duration_text = f"{minutes:02d}:{seconds:02d}" if duration else "غير معروف"

    if not os.path.isfile(SESSION_FILE):
      await msg.edit_text("❌ ملف assistant_session.txt غير موجود.")
      return
    global call_py
    if call_py is None:
      with open(SESSION_FILE, "r", encoding="utf-8") as file:
        session_string = file.read().strip()
      assistant = Client("assistant_session_name", api_id=API_ID, api_hash=API_HASH, session_string=session_string)
      await assistant.start()
      call_py = PyTgCalls(assistant)
      await call_py.start()
    await call_py.join_group_call(message.chat.id, AudioPiped(audio_url))
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("تخطي ⏭", callback_data="skip"), InlineKeyboardButton("إنهاء ⏹", callback_data="end"), InlineKeyboardButton("إيقاف ⏸", callback_data="pause")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close")],
    ])
    await msg.edit_text(f"🎵 تم التشغيل: <b>{title}</b>\n⏱ المدة: <b>{duration_text}</b>\n🔊 يعمل الآن 🟢", reply_markup=keyboard)
  except yt_dlp.utils.DownloadError:
    await msg.edit_text("❌ رفض YouTube الطلب. تأكد من cookies.txt أو جرّب أغنية أخرى.")
  except Exception as error:
    print(f"playback error: {error}")
    await msg.edit_text("❌ تعذر تشغيل الأغنية حالياً. تحقق من FFmpeg والجلسة ثم حاول مجدداً.")


async def main():
  await app.start()
  print("🚀 البوت يعمل؛ cookies.txt اختياري")
  await idle()
  await app.stop()


if __name__ == "__main__":
  asyncio.get_event_loop().run_until_complete(main())
