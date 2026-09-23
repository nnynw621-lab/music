import asyncio
import json
import os
import tempfile
from contextlib import suppress

from pyrogram import Client, filters, idle
from pyrogram.errors import SessionPasswordNeeded
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
import yt_dlp

# Secrets must be supplied by Railway Variables.
def required_env(name, cast=str):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    try:
        return cast(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid environment variable: {name}") from exc

API_ID = required_env("API_ID", int)
API_HASH = required_env("API_HASH")
BOT_TOKEN = required_env("BOT_TOKEN")
DEVELOPER_ID = required_env("DEVELOPER_ID", int)

SESSION_FILE = "assistant_session.txt"
DATA_FILE = "bot_data.json"
app = Client("music_bot_main", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call_py = None
assistant_client = None
user_states = {}
temp_logins = {}
active_chats = set()


def default_data():
    return {
        "developer_id": DEVELOPER_ID, "admins": [], "banned_users": [], "users": [],
        "forced_subs": [], "assistants": [],
        "broadcast_config": {
            "media_url": "https://envs.sh/i/XYZ.jpg", "btn1_text": "SG SOURCE",
            "btn1_url": "https://t.me/YourDeveloperChannel", "btn2_text": "ADD",
            "btn2_url": "https://t.me/YourBot?startgroup=true", "btn3_text": "X",
            "btn3_url": "https://t.me/YourChannel",
        },
    }


def load_data():
    data = default_data()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                saved = json.load(file)
            for key, value in saved.items():
                if key == "broadcast_config":
                    data[key].update(value or {})
                else:
                    data[key] = value
        except (OSError, json.JSONDecodeError):
            pass
    return data


def save_data(data):
    directory = os.path.dirname(DATA_FILE) or "."
    fd, temp_path = tempfile.mkstemp(prefix="bot-data-", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, DATA_FILE)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def is_admin_or_dev(user_id):
    data = load_data()
    return user_id == data["developer_id"] or user_id in data["admins"]


def one_button(text, callback):
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callback)]])


def main_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ المشرفون", callback_data="adv_menu"), InlineKeyboardButton("📊 الإحصائيات", callback_data="stats_menu")],
        [InlineKeyboardButton("📢 الاشتراك الإجباري", callback_data="sub_menu"), InlineKeyboardButton("🎨 إعدادات النشر", callback_data="broadcast_menu")],
        [InlineKeyboardButton("🤖 حسابات المساعدين", callback_data="assistants_menu")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close")],
    ])


def advanced_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin"), InlineKeyboardButton("➖ إزالة مشرف", callback_data="remove_admin")], [InlineKeyboardButton("📋 القائمة", callback_data="list_admins"), InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])


def stats_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚫 المحظورون", callback_data="stat_banned"), InlineKeyboardButton("👥 المستخدمون", callback_data="stat_active")], [InlineKeyboardButton("📊 عام", callback_data="stat_general"), InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])


def forced_sub_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("➕ قناة عامة", callback_data="sub_add_public")], [InlineKeyboardButton("➕ رابط اجتماعي", callback_data="sub_add_social")], [InlineKeyboardButton("➕ قناة خاصة", callback_data="sub_add_private")], [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])


def broadcast_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🖼️ الصورة", callback_data="edit_media")], [InlineKeyboardButton("🔗 الزر الأول", callback_data="edit_btn1"), InlineKeyboardButton("🔗 الزر الثاني", callback_data="edit_btn2")], [InlineKeyboardButton("🔗 الزر الثالث", callback_data="edit_btn3")], [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])


def assistants_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("➕ إضافة مساعد", callback_data="add_assistant_interactive")], [InlineKeyboardButton("📋 عرض المساعدين", callback_data="list_assistants")], [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])


def player_keyboard(data):
    bc = data["broadcast_config"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏹ إنهاء", callback_data="end"), InlineKeyboardButton("⏸ إيقاف", callback_data="pause"), InlineKeyboardButton("▶ استئناف", callback_data="resume")],
        [InlineKeyboardButton(bc["btn1_text"], url=bc["btn1_url"])],
        [InlineKeyboardButton(bc["btn2_text"], url=bc["btn2_url"])],
        [InlineKeyboardButton(bc["btn3_text"], url=bc["btn3_url"])],
    ])


async def check_forced_subscriptions(client, user_id):
    data = load_data()
    if not data["forced_subs"] or is_admin_or_dev(user_id):
        return True
    rows = []
    for sub in data["forced_subs"]:
        try:
            member = await client.get_chat_member(sub["chat_id"], user_id)
            if member.status in ("left", "banned"):
                rows.append([InlineKeyboardButton(f"🔔 اشترك في {sub.get('title', 'القناة')}", url=sub.get("link"))])
        except Exception:
            rows.append([InlineKeyboardButton(f"🔔 اشترك في {sub.get('title', 'القناة')}", url=sub.get("link"))])
    if rows:
        rows.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")])
        return rows
    return True


@app.on_message(filters.command("start"))
async def start_command(client, message):
    data = load_data()
    user_id = message.from_user.id
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)
    check = await check_forced_subscriptions(client, user_id)
    if check is not True:
        await message.reply("⚠️ اشترك بالقنوات المطلوبة أولاً:", reply_markup=InlineKeyboardMarkup(check))
        return
    if is_admin_or_dev(user_id):
        await message.reply("🎛️ لوحة تحكم الإدارة", reply_markup=main_admin_keyboard())
        return
    username = (await client.get_me()).username
    bc = data["broadcast_config"]
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("➕ أضفني لمجموعتك", url=f"https://t.me/{username}?startgroup=true")], [InlineKeyboardButton(bc["btn1_text"], url=bc["btn1_url"])], [InlineKeyboardButton("❌ إغلاق", callback_data="close")]])
    await message.reply(f"أهلاً بك {message.from_user.mention} في بوت الأغاني 🎧", reply_markup=keyboard)


@app.on_callback_query()
async def callback_handler(client, query):
    action, user_id = query.data, query.from_user.id
    if action == "close":
        await query.message.delete(); return
    if action == "check_sub":
        check = await check_forced_subscriptions(client, user_id)
        if check is True:
            await query.answer("✅ تم التحقق بنجاح", show_alert=True)
            await query.message.edit_text("أرسل /start للبدء")
        else:
            await query.answer("⚠️ ما زال الاشتراك ناقصاً", show_alert=True)
        return
    if action in {"end", "pause", "resume"}:
        if not is_admin_or_dev(user_id):
            await query.answer("⚠️ هذا الزر للمشرف فقط", show_alert=True); return
        chat_id = query.message.chat.id
        if call_py is None or chat_id not in active_chats:
            await query.answer("لا توجد مكالمة نشطة", show_alert=True); return
        try:
            if action == "end":
                await call_py.leave_group_call(chat_id)
                active_chats.discard(chat_id)
            elif action == "pause":
                await call_py.pause(chat_id)
            else:
                await call_py.resume(chat_id)
            await query.answer("✅ تم التنفيذ")
        except Exception as exc:
            await query.answer(f"تعذر التنفيذ: {str(exc)[:150]}", show_alert=True)
        return
    if not is_admin_or_dev(user_id):
        await query.answer("⚠️ هذه اللوحة للمشرفين فقط", show_alert=True); return
    screens = {"main_menu": ("🎛️ لوحة الإدارة", main_admin_keyboard()), "adv_menu": ("⚙️ إدارة المشرفين", advanced_keyboard()), "stats_menu": ("📊 الإحصائيات", stats_keyboard()), "sub_menu": ("📢 الاشتراك الإجباري", forced_sub_keyboard()), "broadcast_menu": ("🎨 إعدادات النشر", broadcast_keyboard()), "assistants_menu": ("🤖 المساعدون", assistants_keyboard())}
    if action in screens:
        text, markup = screens[action]; await query.message.edit_text(text, reply_markup=markup); return
    if action == "list_admins":
        data = load_data(); await query.message.edit_text("المطور: `{}`\nالمشرفون: {}".format(data["developer_id"], ", ".join(map(str, data["admins"])) or "لا يوجد"), reply_markup=advanced_keyboard()); return
    if action.startswith("stat_"):
        data = load_data(); text = f"المستخدمون: {len(data['users'])}\nالمحظورون: {len(data['banned_users'])}\nالاشتراكات: {len(data['forced_subs'])}"; await query.message.edit_text(text, reply_markup=stats_keyboard()); return
    prompts = {"add_admin": ("أرسل ID المشرف:", "waiting_add_admin"), "remove_admin": ("أرسل ID المراد إزالته:", "waiting_remove_admin"), "sub_add_public": ("أرسل: المعرف | الرابط | الاسم", "waiting_sub_public"), "sub_add_social": ("أرسل: الرابط | الاسم", "waiting_sub_social"), "sub_add_private": ("أرسل: الرابط | الاسم", "waiting_sub_private"), "edit_media": ("أرسل رابط الصورة:", "waiting_media"), "edit_btn1": ("أرسل: النص | الرابط", "waiting_btn1"), "edit_btn2": ("أرسل: النص | الرابط", "waiting_btn2"), "edit_btn3": ("أرسل: النص | الرابط", "waiting_btn3"), "add_assistant_interactive": ("أرسل رقم الهاتف مع رمز الدولة:", "waiting_assistant_phone")}
    if action in prompts:
        text, state = prompts[action]; user_states[user_id] = state; await query.message.edit_text(text, reply_markup=one_button("🔙 إلغاء", "main_menu")); return
    if action == "list_assistants":
        count = len(load_data()["assistants"]); await query.message.edit_text(f"عدد المساعدين: {count}", reply_markup=assistants_keyboard()); return
    await query.answer("هذا الزر غير متاح حالياً")


@app.on_message(filters.text & ~filters.command(["start"]))
async def admin_input(client, message):
    user_id = message.from_user.id
    if not is_admin_or_dev(user_id) or user_id not in user_states:
        return
    state, data = user_states[user_id], load_data()
    try:
        if state == "waiting_add_admin":
            value = int(message.text.strip()); data["admins"] = list(dict.fromkeys(data["admins"] + [value]))
        elif state == "waiting_remove_admin":
            value = int(message.text.strip()); data["admins"] = [x for x in data["admins"] if x != value]
        elif state == "waiting_media": data["broadcast_config"]["media_url"] = message.text.strip()
        elif state in ("waiting_btn1", "waiting_btn2", "waiting_btn3"):
            text, url = [x.strip() for x in message.text.split("|", 1)]; key = state[-1]; data["broadcast_config"][f"btn{key}_text"] = text; data["broadcast_config"][f"btn{key}_url"] = url
        elif state.startswith("waiting_sub_"):
            parts = [x.strip() for x in message.text.split("|")]
            if len(parts) < 2: raise ValueError
            if state == "waiting_sub_public": data["forced_subs"].append({"chat_id": parts[0], "link": parts[1], "title": parts[2] if len(parts) > 2 else "قناة"})
            else: data["forced_subs"].append({"chat_id": "@forced_social", "link": parts[0], "title": parts[1]})
        else:
            return
        save_data(data); user_states.pop(user_id, None); await message.reply("✅ تم الحفظ", reply_markup=main_admin_keyboard())
    except (ValueError, IndexError):
        await message.reply("⚠️ الصيغة غير صحيحة، حاول مرة أخرى.")


async def get_ytdlp_info(query, download=False, outtmpl=None):
    options = {"format": "bestaudio/best", "default_search": "ytsearch1", "quiet": True, "noplaylist": True}
    if outtmpl: options["outtmpl"] = outtmpl
    if download: options["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(query, download=download)
        return info["entries"][0] if info.get("entries") else info, ydl


@app.on_message(filters.command(["تشغيل", "شغل", "بحث", "play"], prefixes=["/", "!", ""]) & filters.group)
async def play_music(client, message):
    check = await check_forced_subscriptions(client, message.from_user.id)
    if check is not True: await message.reply("⚠️ اشترك أولاً", reply_markup=InlineKeyboardMarkup(check)); return
    query = message.text
    for prefix in ("تشغيل", "شغل", "بحث", "play"): query = query.replace(prefix, "", 1)
    query = query.strip()
    if not query: await message.reply("⚠️ اكتب اسم الأغنية"); return
    status = await message.reply("🔍 جاري البحث...")
    try:
        info, _ = await get_ytdlp_info(query); session = load_data()["assistants"][0] if load_data()["assistants"] else (open(SESSION_FILE).read().strip() if os.path.exists(SESSION_FILE) else None)
        if not session: await status.edit_text("❌ أضف حساب مساعد أولاً"); return
        global call_py, assistant_client
        if call_py is None:
            assistant_client = Client("assistant_session", api_id=API_ID, api_hash=API_HASH, session_string=session); await assistant_client.start(); call_py = PyTgCalls(assistant_client); await call_py.start()
        await call_py.join_group_call(message.chat.id, AudioPiped(info["url"])); active_chats.add(message.chat.id)
        await status.edit_text(f"🎵 يعمل الآن: {info.get('title', query)}", reply_markup=player_keyboard(load_data()))
    except Exception as exc: await status.edit_text(f"❌ تعذر التشغيل: `{str(exc)[:500]}`")


@app.on_message(filters.command(["تنزيل", "نزل", "download"], prefixes=["/", "!", ""]))
async def download_audio(client, message):
    check = await check_forced_subscriptions(client, message.from_user.id)
    if check is not True: await message.reply("⚠️ اشترك أولاً", reply_markup=InlineKeyboardMarkup(check)); return
    query = message.text
    for prefix in ("تنزيل", "نزل", "download"): query = query.replace(prefix, "", 1)
    query = query.strip()
    if not query: await message.reply("⚠️ اكتب اسم الأغنية"); return
    status = await message.reply("📥 جاري التحميل...")
    try:
        with tempfile.TemporaryDirectory() as directory:
            info, ydl = await get_ytdlp_info(query, True, os.path.join(directory, "%(id)s.%(ext)s"))
            audio = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
            await message.reply_audio(audio=audio, caption=f"🎵 {info.get('title', query)}")
        await status.delete()
    except Exception as exc: await status.edit_text(f"❌ تعذر التنزيل: `{str(exc)[:500]}`")


async def main():
    await app.start(); print("🚀 البوت يعمل"); await idle(); await app.stop()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
