import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import FloodWait

# إعداد السجل (Logging)
logging.basicConfig(level=logging.INFO)

# المتغيرات البيئية الأساسية (تؤخذ من Railway)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# تهيئة البوت الأساسي (صانع البوتات)
app = Client(
    "MusicBotMaker",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ذاكرة مؤقتة للحقوق، الوسائط، والإعلانات
settings = {
    "rights_text": "سورس قطر",
    "rights_link": "https://t.me/X_e_5bot",
    "media_type": "photo",  # photo / sticker
    "media_id": "" # آيدي الوسائط أو الملصق المخصص
}

user_bots_db = {} # قاعدة بيانات مؤقتة لتخزين البوتات المصنوعة للمستخدمين

# رسالة البداية والواجهة الرئيسية
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    welcome_text = (
        f"أهلاً بك عزيزي {name} في منصة **صانع بوتات ميوزك قطر**.\n\n"
        "من خلال هذه المنصة يمكنك إنشاء بوت ميوزك خاص بك بروابطك وحقوقك وبشكل تلقائي بالكامل!\n\n"
        "اختر ما يناسبك من الأزرار في الأسفل:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡️ صنع بوت مجاني", callback_data="create_free")],
        [InlineKeyboardButton("💎 صنع بوت VIP", callback_data="create_vip")],
        [InlineKeyboardButton("🤖 بوتاتي المصنوعة", callback_data="my_bots")],
        [InlineKeyboardButton("📢 قناة السورس والإعلانات", url="https://t.me/X_e_5bot")],
        [InlineKeyboardButton("👨‍💻 المطور", user_id=OWNER_ID)]
    ])
    
    if settings["media_type"] == "photo" and settings.get("media_id"):
        try:
            await message.reply_photo(photo=settings["media_id"], caption=welcome_text, reply_markup=keyboard)
            return
        except:
            pass
    elif settings["media_type"] == "sticker" and settings.get("media_id"):
        try:
            await message.reply_sticker(sticker=settings["media_id"])
        except:
            pass
            
    await message.reply_text(text=welcome_text, reply_markup=keyboard)

# معالجة الأزرار الشفافة
@app.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "create_free":
        steps_text = (
            "**خطوات صنع بوت مجاني:**\n\n"
            "1. اذهب إلى البوت الرسمي: @BotFather\n"
            "2. أرسل الأمر `/newbot`\n"
            "3. اختر اسماً للبوت، ثم يوزراً (يجب أن ينتهي بـ `bot`).\n"
            "4. انسخ **التوكن (Token)** وأرسله هنا في الحوار.\n\n"
            "أرسل التوكن الآن أو اضغط إلغاء:"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="back_home")]])
        await callback_query.message.edit_text(steps_text, reply_markup=keyboard)
        
    elif data == "my_bots":
        bots = user_bots_db.get(user_id, [])
        if not bots:
            text = "عذراً، أنت لم تقم بصنع أي بوت حتى الآن."
        else:
            text = f"**قائمة بوتاتك المصنوعة ({len(bots)}):**\n\n" + "\n".join([f"• @{b}" for b in bots])
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_home")]])
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        
    elif data == "back_home":
        await callback_query.message.delete()
        await start_command(client, callback_query.message)

# أمر لوحة المطور الخاصة
@app.on_message(filters.command("admin") & filters.user(OWNER_ID))
async def developer_panel(client: Client, message: Message):
    dev_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ تعديل أزرار الحقوق", callback_data="edit_rights")],
        [InlineKeyboardButton("🖼 تعيين صورة/ملصق ترحيبي", callback_data="set_media")],
        [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="bot_stats")]
    ])
    await message.reply_text("**أهلاً بك يا مطورنا العظيم في لوحة التحكم:**", reply_markup=dev_keyboard)

if __name__ == "__main__":
    app.run()
