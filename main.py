import os
import logging
from pyrogram import Client, filters
from pymongo import MongoClient
from config import Config

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Setup
client = MongoClient(Config.MONGO_DB_URI)
db = client["file_to_link_bot"]
users_collection = db["users"]

# Initialize Bot
bot = Client(
    "FileToLinkBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# /start command
@bot.on_message(filters.command("start"))
async def start(bot, message):
    user_id = message.from_user.id
    users_collection.update_one({"_id": user_id}, {"$set": {"username": message.from_user.username}}, upsert=True)
    await message.reply_text("✅ **Bot is alive!**\nSend me a file to generate a direct download link.")

# /stats command
@bot.on_message(filters.command("stats"))
async def stats(bot, message):
    user_count = users_collection.count_documents({})
    await message.reply_text(f"📊 **Total Users:** `{user_count}`")

# Handle Files
@bot.on_message(filters.document | filters.video | filters.audio)
async def handle_file(bot, message):
    try:
        file_id = message.document.file_id if message.document else (
            message.video.file_id if message.video else message.audio.file_id
        )
        file_name = message.document.file_name if message.document else (
            message.video.file_name if message.video else message.audio.file_name
        )

        # Get Public Link
        file_link = f"{Config.FQDN}/download/{file_id}"

        await message.reply_text(
            f"✅ **Your File Link:**\n📥 Download: [Click Here]({file_link})\n📂 File: `{file_name}`",
            disable_web_page_preview=True
        )
        logger.info(f"Generated link: {file_link} for file: {file_name}")

    except Exception as e:
        logger.error(f"Error generating file link: {str(e)}")
        await message.reply_text("❌ Error generating link. Please try again.")

if __name__ == "__main__":
    bot.run()
``
