import os
import pymongo
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")

# Initialize bot
bot = Client("FileBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["telegram_file_bot"]
files_collection = db["files"]
users_collection = db["users"]

# Start Command
@bot.on_message(filters.command("start"))
def start(client, message):
    args = message.command
    user_id = message.from_user.id

    # Store user info in MongoDB
    user_data = {"user_id": user_id, "username": message.from_user.username}
    users_collection.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)

    # If a file_id is provided, fetch & send the file
    if len(args) > 1:
        file_id = args[1]
        file_data = files_collection.find_one({"file_id": file_id})
        if file_data:
            client.send_document(chat_id=message.chat.id, document=file_id, caption=file_data["file_name"])
        else:
            message.reply_text("⚠️ File not found!")
    else:
        message.reply_text("✅ Bot is alive!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Stats", callback_data="stats")]
        ]))

# Stats Command
@bot.on_message(filters.command("stats"))
def stats(client, message):
    user_count = users_collection.count_documents({})
    file_count = files_collection.count_documents({})
    message.reply_text(f"📊 Total Users: {user_count}\n📂 Total Files: {file_count}")

# File Handler
@bot.on_message(filters.document | filters.video | filters.audio)
def file_handler(client, message):
    file_id = message.document.file_id if message.document else \
              message.video.file_id if message.video else \
              message.audio.file_id

    file_name = message.document.file_name if message.document else \
                message.video.file_name if message.video else \
                message.audio.file_name

    # Store file in MongoDB
    files_collection.update_one({"file_id": file_id}, {"$set": {"file_name": file_name}}, upsert=True)

    # Generate file link
    file_link = f"https://t.me/{client.me.username}?start={file_id}"

    buttons = [
        [InlineKeyboardButton("▶️ Stream", url=f"https://t.me/{client.me.username}/{file_id}")],
        [InlineKeyboardButton("📥 Download", url=file_link)],
        [InlineKeyboardButton("🔗 Get File Link", url=file_link)]
    ]

    message.reply_text(f"**File:** {file_name}\n📥 [Download File]({file_link})",
                       reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# Flask Web Server (to keep Render service alive)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Run bot and Flask server in parallel
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()
