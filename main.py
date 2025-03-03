import os
import pymongo
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Initialize bot
bot = Client("FileBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["telegram_file_bot"]
users_collection = db["users"]

# Start Command
@bot.on_message(filters.command("start"))
def start(client, message):
    user_id = message.from_user.id
    user_data = {"user_id": user_id, "username": message.from_user.username}
    users_collection.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
    message.reply_text("✅ Bot is alive!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]))

# Stats Command
@bot.on_message(filters.command("stats"))
def stats(client, message):
    user_count = users_collection.count_documents({})
    message.reply_text(f"📊 Total Users: {user_count}")

# File Handler
@bot.on_message(filters.document | filters.video | filters.audio)
def file_handler(client, message):
    file_id = message.document.file_id if message.document else message.video.file_id if message.video else message.audio.file_id
    file_name = message.document.file_name if message.document else message.video.file_name if message.video else message.audio.file_name
    file_link = f"https://t.me/{client.me.username}?start={file_id}"
    
    buttons = [
        [InlineKeyboardButton("▶️ Stream", url=f"https://vlc://{file_link}")],
        [InlineKeyboardButton("📥 Download", url=file_link)],
        [InlineKeyboardButton("🔗 Get File Link", url=file_link)]
    ]
    
    message.reply_text(f"**File:** {file_name}", reply_markup=InlineKeyboardMarkup(buttons))

bot.run()
